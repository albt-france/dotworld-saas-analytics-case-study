# Recommandations priorisées

Chiffres issus du parcours **SIMULÉ** (graine 42, 18 mois) : ils montrent l'ordre de grandeur et la méthode de
chiffrage, pas la situation réelle de DotWorld. Sources : `data/results/key_numbers.json`, `sql/`, `src/analysis.py`.
Chaque fourchette est un intervalle de confiance à 95 %. Le revenu chiffré est le revenu **immédiat** récupéré ;
la valeur future des abonnés sauvés n'est pas comptée (estimation prudente).

| # | Action | Impact chiffré | Effort | Risque | Comment mesurer |
|---|---|---|---|---|---|
| 1 | **Arrêter les relances après refus définitif** (configuration de PSP_A) | 555 relances interdites évitées ; succès actuel 1,3 % | faible (paramétrage) | nul | compteur hebdomadaire `hard_decline_retries` = 0 |
| 2 | **Relancer les refus « soft » à J+3 ou J+5**, plus le jour même ni le lendemain | **+21,2 K€** (18,1 à 24,2 K€) : 882 paiements récupérés | faible | faible : quelques jours de service en plus avant récupération | test A/B sur le calendrier de relance, critère : succès après retries par code |
| 3 | **Router les cartes brésiliennes et mexicaines vers PSP_A** | **+14,9 K€** (11,5 à 18,4 K€) : +8,6 pts d'acceptation au Brésil, +10,4 pts au Mexique | moyen (règles de routage) | frais de PSP_A à comparer ; volume concentré | bascule à 50 % pendant 4 semaines, puis 100 % si l'écart tient |
| 4 | **Traiter l'incident espagnol de PSP_S** (ticket + routage temporaire vers PSP_A) | **+2,3 K€** (1,5 à 3,1 K€) depuis avril : −7 pts d'acceptation, refus `do_not_honor` | faible | faible | acceptation hebdomadaire ES par PSP (skill `payment-health`) |
| 5 | **Piloter chaque campagne sur son taux de litige à 45 jours**, pas seulement son ROAS ; arrêter ou corriger les messages de la campagne agressive | rester sous le seuil Visa de 1,5 % (le MID principal l'a franchi en avril : 1,52 %) ; 73 litiges pour 1 000 premiers renouvellements contre 14 en moyenne | faible | baisse de volume à court terme | ratio de litiges par MID et par campagne, alerte à 1 % |
| 6 | **Bloquer les rafales de tests de cartes** (plus de 5 essais sur le même BIN en une heure) | 45 % de la fraude confirmée évitée ; 5 clients légitimes bloqués sur 4 219 blocages | faible | faible | faux positifs observables chaque semaine |
| 7 | **Réconcilier PSP et base interne chaque jour** : dédoublonner les webhooks, rejouer les manquants, intégrer les litiges, fixer UTC et le taux du jour | écart de −0,63 % (−10,4 K€ sur 18 mois) expliqué à 98 % ; 140 paiements changeaient de mois | moyen (avec le Data Engineer) | nul | écart quotidien < 0,05 % |
| 8 | **Généraliser l'affichage du prix du renouvellement** au paiement de l'essai | revenu à 60 jours inchangé (+0,07 € par utilisateur, IC −0,67 à +0,83) ; −2,6 pts d'essais ; litiges 35 → 27 ‰ (non significatif) | faible | faible | suivi des litiges du produit A pendant 8 semaines |
| 9 | **Donner aux équipes les 4 skills d'analyse** (rétention, LTV par canal, santé des paiements, lecture de test) | moins de demandes ad hoc ; mêmes définitions partout | moyen | réponses fausses si les définitions dérivent : contrôles intégrés | nombre de questions résolues sans l'équipe Data |

## Ordre proposé
1. **Semaine 1** : actions 1, 4 et 6 (paramétrage, risque nul ou faible, effet immédiat).
2. **Semaines 2 à 6** : tests des actions 2 et 3 avec le Data Scientist et l'équipe Paiement.
3. **En continu** : actions 5 et 7 (suivi), 8 (décision produit), 9 (outillage des équipes).

## Ce qui reste à vérifier sur les vraies données
- Les frais réels de chaque PSP par pays (ils peuvent annuler une partie du gain de routage).
- La politique de relance déjà active (Smart Retries ou calendrier maison) et la mise à jour automatique des cartes.
- Le volume réel de litiges par MID, contre les seuils Visa (1 500 événements) et Mastercard (100 chargebacks).
