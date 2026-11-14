# Hypothèses de la simulation (données SIMULÉES)

Le parcours de [`src/simulate.py`](../src/simulate.py) est **inventé** (graine fixe 42). Il reproduit des
mécanismes réalistes d'un studio SaaS par abonnement pour montrer une méthode d'analyse.
**Aucun de ces chiffres n'est un chiffre de DotWorld.** Toutes les constantes sont en tête du script.

## Périmètre
- 18 mois : du 01/01/2025 au 30/06/2026 (date d'observation ; la suite est censurée).
- ~2 100 visites par jour au départ, +60 % sur la période, pic de janvier (+15 %), week-end −20 %.
- Une visite = un nouveau visiteur (pas de visites répétées).

## Produits fictifs
| Produit | Inspiré de | Essai | Renouvellement | Annuel | Source du prix |
|---|---|---|---|---|---|
| A | univers RH / CV | 2,90 € pour 7 jours | 27,95 € toutes les 4 semaines | 94,80 € | **prix publics de Makemycv** (13/11/2026) |
| B | univers création design / contenus | gratuit, 7 jours (carte enregistrée) | 14,95 € / 30 jours | 119 € | hypothèse |
| C | verticale automobile | 1,00 € pour 3 jours | 19,90 € / 30 jours | aucun | hypothèse |

## Pays, devises, canaux
- 10 pays de carte : FR 22 %, US 18 %, DE 10 %, ES 9 %, IT 8 %, BR 8 %, MX 7 %, PL 7 %, GB 6 %, NL 5 %.
- Devise : USD aux États-Unis, EUR ailleurs (comme Makemycv, y compris au Brésil et au Mexique).
- Canaux (part des visites, coût par visite) : SEO 36 % (0 €), Google marque 7 % (0,15 €), Google générique 18 % (0,52 €),
  Meta prospection 9 % (0,30 €), Meta retargeting 4 % (0,40 €), TikTok 10 % (0,11 €), affiliation 6 % (12 € par premier
  paiement), direct 10 % (0 €). Coefficient pays : US ×1,6, GB ×1,3, PL ×0,6, MX ×0,5, BR ×0,45.
  Le choix Google / Meta / TikTok suit l'offre « Creative Strategist » de DotWorld.

## Mécanismes programmés (ce que l'analyse doit retrouver)
1. **Le moins cher n'est pas le plus rentable** : TikTok a le coût par visite le plus bas mais convertit 2 à 4 fois moins
   et ses abonnés partent plus vite (churn ×1,35).
2. **Un PSP refuse plus dans certains pays** : PSP_S (type Stripe) +20 pts de refus au Brésil et +16 pts au Mexique
   (pas d'acquisition locale) ; PSP_A (type Adyen) +4 pts. 15 % du trafic va à l'autre PSP (répartition de charge),
   ce qui permet de comparer les PSP à cartes égales.
3. **Incident** : à partir du 01/04/2026, +8 pts de refus `do_not_honor` sur PSP_S pour les cartes espagnoles.
4. **Nouvelles tentatives** : jusqu'à 4 relances sur refus « soft », délai tiré dans {0, 1, 2, 3, 5, 7} jours ;
   le succès dépend du code et du délai (fonds insuffisants : 5 % le jour même, 25-27 % à 5-7 jours), et baisse de 15 %
   à chaque tentative. PSP_A relance aussi 70 % des refus définitifs (mauvaise configuration, contraire aux règles des réseaux).
5. **3DS** : sur les paiements initiés par le client dans l'EEE, 65 % de « challenge », dont 9 % échouent ou sont abandonnés.
6. **Fraude** : 10 rafales de tests de cartes (150 à 600 essais en 2 heures) sur les produits A et C (essais à petit prix),
   plus une fraude « organique » de 0,6 % des essais (×4 sur cartes prépayées, ×2 TikTok, ×2,5 affiliation, ×0,4 produit B).
7. **Litiges** : 1 % au premier renouvellement (« j'ai oublié l'essai »), 0,2 % ensuite, ×1,3 sur le produit A ;
   60 % des paiements frauduleux acceptés finissent en litige ; délai log-normal médian ~25 jours.
8. **Campagne agressive** `meta_promo_choc` (15/02 → 31/03/2026, FR/US/ES) : CAC bas, mais litiges ×6 au premier renouvellement.
9. **Expérimentation** `EXP-A-PRIX-TRANSPARENT` (produit A, 01/03 → 30/04/2026, 50/50) : effet programmé −6 % sur le
   lancement de l'essai, −8 % d'annulations pendant l'essai, −50 % de litiges au premier renouvellement.
   La lecture du test dit ce que les données montrent, pas ce qui a été programmé (voir page 8 du rapport).
10. **Qualité des données** : 0,25 % des paiements absents de la base interne (webhooks perdus), 0,4 % en double (webhooks
    rejoués) ; base interne convertie au taux moyen du mois, rapports PSP au taux du jour ; PSP_S rapporte à l'heure de
    Zurich, PSP_A et la base en UTC ; les litiges ne sont débités que dans les rapports PSP.
11. **Frais PSP** (hypothèse) : PSP_S 1,5 % + 0,25 € (3,25 % hors Europe) ; PSP_A 1,2 % + 0,11 € (2,8 % hors Europe) ;
    frais de litige 15 €.

## Rétention (aléa de départ volontaire par cycle payé)
- A : 36 %, 24 %, 17 %, 13 %, 11 %, 10 %, 9 %, 8 % ; B : 20 %, 13 %, 10 %, 8 %, 7 %, 6 %, 5,5 %, 5 % ;
  C : 42 %, 28 %, 19 %, 15 %, 12 %, 10 %, 9 %, 8 % ; multiplié par canal (0,85 pour la marque à 1,35 pour TikTok).
- Annulation pendant l'essai : 30 % (Google marque) à 68 % (TikTok), ×1,1 produit A, ×0,9 produit B, ×1,15 produit C.

## Ce que la simulation ne fait pas
- Pas de visites répétées, pas de multi-appareils, pas d'attribution multi-touch.
- Pas de mise à jour automatique des cartes (account updater) ni de changement de moyen de paiement par le client.
- Pas de PayPal ni de portefeuilles : uniquement des cartes Visa, Mastercard et Amex.
