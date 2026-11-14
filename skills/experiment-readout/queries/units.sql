-- Une ligne par utilisateur affecté au test, avec ses résultats sur une fenêtre fixe
-- de {{window}} jours après l'affectation (même durée pour tout le monde).
-- Paramètres : {{experiment_id}}, {{window}}
WITH e AS (SELECT * FROM experiments WHERE experiment_id = {{experiment_id}}),
rev AS (
    SELECT e.signup_id,
           sum(r.amount_eur) AS revenue,
           count(*) FILTER (WHERE r.event_type = 'dispute') AS disputes,
           count(*) FILTER (WHERE r.event_type = 'refund')  AS refunds
    FROM e JOIN revenue_events r USING (signup_id)
    WHERE r.event_ts < e.assigned_at + to_days({{window}})
    GROUP BY 1
)
SELECT e.signup_id, e.variant, e.assigned_at, c.country, c.device, c.channel, c.campaign,
       c.trial_checkout::INT        AS trial_checkout,
       (c.paid_cycles >= 1)::INT    AS paid_first_renewal,
       coalesce(rev.revenue, 0)     AS revenue,
       coalesce(rev.disputes, 0)    AS disputes,
       coalesce(rev.refunds, 0)     AS refunds
FROM e
JOIN customers c USING (signup_id)
LEFT JOIN rev USING (signup_id)
ORDER BY e.signup_id;
