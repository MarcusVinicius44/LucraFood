"""Ficha técnica a partir de um texto livre do dono ("pão, hambúrguer de 150g, 2 fatias de queijo").

Mesmo padrão da foto do cardápio:
- A IA só LÊ: nome do ingrediente, qual ingrediente do cadastro é (ou null), quantidade e
  unidade como estão escritas. Não converte, não soma, não calcula custo.
- A saída é validada com Pydantic, com uma nova tentativa devolvendo o erro ao modelo.
- O Python confere o id (id que não está no cadastro vira null), converte kg -> g e l -> ml
  (calculos.converter_unidade) e marca o que o dono precisa revisar. Nada é salvo aqui.
"""
import json
import time
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
    """Item pronto para o dono revisar. `quantidade` já está na unidade do cadastro (ou None)."""

    nome_lido: str
    ingrediente: Optional[dict]  # {"id", "nome", "unidade"} do cadastro, ou None
    quantidade_lida: Optional[Decimal]
    unidade_lida: Optional[str]
    quantidade: Optional[Decimal]
    motivos: list[str] = field(default_factory=list)

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
            "unidade": self.ingrediente["unidade"] if self.ingrediente else None,
            "precisa_confirmar": self.precisa_confirmar,
            "motivos": self.motivos,
        }


def _unidade_canonica(unidade: Optional[str]) -> Optional[str]:
    if not unidade:
        return None
    return SINONIMOS_UNIDADE.get(unidade.strip().lower().rstrip("."))


def resolver(itens: list[ItemLido], cadastro: list[dict]) -> list[ItemExtraido]:
    """Confere o que a IA leu contra o cadastro e converte as quantidades (sem IA)."""
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

        quantidade = None
        canonica = _unidade_canonica(lido.unidade)
        destino = ingrediente["unidade"] if ingrediente else None
        if lido.quantidade is None:
            motivos.append(SEM_QUANTIDADE)
            # "pão" sem número: assume 1 unidade, mas o dono confirma (o motivo fica marcado).
            if destino == "un" and canonica in (None, "un"):
                quantidade = Decimal("1.000")
        elif lido.unidade is None:
            if destino == "un":
                quantidade = calculos.converter_unidade(lido.quantidade, "un", "un")
            elif destino is not None:
                motivos.append(SEM_UNIDADE)
        elif canonica is None:
            motivos.append(UNIDADE_INFORMAL)
        elif destino is not None:
            try:
                quantidade = calculos.converter_unidade(lido.quantidade, canonica, destino)
            except ValueError:
                motivos.append(UNIDADE_INCOMPATIVEL)

        resultado.append(
            ItemExtraido(
                nome_lido=lido.nome_lido.strip(),
                ingrediente=ingrediente,
                quantidade_lida=lido.quantidade,
                unidade_lida=lido.unidade,
                quantidade=quantidade,
                motivos=motivos,
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


def extrair_ficha(texto, cadastro, prato="", cliente=None, esperar=time.sleep, uso=None) -> list[ItemExtraido]:
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
        return resolver(lida.itens, cadastro)
    raise ValueError(f"A IA não devolveu uma ficha válida: {ultimo_erro}")
