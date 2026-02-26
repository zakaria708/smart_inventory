from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste_produits, name="liste_produits"),
    path("commande/", views.creer_commande, name="creer_commande"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # 👉 nouvelles routes
    path("produits/ajouter/", views.ajouter_produit, name="ajouter_produit"),
    path("clients/ajouter/", views.ajouter_client, name="ajouter_client"),
    path("produits/<int:pk>/modifier_stock/", views.modifier_stock, name="modifier_stock"),
]