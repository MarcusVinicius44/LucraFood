"""Etapa 1 do LucraFood: foto do cardápio -> lista estruturada de pratos.

Decisões de projeto (boas para contar na entrevista):
- A IA só EXTRAI. Ela não calcula nada; contas ficam no Python (calculos.py).
- A saída é validada com Pydantic. Se vier JSON inválido, mandamos o erro de
  volta para o modelo e tentamos de novo uma única vez.
- Preço ilegível vira `null` em vez de chute: o dono confere na tela.
"""
import base64
import json
import re
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from .cliente import MODELO_VISAO, get_cliente

PROMPT_SISTEMA = """Você extrai cardápios de restaurantes brasileiros a partir de fotos.
Responda SOMENTE com um objeto JSON no formato:
{"pratos": [{"nome": str, "descricao": str|null, "categoria": str|null, "preco": number|null}]}

Regras:
- Um item por prato/produto vendido. Ignore telefones, endereços, horários e slogans.
- "preco" em reais como número (ex.: 24.9). Se houver tamanhos (P/M/G), crie um item
  por tamanho com o tamanho no nome (ex.: "Pizza Calabresa (G)").
- Se o preço estiver ilegível ou ausente, use null. NUNCA invente preço.
- "categoria" é o título da seção do cardápio (ex.: "Lanches", "Bebidas"), se houver.
- Mantenha os nomes como estão escritos, corrigindo só erros óbvios de leitura."""


class PratoExtraido(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    preco: Optional[Decimal] = Field(default=None, ge=0, le=10000)

    @field_validator("preco", mode="before")
    @classmethod
    def normalizar_preco(cls, v):
        # Aceita "R$ 24,90", "24,90", 24.9 ...
        if isinstance(v, str):
            limpo = v.replace("R$", "").replace(" ", "")
            if "," in limpo:
                limpo = limpo.replace(".", "").replace(",", ".")
            return limpo or None
        return v


class CardapioExtraido(BaseModel):
    pratos: list[PratoExtraido]


def _imagem_para_data_url(conteudo: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"


def _extrair_json(texto: str) -> str:
    """Remove blocos de raciocínio (<think>...</think>) e cercas ``` se vierem."""
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.MULTILINE).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    return texto[inicio : fim + 1] if inicio != -1 and fim != -1 else texto


def extrair_cardapio(imagem: bytes, mime: str = "image/jpeg", cliente=None) -> CardapioExtraido:
    cliente = cliente or get_cliente()
    mensagens = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extraia todos os pratos deste cardápio."},
                {"type": "image_url", "image_url": {"url": _imagem_para_data_url(imagem, mime)}},
            ],
        },
    ]

    ultimo_erro = None
    for _tentativa in range(2):
        resposta = cliente.chat.completions.create(
            model=MODELO_VISAO,
            messages=mensagens,
            response_format={"type": "json_object"},
            temperature=0,
        )
        texto = resposta.choices[0].message.content or ""
        try:
            return CardapioExtraido.model_validate(json.loads(_extrair_json(texto)))
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens += [
                {"role": "assistant", "content": texto},
                {"role": "user", "content": f"Seu JSON não passou na validação: {erro}. Corrija e responda só o JSON."},
            ]
    raise ValueError(f"A IA não devolveu um cardápio válido: {ultimo_erro}")
