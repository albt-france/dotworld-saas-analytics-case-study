# Sources, licences et dates de collecte

Trois natures de données, toujours étiquetées : **DONNÉES PUBLIQUES**, **DONNÉES RÉELLES (KKBOX)**, **SIMULÉ**.

## 1. Données publiques sur DotWorld (collecte du 13/11/2026)
Faits datés et sourcés, un par ligne : [`public/dotworld_facts.csv`](public/dotworld_facts.csv).
Grille de prix : [`public/price_book.csv`](public/price_book.csv). Script : [`src/collect_dotworld.py`](../src/collect_dotworld.py).

| Source | URL | Ce qu'on y prend |
|---|---|---|
| Site vitrine DotWorld | https://www.dotworld.ch/ , /team | modèle « Test, Learn, Scale », chiffres du site (5 SaaS, 19 pays), adresse |
| Site Carrières DotWorld | https://dotworld.teamtailor.com/ , /jobs , /pages/notre-histoire , /departments/produit | création 2015, 55 collègues, 90 % de télétravail, 50 M+ visiteurs par an, autofinancement, univers produits, outils data |
| Offre Data Analyst SaaS | https://dotworld.teamtailor.com/jobs/8642089-data-analyst-saas | missions, profil, rattachement |
| Offres Payment Operations et Risk & Compliance | https://dotworld.teamtailor.com/jobs/8592394-payment-operations-specialist-international , /jobs/8591658-risk-compliance-specialist-paiement | plusieurs PSP, billing, MID, moyens de paiement, fraude à l'essai, seuils des réseaux |
| Offres Product Manager Growth, Creative Strategist, Product Data Scientist | /jobs/8463157-product-manager-growth , /jobs/8274972-creative-strategist , /jobs/8642055-product-data-scientist-saas | verticale automobile, canaux Google / Meta / TikTok, pratique d'A/B testing |
| Makemycv : mentions légales | https://makemycv.com/en-SG/legal (mise à jour du 12/02/2026) | **preuve du lien** : éditeur DOTWORLD SA |
| Makemycv : CGV | https://makemycv.com/en-US/tos (mise à jour du 25/08/2025) | moyens de paiement (carte, Google Pay, Stripe), formules |
| Makemycv : tarifs | https://makemycv.com/{fr, de, it, es, es-MX, nl, pl, pt-BR, ro, sv, en-AU, en-CA, en-SG, en-US}/pricing | essai 2,90 € / 7 jours, 27,95 € / 4 semaines, annuel 94,80 € |
| Makemycv : robots.txt | https://makemycv.com/robots.txt | 34 versions localisées |

**Règles suivies** : `robots.txt` lu et respecté (dotworld.ch : vide ; Teamtailor : pages publiques autorisées,
`Content-Signal: ai-input=yes`) ; une requête toutes les 3 secondes ; aucune connexion, aucun formulaire, aucune
inscription, aucun essai, aucun paiement. La page Himalayas de l'offre affiche une vérification de sécurité :
elle n'a pas été contournée, l'offre a été lue sur le site Carrières de DotWorld.
**Non-publication des instantanés bruts** : les pages HTML enregistrées (`data/raw/`) restent locales, car elles
contiennent des textes protégés et les noms de salariés de DotWorld. Le dépôt publie les faits extraits, l'URL et la date.

**Produits** : seul Makemycv est attribué à DotWorld (preuve : mentions légales). La verticale automobile et les univers
« gestion de contenus » et « création design » sont cités par DotWorld sans nom de produit ; aucun nom n'est supposé.
Des noms de produits apparaissent sur la page Équipe du site vitrine dans des témoignages fictifs (texte « lorem ipsum ») :
ils ne sont pas retenus comme preuve.

## 2. Références publiques sur les paiements (collecte du 13/11/2026)
Fichier : [`public/payment_references.csv`](public/payment_references.csv).

| Sujet | Source | Fiabilité |
|---|---|---|
| Stripe Smart Retries (jusqu'à 8 relances sur 2 semaines, jamais après un refus définitif) | https://docs.stripe.com/billing/revenue-recovery/smart-retries | documentation officielle |
| Stripe : mesure de l'acceptation sur les refus uniques | https://docs.stripe.com/declines | documentation officielle |
| Stripe : codes de refus | https://docs.stripe.com/declines/codes | documentation officielle |
| Stripe : 3D Secure et DSP2 | https://docs.stripe.com/payments/3d-secure | documentation officielle |
| Adyen : refusal reasons | https://docs.adyen.com/development-resources/refusal-reasons | documentation officielle |
| Visa VAMP : seuil marchand 1,5 % depuis le 01/04/2026 (2,2 % avant), 1 500 événements | https://merchantriskcouncil.org/learning/resource-center/member-news/blog/2026/stricter-vamp-ratio-thresholds-are-now-in-effect-heres-how-to-stay-compliant et guides concordants | sources secondaires concordantes, à confirmer sur la fiche Visa |
| Mastercard ECM 1,5 % / 100 chargebacks, HECM 3 % / 300 | https://www.jpmorgan.com/directdoc/mastercard-excessive-chargeback-program-guide.pdf | guide acquéreur (révision 2019) |

## 3. Données réelles d'abonnement : KKBox
- **Jeu** : *WSDM - KKBox's Churn Prediction Challenge* (WSDM Cup 2018), Kaggle :
  https://www.kaggle.com/competitions/kkbox-churn-prediction-challenge/data
- **Contenu utilisé** : `transactions.csv`, `transactions_v2.csv` (transactions d'abonnement : moyen de paiement, durée,
  prix affiché et payé, renouvellement automatique, annulation, expiration), `train_v2.csv` (étiquette de churn de mars 2017).
- **Accès et licence** : téléchargement par un compte Kaggle personnel après acceptation des règles de la compétition.
  Les données sont réservées à un usage non commercial lié à la compétition et à la recherche ; elles **ne sont pas
  redistribuées** : `data/raw/kkbox/` est exclu du dépôt. Seuls des agrégats (`public/kkbox_*.csv`) et le script
  [`src/kkbox_prepare.py`](../src/kkbox_prepare.py) sont publiés.
- **Monnaie** : dollar taïwanais (NT$).

## 4. Données simulées
Produites par [`src/simulate.py`](../src/simulate.py) (graine 42), hypothèses dans [`ASSUMPTIONS.md`](ASSUMPTIONS.md).
Elles ne sont pas des données de DotWorld. Les fichiers `data/simulated/*.parquet` se régénèrent en ~40 secondes.
