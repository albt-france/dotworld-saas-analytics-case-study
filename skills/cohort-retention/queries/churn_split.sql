-- Churn volontaire (annulation) contre involontaire (paiement refusé après toutes les
-- nouvelles tentatives), par produit et par rang du cycle où l'abonné est parti.
-- Paramètres : {{start}}, {{end}}, {{products}}
SELECT product,
       CASE WHEN paid_cycles = 1 THEN '1 cycle payé' WHEN paid_cycles <= 3 THEN '2-3 cycles' ELSE '4 cycles et +' END AS tenure,
       count(*) FILTER (WHERE status = 'annule' AND cancel_reason <> 'fraude_detectee') AS voluntary,
       count(*) FILTER (WHERE status = 'annule_echec_paiement')                         AS involuntary,
       round(count(*) FILTER (WHERE status = 'annule_echec_paiement')
             / nullif(count(*) FILTER (WHERE status IN ('annule', 'annule_echec_paiement')), 0), 4) AS share_involuntary
FROM customers
WHERE paid_cycles >= 1 AND signup_ts >= {{start}} AND signup_ts < {{end}} AND product IN {{products}}
GROUP BY 1, 2
ORDER BY 1, 2;
