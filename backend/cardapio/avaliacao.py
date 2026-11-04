"""Comparação entre o que a extração devolveu e o gabarito. Sem IA, sem Django.

Cada prato do gabarito é pareado com no máximo um prato extraído, pelo nome
(normalizado: sem acento, caixa ou pontuação; tolera diferenças pequenas).
- encontrado: par existe (preço pode estar certo ou errado)
- faltando:   está no gabarito e não foi extraído
- inventado:  foi extraído e não está no gabarito
- preço errado: par existe, mas o preço difere (null no gabarito vs valor extraído também conta)
"""
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Optional

LIMIAR_NOME = 0.75


def normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def similaridade(a: str, b: str) -> float:
    na, nb = normalizar(a), normalizar(b)
    ta, tb = set(na.split()), set(nb.split())
    # "Bacalhau na Brasa" dentro de "Bacalhau na Brasa Prato Individual": mesmo prato.
    if min(len(ta), len(tb)) >= 2 and (ta <= tb or tb <= ta):
        return 0.95
    return SequenceMatcher(None, na, nb).ratio()


@dataclass
class Resultado:
    gabarito: int = 0
    extraidos: int = 0
    encontrados: int = 0
    faltando: list = field(default_factory=list)        # nomes do gabarito
    inventados: list = field(default_factory=list)      # nomes extraídos
    precos_errados: list = field(default_factory=list)  # (nome_gabarito, esperado, obtido)

    def somar(self, outro: "Resultado") -> None:
        self.gabarito += outro.gabarito
        self.extraidos += outro.extraidos
        self.encontrados += outro.encontrados
        self.faltando += outro.faltando
        self.inventados += outro.inventados
        self.precos_errados += outro.precos_errados


def _preco_igual(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return Decimal(a) == Decimal(b)


def comparar(gabarito: list, extraidos: list) -> Resultado:
    """Ambos são listas de objetos com `.nome` e `.preco` (ex.: PratoExtraido)."""
    pares = []
    for i, g in enumerate(gabarito):
        for j, e in enumerate(extraidos):
            nota = similaridade(g.nome, e.nome)
            if nota >= LIMIAR_NOME:
                # Desempate: com nomes parecidos (ex.: tamanhos), o preço igual vence.
                bonus = 0.001 if _preco_igual(g.preco, e.preco) else 0
                pares.append((nota + bonus, i, j))
    pares.sort(reverse=True)

    usados_g, usados_e, casados = set(), set(), []
    for _nota, i, j in pares:
        if i not in usados_g and j not in usados_e:
            usados_g.add(i)
            usados_e.add(j)
            casados.append((i, j))

    r = Resultado(gabarito=len(gabarito), extraidos=len(extraidos), encontrados=len(casados))
    r.faltando = [g.nome for i, g in enumerate(gabarito) if i not in usados_g]
    r.inventados = [e.nome for j, e in enumerate(extraidos) if j not in usados_e]
    for i, j in sorted(casados):
        if not _preco_igual(gabarito[i].preco, extraidos[j].preco):
            r.precos_errados.append((gabarito[i].nome, gabarito[i].preco, extraidos[j].preco))
    return r
