"""Ficha em conversa: escolha da pergunta, conta da resposta e a rota (IA sempre simulada)."""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from . import calculos
from .avaliacao_conversa import comparar_resposta
from .ia import conversa as ia_conversa
from .models import Ingrediente
from .tests_ficha import BaseFicha, _cliente

QUEIJO = {"id": 3, "nome": "Queijo prato", "unidade": "g"}
OLEO = {"id": 9, "nome": "Óleo de soja", "unidade": "ml"}
PAO = {"id": 1, "nome": "Pão", "unidade": "un"}


def _item(chave, ingrediente, quantidade=None, quantidade_lida=None, unidade_lida=None, motivos=()):
    return ia_conversa.ItemConversa(
        chave=chave,
        nome_lido="x",
        ingrediente=ingrediente,
        quantidade=None if quantidade is None else Decimal(quantidade),
        quantidade_lida=None if quantidade_lida is None else Decimal(quantidade_lida),
        unidade_lida=unidade_lida,
        motivos=list(motivos),
    )


def _lida(quantidade=None, unidade=None, entendeu=True, nao_sabe=False):
    return ia_conversa.RespostaLida(entendeu=entendeu, nao_sabe=nao_sabe, quantidade=quantidade, unidade=unidade)


class QuantidadeDeMedidasTest(TestCase):
    def test_multiplica_e_converte(self):
        self.assertEqual(calculos.quantidade_de_medidas(2, 20, "g", "g"), Decimal("40.000"))
        self.assertEqual(calculos.quantidade_de_medidas(1, Decimal("0.01"), "l", "ml"), Decimal("10.000"))

    def test_zero_ou_unidade_errada_e_erro(self):
        for args in ((0, 20, "g", "g"), (2, 20, "ml", "g")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                calculos.quantidade_de_medidas(*args)


class ProximaPerguntaTest(TestCase):
    def test_ordem_e_tipo_de_cada_motivo(self):
        itens = [
            _item(1, PAO, quantidade=1, motivos=["sem_quantidade"]),  # pão assumido 1: não pergunta
            _item(2, None, quantidade_lida=150, unidade_lida="g", motivos=["sem_ingrediente"]),  # sem cadastro
            _item(3, QUEIJO, quantidade_lida=2, unidade_lida="fatia", motivos=["unidade_informal"]),
            _item(4, OLEO, quantidade_lida=50, unidade_lida="g", motivos=["unidade_incompativel"]),
            _item(5, QUEIJO, quantidade_lida=150, motivos=["sem_unidade"]),
            _item(6, OLEO, motivos=["sem_quantidade"]),
        ]
        tipos = []
        pulados = []
        while (p := ia_conversa.proxima_pergunta(itens, pulados)) is not None:
            tipos.append((p.chave, p.tipo))
            pulados.append(p.chave)
        self.assertEqual(tipos, [(3, "por_medida"), (4, "converter"), (5, "unidade"), (6, "total")])

    def test_textos(self):
        fatia = ia_conversa.proxima_pergunta([_item(1, QUEIJO, quantidade_lida=2, unidade_lida="fatia", motivos=["unidade_informal"])])
        self.assertEqual(fatia.texto, "Quanto dá mais ou menos 1 fatia de Queijo prato, em gramas?")
        unidade = ia_conversa.proxima_pergunta([_item(1, QUEIJO, quantidade_lida=150, motivos=["sem_unidade"])])
        self.assertEqual(unidade.texto, "Você escreveu 150 de Queijo prato. São gramas?")

    def test_item_com_quantidade_digitada_nao_pergunta(self):
        item = _item(1, QUEIJO, quantidade=40, quantidade_lida=2, unidade_lida="fatia", motivos=["unidade_informal"])
        self.assertIsNone(ia_conversa.proxima_pergunta([item]))


class AplicarRespostaTest(TestCase):
    def test_fatia_multiplica_pela_quantidade_escrita(self):
        item = _item(1, QUEIJO, quantidade_lida=2, unidade_lida="fatia", motivos=["unidade_informal", "nome_diferente"])
        a = ia_conversa.aplicar_resposta(item, "por_medida", _lida(20, "g"))
        self.assertEqual((a.quantidade, a.unidade, a.motivos), (Decimal("40.000"), "g", ["nome_diferente"]))
        self.assertEqual(a.origem, "2 × 20 g por fatia = 40 g (você informou)")

    def test_fio_sem_numero_conta_como_1_e_converte_litro(self):
        item = _item(1, OLEO, unidade_lida="fio", motivos=["unidade_informal"])
        a = ia_conversa.aplicar_resposta(item, "por_medida", _lida(Decimal("0.01"), "l"))
        self.assertEqual(a.quantidade, Decimal("10.000"))

    def test_so_o_numero_usa_a_unidade_da_pergunta(self):
        a = ia_conversa.aplicar_resposta(_item(1, OLEO, motivos=["sem_quantidade"]), "total", _lida(30))
        self.assertEqual((a.quantidade, a.unidade, a.motivos), (Decimal("30.000"), "ml", []))

    def test_confirmar_unidade_usa_o_numero_escrito(self):
        item = _item(1, QUEIJO, quantidade_lida=150, motivos=["sem_unidade"])
        a = ia_conversa.aplicar_resposta(item, "unidade", _lida(None, "g"))
        self.assertEqual(a.quantidade, Decimal("150.000"))

    def test_unidade_caseira_ou_incompativel_na_resposta_e_invalida(self):
        item = _item(1, QUEIJO, quantidade_lida=2, unidade_lida="fatia", motivos=["unidade_informal"])
        for lida in (_lida(2, "colher"), _lida(20, "ml")):
            with self.subTest(lida=lida), self.assertRaises(ia_conversa.RespostaInvalida):
                ia_conversa.aplicar_resposta(item, "por_medida", lida)

    def test_sem_numero_e_invalida(self):
        with self.assertRaises(ia_conversa.RespostaInvalida):
            ia_conversa.aplicar_resposta(_item(1, OLEO, motivos=["sem_quantidade"]), "total", _lida(None, "ml"))


class InterpretarRespostaTest(TestCase):
    def test_le_e_normaliza_virgula(self):
        cliente = _cliente('{"entendeu": true, "nao_sabe": false, "quantidade": "1,5", "unidade": "kg"}')
        lida = ia_conversa.interpretar_resposta("Quanto vai?", "um quilo e meio", cliente=cliente)
        self.assertEqual((lida.quantidade, lida.unidade), (Decimal("1.5"), "kg"))
        mensagem = cliente.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertIn("um quilo e meio", mensagem)

    def test_json_invalido_duas_vezes_e_value_error(self):
        with self.assertRaises(ValueError):
            ia_conversa.interpretar_resposta("Quanto vai?", "20", cliente=_cliente("nada", '{"quantidade": -1}'))


class ConversaViewTest(BaseFicha):
    def setUp(self):
        super().setUp()
        self.queijo.nome = "Queijo prato"
        self.queijo.save()
        self.url = f"/api/pratos/{self.prato.id}/ficha/conversa/"
        self.itens = [
            {"chave": 1, "nome_lido": "pão", "ingrediente": self.pao.id, "quantidade": "1", "motivos": ["sem_quantidade"]},
            {
                "chave": 2,
                "nome_lido": "queijo prato",
                "ingrediente": self.queijo.id,
                "quantidade": None,
                "quantidade_lida": "2",
                "unidade_lida": "fatia",
                "motivos": ["unidade_informal"],
            },
            {"chave": 3, "nome_lido": "carne", "ingrediente": self.carne.id, "quantidade": None, "motivos": ["sem_quantidade"]},
        ]

    def post(self, dados, *respostas_ia):
        with patch("cardapio.ia.conversa.get_cliente", return_value=_cliente(*respostas_ia)) as falso:
            resposta = self.client.post(self.url, dados, content_type="application/json")
        return resposta, falso

    def test_sem_resposta_devolve_a_primeira_pergunta_sem_ia(self):
        resposta, falso = self.post({"itens": self.itens})
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual((corpo["pergunta"]["chave"], corpo["pergunta"]["tipo"]), (2, "por_medida"))
        self.assertIsNone(corpo["atualizado"])
        falso.assert_not_called()

    def test_resposta_atualiza_e_passa_para_a_proxima(self):
        ia = '{"entendeu": true, "nao_sabe": false, "quantidade": 20, "unidade": "g"}'
        resposta, _ = self.post({"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "uns 20 gramas"}, ia)
        corpo = resposta.json()
        self.assertEqual(corpo["atualizado"]["quantidade"], "40.000")
        self.assertEqual(corpo["atualizado"]["motivos"], [])
        self.assertEqual(corpo["pergunta"]["chave"], 3)
        self.assertEqual(self.prato.itens.count(), 0)  # nada gravado

    def test_nao_sabe_pula(self):
        ia = '{"entendeu": true, "nao_sabe": true, "quantidade": null, "unidade": null}'
        corpo = self.post({"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "sei lá"}, ia)[0].json()
        self.assertEqual(corpo["pulados"], [2])
        self.assertEqual(corpo["pergunta"]["chave"], 3)

    def test_nao_entendeu_repete_a_pergunta_com_aviso(self):
        ia = '{"entendeu": false, "nao_sabe": false, "quantidade": null, "unidade": null}'
        corpo = self.post({"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "depende"}, ia)[0].json()
        self.assertIsNone(corpo["atualizado"])
        self.assertTrue(corpo["aviso"])
        self.assertEqual(corpo["pergunta"]["chave"], 2)

    def test_unidade_caseira_na_resposta_repete_com_aviso(self):
        ia = '{"entendeu": true, "nao_sabe": false, "quantidade": 1, "unidade": "colher"}'
        corpo = self.post({"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "uma colher"}, ia)[0].json()
        self.assertIn("gramas", corpo["aviso"])
        self.assertEqual(corpo["pergunta"]["chave"], 2)

    def test_acabou(self):
        itens = [dict(self.itens[0])]
        corpo = self.post({"itens": itens})[0].json()
        self.assertIsNone(corpo["pergunta"])

    def test_ingrediente_de_outro_restaurante_vira_sem_cadastro(self):
        from .models import Restaurante

        outro = Restaurante.objects.create(nome="Outro")
        alheio = Ingrediente.objects.create(restaurante=outro, nome="Bacon", preco_embalagem=10, quantidade_embalagem=100)
        itens = [{"chave": 1, "ingrediente": alheio.id, "quantidade": None, "motivos": ["sem_quantidade"]}]
        corpo = self.post({"itens": itens})[0].json()
        self.assertEqual((corpo["pergunta"], corpo["sem_cadastro"]), (None, 1))

    def test_pergunta_de_item_ja_resolvido_400(self):
        itens = [dict(self.itens[1], quantidade="40")]
        resposta, falso = self.post({"itens": itens, "pergunta": {"chave": 2}, "resposta": "20 g"})
        self.assertEqual(resposta.status_code, 400)
        falso.assert_not_called()

    def test_validacao(self):
        self.assertEqual(self.post({"itens": []})[0].status_code, 400)
        longa = {"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "x" * 201}
        self.assertEqual(self.post(longa)[0].status_code, 400)

    def test_erro_da_ia_vira_502(self):
        resposta, _ = self.post({"itens": self.itens, "pergunta": {"chave": 2}, "resposta": "20"}, "nada", "nada")
        self.assertEqual(resposta.status_code, 502)


class AvaliacaoConversaTest(TestCase):
    def test_compara_quantidade_unidade_e_flags(self):
        esperado = {"entendeu": True, "nao_sabe": False, "quantidade": "20", "unidade": "g"}
        self.assertTrue(comparar_resposta(esperado, {"entendeu": True, "nao_sabe": False, "quantidade": "20.0", "unidade": "g"}))
        self.assertFalse(comparar_resposta(esperado, {"entendeu": True, "nao_sabe": False, "quantidade": "2", "unidade": "g"}))
        self.assertFalse(comparar_resposta(esperado, {"entendeu": True, "nao_sabe": False, "quantidade": "20", "unidade": None}))

    def test_nao_entendeu_ignora_numeros(self):
        esperado = {"entendeu": False, "nao_sabe": False, "quantidade": None, "unidade": None}
        self.assertTrue(comparar_resposta(esperado, {"entendeu": False, "nao_sabe": False, "quantidade": "5", "unidade": "g"}))
        self.assertFalse(comparar_resposta(esperado, {"entendeu": True, "nao_sabe": False, "quantidade": "5", "unidade": "g"}))

    def test_unidade_none_no_esperado_aceita_ausente(self):
        esperado = {"entendeu": True, "nao_sabe": False, "quantidade": "30", "unidade": None}
        self.assertTrue(comparar_resposta(esperado, {"entendeu": True, "nao_sabe": False, "quantidade": "30", "unidade": None}))
