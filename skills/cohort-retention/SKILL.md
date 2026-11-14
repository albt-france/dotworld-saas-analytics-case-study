---
name: cohort-retention
description: Calcule la rétention des abonnés payants par cohorte et par cycle facturé, sans biais de censure, et sépare le churn volontaire (annulation) du churn involontaire (paiement refusé). À utiliser pour « nos cohortes récentes retiennent-elles moins bien ? », « quel est le churn au 3e mois ? », « combien de départs sont dus aux paiements ? ».
---

# cohort-retention

## Quand l'utiliser
- Suivre la rétention mois après mois d'un produit, ou comparer des cohortes (avant / après un changement).
- Distinguer ce qui relève du produit (churn volontaire) de ce qui relève du paiement (churn involontaire).
- Alimenter une LTV (le skill `ltv-by-channel` s'appuie sur la même logique de maturité).

## Questions types
1. « Les abonnés du T4 2025 restent-ils aussi longtemps que ceux du T1 ? »
2. « Quelle part des abonnés paie encore au 6e cycle ? »
3. « Quelle part du churn est involontaire, et chez quels abonnés ? »

## Définitions
- **Cohorte** : abonnés payants regroupés par mois (ou trimestre) d'inscription.
- **Abonné payant** : au moins un cycle payé plein tarif (`paid_cycles >= 1`). L'essai payant ne suffit pas.
- **Rétention au cycle k** : part de la cohorte qui a payé au moins k cycles. C1 = 100 % par construction.
- **Churn volontaire** : l'abonné annule (`status = 'annule'`, hors fraude détectée).
- **Churn involontaire** : le renouvellement échoue après toutes les nouvelles tentatives (`annule_echec_paiement`).
- **Maturité** : un cycle k n'est lu pour une cohorte que si son DERNIER membre a eu le temps de l'atteindre
  (essai + (k − 1) cycles + 21 jours de nouvelles tentatives). Sinon les cohortes récentes paraissent
  artificiellement mauvaises : c'est le biais de censure.

## Étapes
1. Choisir la période d'inscription, les produits et le grain (mois ou trimestre).
2. Lancer `run.py` : matrice de rétention (cohortes en ligne, cycles en colonne) et churn par ancienneté.
3. Lire en diagonale : une cohorte qui décroche au même cycle que les autres = effet produit ;
   toutes les cohortes qui décrochent à la même DATE = événement (prix, incident, paiement).
4. Vérifier les contrôles avant de répondre.

## Pièges
- Mélanger formule mensuelle et annuelle (le skill ne garde que la mensuelle).
- Compter l'essai comme un cycle payé.
- Lire une cohorte trop jeune (les `nan` sont voulus : cycle pas encore observable).
- Conclure qu'un produit « retient mal » alors que c'est le paiement qui échoue : regarder le churn involontaire.

## Utilisation
```bash
python skills/cohort-retention/run.py --products A B C --start 2025-01-01 --end 2026-01-01 --grain quarter --max-cycle 8
python skills/cohort-retention/run.py --products B --grain month
```
Avec un assistant IA (par exemple Claude) : il lit ce fichier, lance `run.py` avec les bons paramètres
et ne répond qu'après le bloc « CONTRÔLES DE COHÉRENCE ».
