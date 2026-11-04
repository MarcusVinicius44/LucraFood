from django.db import transaction
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from .ia.extracao import extrair_cardapio
from .models import MSG_MINIMA_MAIOR, Prato, Restaurante

TIPOS_ACEITOS = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAX = 4 * 1024 * 1024  # 4 MB: base64 cresce ~33% e o Groq limita o request


@api_view(["POST"])
@parser_classes([MultiPartParser])
def extrair(request):
    """Recebe a foto (campo 'imagem') e devolve os pratos para o dono CONFERIR.
    Nada é salvo aqui."""
    arquivo = request.FILES.get("imagem")
    if not arquivo:
        return Response({"erro": "Envie a foto no campo 'imagem'."}, status=400)
    if arquivo.content_type not in TIPOS_ACEITOS:
        return Response({"erro": "Formato aceito: JPG, PNG ou WEBP."}, status=400)
    if arquivo.size > TAMANHO_MAX:
        return Response({"erro": "Imagem acima de 4 MB."}, status=400)
    try:
        cardapio = extrair_cardapio(arquivo.read(), arquivo.content_type)
    except ValueError as erro:
        return Response({"erro": str(erro)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(cardapio.model_dump(mode="json"))


class PratoConfirmadoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)
    descricao = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    categoria = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    preco = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False)


class ConfirmarSerializer(serializers.Serializer):
    restaurante = serializers.CharField(max_length=120)
    pratos = PratoConfirmadoSerializer(many=True)


@api_view(["POST"])
@parser_classes([JSONParser])
def confirmar(request):
    """Salva a lista já conferida/corrigida pelo dono."""
    dados = ConfirmarSerializer(data=request.data)
    dados.is_valid(raise_exception=True)
    with transaction.atomic():
        restaurante, _ = Restaurante.objects.get_or_create(nome=dados.validated_data["restaurante"])
        criados = [
            Prato.objects.create(
                restaurante=restaurante,
                nome=p["nome"],
                descricao=p.get("descricao") or "",
                categoria=p.get("categoria") or "",
                preco_venda=p.get("preco"),
            )
            for p in dados.validated_data["pratos"]
        ]
    return Response({"restaurante_id": restaurante.id, "pratos_salvos": len(criados)}, status=201)


class RestauranteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurante
        fields = ["id", "nome", "taxa_delivery_pct", "impostos_pct", "margem_desejada_pct", "margem_minima_pct"]

    def validate(self, attrs):
        # Em PATCH parcial, o campo ausente vem do registro atual.
        atual = self.instance
        minima = attrs.get("margem_minima_pct", getattr(atual, "margem_minima_pct", None))
        desejada = attrs.get("margem_desejada_pct", getattr(atual, "margem_desejada_pct", None))
        if minima is not None and desejada is not None and minima > desejada:
            raise serializers.ValidationError({"margem_minima_pct": MSG_MINIMA_MAIOR})
        return attrs


class RestauranteDetalhe(generics.RetrieveUpdateAPIView):
    """Consulta e ajusta taxas e limiares do semáforo de um restaurante."""

    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
