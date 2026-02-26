from django.db import models

# Create your models here.
from django.db import models

class Produit(models.Model):
    id = models.IntegerField(primary_key=True)
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    prix = models.FloatField()
    quantite_en_stock = models.IntegerField()

    class Meta:
        db_table = "produits"
        unique_together = ("nom", "categorie")
    def __str__(self):
        return self.nom


class Client(models.Model):
    id = models.IntegerField(primary_key=True)
    nom = models.CharField(max_length=100)
    email = models.CharField(max_length=100,unique=True)

    class Meta:
        db_table = "clients"

    def __str__(self):
        return self.nom


class Commande(models.Model):
    id = models.IntegerField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    date_commande = models.DateField()

    class Meta:
        db_table = "commandes"

    def __str__(self):
        return f"Commande #{self.id}"


class LigneCommande(models.Model):
    id = models.AutoField(primary_key=True)
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.IntegerField()

    class Meta:
        db_table = "lignes_commande"