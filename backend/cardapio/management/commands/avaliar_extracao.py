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
from cardapio.ia.extracao import CardapioExtraido, extrair_cardapio

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}


def _preco(p) -> str:
    return f"R$ {p:.2f}" if p is not None else "(sem preço)"


class Command(BaseCommand):
    help = "Roda a extração real nas fotos de evals/cardapios/ e compara com os gabaritos."

    def add_arguments(self, parser):
        parser.add_argument("--foto", help="Nome (sem extensão) de uma única foto, ex.: cardapio_01")
        parser.add_argument("--pasta", help="Pasta com fotos e gabaritos (padrão: evals/cardapios)")

    def handle(self, *args, foto=None, pasta=None, **opts):
        pasta = Path(pasta) if pasta else Path(settings.BASE_DIR).parent / "evals" / "cardapios"
        if not pasta.is_dir():
            raise CommandError(f"Pasta não encontrada: {pasta}")

        fotos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)
        if foto:
            fotos = [p for p in fotos if p.stem == foto]
            if not fotos:
                raise CommandError(f"Foto '{foto}' não encontrada em {pasta}")

        total, avaliadas, falhas = Resultado(), 0, []
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
                extraido = extrair_cardapio(caminho.read_bytes(), mime)
            except Exception as erro:  # falha de API/validação conta como falha, não derruba a avaliação
                self.stdout.write(self.style.ERROR(f"   FALHOU: {erro}"))
                falhas.append(caminho.name)
                continue
            segundos = time.perf_counter() - inicio

            r = comparar(gabarito.pratos, extraido.pratos)
            avaliadas += 1
            total.somar(r)
            self._mostrar(r)
            self.stdout.write(f"   ({segundos:.1f}s)")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"TOTAL: {avaliadas} foto(s) avaliada(s), {len(falhas)} falha(s) na extração")
        if falhas:
            self.stdout.write(self.style.ERROR(f"Falharam: {', '.join(falhas)}"))
        if avaliadas:
            self._mostrar(total, detalhes=False)

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
