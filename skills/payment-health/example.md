# Exemple : « Pourquoi l'acceptation baisse-t-elle en Espagne depuis avril ? » (données SIMULÉES)

**Commande**
```bash
python skills/payment-health/run.py --countries ES --start 2026-01-01 --end 2026-07-01 --split 2026-04-01 --dim psp
```

**Ce que montre la sortie**

| PSP | Acceptation avant le 1er avril | Après | Écart |
|---|---|---|---|
| PSP_S | 85,2 % (1 858 tentatives) | 78,8 % (1 454) | **−6,5 pts** |
| PSP_A | 81,8 % (1 037) | 84,7 % (733) | +3,0 pts |

Code qui explique la baisse : `do_not_honor` passe de 2,9 % à 10,7 % des tentatives sur PSP_S (+7,9 pts) ;
il bouge peu sur PSP_A (+1,3 pt).

**Réponse vérifiée**
> La baisse est localisée sur **PSP_S** : −6,5 points d'acceptation sur les cartes espagnoles depuis avril,
> alors que PSP_A, sur les mêmes cartes, reste stable. Elle vient presque entièrement d'une hausse des refus
> génériques `do_not_honor`, signature typique d'un problème côté acquéreur ou d'une règle d'émetteur, pas d'un
> changement de clientèle. Actions : (1) ouvrir un ticket chez PSP_S avec les tentatives concernées ;
> (2) en attendant, router les cartes espagnoles vers PSP_A (test à 50 % pendant deux semaines pour mesurer) ;
> (3) suivre l'acceptation hebdomadaire. Tous les contrôles de cohérence passent ; le skill signale aussi
> 31 relances après refus définitif sur la période, à arrêter.

**Contrôles passés** : une tentative initiale par paiement, total des segments = total de la période,
taux dans [0, 1], plus de 300 tentatives de chaque côté de la rupture.
