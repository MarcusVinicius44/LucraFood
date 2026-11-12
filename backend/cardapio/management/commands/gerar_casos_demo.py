"""Gera os casos que obrigam o calculosDemo.ts (só da demo da landing) a dar o mesmo resultado que calculos.py.

    python manage.py gerar_casos_demo

Escreve frontend/src/demo/casos-calculos.json (entrada -> saída do Python). O teste
frontend/src/demo/calculosDemo.test.ts roda cada caso no TypeScript e exige o mesmo texto,
centavo por centavo. Não chama IA. Rode de novo sempre que calculos.py mudar.

Itens de ficha vêm como [quantidade, preco_embalagem, quantidade_embalagem]; o custo por unidade
é preco / quantidade, como em Ingrediente.custo_por_unidade.
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from cardapio import calculos

D = Decimal


def _itens(lista):
    return [(D(q), D(p) / D(qe)) for q, p, qe in lista]


def _txt(valor):
    if valor is None:
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, Decimal):
        return str(abs(valor) if valor == 0 else valor)  # "-0.0" -> "0.0"
    return valor


# Cadastro fictício da demo (o mesmo de frontend/src/demo/fixtures/entrada-demo.json).
PAO = ["1", "15.60", "12"]
BLEND = ["150", "37.00", "1000"]
BLEND_NOVO = ["150", "42.00", "1000"]
QUEIJO = ["36", "45.00", "1000"]
EMB_LANCHE = ["1", "45.00", "50"]
BACON = ["40", "49.90", "1000"]
CHEDDAR = ["30", "62.00", "1000"]
MAIONESE = ["15", "19.90", "1000"]
BATATA = ["300", "32.90", "2000"]
OLEO = ["80", "8.49", "900"]
EMB_PORCAO = ["1", "60.00", "50"]

CASOS = [
    # custo_prato
    ("custo_prato", {"itens": [["150", "0.042", "1"], ["1", "1.20", "1"]], "embalagem": "0.80", "rendimento": "1"}),
    ("custo_prato", {"itens": [PAO, BLEND, QUEIJO, EMB_LANCHE], "embalagem": "0", "rendimento": "1"}),
    ("custo_prato", {"itens": [BATATA, OLEO, EMB_PORCAO], "embalagem": "0", "rendimento": "1"}),
    ("custo_prato", {"itens": [["1", "12", "1"]], "embalagem": "0.50", "rendimento": "12"}),
    ("custo_prato", {"itens": [["1", "10", "3"]], "embalagem": "0", "rendimento": "1"}),  # 3,333... -> 3,33
    ("custo_prato", {"itens": [["1", "0.005", "1"]], "embalagem": "0", "rendimento": "1"}),  # meio centavo sobe
    ("custo_prato", {"itens": [["2", "0.0125", "1"]], "embalagem": "1.10", "rendimento": "0.5"}),
    ("custo_prato", {"itens": [["1", "1", "1"]], "embalagem": "0", "rendimento": "0"}),  # erro
    # margem
    ("margem", {"preco": "25", "custo": "12", "taxa": "23", "impostos": "6"}),
    ("margem", {"preco": "24.90", "custo": "8.44", "taxa": "26", "impostos": "6"}),
    ("margem", {"preco": "10", "custo": "9.99", "taxa": "0", "impostos": "0"}),  # 0,1%
    ("margem", {"preco": "10", "custo": "10.004", "taxa": "0", "impostos": "0"}),  # -0,04 -> 0,0
    ("margem", {"preco": "0", "custo": "1", "taxa": "0", "impostos": "0"}),  # erro
    # preco_sugerido
    ("preco_sugerido", {"custo": "8.44", "desejada": "30", "taxa": "26", "impostos": "6"}),
    ("preco_sugerido", {"custo": "5", "desejada": "30", "taxa": "0", "impostos": "0"}),
    ("preco_sugerido", {"custo": "5", "desejada": "60", "taxa": "35", "impostos": "6"}),  # erro: passa de 100%
    # diagnosticar
    ("diagnosticar", {"preco": "25", "custo": "12", "taxa": "23", "impostos": "6", "desejada": "30", "minima": "10"}),
    ("diagnosticar", {"preco": "34.90", "custo": "8", "taxa": "26", "impostos": "6", "desejada": "30", "minima": "10"}),
    ("diagnosticar", {"preco": "14.90", "custo": "6.20", "taxa": "26", "impostos": "6", "desejada": None, "minima": None}),
    ("diagnosticar", {"preco": "20", "custo": "6.4", "taxa": "0", "impostos": "0", "desejada": "68", "minima": "10"}),  # 68,0 = verde
    ("diagnosticar", {"preco": "20", "custo": "6", "taxa": "26", "impostos": "6", "desejada": "10", "minima": "30"}),  # erro
    # decompor
    ("decompor", {"preco": "24.90", "itens": [PAO, BLEND, QUEIJO, EMB_LANCHE], "embalagem": "0", "rendimento": "1", "taxa": "26", "impostos": "6"}),
    ("decompor", {"preco": "29.90", "itens": [PAO, BLEND, BACON, CHEDDAR, MAIONESE, EMB_LANCHE], "embalagem": "0", "rendimento": "1", "taxa": "26", "impostos": "6"}),
    ("decompor", {"preco": "22.00", "itens": [BATATA, OLEO, EMB_PORCAO], "embalagem": "0", "rendimento": "1", "taxa": "0", "impostos": "6"}),
    ("decompor", {"preco": "10", "itens": [["1", "12", "1"]], "embalagem": "0.50", "rendimento": "12", "taxa": "0", "impostos": "0"}),
    ("decompor", {"preco": "10.05", "itens": [["1", "9", "1"]], "embalagem": "0.333", "rendimento": "1", "taxa": "30", "impostos": "6"}),
    # variacao_sobra (demo: blend de R$ 37 para R$ 42/kg)
    ("variacao_sobra", {"preco": "24.90", "antes": [PAO, BLEND, QUEIJO, EMB_LANCHE], "depois": [PAO, BLEND_NOVO, QUEIJO, EMB_LANCHE], "embalagem": "0", "rendimento": "1", "taxa": "26", "impostos": "6"}),
    ("variacao_sobra", {"preco": "29.90", "antes": [PAO, BLEND, BACON, CHEDDAR, MAIONESE, EMB_LANCHE], "depois": [PAO, BLEND_NOVO, BACON, CHEDDAR, MAIONESE, EMB_LANCHE], "embalagem": "0", "rendimento": "1", "taxa": "26", "impostos": "6"}),
    # preco_antigo
    ("preco_antigo", {"atualizado_em": "2026-10-13", "hoje": "2026-11-12"}),
    ("preco_antigo", {"atualizado_em": "2026-10-12", "hoje": "2026-11-12"}),
    ("preco_antigo", {"atualizado_em": "2026-09-20", "hoje": "2026-11-12"}),
    # conversões
    ("converter_unidade", {"quantidade": "0.2", "de": "kg", "para": "g"}),
    ("converter_unidade", {"quantidade": "1.5", "de": "l", "para": "ml"}),
    ("converter_unidade", {"quantidade": "2", "de": "fatia", "para": "g"}),  # erro
    ("quantidade_de_medidas", {"medidas": "2", "por_medida": "18", "de": "g", "para": "g"}),
    ("quantidade_de_medidas", {"medidas": "3", "por_medida": "0.0125", "de": "kg", "para": "g"}),
    ("quantidade_de_medidas", {"medidas": "0", "por_medida": "18", "de": "g", "para": "g"}),  # erro
]


def _rodar(funcao, e):
    c = calculos
    if funcao == "custo_prato":
        return {"custo": c.custo_prato(_itens(e["itens"]), D(e["embalagem"]), D(e["rendimento"]))}
    if funcao == "margem":
        return {"margem": c.margem(D(e["preco"]), D(e["custo"]), e["taxa"], e["impostos"])}
    if funcao == "preco_sugerido":
        return {"preco": c.preco_sugerido(D(e["custo"]), e["desejada"], e["taxa"], e["impostos"])}
    if funcao == "diagnosticar":
        d = c.diagnosticar(D(e["preco"]), D(e["custo"]), e["taxa"], e["impostos"], e["desejada"], e["minima"])
        return {
            "custo": d.custo,
            "margem_balcao": d.margem_balcao,
            "margem_delivery": d.margem_delivery,
            "semaforo": d.semaforo,
            "preco_sugerido_delivery": d.preco_sugerido_delivery,
        }
    if funcao == "decompor":
        k = c.decompor(D(e["preco"]), _itens(e["itens"]), D(e["embalagem"]), D(e["rendimento"]), e["taxa"], e["impostos"])
        return {"preco": k.preco, "ingredientes": k.ingredientes, "embalagem": k.embalagem, "impostos": k.impostos, "taxa_app": k.taxa_app, "sobra": k.sobra}
    if funcao == "variacao_sobra":
        v = c.variacao_sobra(D(e["preco"]), _itens(e["antes"]), _itens(e["depois"]), D(e["embalagem"]), D(e["rendimento"]), e["taxa"], e["impostos"])
        return {"antes": v.antes, "depois": v.depois, "diferenca": v.diferenca}
    if funcao == "preco_antigo":
        return {"antigo": c.preco_antigo(date.fromisoformat(e["atualizado_em"]), date.fromisoformat(e["hoje"]))}
    if funcao == "converter_unidade":
        return {"quantidade": c.converter_unidade(D(e["quantidade"]), e["de"], e["para"])}
    if funcao == "quantidade_de_medidas":
        return {"quantidade": c.quantidade_de_medidas(D(e["medidas"]), D(e["por_medida"]), e["de"], e["para"])}
    raise ValueError(f"função desconhecida: {funcao}")


class Command(BaseCommand):
    help = "Gera frontend/src/demo/casos-calculos.json a partir de calculos.py (sem IA)."

    def handle(self, *args, **opts):
        casos = []
        for funcao, entrada in CASOS:
            try:
                saida = {k: _txt(v) for k, v in _rodar(funcao, entrada).items()}
            except ValueError:
                saida = {"erro": True}
            casos.append({"funcao": funcao, "entrada": entrada, "saida": saida})
        destino = Path(settings.BASE_DIR).parent / "frontend" / "src" / "demo" / "casos-calculos.json"
        dados = {
            "_origem": "Gerado por `python manage.py gerar_casos_demo` a partir de backend/cardapio/calculos.py. Não editar à mão.",
            "casos": casos,
        }
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        erros = sum(1 for c in casos if "erro" in c["saida"])
        self.stdout.write(self.style.SUCCESS(f"{len(casos)} casos ({erros} de erro) em {destino}"))
