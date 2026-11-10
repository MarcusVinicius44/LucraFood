"""Compara a leitura de uma resposta do dono (ia/conversa.py) com a esperada (Python puro, sem API).

Acerta quando "entendeu" e "nao_sabe" batem e, se a resposta foi entendida e não é "não sei",
a quantidade e a unidade também batem (unidade comparada já no nome canônico: "gramas" = "g").
"""
from decimal import Decimal

from .ia.ficha import _unidade_canonica


def _decimal(valor):
    return None if valor is None else Decimal(str(valor))


def _unidade(valor):
    if not valor:
        return None
    return _unidade_canonica(valor) or valor.strip().lower()


def comparar_resposta(esperado: dict, lido: dict) -> bool:
    if bool(lido.get("entendeu")) != esperado["entendeu"]:
        return False
    if not esperado["entendeu"]:
        return True
    if bool(lido.get("nao_sabe")) != esperado.get("nao_sabe", False):
        return False
    if esperado.get("nao_sabe"):
        return True
    return _decimal(lido.get("quantidade")) == _decimal(esperado["quantidade"]) and _unidade(
        lido.get("unidade")
    ) == _unidade(esperado["unidade"])
