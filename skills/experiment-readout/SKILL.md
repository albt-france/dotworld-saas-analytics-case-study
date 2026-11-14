---
name: experiment-readout
description: Lit un test A/B à deux groupes : contrôles de validité (déséquilibre d'échantillon, affectation unique, fenêtre complète), effets avec intervalles de confiance, garde-fous (litiges, remboursements), puissance et décision selon une règle fixée à l'avance. À utiliser pour « comment lire ce test ? », « peut-on généraliser la variante ? », « combien de temps faut-il le laisser tourner ? ».
---

# experiment-readout

## Quand l'utiliser
- À la fin d'un test sur le parcours (essai, paiement, prix, page d'abonnement).
- Pour préparer une décision avec le Data Scientist et le Product Manager.
- Avant de lancer un test : la partie puissance dit combien d'utilisateurs il faut.

## Questions types
1. « La variante "prix transparent" augmente-t-elle le revenu par utilisateur ? »
2. « Réduit-elle les litiges, sans faire chuter les essais ? »
3. « Le test est-il assez grand pour conclure ? »

## Ce que fait le skill, dans l'ordre
1. **Contrôles de validité, avant tout** :
   - **SRM** (sample ratio mismatch) : khi-deux contre le partage prévu ; p < 0,001 = affectation cassée, on ne lit rien.
   - affectation unique par utilisateur ; fenêtre de suivi complète pour tous ; mêmes appareils dans les deux groupes.
2. **Métrique principale**, choisie AVANT le test (par défaut le revenu net par utilisateur affecté à 60 jours) :
   différence, IC à 95 % (bootstrap pour une moyenne, Wald pour une proportion), p-value.
3. **Métriques secondaires** : passage au paiement de l'essai, conversion payante.
4. **Garde-fous** : litiges et remboursements pour 1 000 payants.
5. **Puissance** : effet minimal détectable (80 %, alpha 5 %) avec la taille obtenue.
6. **Décision** selon la règle écrite dans `run.py` : généraliser, arrêter ou « pas de conclusion ».

## Pièges
- Regarder les résultats tous les jours et s'arrêter dès que p < 0,05 (« peeking ») : fixer la durée avant.
- Changer de métrique principale après coup.
- Conclure « pas d'effet » quand le test manque de puissance : dire « pas de conclusion » et donner l'effet minimal détectable.
- Analyser seulement les utilisateurs qui ont payé (biais de sélection) : l'unité est l'utilisateur AFFECTÉ.
- Les litiges arrivent 3 à 4 semaines après le paiement : une fenêtre trop courte les rate.

## Utilisation
```bash
python skills/experiment-readout/run.py --experiment EXP-A-PRIX-TRANSPARENT --window 60 --primary revenue
python skills/experiment-readout/run.py --experiment EXP-A-PRIX-TRANSPARENT --primary paid_first_renewal
```
Avec un assistant IA (par exemple Claude) : il lit ce fichier, lance `run.py`, et recopie la décision
telle quelle ; il ne la reformule pas en « la variante gagne » si le skill dit « pas de conclusion ».
