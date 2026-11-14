-- =====================================================================================
-- 02_funnel_retention.sql : funnel visite -> 1er renouvellement, rétention, churn
-- =====================================================================================

-- name: funnel_product
-- Fenêtre : visites jusqu'au 2026-04-30, pour que chaque inscription ait eu le temps
-- d'atteindre son premier renouvellement (essai <= 7 jours + nouvelles tentatives).
WITH win AS (SELECT TIMESTAMP '2026-04-30 23:59:59' AS last_visit),
v AS (SELECT product, count(*) AS visits FROM sessions, win WHERE ts_utc <= last_visit GROUP BY 1),
c AS (
    SELECT product,
           count(*)                                                       AS signups,
           count(*) FILTER (WHERE trial_checkout)                         AS checkout,
           count(*) FILTER (WHERE trial_checkout AND status NOT IN ('echec_paiement_essai', 'echec_paiement_initial'))
                                                                          AS trial_started,
           count(*) FILTER (WHERE paid_cycles >= 1)                       AS first_paid,
           count(*) FILTER (WHERE paid_cycles >= 2)                       AS second_paid
    FROM customers, win WHERE signup_ts <= last_visit GROUP BY 1
)
SELECT product, visits, signups, checkout, trial_started, first_paid, second_paid,
       round(signups / visits, 4)          AS r_visit_signup,
       round(checkout / signups, 4)        AS r_signup_checkout,
       round(trial_started / checkout, 4)  AS r_checkout_trial,
       round(first_paid / trial_started, 4) AS r_trial_paid,
       round(second_paid / first_paid, 4)  AS r_paid_second
FROM v JOIN c USING (product)
ORDER BY product;

-- name: funnel_channel
WITH win AS (SELECT TIMESTAMP '2026-04-30 23:59:59' AS last_visit),
v AS (SELECT channel, count(*) AS visits FROM sessions, win WHERE ts_utc <= last_visit GROUP BY 1),
c AS (
    SELECT channel,
           count(*) AS signups,
           count(*) FILTER (WHERE trial_checkout) AS checkout,
           count(*) FILTER (WHERE trial_checkout AND status NOT IN ('echec_paiement_essai', 'echec_paiement_initial')) AS trial_started,
           count(*) FILTER (WHERE paid_cycles >= 1) AS first_paid
    FROM customers, win WHERE signup_ts <= last_visit GROUP BY 1
)
SELECT channel, visits, signups, checkout, trial_started, first_paid,
       round(signups / visits, 4) AS r_visit_signup,
       round(first_paid / visits, 5) AS r_visit_paid,
       round(first_paid / trial_started, 4) AS r_trial_paid
FROM v JOIN c USING (channel)
ORDER BY r_visit_paid DESC;

-- name: trial_outcomes
-- Que deviennent les essais ? (produits A et C : essai payant ; B : essai gratuit)
SELECT product,
       count(*) FILTER (WHERE trial_checkout)                                             AS checkout,
       count(*) FILTER (WHERE status = 'echec_paiement_essai')                            AS refus_paiement_essai,
       count(*) FILTER (WHERE status = 'essai_annule')                                    AS annule_pendant_essai,
       count(*) FILTER (WHERE paid_cycles = 0 AND status = 'annule_echec_paiement')       AS refus_au_1er_renouvellement,
       count(*) FILTER (WHERE paid_cycles >= 1)                                           AS converti
FROM customers
WHERE signup_ts <= TIMESTAMP '2026-04-30 23:59:59' AND trial_checkout
GROUP BY 1 ORDER BY 1;

-- name: retention_by_cycle
-- Rétention des abonnés payants par cycle facturé, cohortes trimestrielles.
-- Un cycle k n'est compté que si la cohorte a eu le temps de l'atteindre (anti-censure).
WITH p AS (SELECT obs_end FROM params),
pay AS (
    SELECT c.*, pr.trial_days, pr.cycle_days, date_trunc('quarter', c.signup_ts) AS cohort_q
    FROM customers c JOIN products pr USING (product)
    WHERE c.paid_cycles >= 1 AND c.plan = 'essai_puis_mensuel'
),
k AS (SELECT range AS k FROM range(1, 13))
SELECT strftime(cohort_q, '%Y-T') || quarter(cohort_q) AS cohort, product, k.k AS cycle,
       count(*) AS eligible,
       round(avg((paid_cycles >= k.k)::INT), 4) AS retention
FROM pay, k, p
WHERE pay.signup_ts + to_days(pay.trial_days + (k.k - 1) * pay.cycle_days + 21) <= p.obs_end
GROUP BY ALL
HAVING count(*) >= 50
ORDER BY product, cohort, cycle;

-- name: churn_split
-- Churn volontaire (le client annule) contre involontaire (le paiement échoue après les
-- nouvelles tentatives), chez les abonnés payants dont l'abonnement est terminé.
SELECT product,
       count(*) FILTER (WHERE status = 'annule' AND cancel_reason <> 'fraude_detectee') AS volontaire,
       count(*) FILTER (WHERE status = 'annule_echec_paiement')                         AS involontaire,
       count(*) FILTER (WHERE status = 'impaye_en_cours')                               AS impaye_en_cours,
       round(count(*) FILTER (WHERE status = 'annule_echec_paiement')
             / count(*) FILTER (WHERE status IN ('annule', 'annule_echec_paiement')), 4) AS part_involontaire
FROM customers
WHERE paid_cycles >= 1
GROUP BY 1 ORDER BY 1;

-- name: cancel_reasons
SELECT product, cancel_reason, count(*) AS n
FROM customers
WHERE status = 'annule' AND paid_cycles >= 1
GROUP BY 1, 2 ORDER BY 1, 3 DESC;

-- name: churn_by_tenure
-- Part du churn involontaire selon l'ancienneté de l'abonné au moment du départ.
SELECT product,
       CASE WHEN paid_cycles = 1 THEN '1 cycle' WHEN paid_cycles <= 3 THEN '2-3 cycles' ELSE '4 cycles et +' END AS tenure,
       count(*) FILTER (WHERE status = 'annule' AND cancel_reason <> 'fraude_detectee') AS voluntary,
       count(*) FILTER (WHERE status = 'annule_echec_paiement') AS involuntary,
       round(count(*) FILTER (WHERE status = 'annule_echec_paiement')
             / count(*) FILTER (WHERE status IN ('annule', 'annule_echec_paiement')), 4) AS share_involuntary
FROM customers WHERE paid_cycles >= 1
GROUP BY 1, 2 ORDER BY 1, 2;
