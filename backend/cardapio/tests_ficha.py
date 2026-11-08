"""Testes de ingredientes, ficha técnica e diagnóstico (sem IA)."""
from decimal import Decimal

from django.test import TestCase

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
