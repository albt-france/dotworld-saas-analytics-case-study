# Exemple : « Quelle est la LTV selon le canal, et où la croissance est-elle rentable ? » (données SIMULÉES)

**Commande**
```bash
python skills/ltv-by-channel/run.py --horizon 180 --start 2025-01-01 --end 2026-01-01
```

**Ce que montre la sortie (cohortes 2025, horizon 180 jours)**

| Canal | CAC | LTV 180 j par payant | ROAS 180 j |
|---|---|---|---|
| Google Ads | 21,6 € | 72,9 € | 3,4 |
| Affiliation | 26,7 € | 65,5 € | 2,5 |
| Meta | 41,2 € | 70,9 € | 1,7 |
| TikTok | 48,3 € | 68,6 € | 1,4 |

**Réponse vérifiée**
> La LTV à 180 jours varie peu d'un canal à l'autre (66 à 77 € par abonné payant) ; c'est le **coût
> d'acquisition** qui fait la différence. TikTok a le coût par visite le plus bas, mais il convertit si peu
> que son CAC est le plus élevé (48 €) : le canal le moins cher à l'achat n'est pas le plus rentable.
> Google Ads rapporte 3,4 € par euro dépensé à 180 jours. Recommandation : plafonner le CAC de TikTok et de
> Meta prospection autour de 35 € et réallouer vers Google générique et l'affiliation, en surveillant les
> litiges de l'affiliation (2 fois la moyenne au premier renouvellement). Contrôles passés : 72 993 inscriptions
> observées 180 jours, LTV croissante avec l'horizon ; SEO et direct signalés (CAC média nul).
