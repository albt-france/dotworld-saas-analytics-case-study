-- =====================================================================================
-- 00_views.sql : vues de base sur le parcours SIMULÉ (fichiers parquet, DuckDB)
-- Lancer depuis la racine du dépôt :  duckdb -c ".read sql/00_views.sql"
-- =====================================================================================

CREATE OR REPLACE VIEW sessions          AS SELECT * FROM read_parquet('data/simulated/sessions.parquet');
CREATE OR REPLACE VIEW signups           AS SELECT * FROM read_parquet('data/simulated/signups.parquet');
CREATE OR REPLACE VIEW subscriptions     AS SELECT * FROM read_parquet('data/simulated/subscriptions.parquet');
CREATE OR REPLACE VIEW payment_attempts  AS SELECT * FROM read_parquet('data/simulated/payment_attempts.parquet');
CREATE OR REPLACE VIEW refunds           AS SELECT * FROM read_parquet('data/simulated/refunds.parquet');
CREATE OR REPLACE VIEW disputes          AS SELECT * FROM read_parquet('data/simulated/disputes.parquet');
CREATE OR REPLACE VIEW fraud_reports     AS SELECT * FROM read_parquet('data/simulated/fraud_reports.parquet');
CREATE OR REPLACE VIEW fraud_signals     AS SELECT * FROM read_parquet('data/simulated/fraud_signals.parquet');
CREATE OR REPLACE VIEW marketing_spend   AS SELECT * FROM read_parquet('data/simulated/marketing_spend.parquet');
CREATE OR REPLACE VIEW experiments       AS SELECT * FROM read_parquet('data/simulated/experiments.parquet');
CREATE OR REPLACE VIEW internal_payments AS SELECT * FROM read_parquet('data/simulated/internal_payments.parquet');
CREATE OR REPLACE VIEW psp_settlements   AS SELECT * FROM read_parquet('data/simulated/psp_settlements.parquet');
CREATE OR REPLACE VIEW fx_rates          AS SELECT CAST(date AS DATE) AS date, usd_to_eur
                                            FROM read_parquet('data/simulated/fx_rates.parquet');

-- Paramètres partagés : date d'observation (tout ce qui suit est inconnu) et frais de litige
CREATE OR REPLACE VIEW params AS
SELECT TIMESTAMP '2026-06-30 23:59:59' AS obs_end, 15.0 AS dispute_fee_eur;

-- Catalogue des produits fictifs (durée d'essai et de cycle, pour savoir quand un cycle est observable)
CREATE OR REPLACE VIEW products AS
SELECT * FROM (VALUES ('A', 7, 28), ('B', 7, 30), ('C', 3, 30)) t(product, trial_days, cycle_days);

-- Une ligne par inscription, avec son abonnement éventuel.
-- « Abonné payant » = au moins un paiement plein tarif (paid_cycles >= 1).
CREATE OR REPLACE VIEW customers AS
SELECT g.signup_id, g.signup_ts, g.product, g.channel, g.campaign, g.country, g.device, g.variant,
       g.trial_checkout, s.subscription_id, s.plan, s.status, s.cancel_reason,
       coalesce(s.paid_cycles, 0) AS paid_cycles, s.first_payment_at, s.ended_at,
       date_trunc('month', g.signup_ts) AS cohort_month
FROM signups g
LEFT JOIN subscriptions s USING (signup_id);

-- Revenu net en EUR, événement par événement (taux de change du jour) :
--   + paiements acceptés, - remboursements, - litiges perdus ou acceptés, - frais de litige.
CREATE OR REPLACE VIEW revenue_events AS
SELECT a.signup_id, a.product, a.ts_utc AS event_ts, 'charge' AS event_type,
       a.amount * CASE WHEN a.currency = 'USD' THEN fx.usd_to_eur ELSE 1 END AS amount_eur
FROM payment_attempts a
JOIN fx_rates fx ON fx.date = CAST(a.ts_utc AS DATE)
WHERE a.outcome = 'approved'
UNION ALL
SELECT r.signup_id, a.product, r.refunded_at, 'refund',
       -r.amount * CASE WHEN r.currency = 'USD' THEN fx.usd_to_eur ELSE 1 END
FROM refunds r
JOIN payment_attempts a USING (attempt_id)
JOIN fx_rates fx ON fx.date = CAST(r.refunded_at AS DATE)
UNION ALL
SELECT d.signup_id, d.product, d.created_at, 'dispute',
       -(CASE WHEN d.outcome = 'won' THEN 0 ELSE d.amount * CASE WHEN d.currency = 'USD' THEN fx.usd_to_eur ELSE 1 END END)
       - p.dispute_fee_eur
FROM disputes d
JOIN fx_rates fx ON fx.date = CAST(d.created_at AS DATE)
CROSS JOIN params p;
