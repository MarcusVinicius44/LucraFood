from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase

from . import calculos
from .ia.extracao import extrair_cardapio
from .models import Restaurante


def _resposta(texto):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=texto))])


class CalculosTest(TestCase):
    def test_custo_prato(self):
        # 150 g de carne a R$0,042/g + 1 pão a R$1,20 + embalagem R$0,80
        itens = [(Decimal("150"), Decimal("0.042")), (Decimal("1"), Decimal("1.20"))]
        self.assertEqual(calculos.custo_prato(itens, Decimal("0.80")), Decimal("8.30"))

    def test_margem_delivery_menor_que_balcao(self):
        d = calculos.diagnosticar(preco=Decimal("25"), custo=Decimal("12"), taxa_app_pct=23,
                                  impostos_pct=6, margem_desejada_pct=30)
        self.assertEqual(d.margem_balcao, Decimal("46.0"))
        self.assertEqual(d.margem_delivery, Decimal("23.0"))
        self.assertEqual(d.semaforo, "amarelo")
        # 12 / (1 - 0.23 - 0.06 - 0.30) = 29.27
        self.assertEqual(d.preco_sugerido_delivery, Decimal("29.27"))

    def test_prejuizo_fica_vermelho(self):
        d = calculos.diagnosticar(Decimal("15"), Decimal("12"), 23, 6, 30)
        self.assertEqual(d.semaforo, "vermelho")

    def _semaforo(self, preco, **limiares):
        # custo 12, taxa 23% + impostos 6% => margem delivery = (preco - 12 - 0.29*preco)/preco
        return calculos.diagnosticar(Decimal(preco), Decimal("12"), 23, 6, **limiares)

    def test_vermelho_abaixo_da_margem_minima_mesmo_sem_prejuizo(self):
        # preço 20: sobra 20 - 12 - 5,80 = 2,20 => 11,0% (amarelo no padrão)
        self.assertEqual(self._semaforo("20").semaforo, "amarelo")
        # preço 19: sobra 19 - 12 - 5,51 = 1,49 => 7,8% (> 0, mas abaixo de 10%)
        d = self._semaforo("19")
        self.assertGreater(d.margem_delivery, 0)
        self.assertLess(d.margem_delivery, Decimal("10"))
        self.assertEqual(d.semaforo, "vermelho")

    def test_verde_quando_atinge_a_margem_desejada(self):
        d = self._semaforo("30")  # (30 - 12 - 8,70)/30 = 31,0%
        self.assertEqual(d.semaforo, "verde")
        self.assertIsNone(d.preco_sugerido_delivery)

    def test_padroes_quando_limiares_nao_informados(self):
        com_padrao = self._semaforo("25")
        explicito = self._semaforo("25", margem_desejada_pct=30, margem_minima_pct=10)
        self.assertEqual(com_padrao, explicito)
        self.assertEqual(self._semaforo("25", margem_desejada_pct=None, margem_minima_pct=None), explicito)

    def test_limiares_configuraveis(self):
        # preço 25 => 23,0%: verde se a desejada for 20, vermelho se a mínima for 25
        self.assertEqual(self._semaforo("25", margem_desejada_pct=20, margem_minima_pct=5).semaforo, "verde")
        self.assertEqual(self._semaforo("25", margem_desejada_pct=40, margem_minima_pct=25).semaforo, "vermelho")

    def test_limiares_nas_bordas(self):
        # preço 20 => exatamente 11,0%
        self.assertEqual(self._semaforo("20", margem_minima_pct=11).semaforo, "amarelo")   # igual à mínima: não é vermelho
        self.assertEqual(self._semaforo("20", margem_desejada_pct=11).semaforo, "verde")   # igual à desejada: verde

    def test_minima_maior_que_desejada_e_erro(self):
        with self.assertRaises(ValueError):
            self._semaforo("25", margem_desejada_pct=10, margem_minima_pct=20)

    def test_taxas_impossiveis(self):
        with self.assertRaises(ValueError):
            calculos.preco_sugerido(Decimal("10"), 60, 30, 15)


class ExtracaoTest(TestCase):
    def test_le_json_com_preco_em_texto_e_bloco_think(self):
        cliente = MagicMock()
        cliente.chat.completions.create.return_value = _resposta(
            '<think>vou ler</think>{"pratos": [{"nome": "X-Tudo", "categoria": "Lanches", "preco": "R$ 24,90"},'
            '{"nome": "Suco", "preco": null}]}'
        )
        cardapio = extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual(cardapio.pratos[0].preco, Decimal("24.90"))
        self.assertIsNone(cardapio.pratos[1].preco)

    def test_tenta_de_novo_quando_json_invalido(self):
        cliente = MagicMock()
        cliente.chat.completions.create.side_effect = [
            _resposta('{"pratos": [{"nome": ""}]}'),  # nome vazio: inválido
            _resposta('{"pratos": [{"nome": "Coxinha", "preco": 7}]}'),
        ]
        cardapio = extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual(cardapio.pratos[0].nome, "Coxinha")
        self.assertEqual(cliente.chat.completions.create.call_count, 2)

    def test_desiste_depois_de_duas_falhas(self):
        cliente = MagicMock()
        cliente.chat.completions.create.return_value = _resposta("não sei")
        with self.assertRaises(ValueError):
            extrair_cardapio(b"fake", cliente=cliente)


class MargemMinimaValidacaoTest(TestCase):
    def setUp(self):
        self.r = Restaurante.objects.create(nome="Lanchonete", margem_desejada_pct=30, margem_minima_pct=10)
        self.url = f"/api/restaurantes/{self.r.id}/"

    def _patch(self, dados):
        return self.client.patch(self.url, dados, content_type="application/json")

    def test_model_clean_rejeita_minima_maior_que_desejada(self):
        self.r.margem_minima_pct = Decimal("35")
        with self.assertRaises(ValidationError) as ctx:
            self.r.full_clean()
        self.assertIn("margem_minima_pct", ctx.exception.message_dict)

    def test_model_clean_aceita_minima_igual_ou_menor(self):
        for minima in ("10", "30"):
            self.r.margem_minima_pct = Decimal(minima)
            self.r.full_clean()  # não levanta

    def test_api_devolve_400_com_mensagem_clara(self):
        resp = self._patch({"margem_minima_pct": "40"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["margem_minima_pct"],
            ["A margem mínima não pode ser maior que a margem desejada."],
        )
        self.r.refresh_from_db()
        self.assertEqual(self.r.margem_minima_pct, Decimal("10"))  # nada foi salvo

    def test_api_valida_quando_so_a_desejada_cai_abaixo_da_minima(self):
        resp = self._patch({"margem_desejada_pct": "5"})  # mínima atual é 10
        self.assertEqual(resp.status_code, 400)

    def test_api_aceita_quando_ajusta_os_dois_de_uma_vez(self):
        resp = self._patch({"margem_desejada_pct": "20", "margem_minima_pct": "20"})
        self.assertEqual(resp.status_code, 200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.margem_minima_pct, Decimal("20"))


class AvaliacaoTest(TestCase):
    def _p(self, nome, preco):
        return SimpleNamespace(nome=nome, preco=None if preco is None else Decimal(str(preco)))

    def test_conta_encontrados_faltando_inventados_e_precos_errados(self):
        from .avaliacao import comparar

        gabarito = [self._p("X-Tudo", 24.9), self._p("Suco de Laranja", 8), self._p("Coxinha", 7)]
        extraido = [self._p("X Tudo", 24.9), self._p("Suco de laranja", 9), self._p("Pastel", 6)]
        r = comparar(gabarito, extraido)
        self.assertEqual((r.gabarito, r.extraidos, r.encontrados), (3, 3, 2))
        self.assertEqual(r.faltando, ["Coxinha"])
        self.assertEqual(r.inventados, ["Pastel"])
        self.assertEqual(r.precos_errados, [("Suco de Laranja", Decimal("8"), Decimal("9"))])

    def test_nome_tolera_acento_caixa_e_sufixo(self):
        from .avaliacao import comparar

        r = comparar([self._p("Bacalhau na Brasa (Prato Individual)", 130)], [self._p("BACALHAU NA BRASA", 130)])
        self.assertEqual(r.encontrados, 1)
        self.assertEqual(r.precos_errados, [])

    def test_tamanhos_diferentes_nao_se_misturam(self):
        from .avaliacao import comparar

        gab = [self._p("Espiritual (1 pessoa)", 80), self._p("Espiritual (2 pessoas)", 135)]
        ext = [self._p("Espiritual (2 pessoas)", 135), self._p("Espiritual (1 pessoa)", 80)]
        r = comparar(gab, ext)
        self.assertEqual(r.encontrados, 2)
        self.assertEqual(r.precos_errados, [])

    def test_preco_null_so_confere_com_null(self):
        from .avaliacao import comparar

        r = comparar([self._p("Suco", None), self._p("Água", None)], [self._p("Suco", None), self._p("Água", 3)])
        self.assertEqual([x[0] for x in r.precos_errados], ["Água"])
