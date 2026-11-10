"""Ficha em conversa: o sistema pergunta o que faltou na ficha lida do texto ("quanto pesa a fatia
de queijo?") e o dono responde do jeito dele ("uns 20 gramas").

Divisão de trabalho (a IA não faz conta):
- O Python escolhe QUAL item perguntar e escreve a pergunta (`proxima_pergunta`), a partir dos
  motivos de revisão de ia/ficha.py.
- A IA só INTERPRETA a resposta: número e unidade como foram ditos, ou "não sabe"/"não entendi"
  (`interpretar_resposta`).
- O Python faz a conta e converte (`aplicar_resposta`, usando calculos). Nada é salvo aqui: o dono
  confere a ficha no fim e confirma, como na ficha por texto.

Sem estado no servidor: a cada rodada o front manda os itens como estão e a lista de itens pulados.
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
from .ficha import (
    SEM_QUANTIDADE,
    SEM_UNIDADE,
    UNIDADE_INCOMPATIVEL,
    UNIDADE_INFORMAL,
    _normalizar_numero,
    _unidade_canonica,
)

# Tipos de pergunta (o motivo que a resposta resolve).
POR_MEDIDA = "por_medida"  # "2 fatias": quanto dá 1 fatia?
TOTAL = "total"  # sem quantidade: quanto vai no total?
UNIDADE = "unidade"  # "150 de carne": 150 o quê?
CONVERTER = "converter"  # "50 g de óleo" com óleo em ml: quanto dá em ml?

MOTIVO_DO_TIPO = {
    POR_MEDIDA: UNIDADE_INFORMAL,
    TOTAL: SEM_QUANTIDADE,
    UNIDADE: SEM_UNIDADE,
    CONVERTER: UNIDADE_INCOMPATIVEL,
}

NOME_UNIDADE = {"g": "gramas", "ml": "ml", "un": "unidades"}
RESPOSTA_MAX = 200

PROMPT_RESPOSTA = """Você ajuda a montar a ficha técnica de um prato. O sistema fez UMA pergunta ao dono do
restaurante sobre a quantidade de um ingrediente, e você lê a resposta dele.
Responda SOMENTE com um objeto JSON no formato:
{"entendeu": bool, "nao_sabe": bool, "quantidade": number|null, "unidade": str|null}

Regras:
- "quantidade": o número que o dono disse, sem converter nem fazer conta ("uns 20" -> 20,
  "meio" -> 0.5, "1,5" -> 1.5, "duzentos" -> 200). Aproximações ("uns", "mais ou menos") valem.
- "unidade": a unidade que o dono disse, em minúsculas e no singular ("g", "kg", "ml", "l", "un"),
  ou a palavra que ele usou ("colher", "xícara"). Se ele só confirmou a unidade sugerida na
  pergunta ("isso", "sim", "gramas"), devolva essa unidade e quantidade null. Se ele disse só o
  número, unidade null.
- Se ele disse que não sabe ou quer pular: {"entendeu": true, "nao_sabe": true, ...} com
  quantidade e unidade null.
- Se a resposta não tem quantidade nem unidade, ou fala de outra coisa: "entendeu": false.
- Se ele deu um intervalo ("entre 20 e 30"), use o número do meio só se for óbvio; senão "entendeu": false.
- Não invente números que o dono não disse."""


class RespostaLida(BaseModel):
    entendeu: bool
    nao_sabe: bool = False
    quantidade: Optional[Decimal] = Field(default=None, gt=0, le=1_000_000)
    unidade: Optional[str] = Field(default=None, max_length=30)

    @field_validator("quantidade", mode="before")
    @classmethod
    def normalizar_quantidade(cls, v):
        return _normalizar_numero(v)


@dataclass
class ItemConversa:
    """Uma linha da ficha em revisão, como o front manda."""

    chave: int
    nome_lido: str
    ingrediente: Optional[dict]  # {"id", "nome", "unidade"} do cadastro, ou None
    quantidade: Optional[Decimal]  # já na unidade do cadastro; None = falta
    quantidade_lida: Optional[Decimal] = None
    unidade_lida: Optional[str] = None
    motivos: list[str] = field(default_factory=list)


@dataclass
class Pergunta:
    chave: int
    tipo: str
    texto: str

    def para_json(self):
        return {"chave": self.chave, "tipo": self.tipo, "texto": self.texto}


def _numero(valor: Decimal) -> str:
    texto = f"{valor.normalize():f}"
    return texto.replace(".", ",")


def _tipo_da_pergunta(item: ItemConversa) -> Optional[str]:
    """Que pergunta resolve o item, ou None se não há o que perguntar (já tem quantidade, não tem
    ingrediente do cadastro, ou o motivo não se resolve conversando)."""
    if item.ingrediente is None or item.quantidade is not None:
        return None
    if UNIDADE_INFORMAL in item.motivos:
        return POR_MEDIDA
    if UNIDADE_INCOMPATIVEL in item.motivos:
        return CONVERTER
    if SEM_UNIDADE in item.motivos:
        return UNIDADE
    return TOTAL  # ingrediente ligado e sem quantidade, seja qual for o motivo


def texto_da_pergunta(item: ItemConversa, tipo: str) -> str:
    nome = item.ingrediente["nome"]
    unidade = item.ingrediente["unidade"]
    medida = item.unidade_lida or "medida"
    if tipo == POR_MEDIDA:
        if unidade == "un":
            return f"Quantas unidades de {nome} dá 1 {medida}?"
        return f"Quanto dá mais ou menos 1 {medida} de {nome}, em {NOME_UNIDADE[unidade]}?"
    if tipo == CONVERTER:
        escrito = f"{_numero(item.quantidade_lida)} {item.unidade_lida}" if item.quantidade_lida else item.unidade_lida
        return f"{nome} está cadastrado em {NOME_UNIDADE[unidade]}. Quanto dá {escrito}, em {NOME_UNIDADE[unidade]}?"
    if tipo == UNIDADE:
        return f"Você escreveu {_numero(item.quantidade_lida)} de {nome}. São {NOME_UNIDADE[unidade]}?"
    return f"Quanto vai de {nome} nesta receita? (em {NOME_UNIDADE[unidade]})"


def proxima_pergunta(itens: list[ItemConversa], pulados=()) -> Optional[Pergunta]:
    """A primeira linha (na ordem da ficha) que uma pergunta resolve; None quando acabou."""
    for item in itens:
        if item.chave in pulados:
            continue
        tipo = _tipo_da_pergunta(item)
        if tipo:
            return Pergunta(item.chave, tipo, texto_da_pergunta(item, tipo))
    return None


class RespostaInvalida(Exception):
    """A resposta foi entendida, mas não serve (ex.: "2 colheres" quando a pergunta pede gramas)."""


@dataclass
class Atualizacao:
    chave: int
    quantidade: Decimal
    unidade: str
    motivos: list[str]
    origem: str  # de onde veio o número, para a etiqueta no front

    def para_json(self):
        return {
            "chave": self.chave,
            "quantidade": str(self.quantidade),
            "unidade": self.unidade,
            "motivos": self.motivos,
            "origem": self.origem,
        }


def aplicar_resposta(item: ItemConversa, tipo: str, lida: RespostaLida) -> Atualizacao:
    """Converte a resposta lida pela IA na quantidade do item (conta feita em calculos)."""
    destino = item.ingrediente["unidade"]
    unidade = _unidade_canonica(lida.unidade)
    if lida.unidade and unidade is None:
        raise RespostaInvalida(f"Preciso da quantidade em {NOME_UNIDADE[destino]}, não em {lida.unidade}.")
    if tipo == UNIDADE:
        quantidade = lida.quantidade if lida.quantidade is not None else item.quantidade_lida
        unidade = unidade or destino
    else:
        quantidade = lida.quantidade
        unidade = unidade or destino  # só o número: vale a unidade que a pergunta pediu
    if quantidade is None:
        raise RespostaInvalida(f"Não entendi o número. Quanto dá, em {NOME_UNIDADE[destino]}?")
    try:
        if tipo == POR_MEDIDA:
            medidas = item.quantidade_lida or Decimal(1)
            total = calculos.quantidade_de_medidas(medidas, quantidade, unidade, destino)
            origem = (
                f"{_numero(medidas)} × {_numero(quantidade)} {unidade} por {item.unidade_lida or 'medida'} "
                f"= {_numero(total)} {destino} (você informou)"
            )
        else:
            total = calculos.converter_unidade(quantidade, unidade, destino)
            origem = f"{_numero(total)} {destino} (você informou)"
    except ValueError:
        raise RespostaInvalida(f"Preciso da quantidade em {NOME_UNIDADE[destino]}. Quanto dá?")
    resolvidos = {MOTIVO_DO_TIPO[tipo], SEM_QUANTIDADE, SEM_UNIDADE, UNIDADE_INFORMAL, UNIDADE_INCOMPATIVEL}
    motivos = [m for m in item.motivos if m not in resolvidos]
    return Atualizacao(item.chave, total, destino, motivos, origem)


def interpretar_resposta(pergunta: str, resposta: str, cliente=None, esperar=time.sleep, uso=None) -> RespostaLida:
    """Resposta do dono -> número e unidade como ditos. ValueError se a IA não devolver JSON
    válido nem na segunda tentativa."""
    uso = uso if uso is not None else Uso()
    cliente = cliente or get_cliente()
    mensagens = [
        {"role": "system", "content": PROMPT_RESPOSTA},
        {"role": "user", "content": f"Pergunta do sistema: {pergunta}\nResposta do dono: {resposta}"},
    ]
    ultimo_erro = None
    for _tentativa in range(2):
        r = _chamar(
            cliente,
            esperar,
            None,
            uso,
            model=config().modelo,
            messages=mensagens,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        if getattr(r, "usage", None):
            uso.entrada += r.usage.prompt_tokens or 0
            uso.saida += r.usage.completion_tokens or 0
        conteudo = r.choices[0].message.content or ""
        try:
            return RespostaLida.model_validate(json.loads(_extrair_json(conteudo)))
        except (json.JSONDecodeError, ValidationError) as erro:
            ultimo_erro = erro
            mensagens += [
                {"role": "assistant", "content": conteudo},
                {"role": "user", "content": f"Seu JSON não passou na validação: {erro}. Corrija e responda só o JSON."},
            ]
    raise ValueError(f"A IA não devolveu uma resposta válida: {ultimo_erro}")
