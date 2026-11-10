from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

MSG_MINIMA_MAIOR = "A margem mínima não pode ser maior que a margem desejada."


class Restaurante(models.Model):
    nome = models.CharField(max_length=120)
    # Taxas informadas pelo dono, em percentual (ex.: 23.00 = 23%).
    # Nada fixo no código: cada restaurante tem a sua realidade.
    taxa_delivery_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    impostos_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    # Limiares do semáforo (margem do delivery): verde >= desejada; vermelho < mínima.
    margem_desejada_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("30"))
    margem_minima_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if (
            self.margem_minima_pct is not None
            and self.margem_desejada_pct is not None
            and self.margem_minima_pct > self.margem_desejada_pct
        ):
            raise ValidationError({"margem_minima_pct": MSG_MINIMA_MAIOR})

    def __str__(self):
        return self.nome


class Ingrediente(models.Model):
    class Unidade(models.TextChoices):
        GRAMA = "g", "grama"
        MILILITRO = "ml", "mililitro"
        UNIDADE = "un", "unidade"

    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="ingredientes")
    nome = models.CharField(max_length=120)
    unidade = models.CharField(max_length=2, choices=Unidade.choices, default=Unidade.GRAMA)
    # Preço pago por uma embalagem e o tamanho dela, do jeito que o dono compra
    # (ex.: R$ 42,00 por 1000 g de carne). O custo unitário sai da divisão.
    preco_embalagem = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_embalagem = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        unique_together = ("restaurante", "nome")

    @property
    def custo_por_unidade(self) -> Decimal:
        return self.preco_embalagem / self.quantidade_embalagem

    def __str__(self):
        return f"{self.nome} ({self.unidade})"


class Prato(models.Model):
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="pratos")
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=60, blank=True)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    custo_embalagem = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    # Porções que a receita da ficha rende (bolo inteiro = 12 fatias). O preço de venda é por porção.
    rendimento = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1"), validators=[MinValueValidator(Decimal("0.01"))]
    )
    # Quando o dono gravou a ficha pela última vez (PUT ou confirmar). Nulo = sem ficha.
    # Junto com o número de ingredientes, ajuda o dono a perceber se esqueceu algo.
    ficha_confirmada_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome


class ItemFichaTecnica(models.Model):
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE, related_name="itens")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        unique_together = ("prato", "ingrediente")

    def __str__(self):
        return f"{self.quantidade} {self.ingrediente.unidade} de {self.ingrediente.nome}"


class MedidaCaseira(models.Model):
    """O que o dono ensinou na ficha em conversa: "1 fatia de Queijo prato = 18 g".

    Gravada só quando o dono confirma a ficha (nada grava sem confirmação). Na próxima receita,
    "2 fatias de queijo prato" já vira 36 g, marcado para conferir."""

    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE, related_name="medidas")
    medida = models.CharField(max_length=30)  # ia.ficha.chave_medida: "fatia", "colher de sopa"
    # Quanto dá 1 medida, na unidade do cadastro do ingrediente (g, ml ou un).
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("ingrediente", "medida")

    def __str__(self):
        return f"1 {self.medida} de {self.ingrediente.nome} = {self.quantidade} {self.ingrediente.unidade}"
