-- =====================================================================================
-- 03_payments.sql : acceptation, refus et nouvelles tentatives par PSP, pays et produit
-- Règle (documentation Stripe) : le taux d'acceptation se calcule sur les tentatives
-- INITIALES ; les nouvelles tentatives se mesurent à part (taux de récupération).
-- =====================================================================================

-- name: acceptance_psp_country
SELECT psp, card_country,
       count(*)                                         AS first_attempts,
       round(avg((outcome = 'approved')::INT), 4)       AS acceptance_rate
FROM payment_attempts
WHERE attempt_no = 1
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: acceptance_psp_product
SELECT psp, product, initiator,
       count(*) AS first_attempts,
       round(avg((outcome = 'approved')::INT), 4) AS acceptance_rate
FROM payment_attempts
WHERE attempt_no = 1
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- name: payment_success_after_retries
-- Une « charge » (payment_id) réussit si l'une de ses tentatives est acceptée.
WITH pay AS (
    SELECT payment_id, any_value(psp) AS psp, any_value(payment_kind) AS kind,
           bool_or(outcome = 'approved') AS ok,
           bool_or(outcome = 'approved' AND attempt_no = 1) AS ok_first
    FROM payment_attempts GROUP BY 1
)
SELECT psp, kind, count(*) AS payments,
       round(avg(ok_first::INT), 4) AS acceptance_first_attempt,
       round(avg(ok::INT), 4)       AS success_after_retries,
       round(avg(ok::INT) - avg(ok_first::INT), 4) AS uplift_from_retries
FROM pay GROUP BY 1, 2 ORDER BY 1, 2;

-- name: decline_codes
SELECT decline_type, decline_code, count(*) AS n,
       round(count(*) / sum(count(*)) OVER (), 4) AS share
FROM payment_attempts
WHERE attempt_no = 1 AND outcome = 'declined'
GROUP BY 1, 2 ORDER BY n DESC;

-- name: retry_by_delay
-- Efficacité des nouvelles tentatives du marchand (MIT) sur refus « soft », selon le délai.
SELECT retry_delay_days AS delay_days,
       count(*) AS retries,
       round(avg((outcome = 'approved')::INT), 4) AS success_rate
FROM payment_attempts
WHERE attempt_no >= 2 AND initiator = 'MIT' AND decline_type IS DISTINCT FROM 'hard'
  AND payment_id IN (SELECT payment_id FROM payment_attempts
                     WHERE attempt_no = 1 AND decline_type = 'soft')
GROUP BY 1 ORDER BY 1;

-- name: retry_by_number
SELECT attempt_no, count(*) AS retries,
       round(avg((outcome = 'approved')::INT), 4) AS success_rate
FROM payment_attempts
WHERE attempt_no >= 2 AND initiator = 'MIT'
  AND payment_id IN (SELECT payment_id FROM payment_attempts WHERE attempt_no = 1 AND decline_type = 'soft')
GROUP BY 1 ORDER BY 1;

-- name: retry_by_code_delay
-- Pour quel code le délai compte-t-il ? (fonction de fenêtre : code du refus initial)
WITH a AS (
    SELECT *, first_value(decline_code) OVER (PARTITION BY payment_id ORDER BY attempt_no) AS first_code
    FROM payment_attempts
)
SELECT first_code, retry_delay_days AS delay_days, count(*) AS retries,
       round(avg((outcome = 'approved')::INT), 4) AS success_rate
FROM a
WHERE attempt_no >= 2 AND initiator = 'MIT' AND first_code IN ('insufficient_funds', 'do_not_honor')
GROUP BY 1, 2 ORDER BY 1, 2;

-- name: hard_decline_retries
-- Nouvelles tentatives après un refus définitif : contraire aux règles des réseaux, à arrêter.
WITH a AS (
    SELECT *, lag(decline_type) OVER (PARTITION BY payment_id ORDER BY attempt_no) AS prev_type
    FROM payment_attempts
)
SELECT psp, count(*) AS retries_after_hard_decline,
       round(avg((outcome = 'approved')::INT), 4) AS success_rate
FROM a WHERE attempt_no >= 2 AND prev_type = 'hard'
GROUP BY 1 ORDER BY 1;

-- name: routing_whatif_inputs
-- Le trafic est réparti à ~85/15 entre les PSP : dans chaque pays on observe donc les deux.
-- Acceptation des tentatives initiales par PSP et pays, avec le montant moyen en EUR.
SELECT a.card_country, a.psp,
       count(*) AS first_attempts,
       sum((a.outcome = 'approved')::INT) AS approved,
       round(avg(a.amount * CASE WHEN a.currency = 'USD' THEN fx.usd_to_eur ELSE 1 END), 2) AS avg_amount_eur
FROM payment_attempts a JOIN fx_rates fx ON fx.date = CAST(a.ts_utc AS DATE)
WHERE a.attempt_no = 1
GROUP BY 1, 2 ORDER BY 1, 2;

-- name: acceptance_weekly_es
-- « Pourquoi l'acceptation baisse-t-elle en Espagne ? » : par semaine, PSP et code de refus.
SELECT date_trunc('week', ts_utc) AS week, psp,
       count(*) AS first_attempts,
       round(avg((outcome = 'approved')::INT), 4) AS acceptance_rate,
       round(avg((decline_code = 'do_not_honor')::INT), 4) AS do_not_honor_rate
FROM payment_attempts
WHERE attempt_no = 1 AND card_country = 'ES' AND ts_utc >= TIMESTAMP '2025-10-01'
GROUP BY 1, 2 ORDER BY 1, 2;

-- name: acceptance_monthly
SELECT date_trunc('month', ts_utc) AS month, psp,
       count(*) AS first_attempts,
       round(avg((outcome = 'approved')::INT), 4) AS acceptance_rate
FROM payment_attempts WHERE attempt_no = 1
GROUP BY 1, 2 ORDER BY 1, 2;
