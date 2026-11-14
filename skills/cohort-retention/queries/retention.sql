-- Rétention des abonnés payants par cohorte et par cycle facturé (formule mensuelle).
-- Anti-censure : le cycle k d'une cohorte n'est compté que si TOUS ses membres ont eu le temps
-- de l'atteindre (essai + (k-1) cycles + 21 jours de nouvelles tentatives <= date d'observation).
-- Paramètres : {{start}}, {{end}} (bornes des inscriptions), {{products}}, {{max_cycle}}
WITH p AS (SELECT obs_end FROM params),
pay AS (
    SELECT c.signup_id, c.product, c.paid_cycles, c.signup_ts,
           date_trunc('__GRAIN__', c.signup_ts) AS cohort
    FROM customers c
    WHERE c.paid_cycles >= 1 AND c.plan = 'essai_puis_mensuel'
      AND c.signup_ts >= {{start}} AND c.signup_ts < {{end}} AND c.product IN {{products}}
),
-- dernière inscription de chaque cohorte : c'est elle qui fixe la maturité de la cohorte
coh AS (
    SELECT pay.cohort, pay.product, max(pay.signup_ts) AS last_signup, count(*) AS cohort_size,
           any_value(pr.trial_days) AS trial_days, any_value(pr.cycle_days) AS cycle_days
    FROM pay JOIN products pr USING (product)
    GROUP BY 1, 2
),
k AS (SELECT range AS k FROM range(1, {{max_cycle}} + 1)),
eligible AS (
    SELECT coh.*, k.k
    FROM coh CROSS JOIN k CROSS JOIN p
    WHERE coh.last_signup + to_days(coh.trial_days + (k.k - 1) * coh.cycle_days + 21) <= p.obs_end
)
SELECT strftime(e.cohort, '%Y-%m') AS cohort, e.product, e.k AS cycle, e.cohort_size,
       sum((pay.paid_cycles >= e.k)::INT) AS still_paying,
       round(avg((pay.paid_cycles >= e.k)::INT), 4) AS retention
FROM eligible e
JOIN pay USING (cohort, product)
GROUP BY ALL
ORDER BY e.product, cohort, cycle;
