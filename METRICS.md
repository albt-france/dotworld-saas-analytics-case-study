# Définitions partagées des indicateurs

Une seule définition par indicateur, utilisée par le SQL (`sql/`), les skills (`skills/`), le rapport et le
tableau de bord. Les requêtes s'appuient sur les vues de [`sql/00_views.sql`](sql/00_views.sql).

Conventions : montants en EUR au taux de change **du jour** de l'événement ; horodatages en **UTC** ;
date d'observation `params.obs_end` (30/06/2026 dans la simulation) : tout ce qui suit est inconnu.

---

## Acquisition

### Conversion (visite → abonné payant)
- **Définition** : abonnés payants / visites, sur une même fenêtre d'inscription.
- **Abonné payant** : au moins un cycle payé **plein tarif** (`paid_cycles >= 1`). L'essai à petit prix ne compte pas.
```sql
SELECT channel, count(*) FILTER (WHERE paid_cycles >= 1)::DOUBLE / count(*) AS signup_to_payer
FROM customers WHERE signup_ts < TIMESTAMP '2026-01-01' GROUP BY 1;
```
- **Cas limites** : les rafales de robots (tests de cartes) gonflent visites et inscriptions « directes » ; les exclure
  avec `fraud_signals.velocity_1h_same_bin >= 5` avant de comparer les canaux.

### CAC (coût d'acquisition client)
- **Définition** : dépense média de la période / abonnés payants acquis sur la même période.
- **Cas limites** : SEO et direct ont un CAC média nul (contenu, équipe, marque non imputés) ; l'affiliation est payée
  au premier paiement, donc légèrement après l'inscription ; attribution au dernier clic.

### LTV (valeur client) à h jours
- **Définition** : revenu net cumulé pendant h jours après l'inscription / abonnés payants de la cohorte.
  Revenu net = paiements acceptés − remboursements − montants des litiges perdus ou acceptés − frais de litige.
- **Anti-censure** : seules les inscriptions observées h jours entiers entrent dans le calcul
  (`signup_ts + h jours <= obs_end`).
```sql
WITH m AS (SELECT * FROM customers, params WHERE signup_ts + to_days(180) <= obs_end)
SELECT m.channel, sum(e.amount_eur) / count(DISTINCT m.signup_id) FILTER (WHERE m.paid_cycles >= 1) AS ltv180
FROM m JOIN revenue_events e USING (signup_id)
WHERE e.event_ts < m.signup_ts + to_days(180) GROUP BY 1;
```
- **Cas limites** : dire si la LTV est par inscription ou par payant ; ne jamais comparer des horizons différents.

### ROAS et délai de rentabilisation
- **ROAS(h)** = revenu net à h jours / dépense média. **Contribution** = revenu net − dépense.
- **Délai de rentabilisation** : premier âge d où la LTV cumulée par payant dépasse le CAC du canal.

## Parcours et rétention

### Funnel
Étapes : inscription → paiement de l'essai lancé → essai actif → 1er renouvellement payé → 2e renouvellement payé.
Fenêtre d'inscription arrêtée assez tôt (30/04/2026) pour que chaque inscrit ait pu atteindre son 1er renouvellement.

### Rétention au cycle k
- **Définition** : part des abonnés payants d'une cohorte qui ont payé au moins k cycles. C1 = 100 %.
- **Anti-censure** : un cycle k n'est lu que si le **dernier** membre de la cohorte a eu le temps de l'atteindre :
  essai + (k − 1) cycles + 21 jours de nouvelles tentatives ≤ `obs_end`.

### Churn volontaire et involontaire
- **Volontaire** : l'abonné annule (`status = 'annule'`, hors fraude détectée).
- **Involontaire** : le renouvellement échoue après toutes les nouvelles tentatives (`status = 'annule_echec_paiement'`).
- **KKBox (données réelles)** : pas de journal des refus ; on approxime l'involontaire par « renouvellement automatique
  actif, aucune annulation, aucun paiement suivant ».

### ARPA (revenu moyen par compte payant)
- **Définition** : revenu encaissé du mois / comptes ayant payé dans le mois.
- **Cas limites** : formules de durées différentes (30 contre 365 jours) : un paiement annuel gonfle l'ARPA du mois d'achat ;
  comparer à formule égale ou mensualiser.

## Paiements et risques

### Taux d'acceptation
- **Définition** : tentatives **initiales** acceptées / tentatives initiales (`attempt_no = 1`).
  Les nouvelles tentatives sont exclues, comme le recommande la documentation Stripe.
```sql
SELECT psp, card_country, avg((outcome = 'approved')::INT) AS acceptance_rate
FROM payment_attempts WHERE attempt_no = 1 GROUP BY 1, 2;
```
- **Cas limites** : comparer les PSP à périmètre égal (pays de la carte, type de carte, CIT/MIT) ; ≥ 300 tentatives par segment ;
  les rafales de tests de cartes font chuter l'acceptation sans problème de PSP.

### Succès après nouvelles tentatives et taux de récupération
- **Succès après retries** : paiements (`payment_id`) dont une tentative est acceptée / paiements.
- **Succès d'une nouvelle tentative** : nouvelles tentatives acceptées / nouvelles tentatives, par délai et par numéro.
- **Refus « soft »** (temporaires) : `insufficient_funds`, `do_not_honor`, `try_again_later`, `processing_error`,
  `authentication_required`. **Refus « hard »** (définitifs, ne jamais relancer) : `stolen_card`, `lost_card`,
  `expired_card`, `incorrect_number`, `transaction_not_allowed`, `fraudulent`.

### Taux de litiges
- **Visa (type VAMP)** : (litiges + signalements de fraude TC40) du mois / transactions Visa réglées du mois.
  Seuil « Excessive » marchand : 1,5 % depuis le 01/04/2026 (2,2 % avant), avec au moins 1 500 événements.
- **Mastercard (ECM)** : chargebacks du mois / transactions Mastercard du **mois précédent** ; seuil 1,5 % et 100 chargebacks.
```sql
SELECT mid, month, chargebacks / lag(settled) OVER (PARTITION BY mid ORDER BY month) AS mc_ratio FROM ...
```
- **Cas limites** : un litige arrive 3 à 4 semaines après le paiement : les mois récents sont incomplets ; diviser par
  des transactions réglées, pas par des tentatives.

### Fraude confirmée
- **Définition** : inscription ayant reçu un litige pour fraude ou un signalement TC40.
- **Piège** : une carte testée puis refusée n'a jamais de litige. Mesurer une règle anti-fraude sur ses faux positifs
  observables (clients bloqués qui auraient payé), pas sur la « précision » contre la fraude confirmée.

## Qualité des données

### Revenu et réconciliation
- **Revenu brut** : somme des paiements acceptés en EUR (taux du jour), rangés par mois **UTC**.
- **Réconciliation** : rapprochement ligne à ligne PSP / base interne sur l'identifiant de tentative. Causes d'écart
  suivies : webhooks perdus (manquants), webhooks rejoués (doublons), litiges débités par le PSP mais absents de la base,
  taux de change (moyen du mois contre taux du jour), fuseau horaire des rapports PSP (changement de mois).

## Expérimentation
- **Unité** : l'utilisateur **affecté** (pas seulement ceux qui convertissent).
- **SRM** : test du khi-deux contre le partage prévu ; p < 0,001 = test non lisible.
- **Métrique principale** fixée avant le test (ici : revenu net par utilisateur affecté à 60 jours).
- **Intervalle de confiance** à 95 % : Wald pour une proportion, bootstrap (2 000 tirages) pour une moyenne.
- **Effet minimal détectable** (80 % de puissance, alpha 5 %) publié avec chaque lecture.
