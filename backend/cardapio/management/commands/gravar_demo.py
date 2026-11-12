"""Grava as respostas REAIS da IA usadas pela demo da landing (CHAMA A API: 1 chamada da foto + 1 por ficha).

    python manage.py gravar_demo                 # foto + fichas
    python manage.py gravar_demo --so-fichas     # só as fichas (não relê a foto)

Lê frontend/src/demo/fixtures/cardapio-sabor-da-esquina.png e entrada-demo.json (cadastro e frases
fictícios) e escreve gravado-extracao.json e gravado-fichas.json na mesma pasta. A demo nunca chama
a API: ela só mostra o que foi gravado aqui. Nada é salvo no banco.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cardapio.ia.cliente import config
from cardapio.ia.extracao import FalhaDeCota, FotoIlegivel, ProvedorIndisponivel, Uso, extrair_cardapio_com_uso
from cardapio.ia.ficha import TextoSemIngredientes, extrair_ficha

FOTO = "cardapio-sabor-da-esquina.png"


class Command(BaseCommand):
    help = "Roda a IA de verdade na foto e nas frases da demo e grava as respostas em frontend/src/demo/fixtures/."

    def add_arguments(self, parser):
        parser.add_argument("--so-fichas", action="store_true", help="Não relê a foto; grava só as fichas.")
        parser.add_argument("--pasta", help="Pasta das fixtures (padrão: frontend/src/demo/fixtures)")

    def handle(self, *args, so_fichas=False, pasta=None, **opts):
        pasta = Path(pasta) if pasta else Path(settings.BASE_DIR).parent / "frontend" / "src" / "demo" / "fixtures"
        try:
            entrada = json.loads((pasta / "entrada-demo.json").read_text(encoding="utf-8"))
        except FileNotFoundError as erro:
            raise CommandError(f"Arquivo não encontrado: {erro.filename}")
        cfg = config()
        self.stdout.write(f"Provedor: {cfg.provedor} | modelo: {cfg.modelo}")
        base = {"provedor": cfg.provedor, "modelo": cfg.modelo, "gravado_em": datetime.now().isoformat(timespec="seconds")}

        try:
            if not so_fichas:
                self._gravar_foto(pasta, base)
            self._gravar_fichas(pasta, base, entrada)
        except (FalhaDeCota, ProvedorIndisponivel, FotoIlegivel, ValueError) as erro:
            raise CommandError(f"A IA falhou ({type(erro).__name__}): {erro}. Nada foi sobrescrito depois desse ponto.")

    def _gravar_foto(self, pasta, base):
        foto = pasta / FOTO
        if not foto.exists():
            raise CommandError(f"Foto não encontrada: {foto} (gere o PNG a partir do HTML; veja o comentário nele).")
        uso, inicio = Uso(), time.monotonic()
        cardapio, _ = extrair_cardapio_com_uso(foto.read_bytes(), "image/png", esperar=self._esperar, uso=uso)
        segundos = round(time.monotonic() - inicio, 1)
        saida = {
            "_origem": f"Resposta REAL da IA para {FOTO}, gravada pelo comando gravar_demo. Não editar à mão.",
            **base,
            "segundos": segundos,
            "chamadas": uso.chamadas,
            "tokens_entrada": uso.entrada,
            "tokens_saida": uso.saida,
            "resposta": cardapio.model_dump(mode="json"),
        }
        self._escrever(pasta / "gravado-extracao.json", saida)
        for p in cardapio.pratos:
            preco = f"R$ {p.preco:.2f}" if p.preco is not None else "(sem preço)"
            self.stdout.write(f"  [{p.categoria or '-'}] {p.nome} — {preco}")
        self.stdout.write(self.style.SUCCESS(f"{len(cardapio.pratos)} pratos em {segundos}s, {uso.chamadas} chamada(s)"))

    def _gravar_fichas(self, pasta, base, entrada):
        cadastro = [{"id": i["id"], "nome": i["nome"], "unidade": i["unidade"]} for i in entrada["ingredientes"]]
        fichas = []
        for f in entrada["fichas"]:
            uso, inicio = Uso(), time.monotonic()
            try:
                itens = [i.para_json() for i in extrair_ficha(f["texto"], cadastro, f["prato"], esperar=self._esperar, uso=uso)]
            except TextoSemIngredientes:
                itens = []
            segundos = round(time.monotonic() - inicio, 1)
            fichas.append({"prato": f["prato"], "texto": f["texto"], "segundos": segundos, "chamadas": uso.chamadas, "itens": itens})
            self.stdout.write(f"\n== {f['prato']}: {f['texto']}")
            for i in itens:
                ligado = i["ingrediente"]["nome"] if i["ingrediente"] else "(sem ligação)"
                qtd = f"{i['quantidade']} {i['unidade'] or ''}" if i["quantidade"] else "(sem quantidade)"
                aviso = f"  motivos: {', '.join(i['motivos'])}" if i["motivos"] else ""
                self.stdout.write(f"   {i['nome_lido']!r} -> {ligado} | {qtd}{aviso}")
        saida = {
            "_origem": "Respostas REAIS da IA para as frases de entrada-demo.json, gravadas pelo comando gravar_demo. Não editar à mão.",
            **base,
            "fichas": fichas,
        }
        self._escrever(pasta / "gravado-fichas.json", saida)

    @staticmethod
    def _escrever(caminho, dados):
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _esperar(self, segundos):
        self.stdout.write(f"   provedor recusou (429/503): esperando {segundos:.0f}s...")
        time.sleep(segundos)
