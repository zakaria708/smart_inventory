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
    path("produits/<int:pk>/modifier/", views.modifier_produit, name="modifier_produit"),
    path("produits/<int:pk>/supprimer/", views.supprimer_produit, name="supprimer_produit"),
]