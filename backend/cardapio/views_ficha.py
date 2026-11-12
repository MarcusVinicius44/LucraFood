"""Ingredientes, ficha técnica e diagnóstico (semáforo) dos pratos.

As views só juntam os dados do banco e chamam calculos.py: nenhuma conta mora aqui.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from . import calculos
from .ia import conversa as ia_conversa
from .ia import ficha as ia_ficha
from .ia.extracao import FalhaDeCota, ProvedorIndisponivel
from .models import Ingrediente, ItemFichaTecnica, MedidaCaseira, Prato, Restaurante
from .views import resposta_erro_ia

MSG_INGREDIENTE_REPETIDO = "Já existe um ingrediente com esse nome neste restaurante."
MSG_UNIDADE_EM_USO = (
    "Este ingrediente já está em fichas técnicas. Mudar a unidade mudaria o sentido das quantidades "
    "(150 g viraria 150 un); cadastre um ingrediente novo com a outra unidade."
)
MSG_INGREDIENTE_EM_USO = "Este ingrediente está em fichas técnicas. Tire-o desses pratos antes de apagar."
MSG_ITEM_REPETIDO = "O mesmo ingrediente aparece mais de uma vez; some as quantidades em uma linha só."
PENDENCIAS = {
    "sem_preco": "Informe o preço de venda do prato para calcular a margem.",
    "sem_ficha": "Monte a ficha técnica (ingredientes e quantidades) para calcular o custo.",
}


def _texto(valor):
    return None if valor is None else str(valor)


def _itens_que_usam(ingrediente):
    return ItemFichaTecnica.objects.filter(ingrediente=ingrediente)


# --- Ingredientes ----------------------------------------------------------


class MedidaCaseiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedidaCaseira
        fields = ["id", "medida", "quantidade"]


class IngredienteSerializer(serializers.ModelSerializer):
    preco_embalagem = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    # Zero não pode: o custo por unidade é preço / quantidade da embalagem.
    quantidade_embalagem = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    custo_por_unidade = serializers.SerializerMethodField()
    # O que o dono ensinou na ficha em conversa ("1 fatia = 18 g"). Só leitura; esquecer é DELETE /medidas/<id>/.
    medidas = MedidaCaseiraSerializer(many=True, read_only=True)

    class Meta:
        model = Ingrediente
        fields = ["id", "nome", "unidade", "preco_embalagem", "quantidade_embalagem", "custo_por_unidade", "medidas"]

    def get_custo_por_unidade(self, ingrediente):
        # Só exibição (4 casas); o custo do prato usa o valor sem arredondar.
        return str(ingrediente.custo_por_unidade.quantize(Decimal("0.0001"), ROUND_HALF_UP))

    def validate_nome(self, nome):
        nome = nome.strip()
        restaurante = self.instance.restaurante if self.instance else self.context["restaurante"]
        iguais = Ingrediente.objects.filter(restaurante=restaurante, nome__iexact=nome)
        if self.instance:
            iguais = iguais.exclude(pk=self.instance.pk)
        if iguais.exists():
            raise serializers.ValidationError(MSG_INGREDIENTE_REPETIDO)
        return nome

    def validate_unidade(self, unidade):
        if self.instance and unidade != self.instance.unidade and _itens_que_usam(self.instance).exists():
            raise serializers.ValidationError(MSG_UNIDADE_EM_USO)
        return unidade

    def update(self, instance, validated_data):
        # "1 fatia = 18 g" não vale mais se o ingrediente passa a ser em ml ou un.
        if "unidade" in validated_data and validated_data["unidade"] != instance.unidade:
            instance.medidas.all().delete()
        return super().update(instance, validated_data)


class IngredientesDoRestaurante(generics.ListCreateAPIView):
    """Lista e cadastra os ingredientes de um restaurante, do jeito que o dono compra."""

    serializer_class = IngredienteSerializer

    def restaurante(self):
        if not hasattr(self, "_restaurante"):
            self._restaurante = get_object_or_404(Restaurante, pk=self.kwargs["pk"])
        return self._restaurante

    def get_queryset(self):
        return self.restaurante().ingredientes.prefetch_related("medidas").order_by("nome")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "restaurante": self.restaurante()}

    def perform_create(self, serializer):
        serializer.save(restaurante=self.restaurante())


class IngredienteDetalhe(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer

    def destroy(self, request, *args, **kwargs):
        ingrediente = self.get_object()
        pratos = sorted({item.prato.nome for item in _itens_que_usam(ingrediente).select_related("prato")})
        if pratos:
            # 409: o pedido é válido, mas conflita com o estado atual (o ingrediente está em uso).
            return Response({"erro": MSG_INGREDIENTE_EM_USO, "pratos": pratos}, status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)


class MedidaCaseiraDetalhe(generics.DestroyAPIView):
    """Esquecer uma medida ensinada (na próxima receita, o sistema volta a perguntar)."""

    queryset = MedidaCaseira.objects.all()


# --- Diagnóstico -----------------------------------------------------------


def diagnostico_do_prato(prato):
    """Junta preço, ficha e taxas do restaurante e chama calculos.diagnosticar.

    Sem preço ou sem ficha não há semáforo: custo zero daria um verde falso.
    """
    resultado = {
        "semaforo": None,
        "pendente": None,
        "mensagem": None,
        "custo": None,
        "margem_balcao_pct": None,
        "margem_delivery_pct": None,
        "preco_sugerido_delivery": None,
        "conta": None,  # o pedido no delivery em reais, linha por linha (calculos.decompor)
    }
    itens = list(prato.itens.all())
    if prato.preco_venda is None or prato.preco_venda <= 0:
        return {**resultado, "pendente": "sem_preco", "mensagem": PENDENCIAS["sem_preco"]}
    if not itens:
        return {**resultado, "pendente": "sem_ficha", "mensagem": PENDENCIAS["sem_ficha"]}
    custo = calculos.custo_prato(
        [(item.quantidade, item.ingrediente.custo_por_unidade) for item in itens],
        prato.custo_embalagem,
        prato.rendimento,
    )
    r = prato.restaurante
    try:
        d = calculos.diagnosticar(
            prato.preco_venda, custo, r.taxa_delivery_pct, r.impostos_pct, r.margem_desejada_pct, r.margem_minima_pct
        )
    except ValueError as erro:  # ex.: taxa + impostos + margem desejada passam de 100%
        return {**resultado, "pendente": "configuracao", "mensagem": str(erro), "custo": str(custo)}
    conta = calculos.decompor(
        prato.preco_venda,
        [(item.quantidade, item.ingrediente.custo_por_unidade) for item in itens],
        prato.custo_embalagem,
        prato.rendimento,
        r.taxa_delivery_pct,
        r.impostos_pct,
    )
    return {
        **resultado,
        "conta": {
            "preco": str(conta.preco),
            "ingredientes": str(conta.ingredientes),
            "embalagem": str(conta.embalagem),
            "impostos": str(conta.impostos),
            "taxa_app": str(conta.taxa_app),
            "sobra": str(conta.sobra),
        },
        "semaforo": d.semaforo,
        "custo": str(d.custo),
        "margem_balcao_pct": str(d.margem_balcao),
        "margem_delivery_pct": str(d.margem_delivery),
        "preco_sugerido_delivery": _texto(d.preco_sugerido_delivery),
    }


def resumo_da_ficha(prato):
    """Quantos ingredientes a ficha tem e quando foi confirmada (o painel e a tela do prato mostram)."""
    return {
        "ficha_itens": len(prato.itens.all()),
        "ficha_confirmada_em": (
            timezone.localtime(prato.ficha_confirmada_em).isoformat() if prato.ficha_confirmada_em else None
        ),
    }


def _pratos():
    return Prato.objects.select_related("restaurante").prefetch_related("itens__ingrediente")


@api_view(["GET"])
def diagnostico(request, pk):
    prato = get_object_or_404(_pratos(), pk=pk)
    return Response({"prato": prato.id, "nome": prato.nome, **diagnostico_do_prato(prato)})


@api_view(["GET"])
def pratos_do_restaurante(request, pk):
    """Painel: todos os pratos do restaurante, cada um com o diagnóstico (mesmo cálculo da rota do prato)."""
    restaurante = get_object_or_404(Restaurante, pk=pk)
    pratos = _pratos().filter(restaurante=restaurante).order_by("categoria", "nome")
    return Response(
        [
            {
                "id": prato.id,
                "nome": prato.nome,
                "categoria": prato.categoria,
                "preco_venda": _texto(prato.preco_venda),
                "custo_embalagem": _texto(prato.custo_embalagem),
                "rendimento": _texto(prato.rendimento),
                **resumo_da_ficha(prato),
                **diagnostico_do_prato(prato),
            }
            for prato in pratos
        ]
    )


# --- Prato -----------------------------------------------------------------


class PratoSerializer(serializers.ModelSerializer):
    preco_venda = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), allow_null=True, required=False
    )
    custo_embalagem = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)
    # Porções que a receita rende; zero não pode (o custo da porção é receita / rendimento).
    rendimento = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("0.01"), required=False)

    class Meta:
        model = Prato
        fields = ["id", "nome", "categoria", "preco_venda", "custo_embalagem", "rendimento"]


class PratoDetalhe(generics.RetrieveUpdateAPIView):
    """Consulta e corrige um prato (ex.: preço que veio nulo da foto, custo da embalagem)."""

    queryset = Prato.objects.all()
    serializer_class = PratoSerializer


# --- Ficha técnica ---------------------------------------------------------


class ItemFichaSerializer(serializers.Serializer):
    ingrediente = serializers.IntegerField()
    # Na unidade do cadastro do ingrediente (g, ml ou un).
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))


class FichaSerializer(serializers.Serializer):
    """Ficha completa enviada pelo dono. Substitui a anterior (lista vazia limpa a ficha)."""

    itens = ItemFichaSerializer(many=True, allow_empty=True)

    def validate_itens(self, itens):
        prato = self.context["prato"]
        ids = [item["ingrediente"] for item in itens]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(MSG_ITEM_REPETIDO)
        do_restaurante = set(
            Ingrediente.objects.filter(restaurante=prato.restaurante, pk__in=ids).values_list("pk", flat=True)
        )
        fora = [i for i in ids if i not in do_restaurante]
        if fora:
            raise serializers.ValidationError(f"Ingrediente(s) {fora} não existe(m) neste restaurante.")
        return itens


def ficha_do_prato(prato):
    itens = sorted(prato.itens.all(), key=lambda item: item.ingrediente.nome.lower())
    custo_receita = calculos.custo_prato([(item.quantidade, item.ingrediente.custo_por_unidade) for item in itens])
    return {
        "prato": prato.id,
        "nome": prato.nome,
        "preco_venda": _texto(prato.preco_venda),
        "custo_embalagem": str(prato.custo_embalagem),
        "rendimento": str(prato.rendimento),
        # Só ingredientes, a receita inteira. O custo da porção (com embalagem) está em diagnostico.custo.
        "custo_receita": str(custo_receita),
        **resumo_da_ficha(prato),
        "itens": [
            {
                "ingrediente": item.ingrediente_id,
                "nome": item.ingrediente.nome,
                "unidade": item.ingrediente.unidade,
                "quantidade": str(item.quantidade),
                "custo": str(calculos.custo_prato([(item.quantidade, item.ingrediente.custo_por_unidade)])),
            }
            for item in itens
        ],
        "diagnostico": diagnostico_do_prato(prato),
    }


def salvar_ficha(prato, dados):
    """Valida e grava a ficha inteira de uma vez (tudo ou nada). Devolve a ficha atualizada."""
    entrada = FichaSerializer(data=dados, context={"prato": prato})
    entrada.is_valid(raise_exception=True)
    with transaction.atomic():
        prato.itens.all().delete()
        ItemFichaTecnica.objects.bulk_create(
            ItemFichaTecnica(prato=prato, ingrediente_id=item["ingrediente"], quantidade=item["quantidade"])
            for item in entrada.validated_data["itens"]
        )
        # Lista vazia limpa a ficha: aí não há confirmação a mostrar.
        prato.ficha_confirmada_em = timezone.now() if entrada.validated_data["itens"] else None
        prato.save(update_fields=["ficha_confirmada_em"])
    return ficha_do_prato(_pratos().get(pk=prato.pk))


@api_view(["GET", "PUT"])
@parser_classes([JSONParser])
def ficha_tecnica(request, pk):
    """GET mostra a ficha com custo por item e diagnóstico.
    PUT {"itens": [{"ingrediente": id, "quantidade": n}]} troca a ficha inteira."""
    prato = get_object_or_404(_pratos(), pk=pk)
    if request.method == "PUT":
        return Response(salvar_ficha(prato, request.data))
    return Response(ficha_do_prato(prato))


# --- Ficha por texto (IA) --------------------------------------------------

MSG_SEM_INGREDIENTES = (
    "Não encontrei ingredientes nesse texto. Escreva o que vai no prato e quanto, "
    'por exemplo: "pão, 150 g de carne, 2 fatias de queijo".'
)


@api_view(["POST"])
@parser_classes([JSONParser])
def extrair_ficha_texto(request, pk):
    """{"texto": "..."} -> itens lidos pela IA para o dono REVISAR. Nada é salvo aqui."""
    prato = get_object_or_404(Prato.objects.select_related("restaurante"), pk=pk)
    texto = request.data.get("texto") if isinstance(request.data, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        return Response({"erro": "Envie a receita no campo 'texto'."}, status=400)
    texto = texto.strip()
    if len(texto) > ia_ficha.TEXTO_MAX:
        return Response({"erro": f"Texto acima de {ia_ficha.TEXTO_MAX} caracteres."}, status=400)
    cadastro = list(prato.restaurante.ingredientes.order_by("nome").values("id", "nome", "unidade"))
    medidas = {
        (m.ingrediente_id, m.medida): m.quantidade
        for m in MedidaCaseira.objects.filter(ingrediente__restaurante=prato.restaurante)
    }
    try:
        itens = ia_ficha.extrair_ficha(texto, cadastro, prato.nome, medidas=medidas)
    except ia_ficha.TextoSemIngredientes:
        return Response(
            {"erro": MSG_SEM_INGREDIENTES, "codigo": "sem_ingredientes"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    except (FalhaDeCota, ProvedorIndisponivel, ValueError) as erro:
        return resposta_erro_ia(erro)
    return Response(
        {
            "prato": prato.id,
            "nome": prato.nome,
            "precisa_confirmar": any(item.precisa_confirmar for item in itens),
            "itens": [item.para_json() for item in itens],
        }
    )


class MedidaEnsinadaSerializer(serializers.Serializer):
    ingrediente = serializers.IntegerField()
    medida = serializers.CharField(max_length=60)
    # Quanto dá 1 medida, na unidade do cadastro do ingrediente.
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))

    def validate_medida(self, medida):
        chave = ia_ficha.chave_medida(medida)
        if not chave:
            raise serializers.ValidationError("Medida vazia.")
        return chave


class ConfirmarSerializer(serializers.Serializer):
    medidas = MedidaEnsinadaSerializer(many=True, required=False, default=list, max_length=60)

    def validate_medidas(self, medidas):
        prato = self.context["prato"]
        ids = {m["ingrediente"] for m in medidas}
        do_restaurante = set(
            Ingrediente.objects.filter(restaurante=prato.restaurante, pk__in=ids).values_list("pk", flat=True)
        )
        if ids - do_restaurante:
            raise serializers.ValidationError(f"Ingrediente(s) {sorted(ids - do_restaurante)} não existe(m) neste restaurante.")
        return medidas


@api_view(["POST"])
@parser_classes([JSONParser])
def confirmar_ficha(request, pk):
    """Grava a ficha revisada pelo dono. Mesma validação e gravação do PUT /ficha/ (substitui a anterior):
    cada item precisa de um ingrediente cadastrado e da quantidade na unidade do cadastro.
    `medidas` (opcional): o que o dono ensinou na conversa ("1 fatia de Queijo prato = 18 g"),
    gravado junto com a ficha para a próxima receita."""
    prato = get_object_or_404(_pratos(), pk=pk)
    extras = ConfirmarSerializer(data=request.data, context={"prato": prato})
    extras.is_valid(raise_exception=True)
    with transaction.atomic():
        ficha = salvar_ficha(prato, request.data)
        for m in extras.validated_data["medidas"]:
            MedidaCaseira.objects.update_or_create(
                ingrediente_id=m["ingrediente"], medida=m["medida"], defaults={"quantidade": m["quantidade"]}
            )
    return Response(ficha)


class ItemConversaSerializer(serializers.Serializer):
    chave = serializers.IntegerField()
    nome_lido = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")
    ingrediente = serializers.IntegerField(allow_null=True)
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=3, allow_null=True, min_value=Decimal("0.001"))
    quantidade_lida = serializers.DecimalField(
        max_digits=10, decimal_places=3, allow_null=True, required=False, default=None, min_value=Decimal("0.001")
    )
    unidade_lida = serializers.CharField(max_length=30, allow_null=True, allow_blank=True, required=False, default=None)
    motivos = serializers.ListField(child=serializers.CharField(max_length=40), required=False, default=list)


class PerguntaFeitaSerializer(serializers.Serializer):
    chave = serializers.IntegerField()


class ConversaSerializer(serializers.Serializer):
    itens = ItemConversaSerializer(many=True, allow_empty=False, max_length=60)
    pulados = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    pergunta = PerguntaFeitaSerializer(required=False, allow_null=True, default=None)
    resposta = serializers.CharField(
        max_length=ia_conversa.RESPOSTA_MAX, required=False, allow_null=True, allow_blank=True, default=None
    )


@api_view(["POST"])
@parser_classes([JSONParser])
def conversa_ficha(request, pk):
    """Uma rodada da ficha em conversa. Sem resposta: só devolve a primeira pergunta (sem IA).
    Com resposta: a IA lê o número e a unidade ditos, o Python faz a conta e devolve o item
    atualizado e a próxima pergunta. Nada é salvo: o dono confirma a ficha no fim."""
    prato = get_object_or_404(Prato.objects.select_related("restaurante"), pk=pk)
    entrada = ConversaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    dados = entrada.validated_data
    cadastro = {
        c["id"]: c for c in prato.restaurante.ingredientes.values("id", "nome", "unidade")
    }
    itens = [
        ia_conversa.ItemConversa(
            chave=i["chave"],
            nome_lido=i["nome_lido"],
            ingrediente=cadastro.get(i["ingrediente"]),  # id de outro restaurante vira None
            quantidade=i["quantidade"],
            quantidade_lida=i["quantidade_lida"],
            unidade_lida=i["unidade_lida"] or None,
            motivos=i["motivos"],
        )
        for i in dados["itens"]
    ]
    pulados = list(dict.fromkeys(dados["pulados"]))
    atualizado, aviso = None, None
    resposta = (dados["resposta"] or "").strip()
    if dados["pergunta"] and resposta:
        pergunta = ia_conversa.proxima_pergunta([i for i in itens if i.chave == dados["pergunta"]["chave"]])
        if pergunta is None:
            return Response({"erro": "Esse item não tem mais o que perguntar."}, status=400)
        try:
            lida = ia_conversa.interpretar_resposta(pergunta.texto, resposta)
        except (FalhaDeCota, ProvedorIndisponivel, ValueError) as erro:
            return resposta_erro_ia(erro)
        if lida.nao_sabe:
            pulados.append(pergunta.chave)
        elif not lida.entendeu:
            aviso = "Não entendi. Pode responder com um número, por exemplo \"20 g\"?"
        else:
            item = next(i for i in itens if i.chave == pergunta.chave)
            try:
                atualizado = ia_conversa.aplicar_resposta(item, pergunta.tipo, lida)
                item.quantidade = atualizado.quantidade
            except ia_conversa.RespostaInvalida as erro:
                aviso = str(erro)
    proxima = ia_conversa.proxima_pergunta(itens, pulados)
    return Response(
        {
            "atualizado": atualizado.para_json() if atualizado else None,
            "aviso": aviso,
            "pergunta": proxima.para_json() if proxima else None,
            "pulados": pulados,
            "sem_cadastro": sum(1 for i in itens if i.ingrediente is None),
        }
    )

