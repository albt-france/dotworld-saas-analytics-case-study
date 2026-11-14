---
name: payment-health
description: Analyse la santé des paiements (taux d'acceptation, codes de refus, nouvelles tentatives) par PSP, pays, produit ou MID. À utiliser pour « pourquoi l'acceptation baisse dans tel pays ? », « quel PSP refuse le plus ? », « nos retries sont-ils efficaces ? », « faut-il router tel pays vers un autre PSP ? ».
---

# payment-health

## Quand l'utiliser
- Une alerte : l'acceptation baisse sur un pays, un produit ou un PSP.
- Une revue mensuelle de la performance des PSP avec l'équipe Paiement.
- Avant de changer le routage, la politique de retries ou la stratégie 3DS.

## Questions types
1. « Pourquoi le taux d'acceptation baisse-t-il en Espagne depuis avril ? »
2. « Quel PSP accepte le mieux les cartes brésiliennes et mexicaines ? »
3. « Quel délai entre deux nouvelles tentatives récupère le plus de paiements ? »
4. « Relançons-nous des refus définitifs (interdit par les réseaux) ? »

## Définitions (voir aussi METRICS.md)
- **Taux d'acceptation** = tentatives initiales acceptées / tentatives initiales (`attempt_no = 1`).
  On exclut les nouvelles tentatives, comme le recommande la documentation Stripe :
  sinon un même paiement refusé quatre fois compte quatre refus.
- **Taux de succès après retries** = paiements (`payment_id`) dont au moins une tentative est acceptée / paiements.
- **Refus « soft »** (temporaire : `insufficient_funds`, `do_not_honor`, `try_again_later`, `processing_error`,
  `authentication_required`) : une nouvelle tentative peut réussir.
- **Refus « hard »** (définitif : `stolen_card`, `lost_card`, `expired_card`, `incorrect_number`,
  `transaction_not_allowed`, `fraudulent`) : ne jamais relancer la même carte.
- **CIT / MIT** : paiement initié par le client (essai, achat) ou par le marchand (renouvellement).
  La DSP2 impose l'authentification forte (3DS) sur les CIT de l'EEE, pas sur les MIT.

## Étapes
1. **Cadrer** : période, pays de la carte, date de rupture si l'on cherche une cause.
2. **Mesurer** l'acceptation sur les tentatives initiales, par PSP (puis produit, type de carte, initiateur).
3. **Localiser** : la baisse touche-t-elle un seul PSP ? Un seul produit ? Tous les pays ?
   Si un seul PSP baisse et que l'autre reste stable sur les mêmes cartes, la cause est côté PSP ou acquéreur.
4. **Expliquer** par les codes : quel code a le plus augmenté (en points de % des tentatives) ?
   - `do_not_honor` en hausse sur un seul PSP : problème d'acquéreur ou de règles émetteur, à remonter au PSP.
   - `insufficient_funds` en hausse : effet calendrier (fin de mois) ou clientèle plus prépayée.
   - `authentication_required` : parcours 3DS (abandon, émetteurs).
5. **Chiffrer** : paiements perdus = baisse × volume × montant moyen, avec un intervalle de confiance.
6. **Lancer les contrôles** (automatiques dans `run.py`) et ne conclure que s'ils passent.
7. **Recommander** : action, gain attendu, risque, et comment on mesurera le résultat.

## Pièges
- Mélanger tentatives initiales et nouvelles tentatives dans le taux d'acceptation.
- Comparer deux PSP qui ne voient pas les mêmes cartes (pays, type, CIT/MIT) : comparer à périmètre égal.
- Conclure sur moins de 300 tentatives par segment : ±3 points de bruit.
- Oublier les rafales de tests de cartes : elles font chuter l'acceptation sans problème de PSP
  (vérifier avec le skill de fraude / `fraud_signals.velocity_1h_same_bin`).
- Le jour de la semaine et la fin du mois jouent sur `insufficient_funds`.

## Utilisation
```bash
python skills/payment-health/run.py --countries ES --start 2026-01-01 --end 2026-07-01 --split 2026-04-01 --dim psp
python skills/payment-health/run.py --countries BR MX --dim psp
python skills/payment-health/run.py --dim produit
```
Avec un assistant IA (par exemple Claude) : copier ce dossier dans le répertoire de skills de l'assistant ;
il lit ce fichier, choisit les paramètres à partir de la question, lance `run.py` et ne répond
qu'après le bloc « CONTRÔLES DE COHÉRENCE ».

## Fichiers
- `queries/acceptance.sql` : acceptation par dimension (liste blanche de colonnes).
- `queries/before_after.sql`, `queries/decline_codes.sql` : rupture et codes qui l'expliquent.
- `queries/retries.sql` : succès des nouvelles tentatives par code initial et délai.
- `queries/weekly_trend.sql` : tendance hebdomadaire pour un graphique.
- `run.py` : exécute, contrôle, affiche. `example.md` : une question, une réponse vérifiée.
