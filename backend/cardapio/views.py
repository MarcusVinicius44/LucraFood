from django.db import transaction
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from .ia.extracao import FalhaDeCota, FotoIlegivel, ProvedorIndisponivel, extrair_cardapio
from .models import MSG_MINIMA_MAIOR, Prato, Restaurante

TIPOS_ACEITOS = {"image/jpeg", "image/png", "image/webp"}
MSG_FOTO_ILEGIVEL = (
    "Não consegui ler o cardápio nesta foto. Ela pode estar desfocada, tremida, escura ou cortada. "
    "Tire outra foto com boa luz, o celular parado e o cardápio inteiro aparecendo."
)
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
    except FotoIlegivel as erro:
        # 422: o pedido chegou certo, mas o conteúdo (a foto) não serve. O front mostra "tirar outra foto".
        return Response(
            {
                "erro": MSG_FOTO_ILEGIVEL,
                "codigo": "foto_ilegivel",
                "motivo": erro.motivo,
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except (FalhaDeCota, ProvedorIndisponivel, ValueError) as erro:
        return resposta_erro_ia(erro)
    return Response(cardapio.model_dump(mode="json"))


def resposta_erro_ia(erro):
    """Converte os erros da camada de IA (foto ou ficha) na resposta HTTP certa."""
    if isinstance(erro, FalhaDeCota):
        return Response(
            {"erro": "Limite de uso da IA atingido. Tente de novo em alguns minutos."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if isinstance(erro, ProvedorIndisponivel):
        return Response(
            {"erro": "O serviço de IA está sobrecarregado. Tente de novo em alguns minutos."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    # ValueError: a IA não devolveu dados válidos nem na segunda tentativa.
    return Response({"erro": str(erro)}, status=status.HTTP_502_BAD_GATEWAY)


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
