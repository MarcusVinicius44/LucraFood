"""Medidas caseiras lembradas: o dono ensina "1 fatia de Queijo prato = 18 g" na conversa, a medida
é gravada quando ele confirma a ficha e usada na próxima receita (IA sempre simulada)."""
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from .ia import conversa as ia_conversa
from .ia import ficha as ia_ficha
from .models import Ingrediente, MedidaCaseira, Restaurante
from .tests_conversa import QUEIJO, _item, _lida
from .tests_ficha import BaseFicha, _cliente


def _itens(*itens):
    return json.dumps({"itens": list(itens)})


class ChaveMedidaTest(TestCase):
    def test_singular_sem_acento_e_minusculo(self):
        casos = {
            "fatia": "fatia",
            "Fatias": "fatia",
            "colheres de sopa": "colher de sopa",
            "Conchas ": "concha",
            "pitadas": "pitada",
            "": "",
            None: "",
        }
        for medida, chave in casos.items():
            with self.subTest(medida=medida):
                self.assertEqual(ia_ficha.chave_medida(medida), chave)


class AprenderNaConversaTest(TestCase):
    def test_por_medida_devolve_a_medida_na_unidade_do_cadastro(self):
        item = _item(1, QUEIJO, quantidade_lida=2, unidade_lida="fatias", motivos=["unidade_informal"])
        a = ia_conversa.aplicar_resposta(item, "por_medida", _lida("0,02", "kg"))
        self.assertEqual(a.quantidade, Decimal("40.000"))
        self.assertEqual(a.medida, {"medida": "fatia", "quantidade": "20.000", "nome": "Queijo prato"})

    def test_outros_tipos_nao_ensinam_medida(self):
        item = _item(1, QUEIJO, quantidade_lida=150, motivos=["sem_unidade"])
        self.assertIsNone(ia_conversa.aplicar_resposta(item, "unidade", _lida(None, "g")).medida)

    def test_sem_medida_escrita_nao_ensina(self):
        item = _item(1, QUEIJO, quantidade_lida=2, unidade_lida=None, motivos=["unidade_informal"])
        self.assertIsNone(ia_conversa.aplicar_resposta(item, "por_medida", _lida(20, "g")).medida)


class UsarNaLeituraTest(TestCase):
    CADASTRO = [{"id": 3, "nome": "Queijo prato", "unidade": "g"}, {"id": 4, "nome": "Leite", "unidade": "ml"}]

    def extrair(self, texto_ia, medidas):
        return ia_ficha.extrair_ficha("t", self.CADASTRO, cliente=_cliente(texto_ia), medidas=medidas)

    def item(self, nome, id_, quantidade, unidade):
        return {"nome_lido": nome, "ingrediente": id_, "quantidade": quantidade, "unidade": unidade}

    def test_medida_salva_vira_quantidade_marcada(self):
        (item,) = self.extrair(_itens(self.item("queijo prato", 3, 2, "fatias")), {(3, "fatia"): Decimal("18")})
        self.assertEqual(item.quantidade, Decimal("36.000"))
        self.assertEqual(item.motivos, ["medida_salva"])
        self.assertEqual(item.estimativa, "2 × 18 g por fatia = 36 g (medida que você ensinou)")
        self.assertEqual(item.para_json()["estimativa"], item.estimativa)

    def test_medida_de_outro_ingrediente_ou_outra_medida_nao_vale(self):
        medidas = {(4, "fatia"): Decimal("18"), (3, "concha"): Decimal("100")}
        (item,) = self.extrair(_itens(self.item("queijo prato", 3, 2, "fatia")), medidas)
        self.assertIsNone(item.quantidade)
        self.assertEqual(item.motivos, ["unidade_informal"])

    def test_sem_medidas_nada_muda(self):
        (item,) = self.extrair(_itens(self.item("queijo prato", 3, 2, "fatia")), None)
        self.assertEqual((item.quantidade, item.motivos, item.estimativa), (None, ["unidade_informal"], None))


class MedidasNaApiTest(BaseFicha):
    def confirmar(self, medidas, itens=None):
        itens = itens or [{"ingrediente": self.queijo.id, "quantidade": "36"}]
        return self.client.post(
            f"/api/pratos/{self.prato.id}/ficha/confirmar/",
            {"itens": itens, "medidas": medidas},
            content_type="application/json",
        )

    def test_confirmar_grava_e_atualiza_a_medida(self):
        resposta = self.confirmar([{"ingrediente": self.queijo.id, "medida": "Fatias", "quantidade": "18"}])
        self.assertEqual(resposta.status_code, 200)
        m = MedidaCaseira.objects.get()
        self.assertEqual((m.ingrediente, m.medida, m.quantidade), (self.queijo, "fatia", Decimal("18")))
        self.confirmar([{"ingrediente": self.queijo.id, "medida": "fatia", "quantidade": "20"}])
        self.assertEqual(MedidaCaseira.objects.get().quantidade, Decimal("20"))

    def test_confirmar_sem_medidas_continua_funcionando(self):
        resposta = self.client.post(
            f"/api/pratos/{self.prato.id}/ficha/confirmar/",
            {"itens": [{"ingrediente": self.queijo.id, "quantidade": "36"}]},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(MedidaCaseira.objects.exists())

    def test_medida_invalida_nao_grava_nem_a_ficha(self):
        outro = Restaurante.objects.create(nome="Outro")
        de_fora = Ingrediente.objects.create(
            restaurante=outro, nome="X", unidade="g", preco_embalagem=1, quantidade_embalagem=1
        )
        for medida in (
            {"ingrediente": de_fora.id, "medida": "fatia", "quantidade": "18"},
            {"ingrediente": self.queijo.id, "medida": "fatia", "quantidade": "0"},
            {"ingrediente": self.queijo.id, "medida": "  ", "quantidade": "18"},
        ):
            with self.subTest(medida=medida):
                self.assertEqual(self.confirmar([medida]).status_code, 400)
        self.assertFalse(MedidaCaseira.objects.exists())
        self.assertFalse(self.prato.itens.exists())

    def test_ficha_invalida_nao_grava_a_medida(self):
        resposta = self.confirmar(
            [{"ingrediente": self.queijo.id, "medida": "fatia", "quantidade": "18"}],
            itens=[{"ingrediente": self.queijo.id, "quantidade": "0"}],
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(MedidaCaseira.objects.exists())

    def test_leitura_do_texto_usa_a_medida_do_restaurante(self):
        MedidaCaseira.objects.create(ingrediente=self.queijo, medida="fatia", quantidade=Decimal("18"))
        ia = _itens({"nome_lido": "queijo", "ingrediente": self.queijo.id, "quantidade": 2, "unidade": "fatias"})
        with patch("cardapio.ia.ficha.get_cliente", return_value=_cliente(ia)):
            resposta = self.client.post(
                f"/api/pratos/{self.prato.id}/ficha/extrair/", {"texto": "2 fatias de queijo"}, content_type="application/json"
            )
        self.assertEqual(resposta.status_code, 200)
        (item,) = resposta.json()["itens"]
        self.assertEqual((item["quantidade"], item["motivos"]), ("36.000", ["medida_salva"]))

    def test_ingrediente_lista_e_esquece_medidas(self):
        m = MedidaCaseira.objects.create(ingrediente=self.queijo, medida="fatia", quantidade=Decimal("18"))
        lista = self.client.get(f"/api/restaurantes/{self.restaurante.id}/ingredientes/").json()
        queijo = next(i for i in lista if i["id"] == self.queijo.id)
        self.assertEqual(queijo["medidas"], [{"id": m.id, "medida": "fatia", "quantidade": "18.000"}])
        self.assertEqual(self.client.delete(f"/api/medidas/{m.id}/").status_code, 204)
        self.assertFalse(MedidaCaseira.objects.exists())

    def test_mudar_a_unidade_esquece_as_medidas(self):
        MedidaCaseira.objects.create(ingrediente=self.queijo, medida="fatia", quantidade=Decimal("18"))
        url = f"/api/ingredientes/{self.queijo.id}/"
        self.client.patch(url, {"preco_embalagem": "50"}, content_type="application/json")
        self.assertTrue(MedidaCaseira.objects.exists())
        self.assertEqual(self.client.patch(url, {"unidade": "un"}, content_type="application/json").status_code, 200)
        self.assertFalse(MedidaCaseira.objects.exists())
