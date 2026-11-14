-- =====================================================================================
-- 05_reconciliation_experiment.sql : réconciliation du revenu (PSP contre base interne)
-- et données de l'expérimentation sur le parcours d'essai.
-- =====================================================================================

-- name: reconciliation_monthly
-- Revenu brut mensuel selon les deux sources, chacune lue « telle quelle ».
WITH i AS (
    SELECT date_trunc('month', ts_utc) AS month, sum(amount_eur) AS internal_eur
    FROM internal_payments GROUP BY 1
),
p AS (
    SELECT date_trunc('month', reported_at) AS month,
           sum(gross_eur) AS psp_gross_eur, sum(net_eur) AS psp_net_eur, sum(fee_eur) AS psp_fees_eur
    FROM psp_settlements GROUP BY 1
)
SELECT month, round(internal_eur, 0) AS internal_eur, round(psp_gross_eur, 0) AS psp_gross_eur,
       round(psp_net_eur, 0) AS psp_net_eur, round(psp_gross_eur - internal_eur, 0) AS gap_gross_eur,
       round((psp_gross_eur - internal_eur) / internal_eur, 4) AS gap_pct
FROM i FULL JOIN p USING (month)
WHERE month <= DATE '2026-06-01'
ORDER BY month;

-- name: reconciliation_bridge
-- Pont de réconciliation sur toute la période : on explique l'écart cause par cause,
-- en rapprochant les deux sources ligne à ligne sur attempt_id.
WITH ic AS (SELECT attempt_id, count(*) AS n, sum(amount_eur) AS eur, min(ts_utc) AS ts
            FROM internal_payments WHERE record_type = 'charge' GROUP BY 1),
pc AS (SELECT attempt_id, gross_eur, reported_at, report_timezone
       FROM psp_settlements WHERE type = 'charge')
SELECT
  -- 1) paiements présents chez le PSP mais absents de la base interne (webhooks perdus)
  round(sum(CASE WHEN ic.attempt_id IS NULL THEN pc.gross_eur ELSE 0 END), 0)                    AS missing_in_internal_eur,
  count(*) FILTER (WHERE ic.attempt_id IS NULL)                                                 AS missing_in_internal_n,
  -- 2) doublons dans la base interne (webhooks rejoués)
  round(sum(CASE WHEN ic.n > 1 THEN ic.eur * (ic.n - 1) / ic.n ELSE 0 END), 0)                  AS duplicates_internal_eur,
  count(*) FILTER (WHERE ic.n > 1)                                                              AS duplicates_internal_n,
  -- 3) change : taux moyen du mois (interne) contre taux du jour (PSP), hors doublons
  round(sum(CASE WHEN ic.attempt_id IS NOT NULL THEN pc.gross_eur - ic.eur / ic.n ELSE 0 END), 0) AS fx_difference_eur,
  -- 4) décalage de mois dû au fuseau horaire du rapport PSP (heure de Zurich contre UTC)
  count(*) FILTER (WHERE ic.attempt_id IS NOT NULL
                     AND date_trunc('month', pc.reported_at) <> date_trunc('month', ic.ts))      AS month_shift_n,
  round(sum(CASE WHEN ic.attempt_id IS NOT NULL
                   AND date_trunc('month', pc.reported_at) <> date_trunc('month', ic.ts)
                 THEN pc.gross_eur ELSE 0 END), 0)                                               AS month_shift_eur
FROM pc FULL JOIN ic USING (attempt_id);

-- name: reconciliation_psp_only_items
-- Lignes qui n'existent que chez le PSP : litiges débités et frais.
SELECT type, count(*) AS n, round(sum(gross_eur), 0) AS gross_eur, round(sum(fee_eur), 0) AS fee_eur
FROM psp_settlements GROUP BY 1 ORDER BY 1;

-- name: experiment_users
-- Une ligne par utilisateur affecté : ses résultats à 60 jours.
WITH e AS (SELECT * FROM experiments WHERE experiment_id = 'EXP-A-PRIX-TRANSPARENT'),
rev AS (
    SELECT e.signup_id, sum(r.amount_eur) AS revenue_60d,
           count(*) FILTER (WHERE r.event_type = 'dispute') AS disputes_60d
    FROM e JOIN revenue_events r USING (signup_id)
    WHERE r.event_ts < e.assigned_at + INTERVAL 60 DAY
    GROUP BY 1
)
SELECT e.signup_id, e.variant, c.country, c.device, c.channel,
       c.trial_checkout::INT AS trial_checkout,
       (c.paid_cycles >= 1)::INT AS paid_first_renewal,
       coalesce(rev.revenue_60d, 0) AS revenue_60d,
       coalesce(rev.disputes_60d, 0) AS disputes_60d
FROM e JOIN customers c USING (signup_id) LEFT JOIN rev USING (signup_id)
ORDER BY e.signup_id;
