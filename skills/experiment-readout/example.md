# Exemple : « Peut-on généraliser le parcours d'essai "prix transparent" ? » (données SIMULÉES)

Le test : sur le produit A, du 1er mars au 30 avril 2026, la moitié des inscrits voit le prix du
renouvellement (27,95 € toutes les 4 semaines) en gros à côté du prix de l'essai (2,90 €).

**Commande**
```bash
python skills/experiment-readout/run.py --experiment EXP-A-PRIX-TRANSPARENT --window 60 --primary revenue
```

**Ce que montre la sortie**
- Contrôles : 5 736 contre 5 686 utilisateurs (SRM p = 0,64), affectation unique, fenêtre complète.
- Passage au paiement de l'essai : 44,4 % contre 41,8 %, **−2,6 pts** (IC −4,5 à −0,8 ; p = 0,005).
- Conversion payante au 1er renouvellement : 17,3 % contre 17,8 % (IC −0,9 à +1,9 pt) : pas d'écart.
- Revenu net par utilisateur à 60 jours : 9,28 € contre 9,35 € (IC −0,67 à +0,83 €).
- Litiges pour 1 000 payants : 35 contre 27 (39 contre 29 litiges ; IC −24 à +7) : direction favorable, non significative.
- Effet minimal détectable sur le revenu : 1,10 € par utilisateur (12 %).

**Réponse vérifiée**
> Afficher le prix du renouvellement fait perdre des essais (−2,6 points), mais ce sont des essais qui
> n'auraient pas converti : la conversion payante et le revenu à 60 jours sont inchangés. Les litiges
> baissent d'environ un quart, sans que l'écart soit encore significatif (68 litiges au total).
> Décision : le test ne montre ni gain ni perte de revenu. Comme la variante ne coûte rien et qu'elle va dans
> le sens des exigences de transparence des réseaux de cartes, je recommande de la généraliser et de suivre les
> litiges du produit A pendant 8 semaines ; pour prouver l'effet sur les litiges, il faudrait environ 4 000
> payants par groupe. Contrôles passés.
