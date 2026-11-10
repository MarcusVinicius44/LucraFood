"""Compara a ficha extraída pela IA com a resposta esperada (Python puro, sem API).

Ingrediente: acerta se o item esperado aparece ligado ao mesmo id do cadastro; quando o
esperado é null (fora do cadastro), acerta se a IA também deixou null para um nome parecido.
Quantidade: conta em todo item cujo ingrediente foi acertado (inclusive os null). Compara a
quantidade na unidade do cadastro, ou, fora do cadastro, na unidade-base da medida escrita,
conferindo também "unidade" quando o esperado a informa. null esperado = medida informal
ou ausente (ex.: "1 concha"), que o sistema não deve converter.
Errados: itens ligados a um id que não era esperado (associação errada ou inventada).
Revisão: quando o esperado traz "confirmar" (true/false), confere `precisa_confirmar` do item
acertado. Mede se o sistema pede conferência quando deve (e só quando deve).
"""
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def _decimal(valor):
    return None if valor is None else Decimal(str(valor))


@dataclass
class ResultadoFicha:
    esperados: int = 0
    ingrediente_ok: int = 0
    quantidades: int = 0  # itens com ingrediente acertado, onde a quantidade é avaliada
    quantidade_ok: int = 0
    faltando: list = field(default_factory=list)  # nomes esperados que a IA não ligou certo
    quantidade_errada: list = field(default_factory=list)  # (nome, esperado, extraído)
    errados: list = field(default_factory=list)  # (nome lido, id) ligados a id não esperado
    sobrando: list = field(default_factory=list)  # itens null a mais (não esperados)
    revisoes: int = 0  # itens acertados com "confirmar" no esperado
    revisao_ok: int = 0
    revisao_errada: list = field(default_factory=list)  # (nome, esperado, veio, motivos)

    def somar(self, outro: "ResultadoFicha"):
        for nome in ("esperados", "ingrediente_ok", "quantidades", "quantidade_ok", "revisoes", "revisao_ok"):
            setattr(self, nome, getattr(self, nome) + getattr(outro, nome))
        for nome in ("faltando", "quantidade_errada", "errados", "sobrando", "revisao_errada"):
            getattr(self, nome).extend(getattr(outro, nome))


def comparar(esperado: list[dict], extraido: list[dict]) -> ResultadoFicha:
    """`esperado`: [{"nome", "ingrediente": id|None, "quantidade": str|None}].
    `extraido`: itens no formato de ItemExtraido.para_json()."""
    r = ResultadoFicha(esperados=len(esperado))
    livres = list(extraido)

    def tirar(condicao):
        for item in livres:
            if condicao(item):
                livres.remove(item)
                return item
        return None

    def id_de(item):
        return item["ingrediente"]["id"] if item["ingrediente"] else None

    for esp in esperado:
        if esp["ingrediente"] is not None:
            achado = tirar(lambda item: id_de(item) == esp["ingrediente"])
        else:
            alvo = _normalizar(esp["nome"])
            achado = tirar(
                lambda item: id_de(item) is None
                and (alvo in _normalizar(item["nome_lido"]) or _normalizar(item["nome_lido"]) in alvo)
            )
        if achado is None:
            r.faltando.append(esp["nome"])
            continue
        r.ingrediente_ok += 1
        r.quantidades += 1
        mesma_quantidade = _decimal(achado["quantidade"]) == _decimal(esp["quantidade"])
        # "unidade" é obrigatória no esperado quando não há cadastro para dizer se 150 é g ou ml.
        mesma_unidade = "unidade" not in esp or achado.get("unidade") == esp["unidade"]
        if mesma_quantidade and mesma_unidade:
            r.quantidade_ok += 1
        else:
            esperado_txt = f"{esp['quantidade']} {esp.get('unidade') or ''}".strip()
            obtido_txt = f"{achado['quantidade']} {achado.get('unidade') or ''}".strip()
            r.quantidade_errada.append((esp["nome"], esperado_txt, obtido_txt))
        if "confirmar" in esp:
            r.revisoes += 1
            veio = bool(achado.get("precisa_confirmar"))
            if veio == esp["confirmar"]:
                r.revisao_ok += 1
            else:
                r.revisao_errada.append((esp["nome"], esp["confirmar"], veio, achado.get("motivos", [])))

    for item in livres:
        if id_de(item) is None:
            r.sobrando.append(item["nome_lido"])
        else:
            r.errados.append((item["nome_lido"], id_de(item)))
    return r
