"""Gera cópias das fotos de avaliação como o navegador as enviaria depois de reduzir (frontend/src/imagem.ts).

Lado maior até 2400 px (nunca aumenta), transparência vira preto (o canvas faz isso no JPEG), JPEG na
qualidade pedida. Copia os gabaritos junto, para rodar a avaliação na pasta gerada:

    python evals/cardapios/gerar_jpeg.py SAIDA --qualidade 92
    cd backend && python manage.py avaliar_extracao --pasta SAIDA
"""
import argparse
import shutil
from pathlib import Path

from PIL import Image

LADO_MAX = 2400
PASTA = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("saida", type=Path)
    parser.add_argument("--qualidade", type=int, default=92, help="0-100 (o navegador usa 0-1: 92 = 0.92)")
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    for foto in sorted(PASTA.glob("cardapio_*.png")):
        imagem = Image.open(foto).convert("RGBA")
        escala = min(1, LADO_MAX / max(imagem.size))
        if escala < 1:
            imagem = imagem.resize((round(imagem.width * escala), round(imagem.height * escala)), Image.LANCZOS)
        fundo = Image.new("RGB", imagem.size, (0, 0, 0))
        fundo.paste(imagem, mask=imagem.getchannel("A"))
        destino = args.saida / f"{foto.stem}.jpg"
        fundo.save(destino, "JPEG", quality=args.qualidade)
        shutil.copy(foto.with_suffix(".json"), args.saida / f"{foto.stem}.json")
        print(f"{destino.name}: {imagem.size[0]}x{imagem.size[1]}, {destino.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
