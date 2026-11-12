"""Toda a matemática do LucraFood. Python puro, sem IA (LLM erra conta).

Percentuais entram como número de 0 a 100 (ex.: 23 = 23%).
"""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

CENTAVO = Decimal("0.01")

# Padrões usados quando o restaurante não informa os limiares do semáforo.
MARGEM_DESEJADA_PADRAO = Decimal("30")
MARGEM_MINIMA_PADRAO = Decimal("10")


def _pct(valor) -> Decimal:
    return Decimal(str(valor)) / 100


def custo_prato(
    itens: list[tuple[Decimal, Decimal]], custo_embalagem: Decimal = Decimal("0"), rendimento: Decimal = Decimal("1")
) -> Decimal:
    """Custo de UMA porção vendida.

    itens = [(quantidade_usada, custo_por_unidade), ...] da receita inteira.
    rendimento = porções que a receita rende (bolo que rende 12 fatias = 12; padrão 1).
    A embalagem é por porção vendida, então fica fora da divisão:
    custo = custo dos ingredientes / rendimento + embalagem.
    """
    rendimento = Decimal(rendimento)
    if rendimento <= 0:
        raise ValueError("O rendimento precisa ser maior que zero.")
    ingredientes = sum((Decimal(q) * Decimal(c) for q, c in itens), Decimal("0"))
    return (ingredientes / rendimento + Decimal(custo_embalagem)).quantize(CENTAVO, ROUND_HALF_UP)


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


@dataclass
class Conta:
    """A conta de um pedido, em reais, linha por linha: preco - ingredientes - embalagem - impostos - taxa = sobra."""

    preco: Decimal
    ingredientes: Decimal  # da porção (receita / rendimento)
    embalagem: Decimal
    impostos: Decimal
    taxa_app: Decimal
    sobra: Decimal


def decompor(
    preco,
    itens: list[tuple[Decimal, Decimal]],
    custo_embalagem=Decimal("0"),
    rendimento=Decimal("1"),
    taxa_app_pct=0,
    impostos_pct=0,
) -> Conta:
    """Cada linha é arredondada no centavo e a sobra sai das linhas, para a conta fechar na tela.
    Balcão = mesma conta com taxa_app_pct=0. Pode diferir 1 centavo de preco - custo_prato(...)."""
    preco = Decimal(preco)
    if preco <= 0:
        raise ValueError("Preço precisa ser maior que zero.")
    rendimento = Decimal(rendimento)
    if rendimento <= 0:
        raise ValueError("O rendimento precisa ser maior que zero.")
    soma = sum((Decimal(q) * Decimal(c) for q, c in itens), Decimal("0"))
    ingredientes = (soma / rendimento).quantize(CENTAVO, ROUND_HALF_UP)
    embalagem = Decimal(custo_embalagem).quantize(CENTAVO, ROUND_HALF_UP)
    impostos = (preco * _pct(impostos_pct)).quantize(CENTAVO, ROUND_HALF_UP)
    taxa = (preco * _pct(taxa_app_pct)).quantize(CENTAVO, ROUND_HALF_UP)
    sobra = preco - ingredientes - embalagem - impostos - taxa
    return Conta(preco.quantize(CENTAVO, ROUND_HALF_UP), ingredientes, embalagem, impostos, taxa, sobra)


@dataclass
class VariacaoSobra:
    antes: Decimal
    depois: Decimal
    diferenca: Decimal  # depois - antes (negativa quando a sobra caiu)


def variacao_sobra(
    preco, itens_antes, itens_depois, custo_embalagem=Decimal("0"), rendimento=Decimal("1"), taxa_app_pct=0, impostos_pct=0
) -> VariacaoSobra:
    """Sobra do delivery antes e depois de um ingrediente mudar de preço (itens = [(quantidade, custo_por_unidade)]).
    Ainda só na demo da landing ("Em desenvolvimento"); o app real vai precisar do histórico de preço."""
    antes = decompor(preco, itens_antes, custo_embalagem, rendimento, taxa_app_pct, impostos_pct).sobra
    depois = decompor(preco, itens_depois, custo_embalagem, rendimento, taxa_app_pct, impostos_pct).sobra
    return VariacaoSobra(antes, depois, depois - antes)


PRECO_ANTIGO_DIAS = 30


def preco_antigo(atualizado_em: date, hoje: date, limite_dias: int = PRECO_ANTIGO_DIAS) -> bool:
    """Preço de ingrediente sem atualizar há MAIS de `limite_dias` dias: a conta pode estar desatualizada."""
    return (hoje - atualizado_em).days > limite_dias


# Unidade de medida -> (unidade do cadastro, fator). Só medidas exatas: "fatia" ou "colher"
# não entram, porque transformá-las em gramas seria chute (o dono informa).
FATORES_UNIDADE = {
    "mg": ("g", Decimal("0.001")),
    "g": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "l": ("ml", Decimal("1000")),
    "un": ("un", Decimal("1")),
}
MILESIMO = Decimal("0.001")


def converter_unidade(quantidade, de: str, para: str) -> Decimal:
    """Converte para a unidade do cadastro (ex.: 0,2 kg -> 200 g). ValueError se não houver conversão exata."""
    if de not in FATORES_UNIDADE:
        raise ValueError(f"Unidade sem conversão exata: {de!r}.")
    base, fator = FATORES_UNIDADE[de]
    if base != para:
        raise ValueError(f"Não dá para converter {de} em {para}.")
    return (Decimal(quantidade) * fator).quantize(MILESIMO, ROUND_HALF_UP)


def quantidade_de_medidas(medidas, por_medida, de: str, para: str) -> Decimal:
    """Medida caseira -> unidade do cadastro: 2 fatias de 20 g -> 40 g; 1 fio de 0,01 l -> 10 ml.
    ValueError se `de` não converte para `para` ou se algum valor não for positivo."""
    medidas, por_medida = Decimal(medidas), Decimal(por_medida)
    if medidas <= 0 or por_medida <= 0:
        raise ValueError("Quantidades precisam ser maiores que zero.")
    return converter_unidade(medidas * por_medida, de, para)
