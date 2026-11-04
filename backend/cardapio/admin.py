from django.contrib import admin

from .models import Ingrediente, ItemFichaTecnica, Prato, Restaurante


class ItemInline(admin.TabularInline):
    model = ItemFichaTecnica
    extra = 1


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco_venda", "restaurante")
    inlines = [ItemInline]


admin.site.register([Restaurante, Ingrediente])
