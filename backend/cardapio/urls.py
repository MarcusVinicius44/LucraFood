from django.urls import path

from . import views

urlpatterns = [
    path("cardapio/extrair/", views.extrair),
    path("cardapio/confirmar/", views.confirmar),
    path("restaurantes/<int:pk>/", views.RestauranteDetalhe.as_view()),
]
