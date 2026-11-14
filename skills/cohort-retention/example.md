# Exemple : « Combien de nos départs sont dus aux paiements, et chez qui ? » (données SIMULÉES)

**Commande**
```bash
python skills/cohort-retention/run.py --products A B C --start 2025-01-01 --end 2026-01-01 --grain quarter --max-cycle 8
```

**Ce que montre la sortie**
- Rétention stable d'une cohorte trimestrielle à l'autre : pour le produit A, environ 60 % des abonnés
  payants paient un 2e cycle et environ 15 % un 8e cycle, quel que soit le trimestre de 2025.
- Le produit B (création design) retient mieux : environ 73 % au 2e cycle, 24 à 27 % au 8e.
- Part du churn involontaire selon l'ancienneté (produit A) : 15 % après 1 cycle payé, 25 % après 2-3 cycles,
  **44 % après 4 cycles et plus**.

**Réponse vérifiée**
> La rétention ne se dégrade pas d'une cohorte à l'autre en 2025. En revanche, plus un abonné est ancien,
> plus son départ vient d'un paiement refusé : chez les abonnés de 4 cycles et plus, 41 à 58 % des départs
> sont involontaires selon le produit. Ce sont les clients les plus précieux, et ils ne voulaient pas partir.
> Priorité : le calendrier des nouvelles tentatives et la mise à jour automatique des cartes (account updater),
> à mesurer avec le skill `payment-health`. Tous les contrôles passent (11 563 abonnés, C1 = 100 %,
> aucune remontée de courbe, cohortes récentes tronquées).
