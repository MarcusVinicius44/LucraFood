from django.urls import path

from . import views, views_ficha

urlpatterns = [
    path("cardapio/extrair/", views.extrair),
    path("cardapio/confirmar/", views.confirmar),
    path("restaurantes/<int:pk>/", views.RestauranteDetalhe.as_view()),
    path("restaurantes/<int:pk>/pratos/", views_ficha.pratos_do_restaurante),
    path("restaurantes/<int:pk>/ingredientes/", views_ficha.IngredientesDoRestaurante.as_view()),
    path("ingredientes/<int:pk>/", views_ficha.IngredienteDetalhe.as_view()),
    path("pratos/<int:pk>/", views_ficha.PratoDetalhe.as_view()),
    path("pratos/<int:pk>/ficha/", views_ficha.ficha_tecnica),
    path("pratos/<int:pk>/diagnostico/", views_ficha.diagnostico),
    path("pratos/<int:pk>/ficha/extrair/", views_ficha.extrair_ficha_texto),
    path("pratos/<int:pk>/ficha/confirmar/", views_ficha.confirmar_ficha),
]
