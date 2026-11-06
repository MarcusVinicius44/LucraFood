"""Mede a qualidade da extração em fotos reais (CHAMA A API: consome cota do Groq).

    python manage.py avaliar_extracao                    # todas as fotos de evals/cardapios/
    python manage.py avaliar_extracao --foto cardapio_01
"""
import json
import mimetypes
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cardapio.avaliacao import Resultado, comparar
from cardapio.ia.extracao import CardapioExtraido, FalhaDeCota, extrair_cardapio_com_uso
from cardapio.ia.limitador import LimitadorSaida

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}
LIMITE_TOKENS_MIN = 8000  # limite por minuto do plano: uma foto acima disso nunca passa, esperar não resolve


def _preco(p) -> str:
    return f"R$ {p:.2f}" if p is not None else "(sem preço)"


class Command(BaseCommand):
    help = "Roda a extração real nas fotos de evals/cardapios/ e compara com os gabaritos."

    def add_arguments(self, parser):
        parser.add_argument("--foto", help="Nome (sem extensão) de uma única foto, ex.: cardapio_01")
        parser.add_argument("--faixas", type=int, default=1, help="Dividir cada foto em N faixas horizontais (padrão: 1, foto inteira)")
        parser.add_argument("--pasta", help="Pasta com fotos e gabaritos (padrão: evals/cardapios)")

    def handle(self, *args, foto=None, pasta=None, faixas=1, **opts):
        pasta = Path(pasta) if pasta else Path(settings.BASE_DIR).parent / "evals" / "cardapios"
        if not pasta.is_dir():
            raise CommandError(f"Pasta não encontrada: {pasta}")

        fotos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)
        if foto:
            fotos = [p for p in fotos if p.stem == foto]
            if not fotos:
                raise CommandError(f"Foto '{foto}' não encontrada em {pasta}")

        limitador = LimitadorSaida(ao_esperar=self._aviso_limite)
        total, avaliadas, falhas, falhas_cota, tabela = Resultado(), 0, [], [], []
        for caminho in fotos:
            gabarito_path = caminho.with_suffix(".json")
            if not gabarito_path.exists():
                self.stdout.write(self.style.WARNING(f"{caminho.name}: sem gabarito ({gabarito_path.name}), ignorada"))
                continue
            gabarito = CardapioExtraido.model_validate(json.loads(gabarito_path.read_text(encoding="utf-8")))

            self.stdout.write(f"\n== {caminho.name}")
            inicio = time.perf_counter()
            try:
                mime = mimetypes.guess_type(caminho.name)[0] or "image/jpeg"
                extraido, uso = extrair_cardapio_com_uso(
                    caminho.read_bytes(), mime, esperar=self._esperar, faixas=faixas, limitador=limitador
                )
            except FalhaDeCota as erro:
                self.stdout.write(self.style.ERROR(f"   FALHA DE COTA: {erro}"))
                falhas_cota.append(caminho.name)
                continue
            except Exception as erro:  # falha de API/validação conta como falha, não derruba a avaliação
                self.stdout.write(self.style.ERROR(f"   FALHOU: {erro}"))
                falhas.append(caminho.name)
                continue
            segundos = time.perf_counter() - inicio

            r = comparar(gabarito.pratos, extraido.pratos)
            avaliadas += 1
            total.somar(r)
            self._mostrar(r)
            self.stdout.write(f"   tokens: {uso.entrada} entrada + {uso.saida} saída | tempo total: {segundos:.0f}s")
            tabela.append((caminho.name, r, uso, segundos))
            if uso.maior_chamada > LIMITE_TOKENS_MIN:
                self.stdout.write(self.style.WARNING(
                    f"   AVISO: uma chamada sozinha usou {uso.maior_chamada} tokens > {LIMITE_TOKENS_MIN}/min; "
                    "esperar não resolve (reduza a imagem ou use mais faixas)."
                ))

        self._tabela(tabela)
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            f"TOTAL: {avaliadas} foto(s) avaliada(s), {len(falhas)} falha(s) na extração, "
            f"{len(falhas_cota)} falha(s) de cota"
        )
        if falhas:
            self.stdout.write(self.style.ERROR(f"Falharam (extração): {', '.join(falhas)}"))
        if falhas_cota:
            self.stdout.write(self.style.ERROR(f"Falharam (cota): {', '.join(falhas_cota)}"))
        if avaliadas:
            self._mostrar(total, detalhes=False)

    def _esperar(self, segundos: float):
        self.stdout.write(self.style.WARNING(f"   429 do Groq: esperando {segundos:.0f}s para tentar de novo..."))
        time.sleep(segundos)

    def _aviso_limite(self, segundos: float):
        self.stdout.write(self.style.WARNING(f"   limite de saída/min: esperando {segundos:.0f}s antes da próxima chamada..."))

    def _tabela(self, linhas):
        if not linhas:
            return
        self.stdout.write("\n" + f"{'foto':<18}{'gab':>5}{'ext':>5}{'achou':>6}{'falta':>6}{'inv':>5}{'$err':>5}{'tok.ent':>9}{'tok.sai':>9}{'tempo':>7}")
        ent = sai = tempo = 0
        for nome, r, uso, seg in linhas:
            ent, sai, tempo = ent + uso.entrada, sai + uso.saida, tempo + seg
            self.stdout.write(
                f"{nome:<18}{r.gabarito:>5}{r.extraidos:>5}{r.encontrados:>6}{len(r.faltando):>6}"
                f"{len(r.inventados):>5}{len(r.precos_errados):>5}{uso.entrada:>9}{uso.saida:>9}{seg:>6.0f}s"
            )
        self.stdout.write(f"{'TOTAL tokens':<18}{'':>32}{ent:>9}{sai:>9}{tempo:>6.0f}s")

    def _mostrar(self, r: Resultado, detalhes: bool = True):
        self.stdout.write(
            f"   gabarito: {r.gabarito} | extraídos: {r.extraidos} | encontrados: {r.encontrados} | "
            f"faltando: {len(r.faltando)} | inventados: {len(r.inventados)} | preços errados: {len(r.precos_errados)}"
        )
        if r.encontrados:
            certos = r.encontrados - len(r.precos_errados)
            self.stdout.write(f"   preços certos entre os encontrados: {certos}/{r.encontrados}")
        if not detalhes:
            return
        for nome in r.faltando:
            self.stdout.write(self.style.WARNING(f"   FALTANDO:  {nome}"))
        for nome in r.inventados:
            self.stdout.write(self.style.WARNING(f"   INVENTADO: {nome}"))
        for nome, esperado, obtido in r.precos_errados:
            self.stdout.write(self.style.ERROR(f"   PREÇO:     {nome}: esperado {_preco(esperado)}, veio {_preco(obtido)}"))
