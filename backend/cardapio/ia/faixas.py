"""Divisão da foto em faixas horizontais para cardápios grandes. Sem IA, sem Django.

Por quê: o modelo tem um teto de tokens de SAÍDA por resposta. Cardápio com muitos itens
estoura o teto e o JSON vem cortado. Lendo a foto em pedaços, cada resposta é menor.

- recortar: N faixas de cima para baixo, com sobreposição, para que um prato na linha de
  corte apareça inteiro em pelo menos uma faixa.
- juntar: concatena as listas e remove os pratos repetidos pela sobreposição.
"""
import io

from PIL import Image

from cardapio.avaliacao import normalizar


def recortar(imagem: bytes, n: int = 3, sobreposicao: float = 0.12, minimo_px: int = 80) -> list[bytes]:
    """Devolve `n` faixas (JPEG) de cima para baixo.

    A sobreposição entre faixas vizinhas é `sobreposicao` (fração da altura total), mas nunca
    menos que `minimo_px`: tem que ser maior que a altura de um item, senão um prato na linha de
    corte pode ficar cortado nas duas faixas. Limitada a metade de uma faixa.
    """
    if n < 1:
        raise ValueError("n deve ser >= 1")
    if not 0 <= sobreposicao < 0.5:
        raise ValueError("sobreposicao deve estar entre 0 e 0.5")

    img = Image.open(io.BytesIO(imagem))
    img = img.convert("RGB")  # JPEG não aceita transparência
    largura, altura = img.size

    passo = altura / n
    margem = min(max(altura * sobreposicao, minimo_px), passo / 2)
    faixas = []
    for i in range(n):
        topo = max(0, round(i * passo - (margem if i > 0 else 0)))
        base = min(altura, round((i + 1) * passo + (margem if i < n - 1 else 0)))
        buffer = io.BytesIO()
        img.crop((0, topo, largura, base)).save(buffer, format="JPEG", quality=90)
        faixas.append(buffer.getvalue())
    return faixas


def _mesmo_prato(a, b) -> bool:
    """Mesmo nome (normalizado) e preço compatível: iguais, ou um deles sem preço.

    Preços diferentes com o mesmo nome são tamanhos/variações distintas, não repetição.
    """
    if normalizar(a.nome) != normalizar(b.nome):
        return False
    return a.preco is None or b.preco is None or a.preco == b.preco


def juntar(listas: list[list]) -> list:
    """Concatena as listas de pratos de cada faixa, em ordem, removendo repetidos.

    Só compara com pratos de faixas ANTERIORES: dois itens iguais dentro da mesma faixa
    são do cardápio e ficam. Entre repetidos, vence a versão que tem preço.
    """
    resultado = []
    for lista in listas:
        candidatos = list(range(len(resultado)))  # posições de faixas anteriores ainda não casadas
        for prato in lista:
            pos = next((i for i in candidatos if _mesmo_prato(resultado[i], prato)), None)
            if pos is None:
                resultado.append(prato)
                continue
            candidatos.remove(pos)  # cada prato anterior casa com no máximo um
            if resultado[pos].preco is None and prato.preco is not None:
                resultado[pos] = prato
    return resultado
