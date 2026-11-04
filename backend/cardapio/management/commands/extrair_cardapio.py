"""Teste rápido sem frontend:  python manage.py extrair_cardapio caminho/da/foto.jpg"""
import mimetypes
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cardapio.ia.extracao import extrair_cardapio


class Command(BaseCommand):
    help = "Lê uma foto de cardápio com IA e mostra os pratos encontrados."

    def add_arguments(self, parser):
        parser.add_argument("imagem")

    def handle(self, *args, imagem, **opts):
        caminho = Path(imagem)
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        mime = mimetypes.guess_type(caminho.name)[0] or "image/jpeg"

        inicio = time.perf_counter()
        cardapio = extrair_cardapio(caminho.read_bytes(), mime)
        segundos = time.perf_counter() - inicio

        for p in cardapio.pratos:
            preco = f"R$ {p.preco:.2f}" if p.preco is not None else "(sem preço)"
            cat = f"[{p.categoria}] " if p.categoria else ""
            self.stdout.write(f"  {cat}{p.nome} — {preco}")
        self.stdout.write(self.style.SUCCESS(f"\n{len(cardapio.pratos)} pratos em {segundos:.1f}s"))
