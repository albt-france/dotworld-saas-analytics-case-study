---
name: ltv-by-channel
description: Calcule le CAC, la LTV par abonné payant, le ROAS et la contribution par canal, campagne ou pays, à un horizon fixe et sans biais de censure. À utiliser pour « quelle est la LTV selon le canal ? », « quels canaux ou campagnes génèrent une croissance rentable ? », « faut-il couper telle campagne ? ».
---

# ltv-by-channel

## Quand l'utiliser
- Arbitrer les budgets d'acquisition entre canaux (Google Ads, Meta, TikTok, affiliation).
- Juger une nouvelle campagne à 30 ou 90 jours, puis confirmer à 180 jours.
- Répondre à « le canal le moins cher est-il le plus rentable ? ».

## Questions types
1. « Quelle est la LTV à 180 jours des abonnés venus de chaque canal ? »
2. « Quelles campagnes du dernier semestre sont rentables à 90 jours ? »
3. « Quel pays a le meilleur ROAS sur Google Ads ? » (`--dim pays`)

## Définitions (METRICS.md)
- **Abonné payant** : au moins un cycle payé plein tarif.
- **CAC** = dépenses média de la période / abonnés payants acquis sur la même période.
- **LTV(h)** = revenu net cumulé pendant h jours après l'inscription / abonnés payants
  (net = paiements − remboursements − litiges perdus − frais de litige ; en EUR au taux du jour).
- **ROAS(h)** = revenu net à h jours / dépenses. **Contribution** = revenu net − dépenses.
- **Anti-censure** : seules les inscriptions observées h jours entiers entrent dans le calcul.

## Étapes
1. Choisir l'horizon (30, 90, 180, 365 jours) et une période d'inscription assez ancienne pour cet horizon.
2. Lancer `run.py` par canal, puis par campagne ou par pays sur les canaux qui posent question.
3. Lire CAC et LTV ensemble : un CAC bas n'est intéressant que si la LTV suit.
4. Croiser avec le risque : une campagne rentable mais qui génère des litiges (skill `payment-health`,
   requête `sql/04_risk.sql`) peut faire dépasser les seuils Visa ou Mastercard.
5. Vérifier les contrôles, puis recommander (budget, plafond de CAC, test).

## Pièges
- **Censure** : comparer la LTV d'une cohorte de 2 mois à celle d'une cohorte de 12 mois.
- **CAC = 0 pour le SEO et le direct** : leurs coûts (contenu, équipe, marque) ne sont pas dans les dépenses média.
- **Attribution** : un seul canal par inscription (dernier clic). Le retargeting et la marque captent
  une demande créée ailleurs : leur ROAS est flatteur.
- **LTV par inscription contre LTV par payant** : dire lequel on utilise ; ce skill donne la LTV par payant.
- **Affiliation** : la commission est versée au premier paiement ; une partie de ce coût tombe après l'inscription.

## Utilisation
```bash
python skills/ltv-by-channel/run.py --horizon 180 --start 2025-01-01 --end 2026-01-01
python skills/ltv-by-channel/run.py --horizon 90 --dim campagne --start 2025-10-01 --end 2026-04-01
```
Avec un assistant IA (par exemple Claude) : il lit ce fichier, lance `run.py` et ne répond qu'après
le bloc « CONTRÔLES DE COHÉRENCE ».
