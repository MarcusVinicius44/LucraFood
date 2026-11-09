"""Testes de ingredientes, ficha técnica e diagnóstico (sem IA)."""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from . import calculos
from .avaliacao_ficha import ResultadoFicha
from .avaliacao_ficha import comparar as comparar_ficha
from .ia import ficha as ia_ficha
from .ia.extracao import FalhaDeCota, ProvedorIndisponivel
from .models import Ingrediente, ItemFichaTecnica, Prato, Restaurante


class BaseFicha(TestCase):
    """X-Burger do exemplo: pão R$12/8 un, carne R$42/kg, queijo R$45/kg, embalagem R$1,20,
    vendido a R$20 com taxa do app 23% e impostos 6%."""

    def setUp(self):
        self.restaurante = Restaurante.objects.create(nome="Teste", taxa_delivery_pct=23, impostos_pct=6)
        novo = lambda nome, unidade, preco, qtd: Ingrediente.objects.create(  # noqa: E731
            restaurante=self.restaurante, nome=nome, unidade=unidade, preco_embalagem=preco, quantidade_embalagem=qtd
        )
        self.pao = novo("Pão", "un", Decimal("12"), Decimal("8"))
        self.carne = novo("Carne", "g", Decimal("42"), Decimal("1000"))
        self.queijo = novo("Queijo", "g", Decimal("45"), Decimal("1000"))
        self.prato = Prato.objects.create(
            restaurante=self.restaurante, nome="X-Burger", preco_venda=Decimal("20"), custo_embalagem=Decimal("1.20")
        )

    def put_ficha(self, itens, prato=None):
        prato = prato or self.prato
        return self.client.put(f"/api/pratos/{prato.id}/ficha/", {"itens": itens}, content_type="application/json")

    def ficha_xburger(self):
        return self.put_ficha(
            [
                {"ingrediente": self.pao.id, "quantidade": 1},
                {"ingrediente": self.carne.id, "quantidade": 150},
                {"ingrediente": self.queijo.id, "quantidade": 30},
            ]
        )


class FichaTecnicaTest(BaseFicha):
    def test_xburger_do_exemplo(self):
        resposta = self.ficha_xburger()
        self.assertEqual(resposta.status_code, 200)
        ficha = resposta.json()
        custos = {item["nome"]: item["custo"] for item in ficha["itens"]}
        self.assertEqual(custos, {"Carne": "6.30", "Pão": "1.50", "Queijo": "1.35"})
        d = ficha["diagnostico"]
        self.assertEqual(
            (d["custo"], d["margem_balcao_pct"], d["margem_delivery_pct"], d["semaforo"], d["preco_sugerido_delivery"]),
            ("10.35", "42.3", "19.3", "amarelo", "25.24"),
        )

    def test_get_diagnostico_igual_ao_da_ficha(self):
        self.ficha_xburger()
        d = self.client.get(f"/api/pratos/{self.prato.id}/diagnostico/").json()
        self.assertEqual((d["nome"], d["semaforo"], d["custo"]), ("X-Burger", "amarelo", "10.35"))

    def test_put_substitui_a_ficha_inteira(self):
        self.ficha_xburger()
        self.put_ficha([{"ingrediente": self.carne.id, "quantidade": 200}])
        self.assertEqual(list(self.prato.itens.values_list("ingrediente__nome", "quantidade")), [("Carne", Decimal("200"))])

    def test_lista_vazia_limpa_a_ficha(self):
        self.ficha_xburger()
        d = self.put_ficha([]).json()["diagnostico"]
        self.assertEqual((d["semaforo"], d["pendente"]), (None, "sem_ficha"))

    def test_sem_itens_nao_aceita(self):
        resposta = self.client.put(f"/api/pratos/{self.prato.id}/ficha/", {}, content_type="application/json")
        self.assertEqual(resposta.status_code, 400)

    def test_ingrediente_repetido_400(self):
        resposta = self.put_ficha(
            [{"ingrediente": self.carne.id, "quantidade": 100}, {"ingrediente": self.carne.id, "quantidade": 50}]
        )
        self.assertEqual(resposta.status_code, 400)

    def test_ingrediente_de_outro_restaurante_400_e_nada_muda(self):
        self.ficha_xburger()
        outro = Restaurante.objects.create(nome="Outro")
        alheio = Ingrediente.objects.create(
            restaurante=outro, nome="Bacon", preco_embalagem=10, quantidade_embalagem=100
        )
        resposta = self.put_ficha([{"ingrediente": alheio.id, "quantidade": 10}])
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.prato.itens.count(), 3)

    def test_quantidade_zero_400(self):
        self.assertEqual(self.put_ficha([{"ingrediente": self.carne.id, "quantidade": 0}]).status_code, 400)

    def test_prato_inexistente_404(self):
        self.assertEqual(self.client.get("/api/pratos/999/ficha/").status_code, 404)
        self.assertEqual(self.client.get("/api/pratos/999/diagnostico/").status_code, 404)


class DiagnosticoTest(BaseFicha):
    def diagnostico(self):
        return self.client.get(f"/api/pratos/{self.prato.id}/diagnostico/").json()

    def test_sem_ficha_nao_tem_semaforo(self):
        d = self.diagnostico()
        self.assertEqual((d["semaforo"], d["pendente"], d["custo"]), (None, "sem_ficha", None))

    def test_sem_preco_nao_tem_semaforo(self):
        self.ficha_xburger()
        Prato.objects.filter(pk=self.prato.pk).update(preco_venda=None)
        d = self.diagnostico()
        self.assertEqual((d["semaforo"], d["pendente"]), (None, "sem_preco"))

    def test_verde_nao_sugere_preco(self):
        self.ficha_xburger()
        Prato.objects.filter(pk=self.prato.pk).update(preco_venda=Decimal("40"))
        d = self.diagnostico()
        self.assertEqual((d["semaforo"], d["preco_sugerido_delivery"]), ("verde", None))

    def test_usa_os_limiares_do_restaurante(self):
        self.ficha_xburger()  # margem delivery 19,3%
        Restaurante.objects.filter(pk=self.restaurante.pk).update(margem_desejada_pct=15)
        self.assertEqual(self.diagnostico()["semaforo"], "verde")

    def test_taxas_impossiveis_viram_pendencia_e_nao_erro_500(self):
        self.ficha_xburger()
        Restaurante.objects.filter(pk=self.restaurante.pk).update(taxa_delivery_pct=60, impostos_pct=20)
        d = self.diagnostico()
        self.assertEqual((d["semaforo"], d["pendente"], d["custo"]), (None, "configuracao", "10.35"))
        self.assertIn("100%", d["mensagem"])


class PratoTest(BaseFicha):
    def patch(self, dados):
        return self.client.patch(f"/api/pratos/{self.prato.id}/", dados, content_type="application/json")

    def test_corrige_preco_que_veio_nulo(self):
        Prato.objects.filter(pk=self.prato.pk).update(preco_venda=None)
        self.ficha_xburger()
        self.assertEqual(self.patch({"preco_venda": "20.00"}).status_code, 200)
        d = self.client.get(f"/api/pratos/{self.prato.id}/diagnostico/").json()
        self.assertEqual(d["semaforo"], "amarelo")

    def test_preco_zero_ou_embalagem_negativa_400(self):
        self.assertEqual(self.patch({"preco_venda": "0"}).status_code, 400)
        self.assertEqual(self.patch({"custo_embalagem": "-1"}).status_code, 400)


class PratosDoRestauranteTest(BaseFicha):
    def listar(self):
        return self.client.get(f"/api/restaurantes/{self.restaurante.id}/pratos/")

    def test_cada_prato_vem_com_diagnostico(self):
        self.ficha_xburger()
        Prato.objects.create(restaurante=self.restaurante, nome="Suco", preco_venda=Decimal("8"))
        r = self.listar()
        self.assertEqual(r.status_code, 200)
        por_nome = {p["nome"]: p for p in r.json()}
        self.assertEqual(por_nome["X-Burger"]["semaforo"], "amarelo")
        self.assertEqual(por_nome["X-Burger"]["preco_venda"], "20.00")
        self.assertEqual((por_nome["Suco"]["semaforo"], por_nome["Suco"]["pendente"]), (None, "sem_ficha"))

    def test_mesmo_resultado_da_rota_do_prato(self):
        self.ficha_xburger()
        lista = self.listar().json()[0]
        d = self.client.get(f"/api/pratos/{self.prato.id}/diagnostico/").json()
        for campo in ("semaforo", "custo", "margem_balcao_pct", "margem_delivery_pct", "preco_sugerido_delivery"):
            self.assertEqual(lista[campo], d[campo], campo)

    def test_nao_mistura_restaurantes(self):
        outro = Restaurante.objects.create(nome="Outro")
        Prato.objects.create(restaurante=outro, nome="Pastel", preco_venda=Decimal("9"))
        self.assertEqual([p["nome"] for p in self.listar().json()], ["X-Burger"])

    def test_restaurante_inexistente_404(self):
        self.assertEqual(self.client.get("/api/restaurantes/9999/pratos/").status_code, 404)


class ResumoDaFichaTest(BaseFicha):
    def test_sem_ficha_nao_tem_data(self):
        ficha = self.client.get(f"/api/pratos/{self.prato.id}/ficha/").json()
        self.assertEqual((ficha["ficha_itens"], ficha["ficha_confirmada_em"]), (0, None))

    def test_gravar_ficha_conta_itens_e_marca_a_data(self):
        ficha = self.ficha_xburger().json()
        self.assertEqual(ficha["ficha_itens"], 3)
        self.assertIsNotNone(ficha["ficha_confirmada_em"])
        self.assertTrue(ficha["ficha_confirmada_em"].endswith("-03:00"))  # horário de Brasília
        painel = self.client.get(f"/api/restaurantes/{self.restaurante.id}/pratos/").json()[0]
        self.assertEqual((painel["ficha_itens"], painel["ficha_confirmada_em"]), (3, ficha["ficha_confirmada_em"]))

    def test_confirmar_pela_ia_tambem_marca(self):
        r = self.client.post(
            f"/api/pratos/{self.prato.id}/ficha/confirmar/",
            {"itens": [{"ingrediente": self.carne.id, "quantidade": 150}]},
            content_type="application/json",
        ).json()
        self.assertEqual(r["ficha_itens"], 1)
        self.assertIsNotNone(r["ficha_confirmada_em"])

    def test_esvaziar_a_ficha_apaga_a_data(self):
        self.ficha_xburger()
        ficha = self.put_ficha([]).json()
        self.assertEqual((ficha["ficha_itens"], ficha["ficha_confirmada_em"]), (0, None))


class RendimentoTest(BaseFicha):
    def test_custo_da_porcao_divide_so_os_ingredientes(self):
        # Bolo: receita de R$24 que rende 12 fatias -> R$2 por fatia; a embalagem (R$0,50) é por fatia.
        itens = [(Decimal("1"), Decimal("24"))]
        self.assertEqual(calculos.custo_prato(itens, rendimento=Decimal("12")), Decimal("2.00"))
        self.assertEqual(calculos.custo_prato(itens, Decimal("0.50"), Decimal("12")), Decimal("2.50"))

    def test_rendimento_zero_ou_negativo_e_erro_no_calculo(self):
        for rendimento in ("0", "-1"):
            with self.subTest(rendimento=rendimento), self.assertRaises(ValueError):
                calculos.custo_prato([(Decimal("1"), Decimal("24"))], rendimento=Decimal(rendimento))

    def test_api_recusa_rendimento_zero_ou_negativo(self):
        url = f"/api/pratos/{self.prato.id}/"
        for rendimento in ("0", "-1"):
            with self.subTest(rendimento=rendimento):
                resposta = self.client.patch(url, {"rendimento": rendimento}, content_type="application/json")
                self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Prato.objects.get(pk=self.prato.pk).rendimento, Decimal("1"))

    def test_modelo_recusa_rendimento_zero(self):
        self.prato.rendimento = Decimal("0")
        with self.assertRaises(ValidationError):
            self.prato.full_clean()

    def test_diagnostico_usa_o_custo_da_porcao(self):
        self.ficha_xburger()  # ingredientes R$9,15 + embalagem R$1,20
        ficha = self.client.get(f"/api/pratos/{self.prato.id}/ficha/").json()
        self.assertEqual((ficha["rendimento"], ficha["custo_receita"], ficha["diagnostico"]["custo"]), ("1.00", "9.15", "10.35"))
        resposta = self.client.patch(f"/api/pratos/{self.prato.id}/", {"rendimento": "2"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 200)
        ficha = self.client.get(f"/api/pratos/{self.prato.id}/ficha/").json()
        # 9,15 / 2 = 4,575 + 1,20 = 5,775 -> 5,78
        self.assertEqual((ficha["custo_receita"], ficha["diagnostico"]["custo"]), ("9.15", "5.78"))


class IngredienteTest(BaseFicha):
    def url_lista(self):
        return f"/api/restaurantes/{self.restaurante.id}/ingredientes/"

    def criar(self, **dados):
        base = {"nome": "Alface", "unidade": "g", "preco_embalagem": "5.00", "quantidade_embalagem": "250"}
        return self.client.post(self.url_lista(), {**base, **dados}, content_type="application/json")

    def test_cria_e_calcula_custo_por_unidade(self):
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()["custo_por_unidade"], "0.0200")
        self.assertEqual(Ingrediente.objects.get(nome="Alface").restaurante, self.restaurante)

    def test_lista_so_do_restaurante(self):
        nomes = [i["nome"] for i in self.client.get(self.url_lista()).json()]
        self.assertEqual(nomes, ["Carne", "Pão", "Queijo"])
        self.assertEqual(self.client.get("/api/restaurantes/999/ingredientes/").status_code, 404)

    def test_nome_repetido_ignora_maiusculas_400(self):
        self.assertEqual(self.criar(nome=" carne ").status_code, 400)

    def test_embalagem_zero_400(self):
        self.assertEqual(self.criar(quantidade_embalagem="0").status_code, 400)

    def test_apagar_ingrediente_em_uso_409(self):
        self.ficha_xburger()
        resposta = self.client.delete(f"/api/ingredientes/{self.carne.id}/")
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.json()["pratos"], ["X-Burger"])
        self.assertTrue(Ingrediente.objects.filter(pk=self.carne.pk).exists())

    def test_apagar_ingrediente_livre_204(self):
        self.assertEqual(self.client.delete(f"/api/ingredientes/{self.carne.id}/").status_code, 204)

    def test_mudar_unidade_em_uso_400_mas_preco_pode(self):
        self.ficha_xburger()
        url = f"/api/ingredientes/{self.carne.id}/"
        self.assertEqual(self.client.patch(url, {"unidade": "un"}, content_type="application/json").status_code, 400)
        resposta = self.client.patch(url, {"preco_embalagem": "48.00"}, content_type="application/json")
        self.assertEqual(resposta.status_code, 200)
        d = self.client.get(f"/api/pratos/{self.prato.id}/diagnostico/").json()
        self.assertEqual(d["custo"], "11.25")  # carne 150 g a R$0,048/g = 7,20

    def test_mudar_unidade_livre_ok(self):
        url = f"/api/ingredientes/{self.carne.id}/"
        self.assertEqual(self.client.patch(url, {"unidade": "un"}, content_type="application/json").status_code, 200)

    def test_ficha_continua_valida_depois_do_patch_de_nome(self):
        self.ficha_xburger()
        url = f"/api/ingredientes/{self.carne.id}/"
        self.assertEqual(self.client.patch(url, {"nome": "Blend bovino"}, content_type="application/json").status_code, 200)
        self.assertEqual(ItemFichaTecnica.objects.filter(ingrediente__nome="Blend bovino").count(), 1)


# --- Ficha por texto (IA falsa, sem rede) ----------------------------------


class ConverterUnidadeTest(TestCase):
    def test_conversoes_exatas(self):
        self.assertEqual(calculos.converter_unidade(Decimal("0.2"), "kg", "g"), Decimal("200.000"))
        self.assertEqual(calculos.converter_unidade(Decimal("1.5"), "l", "ml"), Decimal("1500.000"))
        self.assertEqual(calculos.converter_unidade(Decimal("150"), "g", "g"), Decimal("150.000"))

    def test_sem_conversao_exata_e_erro(self):
        for de, para in (("fatia", "g"), ("ml", "g"), ("un", "g")):
            with self.subTest(de=de, para=para), self.assertRaises(ValueError):
                calculos.converter_unidade(Decimal("1"), de, para)


def _resposta(texto):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=texto))], usage=None)


def _cliente(*textos):
    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = [_resposta(t) for t in textos]
    return cliente


CADASTRO = [
    {"id": 1, "nome": "Pão", "unidade": "un"},
    {"id": 2, "nome": "Carne", "unidade": "g"},
    {"id": 3, "nome": "Queijo", "unidade": "g"},
    {"id": 4, "nome": "Leite", "unidade": "ml"},
]


def _itens(*itens):
    return json.dumps({"itens": list(itens)})


class ExtrairFichaTest(TestCase):
    def extrair(self, *respostas):
        return ia_ficha.extrair_ficha("texto", CADASTRO, "X-Burger", cliente=_cliente(*respostas))

    def item(self, nome, ingrediente, quantidade, unidade):
        return {"nome_lido": nome, "ingrediente": ingrediente, "quantidade": quantidade, "unidade": unidade}

    def test_caso_completo(self):
        itens = self.extrair(
            _itens(
                self.item("pão", 1, None, None),
                self.item("hambúrguer", 2, "0,15", "kg"),
                self.item("queijo", 3, 2, "fatia"),
            )
        )
        pao, carne, queijo = (i.para_json() for i in itens)
        # "pão" sem número: 1 unidade, mas marcado para o dono confirmar (decisão B).
        self.assertEqual((pao["quantidade"], pao["motivos"]), ("1.000", ["sem_quantidade"]))
        self.assertEqual((carne["quantidade"], carne["unidade"], carne["precisa_confirmar"]), ("150.000", "g", False))
        self.assertEqual((queijo["quantidade"], queijo["quantidade_lida"], queijo["motivos"]), (None, "2", ["unidade_informal"]))

    def test_id_inventado_vira_null_mas_mantem_a_quantidade(self):
        (item,) = self.extrair(_itens(self.item("bacon", 99, 30, "g")))
        self.assertIsNone(item.ingrediente)
        self.assertEqual(item.motivos, ["sem_ingrediente"])
        self.assertEqual((item.quantidade, item.unidade), (Decimal("30.000"), "g"))

    def test_fora_do_cadastro_mantem_quantidade_exata_e_converte(self):
        mussarela, vinho, sorvete, sal, cenoura = (
            i.para_json()
            for i in self.extrair(
                _itens(
                    self.item("mussarela", None, 150, "g"),
                    self.item("vinho", None, "0,2", "l"),
                    self.item("sorvete", None, 2, "bola"),
                    self.item("sal", None, None, None),
                    self.item("cenouras", None, 2, "un"),
                )
            )
        )
        self.assertEqual((mussarela["quantidade"], mussarela["unidade"]), ("150.000", "g"))
        self.assertEqual((vinho["quantidade"], vinho["unidade"]), ("200.000", "ml"))
        self.assertEqual((sorvete["quantidade"], sorvete["motivos"]), (None, ["sem_ingrediente", "unidade_informal"]))
        self.assertEqual((sal["quantidade"], sal["motivos"]), (None, ["sem_ingrediente", "sem_quantidade"]))
        self.assertEqual((cenoura["quantidade"], cenoura["unidade"]), ("2.000", "un"))

    def test_fora_do_cadastro_sem_unidade_nao_chuta(self):
        (item,) = self.extrair(_itens(self.item("presunto", None, 30, None)))
        self.assertEqual((item.quantidade, item.unidade, item.motivos), (None, None, ["sem_ingrediente", "sem_unidade"]))

    def test_unidade_incompativel(self):
        (item,) = self.extrair(_itens(self.item("queijo", 3, 100, "ml")))
        self.assertEqual((item.quantidade, item.motivos), (None, ["unidade_incompativel"]))

    def test_numero_sem_unidade(self):
        carne, pao = self.extrair(_itens(self.item("carne", 2, 150, None), self.item("pães", 1, 2, None)))
        self.assertEqual((carne.quantidade, carne.motivos), (None, ["sem_unidade"]))
        self.assertEqual((pao.quantidade, pao.motivos), (Decimal("2.000"), []))

    def test_carne_sem_quantidade_nao_vira_1(self):
        (item,) = self.extrair(_itens(self.item("carne", 2, None, None)))
        self.assertEqual((item.quantidade, item.motivos), (None, ["sem_quantidade"]))

    def test_sinonimos_de_unidade(self):
        (item,) = self.extrair(_itens(self.item("leite", 4, "1,5", "Litros")))
        self.assertEqual(item.quantidade, Decimal("1500.000"))

    def test_mesmo_ingrediente_duas_vezes(self):
        _, segundo = self.extrair(_itens(self.item("carne", 2, 100, "g"), self.item("carne moída", 2, 50, "g")))
        self.assertEqual(segundo.motivos, ["ingrediente_repetido"])

    def test_json_invalido_tenta_de_novo_uma_vez(self):
        itens = self.extrair("isso não é json", _itens(self.item("carne", 2, 150, "g")))
        self.assertEqual(itens[0].quantidade, Decimal("150.000"))

    def test_duas_respostas_invalidas_dao_value_error(self):
        with self.assertRaises(ValueError):
            self.extrair('{"itens": [{"nome_lido": ""}]}', "nada")

    def test_quantidade_negativa_e_invalida(self):
        with self.assertRaises(ValueError):
            self.extrair(_itens(self.item("carne", 2, -5, "g")), _itens(self.item("carne", 2, -5, "g")))

    def test_remove_think_e_cercas(self):
        resposta = "<think>hmm</think>```json\n" + _itens(self.item("carne", 2, 150, "g")) + "\n```"
        (item,) = self.extrair(resposta)
        self.assertEqual(item.quantidade, Decimal("150.000"))

    def test_sem_ingredientes(self):
        with self.assertRaises(ia_ficha.TextoSemIngredientes):
            self.extrair('{"itens": []}')

    def test_prompt_recebe_cadastro_e_texto(self):
        cliente = _cliente(_itens(self.item("carne", 2, 150, "g")))
        ia_ficha.extrair_ficha("150 g de carne", CADASTRO, "X-Burger", cliente=cliente)
        mensagem = cliente.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertIn('"nome": "Carne"', mensagem)
        self.assertIn("150 g de carne", mensagem)


class FichaPorTextoViewTest(BaseFicha):
    def url(self, acao):
        return f"/api/pratos/{self.prato.id}/ficha/{acao}/"

    def extrair(self, dados):
        return self.client.post(self.url("extrair"), dados, content_type="application/json")

    def test_extrai_sem_salvar(self):
        resposta_ia = _itens(
            {"nome_lido": "pão", "ingrediente": self.pao.id, "quantidade": None, "unidade": None},
            {"nome_lido": "carne", "ingrediente": self.carne.id, "quantidade": 150, "unidade": "g"},
        )
        with patch("cardapio.ia.ficha.get_cliente", return_value=_cliente(resposta_ia)):
            resposta = self.extrair({"texto": "pão e 150 g de carne"})
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertTrue(corpo["precisa_confirmar"])
        self.assertEqual([i["ingrediente"]["nome"] for i in corpo["itens"]], ["Pão", "Carne"])
        self.assertEqual(self.prato.itens.count(), 0)  # nada gravado

    def test_cadastro_enviado_e_so_do_restaurante(self):
        outro = Restaurante.objects.create(nome="Outro")
        Ingrediente.objects.create(restaurante=outro, nome="Bacon", preco_embalagem=10, quantidade_embalagem=100)
        with patch("cardapio.views_ficha.ia_ficha.extrair_ficha", return_value=[]) as falso:
            self.extrair({"texto": "bacon"})
        cadastro = falso.call_args.args[1]
        self.assertEqual([c["nome"] for c in cadastro], ["Carne", "Pão", "Queijo"])

    def test_texto_vazio_ou_longo_400(self):
        self.assertEqual(self.extrair({"texto": "  "}).status_code, 400)
        self.assertEqual(self.extrair({}).status_code, 400)
        self.assertEqual(self.extrair({"texto": "x" * (ia_ficha.TEXTO_MAX + 1)}).status_code, 400)

    def test_erros_da_ia(self):
        casos = (
            (ia_ficha.TextoSemIngredientes("x"), 422),
            (FalhaDeCota("x"), 429),
            (ProvedorIndisponivel("x"), 503),
            (ValueError("x"), 502),
        )
        for erro, codigo in casos:
            with self.subTest(codigo=codigo), patch("cardapio.views_ficha.ia_ficha.extrair_ficha", side_effect=erro):
                resposta = self.extrair({"texto": "pão"})
                self.assertEqual(resposta.status_code, codigo)
        with patch("cardapio.views_ficha.ia_ficha.extrair_ficha", side_effect=ia_ficha.TextoSemIngredientes("x")):
            self.assertEqual(self.extrair({"texto": "oi"}).json()["codigo"], "sem_ingredientes")

    def test_confirmar_grava_e_substitui(self):
        self.ficha_xburger()
        resposta = self.client.post(
            self.url("confirmar"),
            {"itens": [{"ingrediente": self.carne.id, "quantidade": "150"}]},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.prato.itens.count(), 1)
        self.assertEqual(resposta.json()["diagnostico"]["custo"], "7.50")  # 6,30 + embalagem 1,20

    def test_confirmar_recusa_item_sem_ingrediente_ou_quantidade(self):
        for item in ({"ingrediente": None, "quantidade": 1}, {"ingrediente": self.carne.id, "quantidade": None}):
            with self.subTest(item=item):
                resposta = self.client.post(self.url("confirmar"), {"itens": [item]}, content_type="application/json")
                self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.prato.itens.count(), 0)


def _extraido(nome, id_=None, quantidade=None, unidade=None):
    ingrediente = {"id": id_, "nome": f"#{id_}", "unidade": "g"} if id_ else None
    return {"nome_lido": nome, "ingrediente": ingrediente, "quantidade": quantidade, "unidade": unidade}


class AvaliacaoFichaTest(TestCase):
    ESPERADO = [
        {"nome": "carne", "ingrediente": 2, "quantidade": "150"},
        {"nome": "feijão", "ingrediente": 11, "quantidade": None},
        {"nome": "cenoura", "ingrediente": None, "quantidade": None},
    ]

    def test_tudo_certo(self):
        r = comparar_ficha(
            self.ESPERADO,
            [_extraido("carne", 2, "150.000"), _extraido("feijão", 11), _extraido("2 Cenouras")],
        )
        # A cenoura (null) também conta na quantidade: esperado null, veio null.
        self.assertEqual((r.ingrediente_ok, r.esperados, r.quantidade_ok, r.quantidades), (3, 3, 3, 3))
        self.assertEqual((r.faltando, r.errados, r.sobrando), ([], [], []))

    def test_quantidade_convertida_quando_devia_ficar_null(self):
        r = comparar_ficha(self.ESPERADO[1:2], [_extraido("feijão", 11, "100")])
        self.assertEqual((r.ingrediente_ok, r.quantidade_ok), (1, 0))
        self.assertEqual(r.quantidade_errada, [("feijão", "None", "100")])

    def test_fora_do_cadastro_confere_quantidade_e_unidade(self):
        esperado = [{"nome": "mussarela", "ingrediente": None, "quantidade": "150", "unidade": "g"}]
        certo = comparar_ficha(esperado, [_extraido("mussarela", quantidade="150.000", unidade="g")])
        sem_qtd = comparar_ficha(esperado, [_extraido("mussarela")])
        outra_unidade = comparar_ficha(esperado, [_extraido("mussarela", quantidade="150.000", unidade="ml")])
        self.assertEqual((certo.quantidade_ok, certo.quantidades), (1, 1))
        self.assertEqual((sem_qtd.ingrediente_ok, sem_qtd.quantidade_ok), (1, 0))
        self.assertEqual(outra_unidade.quantidade_errada, [("mussarela", "150 g", "150.000 ml")])

    def test_ligado_ao_id_errado_conta_como_errado_e_faltando(self):
        # "mussarela" forçada para "queijo prato" (id 3) quando o certo era null.
        r = comparar_ficha([{"nome": "mussarela", "ingrediente": None, "quantidade": None}], [_extraido("mussarela", 3)])
        self.assertEqual((r.ingrediente_ok, r.faltando, r.errados), (0, ["mussarela"], [("mussarela", 3)]))

    def test_item_a_mais_sem_ingrediente(self):
        r = comparar_ficha(self.ESPERADO[:1], [_extraido("carne", 2, "150"), _extraido("água")])
        self.assertEqual((r.ingrediente_ok, r.sobrando), (1, ["água"]))

    def test_soma(self):
        total = ResultadoFicha()
        total.somar(comparar_ficha(self.ESPERADO[:1], [_extraido("carne", 2, "150")]))
        total.somar(comparar_ficha(self.ESPERADO[:1], []))
        self.assertEqual((total.esperados, total.ingrediente_ok, total.faltando), (2, 1, ["carne"]))
