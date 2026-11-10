"""Ficha técnica a partir de um texto livre do dono ("pão, hambúrguer de 150g, 2 fatias de queijo").

Mesmo padrão da foto do cardápio:
- A IA só LÊ: nome do ingrediente, qual ingrediente do cadastro é (ou null), quantidade e
  unidade como estão escritas. Não converte, não soma, não calcula custo.
- A saída é validada com Pydantic, com uma nova tentativa devolvendo o erro ao modelo.
- O Python confere o id (id que não está no cadastro vira null), converte kg -> g e l -> ml
  (calculos.converter_unidade) e marca o que o dono precisa revisar. Nada é salvo aqui.
"""
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from .. import calculos
from .cliente import config, get_cliente
from .extracao import Uso, _chamar, _extrair_json

PROMPT_FICHA = """Você lê a ficha técnica (receita) de UM prato de restaurante, escrita pelo dono em texto livre,
e liga cada ingrediente mencionado a um ingrediente já cadastrado.
Responda SOMENTE com um objeto JSON no formato:
{"itens": [{"nome_lido": str, "ingrediente": int|null, "quantidade": number|null, "unidade": str|null}]}

Regras:
- Um item por ingrediente mencionado, na ordem do texto. Ignore modo de preparo e comentários.
- "nome_lido": o ingrediente como o dono escreveu, sem a quantidade.
- "ingrediente": o "id" de um item da lista de CADASTRADOS que seja o mesmo produto (vale sinônimo
  ou nome mais curto, ex.: "muçarela" para "Queijo muçarela"). Se nenhum for claramente o mesmo
  produto, ou se houver dúvida entre dois, use null. NUNCA use um id que não está na lista.
- "quantidade": o número escrito no texto, sem converter nem fazer conta ("duas" -> 2, "meio" -> 0.5,
  "1,5" -> 1.5). Se o texto não diz quanto, null.
- "unidade": a unidade escrita, em minúsculas e no singular: "g", "kg", "ml", "l", ou palavras como
  "fatia", "colher", "xícara", "pitada". Se o texto só conta peças inteiras do próprio ingrediente
  (ex.: "3 ovos"), use "un". Se não há unidade, null.
- Não converta unidades e não estime pesos: "2 fatias" fica quantidade 2, unidade "fatia".
- Se o texto não fala de nenhum ingrediente, responda {"itens": []}."""

TEXTO_MAX = 1000

# Como o dono escreve -> unidade de calculos.FATORES_UNIDADE. Palavras fora daqui ("fatia",
# "colher"...) são unidades informais: a quantidade fica para o dono informar no cadastro.
SINONIMOS_UNIDADE = {
    "mg": "mg", "miligrama": "mg",
    "g": "g", "gr": "g", "grs": "g", "grama": "g", "gramas": "g",
    "kg": "kg", "quilo": "kg", "quilos": "kg", "kilo": "kg", "kilos": "kg", "quilograma": "kg",
    "ml": "ml", "mililitro": "ml", "mililitros": "ml",
    "l": "l", "litro": "l", "litros": "l", "lt": "l",
    "un": "un", "und": "un", "unid": "un", "unidade": "un", "unidades": "un",
}

# Motivos para o dono revisar o item antes de confirmar.
SEM_INGREDIENTE = "sem_ingrediente"  # nada correspondente no cadastro
SEM_QUANTIDADE = "sem_quantidade"  # o texto não diz quanto
SEM_UNIDADE = "sem_unidade"  # número sem unidade para um ingrediente em g ou ml
UNIDADE_INFORMAL = "unidade_informal"  # fatia, colher...: sem conversão exata
UNIDADE_INCOMPATIVEL = "unidade_incompativel"  # ex.: ml para um ingrediente cadastrado em g
INGREDIENTE_REPETIDO = "ingrediente_repetido"  # mais de um item ligado ao mesmo ingrediente
NOME_DIFERENTE = "nome_diferente"  # ligado a um cadastro de nome diferente ("leite" -> "Leite integral")
MEDIDA_SALVA = "medida_salva"  # medida caseira convertida com o que o dono ensinou ("1 fatia = 18 g")


PALAVRAS_DE_LIGACAO = {"de", "da", "do", "das", "dos", "e", "com", "em", "a", "o"}


def _sem_acento(texto: str) -> list[str]:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", sem_acento)


def _singular(p: str) -> str:
    if p.endswith(("oes", "aes")):  # pães, limões
        return p[:-3] + "ao"
    if p.endswith(("res", "zes")) and len(p) > 4:  # hambúrgueres, nozes, colheres
        return p[:-2]
    if len(p) > 3 and p.endswith("s"):
        return p[:-1]
    return p


def _palavras(texto: str) -> set[str]:
    """Palavras sem acento, minúsculas e no singular simples ("Ovos" -> "ovo")."""
    return {_singular(p) for p in _sem_acento(texto) if p not in PALAVRAS_DE_LIGACAO}


def chave_medida(medida: Optional[str]) -> str:
    """Forma única de guardar uma medida caseira: "Fatias" -> "fatia", "colheres de sopa" ->
    "colher de sopa". Vazia ("") quando não há medida."""
    return " ".join(_singular(p) for p in _sem_acento(medida))[:30]


def nome_confere(nome_lido: str, nome_cadastro: str, cadastro: list[dict] = ()) -> bool:
    """Regra C (versão branda, 10/11): o nome lido confere com o ingrediente ligado quando
    - contém todas as palavras do cadastro ("peito de frango grelhado" -> "Peito de frango"); ou
    - é um nome mais curto que só cabe nele ("batata" -> "Batata congelada", se não houver outra
      batata no cadastro).
    Sinônimo ("hambúrguer" -> "Blend bovino"), erro de digitação ("qeijo") ou nome curto com mais
    de um candidato ("leite" com Leite integral e Leite condensado) continuam ligados, mas o dono
    confirma."""
    lido, alvo = _palavras(nome_lido), _palavras(nome_cadastro)
    if not lido or not alvo:
        return False
    if alvo <= lido:
        return True
    if lido <= alvo:
        candidatos = [c for c in cadastro if lido <= _palavras(c["nome"])]
        return len(candidatos) <= 1
    return False


class TextoSemIngredientes(Exception):
    """O texto não menciona nenhum ingrediente (equivalente da foto ilegível)."""


def _normalizar_numero(v):
    if isinstance(v, str):
        v = v.strip().replace(" ", "")
        if "," in v:
            v = v.replace(".", "").replace(",", ".")
        return v or None
    return v


class ItemLido(BaseModel):
    """Um item como a IA devolve."""

    nome_lido: str = Field(min_length=1, max_length=120)
    ingrediente: Optional[int] = None
    quantidade: Optional[Decimal] = Field(default=None, gt=0, le=1_000_000)
    unidade: Optional[str] = Field(default=None, max_length=30)

    @field_validator("quantidade", mode="before")
    @classmethod
    def normalizar_quantidade(cls, v):
        return _normalizar_numero(v)


class FichaLida(BaseModel):
    itens: list[ItemLido]


@dataclass
class ItemExtraido:
    """Item pronto para o dono revisar. `quantidade` está em `unidade`: a do cadastro, ou, para
    ingrediente fora do cadastro, a unidade-base da medida escrita (kg -> g, l -> ml)."""

    nome_lido: str
    ingrediente: Optional[dict]  # {"id", "nome", "unidade"} do cadastro, ou None
    quantidade_lida: Optional[Decimal]
    unidade_lida: Optional[str]
    quantidade: Optional[Decimal]
    unidade: Optional[str] = None
    motivos: list[str] = field(default_factory=list)
    estimativa: Optional[str] = None  # de onde veio a quantidade, quando não foi escrita direto

    @property
    def precisa_confirmar(self) -> bool:
        return bool(self.motivos)

    def para_json(self) -> dict:
        return {
            "nome_lido": self.nome_lido,
            "ingrediente": self.ingrediente,
            "quantidade_lida": None if self.quantidade_lida is None else str(self.quantidade_lida),
            "unidade_lida": self.unidade_lida,
            "quantidade": None if self.quantidade is None else str(self.quantidade),
            "unidade": self.unidade,
            "precisa_confirmar": self.precisa_confirmar,
            "motivos": self.motivos,
            "estimativa": self.estimativa,
        }


def _unidade_canonica(unidade: Optional[str]) -> Optional[str]:
    if not unidade:
        return None
    return SINONIMOS_UNIDADE.get(unidade.strip().lower().rstrip("."))


def _numero(valor: Decimal) -> str:
    return f"{valor.normalize():f}".replace(".", ",")


def resolver(itens: list[ItemLido], cadastro: list[dict], medidas: Optional[dict] = None) -> list[ItemExtraido]:
    """Confere o que a IA leu contra o cadastro e converte as quantidades (sem IA).

    `medidas` = {(id do ingrediente, chave_medida): quantidade na unidade do cadastro}, o que o
    dono já ensinou na conversa ("1 fatia de Queijo prato = 18 g"). Com ela, "2 fatias" vira 36 g,
    marcado como `medida_salva` para o dono conferir."""
    medidas = medidas or {}
    por_id = {c["id"]: c for c in cadastro}
    vistos = set()
    resultado = []
    for lido in itens:
        motivos = []
        ingrediente = por_id.get(lido.ingrediente)  # id fora do cadastro (inventado) vira None
        if ingrediente is None:
            motivos.append(SEM_INGREDIENTE)
        elif ingrediente["id"] in vistos:
            motivos.append(INGREDIENTE_REPETIDO)
        else:
            vistos.add(ingrediente["id"])
        if ingrediente is not None and not nome_confere(lido.nome_lido, ingrediente["nome"], cadastro):
            motivos.append(NOME_DIFERENTE)

        quantidade = None
        estimativa = None
        canonica = _unidade_canonica(lido.unidade)
        # Unidade em que `quantidade` sai: a do cadastro; sem ingrediente, a unidade-base da
        # medida escrita (150 g de um item fora do cadastro continua 150 g, para o dono cadastrar).
        destino = ingrediente["unidade"] if ingrediente else None
        if lido.quantidade is None:
            motivos.append(SEM_QUANTIDADE)
            # "pão" sem número: assume 1 unidade, mas o dono confirma (o motivo fica marcado).
            if destino == "un" and canonica in (None, "un"):
                quantidade = Decimal("1.000")
        elif lido.unidade is None:
            if destino == "un":
                quantidade = calculos.converter_unidade(lido.quantidade, "un", "un")
            else:
                motivos.append(SEM_UNIDADE)
        elif canonica is None:
            por_medida = medidas.get((ingrediente["id"], chave_medida(lido.unidade))) if ingrediente else None
            if por_medida is None:
                motivos.append(UNIDADE_INFORMAL)
            else:
                quantidade = calculos.quantidade_de_medidas(lido.quantidade, por_medida, destino, destino)
                motivos.append(MEDIDA_SALVA)
                estimativa = (
                    f"{_numero(lido.quantidade)} × {_numero(por_medida)} {destino} por {chave_medida(lido.unidade)} "
                    f"= {_numero(quantidade)} {destino} (medida que você ensinou)"
                )
        else:
            alvo = destino or calculos.FATORES_UNIDADE[canonica][0]
            try:
                quantidade = calculos.converter_unidade(lido.quantidade, canonica, alvo)
                destino = alvo
            except ValueError:
                motivos.append(UNIDADE_INCOMPATIVEL)

        resultado.append(
            ItemExtraido(
                nome_lido=lido.nome_lido.strip(),
                ingrediente=ingrediente,
                quantidade_lida=lido.quantidade,
                unidade_lida=lido.unidade,
                quantidade=quantidade,
                unidade=destino,
                motivos=motivos,
                estimativa=estimativa,
            )
        )
    return resultado


def _mensagem_usuario(texto: str, prato: str, cadastro: list[dict]) -> str:
    lista = [{"id": c["id"], "nome": c["nome"], "unidade": c["unidade"]} for c in cadastro]
    return (
        f"Prato: {prato}\n"
        f"Ingredientes CADASTRADOS: {json.dumps(lista, ensure_ascii=False)}\n"
        f"Texto do dono:\n{texto}"
    )


def extrair_ficha(
    texto, cadastro, prato="", cliente=None, esperar=time.sleep, uso=None, medidas=None
) -> list[ItemExtraido]:
    """Texto livre -> itens para o dono revisar. Levanta TextoSemIngredientes se nada foi lido,
    ValueError se a IA não devolver JSON válido nem na segunda tentativa."""
    uso = uso if uso is not None else Uso()
    cliente = cliente or get_cliente()
    mensagens = [
        {"role": "system", "content": PROMPT_FICHA},
        {"role": "user", "content": _mensagem_usuario(texto, prato, cadastro)},
    ]
    ultimo_erro = None
    for _tentativa in range(2):
        resposta = _chamar(
            cliente,
            esperar,
            None,
            uso,
            model=config().modelo,
            messages=mensagens,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=config().max_tokens,
        )
        if getattr(resposta, "usage", None):
            uso.entrada += resposta.usage.prompt_tokens or 0
            uso.saida += resposta.usage.completion_tokens or 0
        conteudo = resposta.choices[0].message.content or ""
        try:
            lida = FichaLida.model_validate(json.loads(_extrair_json(conteudo)))
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens += [
                {"role": "assistant", "content": conteudo},
                {"role": "user", "content": f"Seu JSON não passou na validação: {erro}. Corrija e responda só o JSON."},
            ]
            continue
        if not lida.itens:
            raise TextoSemIngredientes("nenhum ingrediente encontrado no texto")
        return resolver(lida.itens, cadastro, medidas)
    raise ValueError(f"A IA não devolveu uma ficha válida: {ultimo_erro}")
