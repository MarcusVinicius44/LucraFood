from decimal import Decimal
from types import SimpleNamespace
import os
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from . import calculos
import io

import httpx2 as httpx
from PIL import Image
from openai import InternalServerError, RateLimitError

from .ia.cliente import config
from .ia.faixas import juntar, recortar
from .ia.limitador import LimitadorSaida
from .ia.extracao import (
    FalhaDeCota,
    FotoIlegivel,
    ProvedorIndisponivel,
    SaidaCortada,
    Uso,
    extrair_cardapio,
    extrair_cardapio_com_uso,
)
from .models import Restaurante


def _resposta(texto):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=texto))])


class CalculosTest(TestCase):
    def test_custo_prato(self):
        # 150 g de carne a R$0,042/g + 1 pão a R$1,20 + embalagem R$0,80
        itens = [(Decimal("150"), Decimal("0.042")), (Decimal("1"), Decimal("1.20"))]
        self.assertEqual(calculos.custo_prato(itens, Decimal("0.80")), Decimal("8.30"))

    def test_decompor_fecha_a_conta(self):
        # R$ 25, 150 g a 0,042 + 1 pão a 1,20 = 7,50, embalagem 0,80, taxa 23% = 5,75, imposto 6% = 1,50
        itens = [(Decimal("150"), Decimal("0.042")), (Decimal("1"), Decimal("1.20"))]
        c = calculos.decompor(Decimal("25"), itens, Decimal("0.80"), 1, 23, 6)
        self.assertEqual(
            (c.preco, c.ingredientes, c.embalagem, c.impostos, c.taxa_app, c.sobra),
            (Decimal("25.00"), Decimal("7.50"), Decimal("0.80"), Decimal("1.50"), Decimal("5.75"), Decimal("9.45")),
        )
        self.assertEqual(c.preco - c.ingredientes - c.embalagem - c.impostos - c.taxa_app, c.sobra)

    def test_decompor_divide_so_os_ingredientes_pelo_rendimento(self):
        c = calculos.decompor(Decimal("10"), [(Decimal("1"), Decimal("12"))], Decimal("0.50"), Decimal("12"))
        self.assertEqual((c.ingredientes, c.embalagem, c.sobra), (Decimal("1.00"), Decimal("0.50"), Decimal("8.50")))

    def test_decompor_sobra_pode_ser_negativa_e_recusa_preco_zero(self):
        c = calculos.decompor(Decimal("10"), [(Decimal("1"), Decimal("9"))], 0, 1, 30, 6)
        self.assertEqual(c.sobra, Decimal("-2.60"))
        with self.assertRaises(ValueError):
            calculos.decompor(Decimal("0"), [])

    def test_variacao_sobra_quando_ingrediente_sobe(self):
        # 150 g de blend: R$ 37/kg -> R$ 42/kg = +0,75 de custo; sobra cai 0,75
        antes = [(Decimal("150"), Decimal("0.037"))]
        depois = [(Decimal("150"), Decimal("0.042"))]
        v = calculos.variacao_sobra(Decimal("24.90"), antes, depois, Decimal("0"), 1, 26, 6)
        self.assertEqual(v.diferenca, Decimal("-0.75"))
        self.assertEqual(v.depois, v.antes - Decimal("0.75"))

    def test_preco_antigo_passa_de_30_dias(self):
        from datetime import date

        hoje = date(2026, 11, 12)
        self.assertFalse(calculos.preco_antigo(date(2026, 10, 13), hoje))  # 30 dias: ainda vale
        self.assertTrue(calculos.preco_antigo(date(2026, 10, 12), hoje))  # 31 dias

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


def _429(retry_after=None):
    headers = {"retry-after": retry_after} if retry_after else {}
    resp = httpx.Response(429, headers=headers, request=httpx.Request("POST", "http://x"))
    return RateLimitError("limite", response=resp, body=None)


class Retry429Test(TestCase):
    OK = '{"pratos": [{"nome": "Coxinha", "preco": 7}]}'

    def test_espera_retry_after_e_tenta_de_novo(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = [_429("12"), _resposta(self.OK)]
        cardapio, _ = extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual(cardapio.pratos[0].nome, "Coxinha")
        self.assertEqual(esperas, [12.0])

    def test_sem_cabecalho_espera_60s(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = [_429(), _resposta(self.OK)]
        extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual(esperas, [60])

    def test_falha_de_cota_apos_3_tentativas(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = _429("1")
        with self.assertRaises(FalhaDeCota):
            extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual(cliente.chat.completions.create.call_count, 3)
        self.assertEqual(len(esperas), 2)

    def test_soma_tokens(self):
        cliente = MagicMock()
        r = _resposta(self.OK)
        r.usage = SimpleNamespace(prompt_tokens=1500, completion_tokens=200)
        cliente.chat.completions.create.return_value = r
        _, uso = extrair_cardapio_com_uso(b"fake", cliente=cliente)
        self.assertEqual((uso.entrada, uso.saida), (1500, 200))


class FotoIlegivelTest(TestCase):
    def _cliente(self, *textos):
        cliente = MagicMock()
        cliente.chat.completions.create.side_effect = [_resposta(t) for t in textos]
        return cliente

    def test_modelo_avisa_foto_ilegivel(self):
        cliente = self._cliente('{"foto_ilegivel": "foto desfocada", "pratos": []}')
        with self.assertRaises(FotoIlegivel) as ctx:
            extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual(ctx.exception.motivo, "foto desfocada")

    def test_lista_vazia_sem_motivo_tambem_e_ilegivel(self):
        with self.assertRaises(FotoIlegivel) as ctx:
            extrair_cardapio(b"fake", cliente=self._cliente('{"pratos": []}'))
        self.assertEqual(ctx.exception.motivo, "nenhum prato encontrado")

    def test_trecho_ruim_com_pratos_lidos_segue(self):
        # Uma faixa ilegível e outra com pratos: não recusa, o dono confere o que veio.
        cliente = self._cliente(
            '{"foto_ilegivel": "reflexo", "pratos": []}',
            '{"pratos": [{"nome": "Suco", "preco": 8}]}',
        )
        cardapio = extrair_cardapio(_png(), cliente=cliente, faixas=2)
        self.assertEqual([p.nome for p in cardapio.pratos], ["Suco"])

    def test_view_devolve_422_pedindo_outra_foto(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        with patch("cardapio.views.extrair_cardapio", side_effect=FotoIlegivel("foto tremida")):
            foto = SimpleUploadedFile("c.jpg", b"fake", content_type="image/jpeg")
            resposta = self.client.post("/api/cardapio/extrair/", {"imagem": foto})
        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["codigo"], "foto_ilegivel")
        self.assertEqual(resposta.json()["motivo"], "foto tremida")
        self.assertIn("Tire outra foto", resposta.json()["erro"])


def _5xx(codigo=503, retry_after=None):
    headers = {"retry-after": retry_after} if retry_after else {}
    resp = httpx.Response(codigo, headers=headers, request=httpx.Request("POST", "http://x"))
    return InternalServerError("sobrecarga", response=resp, body=None)


class Retry503Test(TestCase):
    OK = Retry429Test.OK

    def test_espera_crescente_e_tenta_de_novo(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = [_5xx(), _5xx(), _resposta(self.OK)]
        cardapio, uso = extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual(cardapio.pratos[0].nome, "Coxinha")
        self.assertEqual(esperas, [10, 30])
        self.assertEqual(uso.chamadas, 3)  # as que falharam também contam

    def test_respeita_retry_after_se_vier(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = [_5xx(retry_after="5"), _resposta(self.OK)]
        extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual(esperas, [5.0])

    def test_indisponivel_apos_3_tentativas_e_conta_chamadas(self):
        cliente, esperas, uso = MagicMock(), [], Uso()
        cliente.chat.completions.create.side_effect = _5xx()
        with self.assertRaises(ProvedorIndisponivel):
            extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append, uso=uso)
        self.assertEqual(cliente.chat.completions.create.call_count, 3)
        self.assertEqual(uso.chamadas, 3)  # o Uso passado de fora guarda a contagem mesmo com erro

    def test_outros_5xx_nao_repetem(self):
        cliente, esperas = MagicMock(), []
        cliente.chat.completions.create.side_effect = _5xx(500)
        with self.assertRaises(InternalServerError):
            extrair_cardapio_com_uso(b"fake", cliente=cliente, esperar=esperas.append)
        self.assertEqual((cliente.chat.completions.create.call_count, esperas), (1, []))

    def test_view_devolve_503_e_429(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        for erro, codigo in ((ProvedorIndisponivel("x"), 503), (FalhaDeCota("x"), 429)):
            with patch("cardapio.views.extrair_cardapio", side_effect=erro):
                foto = SimpleUploadedFile("c.jpg", b"fake", content_type="image/jpeg")
                resposta = self.client.post("/api/cardapio/extrair/", {"imagem": foto})
            self.assertEqual(resposta.status_code, codigo)


def _png(largura=100, altura=300):
    buf = io.BytesIO()
    Image.new("RGB", (largura, altura), "white").save(buf, format="PNG")
    return buf.getvalue()


class FaixasTest(TestCase):
    def test_recortar_cobre_a_imagem_com_sobreposicao(self):
        faixas = [Image.open(io.BytesIO(f)) for f in recortar(_png(100, 300), n=3, sobreposicao=0.10, minimo_px=0)]
        self.assertEqual(len(faixas), 3)
        self.assertTrue(all(f.width == 100 for f in faixas))
        # miolo = 100 + 30 + 30 de margem; pontas = 100 + 30
        self.assertEqual([f.height for f in faixas], [130, 160, 130])

    def test_recortar_uma_faixa_devolve_imagem_inteira(self):
        (unica,) = recortar(_png(100, 300), n=1)
        self.assertEqual(Image.open(io.BytesIO(unica)).size, (100, 300))

    def test_recortar_valida_argumentos(self):
        with self.assertRaises(ValueError):
            recortar(_png(), n=0)
        with self.assertRaises(ValueError):
            recortar(_png(), sobreposicao=0.6)

    def _p(self, nome, preco=None):
        return SimpleNamespace(nome=nome, preco=None if preco is None else Decimal(str(preco)))

    def test_juntar_remove_repetido_da_sobreposicao_ignorando_acento_e_caixa(self):
        a = [self._p("X-Burger", 20), self._p("Pastel de Camarão", 12)]
        b = [self._p("pastel de camarao", 12), self._p("Suco", 8)]
        self.assertEqual([p.nome for p in juntar([a, b])], ["X-Burger", "Pastel de Camarão", "Suco"])

    def test_juntar_prefere_versao_com_preco(self):
        a = [self._p("Suco")]
        b = [self._p("Suco", 8)]
        (resultado,) = juntar([a, b])
        self.assertEqual(resultado.preco, Decimal("8"))

    def test_juntar_mantem_mesmo_nome_com_precos_diferentes(self):
        a = [self._p("Pizza", 30)]
        b = [self._p("Pizza", 50)]
        self.assertEqual(len(juntar([a, b])), 2)

    def test_juntar_mantem_repetidos_dentro_da_mesma_faixa(self):
        a = [self._p("Suco", 8), self._p("Suco", 8)]
        self.assertEqual(len(juntar([a])), 2)

    def test_extrair_em_faixas_junta_e_soma_tokens(self):
        cliente = MagicMock()
        respostas = [
            '{"pratos": [{"nome": "Coxinha", "preco": 7}, {"nome": "Kibe", "preco": 8}]}',
            '{"pratos": [{"nome": "Kibe", "preco": 8}, {"nome": "Suco", "preco": 6}]}',
        ]
        saidas = []
        for texto in respostas:
            r = _resposta(texto)
            r.usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=100)
            saidas.append(r)
        cliente.chat.completions.create.side_effect = saidas
        cardapio, uso = extrair_cardapio_com_uso(_png(), cliente=cliente, faixas=2)
        self.assertEqual([p.nome for p in cardapio.pratos], ["Coxinha", "Kibe", "Suco"])
        self.assertEqual((uso.entrada, uso.saida), (2000, 200))
        self.assertEqual(uso.maior_chamada, 1100)  # por chamada, não a soma das faixas
        self.assertEqual(cliente.chat.completions.create.call_count, 2)

    def test_sobreposicao_minima_em_pixels(self):
        # 10% de 300 = 30px, mas o mínimo de 40px vale (limitado à metade da faixa: 50px)
        faixas = [Image.open(io.BytesIO(f)) for f in recortar(_png(100, 300), n=3, sobreposicao=0.10, minimo_px=40)]
        self.assertEqual([f.height for f in faixas], [140, 180, 140])

    def test_contexto_e_precos_em_lista_chegam_as_faixas_seguintes(self):
        cliente = MagicMock()
        cliente.chat.completions.create.side_effect = [
            _resposta(
                '{"colunas_preco": ["P","G"], "pratos": [{"nome": "Calabresa", "categoria": "Pizzas", "precos": [30, 50]}]}'
            ),
            _resposta('{"pratos": [{"nome": "Mussarela", "precos": [28, 48]}]}'),
        ]
        cardapio, _ = extrair_cardapio_com_uso(_png(), cliente=cliente, faixas=2)
        self.assertEqual(
            [(p.nome, p.preco) for p in cardapio.pratos],
            [("Calabresa (P)", Decimal("30")), ("Calabresa (G)", Decimal("50")),
             ("Mussarela (P)", Decimal("28")), ("Mussarela (G)", Decimal("48"))],
        )
        segunda = cliente.chat.completions.create.call_args_list[1].kwargs["messages"][1]["content"][0]["text"]
        self.assertIn("faixa 2 de 2", segunda)
        self.assertIn('"Pizzas"', segunda)
        self.assertIn('["P", "G"]', segunda)

    def test_precos_em_lista_sem_rotulo_usa_tamanho_n(self):
        cliente = MagicMock()
        cliente.chat.completions.create.return_value = _resposta(
            '{"pratos": [{"nome": "Abobrinha", "precos": [30, 40]}]}'
        )
        cardapio = extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual([p.nome for p in cardapio.pratos], ["Abobrinha (tamanho 1)", "Abobrinha (tamanho 2)"])

    def test_preco_unico_continua_igual_e_sem_precos_no_resultado(self):
        cliente = MagicMock()
        cliente.chat.completions.create.return_value = _resposta('{"pratos": [{"nome": "Suco", "preco": "R$ 8,50"}]}')
        (prato,) = extrair_cardapio(b"fake", cliente=cliente).pratos
        self.assertEqual(prato.preco, Decimal("8.50"))
        self.assertIsNone(prato.precos)

    @patch.dict(os.environ, {"LUCRAFOOD_PROVEDOR": "groq", "LUCRAFOOD_MAX_TOKENS": ""})
    def test_envia_max_tokens_na_chamada(self):
        cliente = MagicMock()
        cliente.chat.completions.create.return_value = _resposta('{"pratos": [{"nome": "Suco", "preco": 8}]}')
        extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual(cliente.chat.completions.create.call_args.kwargs["max_tokens"], 900)

    def test_saida_cortada_levanta_erro_claro_sem_tentar_de_novo(self):
        cliente = MagicMock()
        r = _resposta('{"pratos": [{"nome": "Su')
        r.choices[0].finish_reason = "length"
        cliente.chat.completions.create.return_value = r
        with self.assertRaises(SaidaCortada):
            extrair_cardapio(b"fake", cliente=cliente)
        self.assertEqual(cliente.chat.completions.create.call_count, 1)


class LimitadorTest(TestCase):
    def _limitador(self):
        relogio = SimpleNamespace(t=0.0)
        esperas = []

        def esperar(s):
            esperas.append(s)
            relogio.t += s

        return LimitadorSaida(limite=1000, janela=60, relogio=lambda: relogio.t, esperar=esperar), relogio, esperas

    def test_primeira_chamada_nao_espera(self):
        lim, _, esperas = self._limitador()
        lim.aguardar(900)
        self.assertEqual(esperas, [])

    def test_espera_a_janela_expirar_antes_da_proxima(self):
        lim, relogio, esperas = self._limitador()
        lim.aguardar(900)
        lim.registrar(600)
        relogio.t = 10
        lim.aguardar(900)  # 600 usados + 900 > 1000: espera os 600 saírem da janela (50s + folga)
        self.assertEqual(len(esperas), 1)
        self.assertAlmostEqual(esperas[0], 50.1, places=3)

    def test_chamada_pequena_nao_bloqueia_a_proxima(self):
        lim, _, esperas = self._limitador()
        lim.registrar(50)
        lim.aguardar(900)  # 50 + 900 <= 1000
        self.assertEqual(esperas, [])

    def test_reserva_acima_do_limite_e_erro(self):
        lim, _, _ = self._limitador()
        with self.assertRaises(ValueError):
            lim.aguardar(1200)

    @patch.dict(os.environ, {"LUCRAFOOD_PROVEDOR": "groq", "LUCRAFOOD_MAX_TOKENS": ""})
    def test_extracao_em_faixas_espaca_as_chamadas(self):
        lim, relogio, esperas = self._limitador()
        cliente = MagicMock()
        respostas = []
        for nome in ("A", "B"):
            r = _resposta('{"pratos": [{"nome": "%s", "preco": 1}]}' % nome)
            r.usage = SimpleNamespace(prompt_tokens=100, completion_tokens=500)
            respostas.append(r)
        cliente.chat.completions.create.side_effect = respostas
        extrair_cardapio_com_uso(_png(), cliente=cliente, faixas=2, limitador=lim)
        self.assertEqual(len(esperas), 1)  # só antes da segunda faixa
        self.assertGreater(relogio.t, 59)


# Ambiente limpo: sem nenhuma variável de provedor herdada do .env de quem roda os testes.
_VARS_PROVEDOR = [
    "LUCRAFOOD_PROVEDOR", "LUCRAFOOD_MODELO_VISAO", "LUCRAFOOD_MAX_TOKENS", "LUCRAFOOD_LIMITE_SAIDA_MIN",
    "LUCRAFOOD_LIMITE_TOKENS_MIN", "GROQ_MODELO_VISAO", "GROQ_BASE_URL", "GEMINI_MODELO_VISAO", "GEMINI_BASE_URL",
]


def _ambiente(**valores):
    limpo = {k: v for k, v in os.environ.items() if k not in _VARS_PROVEDOR}
    return patch.dict(os.environ, {**limpo, **valores}, clear=True)


class ConfigProvedorTest(TestCase):
    def test_padrao_e_gemini_sem_variavel_ou_com_variavel_vazia(self):
        for ambiente in ({}, {"LUCRAFOOD_PROVEDOR": ""}):
            with self.subTest(ambiente=ambiente), _ambiente(**ambiente):
                cfg = config()
                self.assertEqual((cfg.provedor, cfg.var_chave, cfg.modelo),
                                 ("gemini", "GEMINI_API_KEY", "gemini-3.5-flash-lite"))

    def test_groq_com_limites_do_plano_gratuito(self):
        with _ambiente(LUCRAFOOD_PROVEDOR="groq"):
            cfg = config()
        self.assertEqual((cfg.provedor, cfg.var_chave, cfg.max_tokens), ("groq", "GROQ_API_KEY", 900))
        self.assertEqual((cfg.limite_saida_min, cfg.limite_tokens_min), (1000, 8000))

    def test_gemini_sem_limitador_de_saida_e_teto_maior(self):
        with _ambiente(LUCRAFOOD_PROVEDOR="gemini"):
            cfg = config()
        self.assertEqual(cfg.var_chave, "GEMINI_API_KEY")
        self.assertIn("generativelanguage.googleapis.com", cfg.base_url)
        self.assertEqual((cfg.limite_saida_min, cfg.limite_tokens_min), (0, 0))
        self.assertGreater(cfg.max_tokens, 900)

    def test_modelo_antigo_do_groq_nao_vaza_para_o_gemini(self):
        with _ambiente(LUCRAFOOD_PROVEDOR="gemini", LUCRAFOOD_MODELO_VISAO="qwen/qwen3.8-27b"):
            self.assertTrue(config().modelo.startswith("gemini"))
        with _ambiente(LUCRAFOOD_PROVEDOR="groq", LUCRAFOOD_MODELO_VISAO="qwen/outro"):
            self.assertEqual(config().modelo, "qwen/outro")

    def test_modelo_e_limites_sobrescritos_pelo_ambiente(self):
        with _ambiente(LUCRAFOOD_PROVEDOR="gemini", GEMINI_MODELO_VISAO="gemini-3.8-flash", LUCRAFOOD_MAX_TOKENS="4000"):
            cfg = config()
        self.assertEqual((cfg.modelo, cfg.max_tokens), ("gemini-3.8-flash", 4000))

    def test_provedor_invalido(self):
        with _ambiente(LUCRAFOOD_PROVEDOR="outro"), self.assertRaises(RuntimeError):
            config()


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


class ConfirmarTest(TestCase):
    """Confirmar a lista revisada grava os pratos uma vez só."""

    def confirmar(self, pratos, restaurante="Bar do Zé"):
        return self.client.post(
            "/api/cardapio/confirmar/", {"restaurante": restaurante, "pratos": pratos}, content_type="application/json"
        )

    def test_grava_os_pratos(self):
        r = self.confirmar([{"nome": "X-Burger", "preco": "20.00"}, {"nome": "Suco", "preco": None}])
        self.assertEqual((r.status_code, r.json()["pratos_salvos"]), (201, 2))

    def test_confirmar_de_novo_da_409_e_nao_duplica(self):
        from .models import Prato

        self.confirmar([{"nome": "X-Burger", "preco": "20.00"}])
        r = self.confirmar([{"nome": " x-burger ", "preco": "20.00"}, {"nome": "Suco", "preco": "8.00"}])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["pratos"], ["x-burger"])  # o DRF já tira os espaços das pontas
        self.assertIn("restaurante_id", r.json())
        self.assertEqual(Prato.objects.count(), 1)  # nem o Suco entra: tudo ou nada

    def test_mesmo_prato_duas_vezes_na_lista_da_400(self):
        r = self.confirmar([{"nome": "Suco", "preco": "8.00"}, {"nome": "SUCO", "preco": "9.00"}])
        self.assertEqual(r.status_code, 400)
        self.assertIn("SUCO", str(r.json()))

    def test_prato_com_mesmo_nome_em_outro_restaurante_pode(self):
        self.confirmar([{"nome": "Suco", "preco": "8.00"}])
        self.assertEqual(self.confirmar([{"nome": "Suco", "preco": "8.00"}], restaurante="Outro").status_code, 201)
