# Skills d'analyse réutilisables

Quatre « skills » pour que les équipes Marketing, Produit, Paiement et Finance répondent seules à leurs
questions les plus fréquentes, avec les mêmes définitions et les mêmes contrôles que l'équipe Data.

| Skill | Question type | Contrôles avant de répondre |
|---|---|---|
| [`cohort-retention`](cohort-retention/SKILL.md) | « Nos cohortes récentes retiennent-elles moins bien ? Combien de départs viennent des paiements ? » | C1 = 100 %, courbes décroissantes, somme des cohortes, cohortes jeunes tronquées |
| [`ltv-by-channel`](ltv-by-channel/SKILL.md) | « Quelle est la LTV selon le canal ? Quelles campagnes sont rentables ? » | cohortes complètes, LTV croissante avec l'horizon, canaux sans coût média signalés |
| [`payment-health`](payment-health/SKILL.md) | « Pourquoi l'acceptation baisse-t-elle dans ce pays ? Nos retries marchent-ils ? » | une tentative initiale par paiement, totaux, taille des segments, relances interdites |
| [`experiment-readout`](experiment-readout/SKILL.md) | « Peut-on généraliser cette variante ? » | SRM, affectation unique, fenêtre complète, équilibre des groupes |

## Format d'un skill
```
skills/<nom>/
  SKILL.md       quand l'utiliser, questions types, définitions, étapes, pièges
  queries/*.sql  modèles SQL paramétrables ({{start}}, {{countries}}...) ; colonnes choisies sur liste blanche
  run.py         exécute les modèles, lance les contrôles de cohérence, affiche une réponse en Markdown
  example.md     une question réelle, la sortie et la réponse vérifiée
skills/_shared/skillkit.py   connexion DuckDB, paramètres validés (pas d'injection SQL), contrôles
```

## Deux façons de s'en servir
1. **En ligne de commande**, par toute personne de l'équipe :
   `python skills/payment-health/run.py --countries ES --split 2026-04-01`
2. **Avec un assistant IA** (Claude ou équivalent) : le dossier suit le format des skills d'assistant
   (`SKILL.md` avec un nom et une description). L'assistant choisit le skill d'après la question, lance
   `run.py` avec les bons paramètres et ne répond qu'une fois les contrôles passés. Le SQL reste lisible
   et versionné : on peut toujours vérifier ce que l'assistant a calculé.

## Règles communes
- Mêmes définitions que [`METRICS.md`](../METRICS.md) ; si une définition change, elle change ici et là.
- Un contrôle en échec = pas de réponse chiffrée, mais une investigation.
- Les paramètres sont validés (dates ISO, codes simples) et les noms de colonnes viennent d'une liste blanche.
- Les données de ce dépôt sont SIMULÉES : brancher les vues de `sql/00_views.sql` sur l'entrepôt réel suffit.
