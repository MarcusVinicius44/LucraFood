"""Etapa 1 do LucraFood: foto do cardápio -> lista estruturada de pratos.

Decisões de projeto (boas para contar na entrevista):
- A IA só EXTRAI. Ela não calcula nada; contas ficam no Python (calculos.py).
- A saída é validada com Pydantic. Se vier JSON inválido, mandamos o erro de
  volta para o modelo e tentamos de novo uma única vez.
- Preço ilegível vira `null` em vez de chute: o dono confere na tela.
- Cardápios grandes são lidos em faixas (faixas.py); cada faixa recebe o contexto
  das anteriores e as chamadas são espaçadas para respeitar o limite de tokens/minuto.
"""
import base64
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from openai import RateLimitError
from pydantic import BaseModel, Field, ValidationError, field_validator

from .cliente import MODELO_VISAO, get_cliente
from .faixas import juntar, recortar
from .limitador import LimitadorSaida

PROMPT_SISTEMA = """Você extrai cardápios de restaurantes brasileiros a partir de fotos.
Responda SOMENTE com um objeto JSON no formato:
{"colunas_preco": [str]|null,
 "pratos": [{"nome": str, "descricao": str|null, "categoria": str|null, "preco": number|null, "precos": [number|null]|null}]}

Regras:
- Um item por prato/produto vendido. Ignore telefones, endereços, horários e slogans.
- "preco" em reais como número (ex.: 24.9). Prato com UM preço: use "preco" e deixe "precos" null.
- Prato com VÁRIOS preços em colunas (tamanhos P/M/G, 30/40/50 cm etc.): faça UM item só,
  "preco" null e "precos" com os valores na ordem das colunas (null onde ilegível).
  Em "colunas_preco" escreva os rótulos das colunas na mesma ordem (ex.: ["P","M","G"]);
  se a imagem não mostra rótulos, "colunas_preco" null.
- Se o preço estiver ilegível ou ausente, use null. NUNCA invente preço.
- "categoria" é o título da seção do cardápio (ex.: "Lanches", "Bebidas"), se houver.
- Mantenha os nomes como estão escritos, corrigindo só erros óbvios de leitura."""


def _normalizar_preco(v):
    # Aceita "R$ 24,90", "24,90", 24.9 ...
    if isinstance(v, str):
        limpo = v.replace("R$", "").replace(" ", "")
        if "," in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        return limpo or None
    return v


class PratoExtraido(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    preco: Optional[Decimal] = Field(default=None, ge=0, le=10000)
    # Só na resposta bruta do modelo: vários preços por coluna. Depois de _expandir vira None.
    precos: Optional[list[Optional[Decimal]]] = None

    @field_validator("preco", mode="before")
    @classmethod
    def normalizar_preco(cls, v):
        return _normalizar_preco(v)

    @field_validator("precos", mode="before")
    @classmethod
    def normalizar_precos(cls, v):
        return [_normalizar_preco(x) for x in v] if isinstance(v, list) else v


class CardapioExtraido(BaseModel):
    pratos: list[PratoExtraido]
    colunas_preco: Optional[list[str]] = None


def _imagem_para_data_url(conteudo: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"


def _extrair_json(texto: str) -> str:
    """Remove blocos de raciocínio (<think>...</think>) e cercas ``` se vierem."""
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.MULTILINE).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    return texto[inicio : fim + 1] if inicio != -1 and fim != -1 else texto


TENTATIVAS_COTA = 3
ESPERA_PADRAO_429 = 60  # segundos, quando o Groq não manda o cabeçalho retry-after
# Teto de tokens de SAÍDA declarado em cada chamada. O Groq recusa (429) pedidos cujo teto
# passa do limite por minuto da conta (1000), então fica abaixo disso.
MAX_TOKENS_SAIDA = 900


class FalhaDeCota(Exception):
    """Cota/limite de taxa (429) esgotado mesmo após esperar e tentar de novo.

    Separada de ValueError de propósito: não é erro de extração, é limite do provedor.
    """


class SaidaCortada(ValueError):
    """A resposta bateu no teto de tokens (finish_reason == "length"): o JSON veio incompleto."""


@dataclass
class Uso:
    """Tokens consumidos (soma de todas as chamadas feitas para uma foto)."""

    entrada: int = 0
    saida: int = 0
    maior_chamada: int = 0  # entrada + saída da chamada mais pesada (o limite por minuto vale por chamada)


def _espera_429(erro: RateLimitError) -> float:
    try:
        return max(float(erro.response.headers["retry-after"]), 0)
    except (KeyError, TypeError, ValueError, AttributeError):
        return ESPERA_PADRAO_429


def _chamar(cliente, esperar, limitador=None, **kwargs):
    """Chama a API; em 429 espera o retry-after e tenta de novo (até TENTATIVAS_COTA).

    Com `limitador`, antes de cada chamada espera caber no orçamento de tokens de saída
    por minuto e, depois, registra os tokens realmente gastos.
    """
    for tentativa in range(1, TENTATIVAS_COTA + 1):
        if limitador:
            limitador.aguardar(kwargs["max_tokens"])
        try:
            resposta = cliente.chat.completions.create(**kwargs)
        except RateLimitError as erro:
            if tentativa == TENTATIVAS_COTA:
                raise FalhaDeCota(f"Cota excedida após {TENTATIVAS_COTA} tentativas: {erro}") from erro
            esperar(_espera_429(erro))
            continue
        if limitador:
            usage = getattr(resposta, "usage", None)
            limitador.registrar((usage.completion_tokens if usage else None) or kwargs["max_tokens"])
        return resposta


def _expandir(cardapio: CardapioExtraido, colunas_herdadas=None):
    """Transforma pratos com `precos` em lista em um item por coluna: "Pizza X (G)".

    Devolve (cardapio sem `precos`, colunas usadas). Sem rótulo legível, usa "tamanho N".
    """
    colunas = cardapio.colunas_preco or colunas_herdadas
    planos = []
    for p in cardapio.pratos:
        if p.precos and p.preco is None:
            if len(p.precos) == 1:
                planos.append(p.model_copy(update={"preco": p.precos[0], "precos": None}))
                continue
            for i, valor in enumerate(p.precos):
                rotulo = colunas[i] if colunas and i < len(colunas) else f"tamanho {i + 1}"
                planos.append(p.model_copy(update={"nome": f"{p.nome} ({rotulo})", "preco": valor, "precos": None}))
        else:
            planos.append(p.model_copy(update={"precos": None}))
    return CardapioExtraido(pratos=planos, colunas_preco=colunas), colunas


def _texto_contexto(k: int, n: int, pratos_anteriores: list, colunas) -> str:
    """Resumo do que as faixas anteriores já mostraram, para a próxima faixa não perder o fio."""
    categoria = next((p.categoria for p in reversed(pratos_anteriores) if p.categoria), None)
    partes = [
        f"Esta imagem é a faixa {k + 1} de {n} de um mesmo cardápio. O topo repete um pouco do fim da "
        "faixa anterior: liste esses pratos mesmo assim (as repetições são removidas depois)."
    ]
    if categoria:
        partes.append(
            f'Categoria em andamento: "{categoria}". Use-a em pratos que apareçam antes de um novo título de seção.'
        )
    if colunas:
        partes.append(
            f"Colunas de preço do cardápio, em ordem: {json.dumps(colunas, ensure_ascii=False)}. "
            'Se esta faixa mostrar preços em colunas sem repetir o cabeçalho, use "precos" nessa ordem '
            'e repita esses rótulos em "colunas_preco".'
        )
    return " ".join(partes)


def extrair_cardapio(imagem: bytes, mime: str = "image/jpeg", cliente=None, faixas: int = 1) -> CardapioExtraido:
    return extrair_cardapio_com_uso(imagem, mime, cliente, faixas=faixas)[0]


def extrair_cardapio_com_uso(
    imagem: bytes,
    mime: str = "image/jpeg",
    cliente=None,
    esperar=time.sleep,
    faixas: int = 1,
    limitador: Optional[LimitadorSaida] = None,
    max_tokens: int = MAX_TOKENS_SAIDA,
) -> tuple[CardapioExtraido, Uso]:
    """Com faixas > 1, lê a foto em pedaços (uma chamada por faixa) e junta os pratos.

    Cada faixa recebe o contexto das anteriores (categoria em andamento e rótulos das colunas
    de preço). `limitador` (opcional) espaça as chamadas para respeitar tokens de saída/minuto.
    """
    pedacos = recortar(imagem, n=faixas) if faixas > 1 else [imagem]
    mime_pedaco = "image/jpeg" if faixas > 1 else mime
    uso, listas, colunas = Uso(), [], None
    for k, pedaco in enumerate(pedacos):
        anteriores = [p for lista in listas for p in lista]
        contexto = _texto_contexto(k, len(pedacos), anteriores, colunas) if k else ""
        bruto, uso_faixa = _extrair_imagem(pedaco, mime_pedaco, cliente, esperar, contexto, limitador, max_tokens)
        plano, colunas = _expandir(bruto, colunas)
        uso.entrada += uso_faixa.entrada
        uso.saida += uso_faixa.saida
        uso.maior_chamada = max(uso.maior_chamada, uso_faixa.maior_chamada)
        listas.append(plano.pratos)
    return CardapioExtraido(pratos=juntar(listas), colunas_preco=colunas), uso


def _extrair_imagem(imagem, mime, cliente, esperar, contexto="", limitador=None, max_tokens=MAX_TOKENS_SAIDA):
    cliente = cliente or get_cliente()
    uso = Uso()
    texto_usuario = "Extraia todos os pratos deste cardápio."
    if contexto:
        texto_usuario += " " + contexto
    mensagens = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": texto_usuario},
                {"type": "image_url", "image_url": {"url": _imagem_para_data_url(imagem, mime)}},
            ],
        },
    ]

    ultimo_erro = None
    for _tentativa in range(2):
        resposta = _chamar(
            cliente,
            esperar,
            limitador,
            model=MODELO_VISAO,
            messages=mensagens,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=max_tokens,
        )
        if getattr(resposta, "usage", None):
            entrada, saida = resposta.usage.prompt_tokens or 0, resposta.usage.completion_tokens or 0
            uso.entrada += entrada
            uso.saida += saida
            uso.maior_chamada = max(uso.maior_chamada, entrada + saida)
        if getattr(resposta.choices[0], "finish_reason", None) == "length":
            raise SaidaCortada(f"A resposta foi cortada no teto de {max_tokens} tokens de saída (JSON incompleto).")
        texto = resposta.choices[0].message.content or ""
        try:
            return CardapioExtraido.model_validate(json.loads(_extrair_json(texto))), uso
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens += [
                {"role": "assistant", "content": texto},
                {"role": "user", "content": f"Seu JSON não passou na validação: {erro}. Corrija e responda só o JSON."},
            ]
    raise ValueError(f"A IA não devolveu um cardápio válido: {ultimo_erro}")
