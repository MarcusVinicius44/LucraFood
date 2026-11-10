"""Mede a extração da ficha técnica por texto (CHAMA A API: 1 chamada por frase, conta na cota).

    python manage.py avaliar_ficha                # todas as frases de evals/fichas/frases.json
    python manage.py avaliar_ficha --frase f03
    python manage.py avaliar_ficha --frases frases_revisao.json   # frases ambíguas de propósito
"""
import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cardapio.avaliacao_ficha import ResultadoFicha, comparar
from cardapio.ia.cliente import config
from cardapio.ia.extracao import FalhaDeCota, ProvedorIndisponivel, Uso
from cardapio.ia.ficha import TextoSemIngredientes, extrair_ficha


def _pct(parte, total):
    return f"{100 * parte / total:.1f}%" if total else "-"


class Command(BaseCommand):
    help = "Roda a extração real da ficha nas frases de evals/fichas/ e compara com a resposta esperada."

    def add_arguments(self, parser):
        parser.add_argument("--frase", help="id de uma única frase, ex.: f03")
        parser.add_argument("--frases", default="frases.json", help="Arquivo de frases dentro da pasta (padrão: frases.json)")
        parser.add_argument("--pasta", help="Pasta com ingredientes.json e frases.json (padrão: evals/fichas)")

    def handle(self, *args, frase=None, frases="frases.json", pasta=None, **opts):
        pasta = Path(pasta) if pasta else Path(settings.BASE_DIR).parent / "evals" / "fichas"
        try:
            cadastro = json.loads((pasta / "ingredientes.json").read_text(encoding="utf-8"))
            dados = json.loads((pasta / frases).read_text(encoding="utf-8"))
        except FileNotFoundError as erro:
            raise CommandError(f"Arquivo não encontrado: {erro.filename}")
        arquivo, frases = frases, dados["frases"]
        if frase:
            frases = [f for f in frases if f["id"] == frase]
            if not frases:
                raise CommandError(f"Frase '{frase}' não encontrada.")

        cfg = config()
        self.stdout.write(f"Provedor: {cfg.provedor} | modelo: {cfg.modelo} | {arquivo}: {len(frases)} frases")
        if dados.get("_origem"):
            self.stdout.write(self.style.WARNING(f"Respostas esperadas: {dados['_origem']}"))

        total, uso_total, falhas, tabela = ResultadoFicha(), Uso(), [], []
        inicio_geral = time.monotonic()
        for f in frases:
            self.stdout.write(f"\n== {f['id']} ({f['caso']})\n   {f['texto']}")
            uso, inicio = Uso(), time.monotonic()
            try:
                itens = extrair_ficha(f["texto"], cadastro, f["prato"], uso=uso, esperar=self._esperar)
                extraido = [item.para_json() for item in itens]
            except TextoSemIngredientes:
                extraido = []
            except (FalhaDeCota, ProvedorIndisponivel, ValueError) as erro:
                falhas.append(f["id"])
                self.stdout.write(self.style.ERROR(f"   FALHOU: {erro}"))
                self._somar_uso(uso_total, uso)
                continue
            segundos = time.monotonic() - inicio
            self._somar_uso(uso_total, uso)
            r = comparar(f["esperado"], extraido)
            total.somar(r)
            tabela.append((f["id"], r, uso, segundos))
            self._detalhes(extraido, r)

        self.stdout.write(f"\n{'frase':6} {'ingr.':>7} {'qtd.':>7} {'errados':>8} {'cham':>5} {'tempo':>6}")
        for fid, r, uso, segundos in tabela:
            self.stdout.write(
                f"{fid:6} {r.ingrediente_ok:>3}/{r.esperados:<3} {r.quantidade_ok:>3}/{r.quantidades:<3} "
                f"{len(r.errados):>8} {uso.chamadas:>5} {segundos:>5.0f}s"
            )
        self.stdout.write("=" * 50)
        self.stdout.write(
            f"Ingrediente certo: {total.ingrediente_ok}/{total.esperados} ({_pct(total.ingrediente_ok, total.esperados)})\n"
            f"Quantidade certa (nos ingredientes acertados): {total.quantidade_ok}/{total.quantidades} "
            f"({_pct(total.quantidade_ok, total.quantidades)})\n"
            f"Ligados a ingrediente errado: {len(total.errados)} | itens a mais sem ingrediente: {len(total.sobrando)}\n"
            + (
                f"Pedido de conferência certo (precisa_confirmar): {total.revisao_ok}/{total.revisoes} "
                f"({_pct(total.revisao_ok, total.revisoes)})\n"
                if total.revisoes
                else ""
            )
            + f"Chamadas: {uso_total.chamadas} | tokens: {uso_total.entrada} entrada + {uso_total.saida} saída | "
            f"tempo: {time.monotonic() - inicio_geral:.0f}s"
        )
        if falhas:
            self.stdout.write(self.style.ERROR(f"Falharam: {', '.join(falhas)}"))

    def _detalhes(self, extraido, r):
        for item in extraido:
            ingr = item["ingrediente"]["nome"] if item["ingrediente"] else "null"
            qtd = f"{item['quantidade']} {item['unidade']}" if item["quantidade"] else "-"
            motivos = f"  [{', '.join(item['motivos'])}]" if item["motivos"] else ""
            self.stdout.write(f"   lido: {item['nome_lido']!r} -> {ingr} | {qtd}{motivos}")
        for nome in r.faltando:
            self.stdout.write(self.style.ERROR(f"   FALTANDO: {nome}"))
        for nome, esperado, obtido in r.quantidade_errada:
            self.stdout.write(self.style.ERROR(f"   QUANTIDADE: {nome}: esperado {esperado}, veio {obtido}"))
        for nome, id_ in r.errados:
            self.stdout.write(self.style.ERROR(f"   ERRADO: {nome!r} ligado ao id {id_}"))
        for nome in r.sobrando:
            self.stdout.write(self.style.WARNING(f"   A MAIS: {nome!r}"))
        for nome, esperado, veio, motivos in r.revisao_errada:
            pedido = "pedir conferência" if esperado else "NÃO pedir conferência"
            self.stdout.write(self.style.ERROR(f"   REVISÃO: {nome}: devia {pedido} (motivos: {motivos or 'nenhum'})"))

    def _esperar(self, segundos):
        self.stdout.write(f"   provedor recusou (429/503): esperando {segundos:.0f}s...")
        time.sleep(segundos)

    @staticmethod
    def _somar_uso(total, uso):
        total.chamadas += uso.chamadas
        total.entrada += uso.entrada
        total.saida += uso.saida
