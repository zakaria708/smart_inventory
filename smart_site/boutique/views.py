from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection
from django.db import models          # pour models.Max
from datetime import datetime

from .models import Produit, Client, Commande, LigneCommande

# Pour l’analyse (dashboard)
import pandas as pd
import numpy as np


# Exceptions “métier”
class OutOfStockException(Exception):
    """Stock insuffisant pour la commande."""
    pass


class InvalidQuantityException(Exception):
    """Quantité invalide (<= 0)."""
    pass


def liste_produits(request):
    """Affiche la liste des produits."""
    produits = Produit.objects.all()
    return render(request, "boutique/produits_list.html", {"produits": produits})


def creer_commande(request):
    """
    Créer une commande + décrémenter le stock
    """
    if request.method == "POST":
        client_id = request.POST.get("client_id")
        produit_id = request.POST.get("produit_id")
        quantite_str = request.POST.get("quantite", "0")

        # Sécuriser la conversion en int
        try:
            quantite = int(quantite_str)
        except ValueError:
            messages.error(request, "La quantité doit être un nombre entier.")
            return redirect("creer_commande")

        client = get_object_or_404(Client, pk=client_id)
        produit = get_object_or_404(Produit, pk=produit_id)

        try:
            if quantite <= 0:
                raise InvalidQuantityException("La quantité doit être positive.")

            if quantite > produit.quantite_en_stock:
                raise OutOfStockException("Stock insuffisant pour ce produit.")

            # Création d'un nouvel ID de commande (max + 1)
            nouveau_id = Commande.objects.aggregate(max_id=models.Max("id"))["max_id"] or 0
            nouveau_id += 1

            # Création de la commande
            commande = Commande.objects.create(
                id=nouveau_id,
                client=client,
                date_commande=datetime.now().date(),
            )

            # Ligne de commande
            LigneCommande.objects.create(
                commande=commande,
                produit=produit,
                quantite=quantite,
            )

            # Mise à jour du stock
            produit.quantite_en_stock -= quantite
            produit.save()

            messages.success(request, "Commande créée avec succès.")
            return redirect("liste_produits")

        except InvalidQuantityException as e:
            messages.error(request, str(e))
        except OutOfStockException as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Erreur inattendue : {e}")

    # Si GET ou erreur → on réaffiche le formulaire
    clients = Client.objects.all()
    produits = Produit.objects.all()
    return render(request, "boutique/commande_create.html", {"clients": clients, "produits": produits})


def dashboard(request):
    """
    PARTIE 4 : analyse avec Pandas + NumPy
    et affichage dans dashboard.html
    """

    # On utilise la connexion Django
    produits_df = pd.read_sql("SELECT * FROM produits", connection)
    commandes_df = pd.read_sql("SELECT * FROM commandes", connection)
    lignes_df = pd.read_sql("SELECT * FROM lignes_commande", connection)

    if not produits_df.empty and not commandes_df.empty and not lignes_df.empty:
        # Jointure lignes_commande + produits
        lignes_produits = lignes_df.merge(
            produits_df,
            left_on="produit_id",
            right_on="id",
            how="left",
        )
        # Jointure avec commandes
        donnees = lignes_produits.merge(
            commandes_df,
            left_on="commande_id",
            right_on="id",
            how="left",
            suffixes=("", "_commande"),
        )

        # Calcul du montant par ligne
        donnees["montant_ligne"] = donnees["prix"] * donnees["quantite"]
        donnees["date_commande"] = pd.to_datetime(donnees["date_commande"])
        donnees["mois"] = donnees["date_commande"].dt.to_period("M")

        # 1) Chiffre d'affaires par mois
        ca_par_mois = donnees.groupby("mois")["montant_ligne"].sum()

        # 2) Produits les plus vendus (en quantité)
        ventes_par_produit = (
            donnees.groupby("nom")["quantite"]
            .sum()
            .sort_values(ascending=False)
        )

        # 3) Valeur totale du stock
        produits_df["valeur_stock"] = produits_df["prix"] * produits_df["quantite_en_stock"]
        valeur_stock_totale = produits_df["valeur_stock"].sum()

        # 4) Panier moyen
        totaux_commandes = donnees.groupby("commande_id")["montant_ligne"].sum()
        panier_moyen = totaux_commandes.mean()

        # 5) Fréquence d'achat des clients
        frequence_clients = commandes_df.groupby("client_id")["id"].count()

    else:
        ca_par_mois = pd.Series(dtype=float)
        ventes_par_produit = pd.Series(dtype=int)
        valeur_stock_totale = 0
        panier_moyen = float("nan")
        frequence_clients = pd.Series(dtype=int)

    contexte = {
        "ca_par_mois": ca_par_mois.to_dict(),
        "ventes_par_produit": ventes_par_produit.to_dict(),
        "valeur_stock_totale": valeur_stock_totale,
        "panier_moyen": panier_moyen,
        "frequence_clients": frequence_clients.to_dict(),
    }

    return render(request, "boutique/dashboard.html", contexte)


# ------------------------------------------------
#     NOUVELLES VUES POUR AJOUT + MODIF STOCK
# ------------------------------------------------

def ajouter_produit(request):
    """Créer un nouveau produit (table produits) en évitant les doublons."""

    if request.method == "POST":
        nom = request.POST.get("nom")
        categorie = request.POST.get("categorie")
        prix_str = request.POST.get("prix")
        stock_str = request.POST.get("quantite_en_stock")

        # 🔎 1) Vérifier si ce produit existe déjà
        # ici on considère qu’un produit est le même si nom + catégorie sont identiques
        if Produit.objects.filter(nom=nom, categorie=categorie).exists():
            messages.error(request, "Ce produit existe déjà (même nom et même catégorie).")
            return redirect("ajouter_produit")

        # 2) Sécuriser la conversion prix / stock
        try:
            prix = float(prix_str)
            quantite_en_stock = int(stock_str)
        except (ValueError, TypeError):
            messages.error(request, "Prix ou quantité invalide.")
            return redirect("ajouter_produit")

        # 3) Générer un nouvel id (car id est IntegerField)
        nouveau_id = Produit.objects.aggregate(max_id=models.Max("id"))["max_id"] or 0
        nouveau_id += 1

        Produit.objects.create(
            id=nouveau_id,
            nom=nom,
            categorie=categorie,
            prix=prix,
            quantite_en_stock=quantite_en_stock,
        )

        messages.success(request, "Produit ajouté avec succès.")
        return redirect("liste_produits")

    return render(request, "boutique/produit_form.html")

def ajouter_client(request):
    """Créer un nouveau client (table clients)."""

    if request.method == "POST":
        nom = request.POST.get("nom")
        email = request.POST.get("email")

        # Générer un nouvel id (car id est IntegerField)
        nouveau_id = Client.objects.aggregate(max_id=models.Max("id"))["max_id"] or 0
        nouveau_id += 1

        Client.objects.create(
            id=nouveau_id,
            nom=nom,
            email=email,
        )

        messages.success(request, "Client ajouté avec succès.")
        return redirect("creer_commande")  # ou liste_produits si tu préfères

    return render(request, "boutique/client_form.html")


def modifier_stock(request, pk):
    """Modifier la quantité en stock d’un produit (table produits)."""

    produit = get_object_or_404(Produit, pk=pk)

    if request.method == "POST":
        stock_str = request.POST.get("quantite_en_stock")
        try:
            nouveau_stock = int(stock_str)
        except (ValueError, TypeError):
            messages.error(request, "Quantité invalide.")
            return redirect("modifier_stock", pk=pk)

        produit.quantite_en_stock = nouveau_stock
        produit.save()

        messages.success(request, "Stock mis à jour.")
        return redirect("liste_produits")

    # GET → afficher formulaire pré-rempli
    return render(request, "boutique/stock_update.html", {"produit": produit})