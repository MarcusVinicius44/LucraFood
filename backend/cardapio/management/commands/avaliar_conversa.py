"""Mede a leitura das respostas do dono na ficha em conversa (CHAMA A API: 1 chamada por resposta).

    python manage.py avaliar_conversa                 # todas as respostas de evals/fichas/respostas.json
    python manage.py avaliar_conversa --resposta c03
"""
import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cardapio.avaliacao_conversa import comparar_resposta
from cardapio.ia.cliente import config
from cardapio.ia.conversa import interpretar_resposta
from cardapio.ia.extracao import FalhaDeCota, ProvedorIndisponivel, Uso


class Command(BaseCommand):
    help = "Roda a leitura real das respostas de evals/fichas/respostas.json e compara com a esperada."

    def add_arguments(self, parser):
        parser.add_argument("--resposta", help="id de uma única resposta, ex.: c03")
        parser.add_argument("--arquivo", help="Caminho do JSON (padrão: evals/fichas/respostas.json)")

    def handle(self, *args, resposta=None, arquivo=None, **opts):
        caminho = Path(arquivo) if arquivo else Path(settings.BASE_DIR).parent / "evals" / "fichas" / "respostas.json"
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        casos = dados["respostas"]
        if resposta:
            casos = [c for c in casos if c["id"] == resposta]
            if not casos:
                raise CommandError(f"Resposta '{resposta}' não encontrada.")

        cfg = config()
        self.stdout.write(f"Provedor: {cfg.provedor} | modelo: {cfg.modelo} | respostas: {len(casos)}")
        if dados.get("_origem"):
            self.stdout.write(self.style.WARNING(f"Esperado: {dados['_origem']}"))

        certas, falhas, uso, inicio = 0, [], Uso(), time.monotonic()
        for c in casos:
            try:
                lida = interpretar_resposta(c["pergunta"], c["resposta"], uso=uso, esperar=self._esperar)
            except (FalhaDeCota, ProvedorIndisponivel, ValueError) as erro:
                falhas.append(c["id"])
                self.stdout.write(self.style.ERROR(f"{c['id']}: FALHOU: {erro}"))
                continue
            obtido = {
                "entendeu": lida.entendeu,
                "nao_sabe": lida.nao_sabe,
                "quantidade": None if lida.quantidade is None else str(lida.quantidade),
                "unidade": lida.unidade,
            }
            ok = comparar_resposta(c["esperado"], obtido)
            certas += ok
            marca = "ok  " if ok else "ERRO"
            linha = f"{marca} {c['id']} ({c['caso']}): {c['resposta']!r} -> {obtido}"
            self.stdout.write(linha if ok else self.style.ERROR(linha + f" | esperado {c['esperado']}"))

        avaliadas = len(casos) - len(falhas)
        self.stdout.write("=" * 50)
        self.stdout.write(
            f"Respostas lidas certo: {certas}/{avaliadas}\n"
            f"Chamadas: {uso.chamadas} | tokens: {uso.entrada} entrada + {uso.saida} saída | "
            f"tempo: {time.monotonic() - inicio:.0f}s"
        )
        if falhas:
            self.stdout.write(self.style.ERROR(f"Falharam: {', '.join(falhas)}"))

    def _esperar(self, segundos):
        self.stdout.write(f"   provedor recusou (429/503): esperando {segundos:.0f}s...")
        time.sleep(segundos)
