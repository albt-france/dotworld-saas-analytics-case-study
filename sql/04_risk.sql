-- =====================================================================================
-- 04_risk.sql : litiges contre seuils publics, effet décalé d'une campagne, fraude
-- Seuils (data/public/payment_references.csv) :
--   Visa VAMP « Excessive » marchand : 1,5 % depuis le 2026-04-01 (2,2 % avant)
--   Mastercard ECM : 1,5 % (et au moins 100 chargebacks par mois)
-- NB : à l'échelle de l'échantillon simulé, les minimums de volume ne sont pas atteints ;
-- on lit le ratio comme un signal d'alerte.
-- =====================================================================================

-- name: vamp_ratio_by_mid
-- Ratio de type VAMP : (litiges + signalements de fraude TC40) du mois / transactions réglées du mois.
WITH st AS (
    SELECT mid, date_trunc('month', ts_utc) AS month, count(*) FILTER (WHERE card_brand = 'visa') AS settled_visa,
           count(*) AS settled
    FROM payment_attempts WHERE outcome = 'approved' GROUP BY 1, 2
),
d AS (SELECT mid, date_trunc('month', created_at) AS month, count(*) FILTER (WHERE card_brand = 'visa') AS disp_visa
      FROM disputes GROUP BY 1, 2),
f AS (SELECT mid, date_trunc('month', reported_at) AS month, count(*) FILTER (WHERE card_brand = 'visa') AS tc40_visa
      FROM fraud_reports GROUP BY 1, 2)
SELECT st.month, st.mid, st.settled_visa,
       coalesce(d.disp_visa, 0) AS disputes_visa, coalesce(f.tc40_visa, 0) AS tc40_visa,
       round((coalesce(d.disp_visa, 0) + coalesce(f.tc40_visa, 0)) / nullif(st.settled_visa, 0), 4) AS vamp_ratio,
       CASE WHEN st.month >= DATE '2026-04-01' THEN 0.015 ELSE 0.022 END AS visa_threshold
FROM st LEFT JOIN d USING (mid, month) LEFT JOIN f USING (mid, month)
WHERE st.month <= DATE '2026-06-01'
ORDER BY st.mid, st.month;

-- name: mastercard_ratio_by_mid
-- Ratio Mastercard : chargebacks du mois / transactions du mois PRÉCÉDENT (fonction de fenêtre LAG).
WITH st AS (
    SELECT mid, date_trunc('month', ts_utc) AS month, count(*) AS settled_mc
    FROM payment_attempts WHERE outcome = 'approved' AND card_brand = 'mastercard' GROUP BY 1, 2
),
d AS (SELECT mid, date_trunc('month', created_at) AS month, count(*) AS cb
      FROM disputes WHERE card_brand = 'mastercard' GROUP BY 1, 2),
j AS (
    SELECT st.mid, st.month, coalesce(d.cb, 0) AS chargebacks,
           lag(st.settled_mc) OVER (PARTITION BY st.mid ORDER BY st.month) AS settled_prev_month
    FROM st LEFT JOIN d USING (mid, month)
)
SELECT *, round(chargebacks / nullif(settled_prev_month, 0), 4) AS mc_ratio, 0.015 AS mc_threshold
FROM j WHERE settled_prev_month IS NOT NULL AND month <= DATE '2026-06-01'
ORDER BY mid, month;

-- name: portfolio_dispute_monthly
SELECT date_trunc('month', d.created_at) AS month,
       count(*) AS disputes,
       count(*) FILTER (WHERE d.reason = 'fraudulent') AS disputes_fraud,
       count(*) FILTER (WHERE d.reason IN ('unrecognized', 'subscription_canceled')) AS disputes_subscription
FROM disputes d GROUP BY 1 ORDER BY 1;

-- name: disputes_by_campaign_first_renewal
-- Taux de litige au premier renouvellement selon la campagne d'acquisition.
WITH fr AS (
    SELECT a.attempt_id, a.signup_id, c.campaign, a.ts_utc
    FROM payment_attempts a JOIN customers c USING (signup_id)
    WHERE a.payment_kind = 'first_renewal' AND a.outcome = 'approved'
      AND a.ts_utc <= TIMESTAMP '2026-05-15'          -- laisse ~45 jours pour qu'un litige arrive
)
SELECT fr.campaign, count(*) AS first_renewals,
       count(d.dispute_id) AS disputes,
       round(1000.0 * count(d.dispute_id) / count(*), 1) AS disputes_per_1000,
       round(median(date_diff('day', fr.ts_utc, d.created_at)), 0) AS median_lag_days
FROM fr LEFT JOIN disputes d USING (attempt_id)
GROUP BY 1 HAVING count(*) >= 200 ORDER BY disputes_per_1000 DESC;

-- name: disputes_weekly_promo
-- L'effet décalé : litiges par semaine, selon que le client vient de la campagne agressive ou non.
SELECT date_trunc('week', d.created_at) AS week,
       count(*) FILTER (WHERE c.campaign = 'meta_promo_choc') AS disputes_promo,
       count(*) FILTER (WHERE c.campaign <> 'meta_promo_choc') AS disputes_other
FROM disputes d JOIN customers c USING (signup_id)
WHERE d.created_at >= TIMESTAMP '2025-12-01'
GROUP BY 1 ORDER BY 1;

-- name: card_testing_bursts
-- Rafales : beaucoup de paiements d'essai sur le même BIN en moins d'une heure.
SELECT CAST(ts_utc AS DATE) AS day, product, bin, max(velocity_1h_same_bin) AS max_velocity, count(*) AS attempts
FROM fraud_signals
WHERE velocity_1h_same_bin >= 20
GROUP BY 1, 2, 3 ORDER BY 1;

-- name: fraud_rule_backtest
-- Test a posteriori de règles simples de blocage au paiement de l'essai.
-- « Fraude confirmée » = litige pour fraude ou signalement TC40 (ce que l'on sait après coup).
WITH lab AS (
    SELECT DISTINCT signup_id FROM disputes WHERE reason = 'fraudulent'
    UNION SELECT DISTINCT signup_id FROM fraud_reports
),
s AS (
    SELECT f.*, (l.signup_id IS NOT NULL) AS confirmed_fraud,
           -- faux positif observable : client bloqué qui a ensuite payé un cycle sans fraude signalée
           (c.paid_cycles >= 1 AND l.signup_id IS NULL) AS clean_payer
    FROM fraud_signals f LEFT JOIN lab l USING (signup_id) JOIN customers c USING (signup_id)
),
rules AS (
    SELECT 'vélocité BIN >= 5 en 1 h' AS rule, confirmed_fraud, clean_payer, (velocity_1h_same_bin >= 5) AS hit FROM s
    UNION ALL SELECT 'score >= 0.5', confirmed_fraud, clean_payer, (risk_score >= 0.5) FROM s
    UNION ALL SELECT 'score >= 0.7', confirmed_fraud, clean_payer, (risk_score >= 0.7) FROM s
    UNION ALL SELECT 'vélocité >= 5 OU (pays IP <> pays carte ET e-mail jetable)', confirmed_fraud, clean_payer,
                     (velocity_1h_same_bin >= 5 OR (ip_card_country_mismatch AND disposable_email)) FROM s
)
SELECT rule,
       count(*) AS checkouts,
       count(*) FILTER (WHERE confirmed_fraud) AS confirmed_fraud,
       count(*) FILTER (WHERE hit) AS blocked,
       count(*) FILTER (WHERE hit AND confirmed_fraud) AS fraud_caught,
       count(*) FILTER (WHERE hit AND clean_payer) AS clean_payers_blocked,
       round(count(*) FILTER (WHERE hit AND confirmed_fraud) / count(*) FILTER (WHERE confirmed_fraud), 4) AS recall,
       round(count(*) FILTER (WHERE hit AND confirmed_fraud) / nullif(count(*) FILTER (WHERE hit), 0), 4) AS precision
FROM rules GROUP BY 1 ORDER BY recall DESC;

-- name: fraud_by_trial_price
-- Les essais à petit prix attirent les tests de cartes : fraude confirmée par produit.
WITH lab AS (
    SELECT DISTINCT signup_id FROM disputes WHERE reason = 'fraudulent'
    UNION SELECT DISTINCT signup_id FROM fraud_reports
)
SELECT f.product, count(*) AS checkouts, count(l.signup_id) AS confirmed_fraud,
       round(1000.0 * count(l.signup_id) / count(*), 2) AS fraud_per_1000_checkouts,
       count(*) FILTER (WHERE f.velocity_1h_same_bin >= 20) AS burst_checkouts
FROM fraud_signals f LEFT JOIN lab l USING (signup_id)
GROUP BY 1 ORDER BY 1;
