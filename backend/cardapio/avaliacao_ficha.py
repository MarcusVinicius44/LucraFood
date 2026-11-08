"""Compara a ficha extraída pela IA com a resposta esperada (Python puro, sem API).

Ingrediente: acerta se o item esperado aparece ligado ao mesmo id do cadastro; quando o
esperado é null (fora do cadastro), acerta se a IA também deixou null para um nome parecido.
Quantidade: só conta nos itens do cadastro que a IA acertou; compara a quantidade já na
unidade do cadastro (null esperado = a IA não deve ter convertido, ex.: "1 concha").
Errados: itens ligados a um id que não era esperado (associação errada ou inventada).
"""
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def _decimal(valor):
    return None if valor is None else Decimal(str(valor))


@dataclass
class ResultadoFicha:
    esperados: int = 0
    ingrediente_ok: int = 0
    quantidades: int = 0  # itens do cadastro acertados, onde a quantidade é avaliada
    quantidade_ok: int = 0
    faltando: list = field(default_factory=list)  # nomes esperados que a IA não ligou certo
    quantidade_errada: list = field(default_factory=list)  # (nome, esperado, extraído)
    errados: list = field(default_factory=list)  # (nome lido, id) ligados a id não esperado
    sobrando: list = field(default_factory=list)  # itens null a mais (não esperados)

    def somar(self, outro: "ResultadoFicha"):
        for nome in ("esperados", "ingrediente_ok", "quantidades", "quantidade_ok"):
            setattr(self, nome, getattr(self, nome) + getattr(outro, nome))
        for nome in ("faltando", "quantidade_errada", "errados", "sobrando"):
            getattr(self, nome).extend(getattr(outro, nome))


def comparar(esperado: list[dict], extraido: list[dict]) -> ResultadoFicha:
    """`esperado`: [{"nome", "ingrediente": id|None, "quantidade": str|None}].
    `extraido`: itens no formato de ItemExtraido.para_json()."""
    r = ResultadoFicha(esperados=len(esperado))
    livres = list(extraido)

    def tirar(condicao):
        for item in livres:
            if condicao(item):
                livres.remove(item)
                return item
        return None

    def id_de(item):
        return item["ingrediente"]["id"] if item["ingrediente"] else None

    for esp in esperado:
        if esp["ingrediente"] is not None:
            achado = tirar(lambda item: id_de(item) == esp["ingrediente"])
            if achado is None:
                r.faltando.append(esp["nome"])
                continue
            r.ingrediente_ok += 1
            r.quantidades += 1
            if _decimal(achado["quantidade"]) == _decimal(esp["quantidade"]):
                r.quantidade_ok += 1
            else:
                r.quantidade_errada.append((esp["nome"], esp["quantidade"], achado["quantidade"]))
        else:
            alvo = _normalizar(esp["nome"])
            achado = tirar(
                lambda item: id_de(item) is None
                and (alvo in _normalizar(item["nome_lido"]) or _normalizar(item["nome_lido"]) in alvo)
            )
            if achado is None:
                r.faltando.append(esp["nome"])
            else:
                r.ingrediente_ok += 1

    for item in livres:
        if id_de(item) is None:
            r.sobrando.append(item["nome_lido"])
        else:
            r.errados.append((item["nome_lido"], id_de(item)))
    return r
