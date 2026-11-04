"""Toda a matemática do LucraFood. Python puro, sem IA (LLM erra conta).

Percentuais entram como número de 0 a 100 (ex.: 23 = 23%).
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

CENTAVO = Decimal("0.01")

# Padrões usados quando o restaurante não informa os limiares do semáforo.
MARGEM_DESEJADA_PADRAO = Decimal("30")
MARGEM_MINIMA_PADRAO = Decimal("10")


def _pct(valor) -> Decimal:
    return Decimal(str(valor)) / 100


def custo_prato(itens: list[tuple[Decimal, Decimal]], custo_embalagem: Decimal = Decimal("0")) -> Decimal:
    """itens = [(quantidade_usada, custo_por_unidade), ...]"""
    total = sum((Decimal(q) * Decimal(c) for q, c in itens), Decimal("0")) + Decimal(custo_embalagem)
    return total.quantize(CENTAVO, ROUND_HALF_UP)


def margem(preco: Decimal, custo: Decimal, taxa_app_pct=0, impostos_pct=0) -> Decimal:
    """Margem sobre o preço, em %, depois de custo, taxa do app e impostos."""
    preco = Decimal(preco)
    if preco <= 0:
        raise ValueError("Preço precisa ser maior que zero.")
    sobra = preco - Decimal(custo) - preco * (_pct(taxa_app_pct) + _pct(impostos_pct))
    return (sobra / preco * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)


def preco_sugerido(custo: Decimal, margem_desejada_pct, taxa_app_pct=0, impostos_pct=0) -> Decimal:
    divisor = 1 - _pct(taxa_app_pct) - _pct(impostos_pct) - _pct(margem_desejada_pct)
    if divisor <= 0:
        raise ValueError("Taxas + impostos + margem passam de 100%: não existe preço possível.")
    return (Decimal(custo) / divisor).quantize(CENTAVO, ROUND_HALF_UP)


@dataclass
class Diagnostico:
    custo: Decimal
    margem_balcao: Decimal
    margem_delivery: Decimal
    semaforo: str  # "verde" | "amarelo" | "vermelho"
    preco_sugerido_delivery: Optional[Decimal]


def diagnosticar(
    preco,
    custo,
    taxa_app_pct,
    impostos_pct,
    margem_desejada_pct=None,
    margem_minima_pct=None,
) -> Diagnostico:
    """Semáforo pela margem do DELIVERY:
    vermelho < margem mínima (padrão 10%) <= amarelo < margem desejada (padrão 30%) <= verde.
    `None` em qualquer limiar usa o padrão."""
    desejada = MARGEM_DESEJADA_PADRAO if margem_desejada_pct is None else Decimal(str(margem_desejada_pct))
    minima = MARGEM_MINIMA_PADRAO if margem_minima_pct is None else Decimal(str(margem_minima_pct))
    if minima > desejada:
        raise ValueError("A margem mínima não pode ser maior que a margem desejada.")

    m_balcao = margem(preco, custo, 0, impostos_pct)
    m_delivery = margem(preco, custo, taxa_app_pct, impostos_pct)
    if m_delivery < minima:
        semaforo = "vermelho"
    elif m_delivery < desejada:
        semaforo = "amarelo"
    else:
        semaforo = "verde"
    sugerido = None
    if semaforo != "verde":
        sugerido = preco_sugerido(custo, desejada, taxa_app_pct, impostos_pct)
    return Diagnostico(Decimal(custo), m_balcao, m_delivery, semaforo, sugerido)
