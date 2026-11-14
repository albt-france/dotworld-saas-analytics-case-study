-- =====================================================================================
-- 01_acquisition_ltv.sql : CAC, LTV par canal et par cohorte, délai de rentabilisation
-- Règle anti-censure : une cohorte n'entre dans la LTV à J+h que si elle a été observée
-- pendant h jours entiers (signup_ts + h jours <= date d'observation).
-- =====================================================================================

-- name: channel_ltv_180
-- Cohortes d'inscription de 2025 (toutes observées 180 jours) ; dépenses de la même période.
WITH p AS (SELECT obs_end, 180 AS h FROM params),
mature AS (
    SELECT c.* FROM customers c, p
    WHERE c.signup_ts + to_days(p.h) <= p.obs_end
),
rev AS (
    SELECT m.channel, sum(e.amount_eur) AS revenue_h
    FROM mature m
    JOIN revenue_events e USING (signup_id), p
    WHERE e.event_ts < m.signup_ts + to_days(p.h)
    GROUP BY 1
),
spend AS (
    SELECT channel, sum(spend_eur) AS spend
    FROM marketing_spend, p
    WHERE date < p.obs_end - to_days(p.h)
    GROUP BY 1
),
base AS (
    SELECT channel,
           count(*)                              AS signups,
           count(*) FILTER (WHERE paid_cycles >= 1) AS payers
    FROM mature GROUP BY 1
)
SELECT b.channel, b.signups, b.payers,
       round(b.payers / b.signups, 4)                         AS signup_to_payer,
       round(coalesce(s.spend, 0), 0)                         AS spend_eur,
       round(coalesce(s.spend, 0) / b.payers, 2)              AS cac_eur,
       round(r.revenue_h / b.payers, 2)                       AS ltv180_per_payer,
       round(r.revenue_h / nullif(s.spend, 0), 2)             AS roas_180
FROM base b
LEFT JOIN spend s USING (channel)
LEFT JOIN rev r USING (channel)
ORDER BY spend_eur DESC;

-- name: ltv_curve
-- LTV cumulée par abonné payant, à chaque âge d (0 à 365 jours), sur les seules cohortes
-- observées au moins d jours. Sert à la courbe et au délai de rentabilisation.
WITH p AS (SELECT obs_end FROM params),
grid AS (SELECT range AS d FROM range(0, 366, 5)),
payers AS (
    SELECT signup_id, channel, signup_ts FROM customers WHERE paid_cycles >= 1
),
ev AS (
    SELECT y.channel, y.signup_ts, date_diff('day', y.signup_ts, e.event_ts) AS age, e.amount_eur
    FROM payers y JOIN revenue_events e USING (signup_id)
),
num AS (
    SELECT g.d, ev.channel, sum(ev.amount_eur) AS rev
    FROM grid g, ev, p
    WHERE ev.age <= g.d AND ev.signup_ts + to_days(g.d) <= p.obs_end
    GROUP BY 1, 2
),
den AS (
    SELECT g.d, y.channel, count(*) AS n
    FROM grid g, payers y, p
    WHERE y.signup_ts + to_days(g.d) <= p.obs_end
    GROUP BY 1, 2
)
SELECT den.d AS day, den.channel, den.n AS payers_observed, round(num.rev / den.n, 2) AS ltv_per_payer
FROM den LEFT JOIN num USING (d, channel)
ORDER BY channel, day;

-- name: ltv_by_cohort
-- LTV à 90 jours par mois de cohorte et par canal (cohortes observées 90 jours).
WITH p AS (SELECT obs_end, 90 AS h FROM params),
m AS (SELECT * FROM customers, p WHERE signup_ts + to_days(p.h) <= p.obs_end AND paid_cycles >= 1),
r AS (
    SELECT m.cohort_month, m.channel, sum(e.amount_eur) AS rev
    FROM m JOIN revenue_events e USING (signup_id), p
    WHERE e.event_ts < m.signup_ts + to_days(p.h)
    GROUP BY 1, 2
)
SELECT strftime(m.cohort_month, '%Y-%m') AS cohort, m.channel, count(*) AS payers,
       round(any_value(r.rev) / count(*), 2) AS ltv90_per_payer
FROM m LEFT JOIN r USING (cohort_month, channel)
GROUP BY m.cohort_month, m.channel
ORDER BY cohort, channel;

-- name: campaign_ltv_90
-- Comparaison par campagne à 90 jours (permet d'inclure la campagne agressive de 2026),
-- avec le taux de litiges observé à 90 jours.
WITH p AS (SELECT obs_end, 90 AS h FROM params),
m AS (SELECT * FROM customers, p WHERE signup_ts + to_days(p.h) <= p.obs_end),
rev AS (
    SELECT m.campaign, sum(e.amount_eur) AS rev, count(*) FILTER (WHERE e.event_type = 'dispute') AS disputes
    FROM m JOIN revenue_events e USING (signup_id), p
    WHERE e.event_ts < m.signup_ts + to_days(p.h)
    GROUP BY 1
),
sp AS (
    SELECT campaign, sum(spend_eur) AS spend FROM marketing_spend, p
    WHERE date < p.obs_end - to_days(p.h) GROUP BY 1
)
SELECT m.channel, m.campaign, count(*) AS signups,
       count(*) FILTER (WHERE paid_cycles >= 1) AS payers,
       round(coalesce(any_value(sp.spend), 0) / count(*) FILTER (WHERE paid_cycles >= 1), 2) AS cac_eur,
       round(any_value(rev.rev) / count(*) FILTER (WHERE paid_cycles >= 1), 2) AS ltv90_per_payer,
       round(1000.0 * any_value(rev.disputes) / count(*) FILTER (WHERE paid_cycles >= 1), 1) AS disputes_per_1000_payers
FROM m
LEFT JOIN rev USING (campaign)
LEFT JOIN sp USING (campaign)
GROUP BY 1, 2
ORDER BY cac_eur DESC NULLS LAST, campaign;

-- name: segments_ltv_180
-- Segments canal x produit x zone : où la croissance est-elle rentable ? (cohortes 2025)
WITH p AS (SELECT obs_end, 180 AS h FROM params),
zone AS (SELECT * FROM (VALUES ('US','US'),('BR','LATAM'),('MX','LATAM')) t(country, zone)),
m AS (
    SELECT c.*, coalesce(z.zone, 'Europe') AS zone
    FROM customers c LEFT JOIN zone z USING (country), p
    WHERE c.signup_ts + to_days(p.h) <= p.obs_end
),
rev AS (
    SELECT m.channel, m.product, m.zone, sum(e.amount_eur) AS rev
    FROM m JOIN revenue_events e USING (signup_id), p
    WHERE e.event_ts < m.signup_ts + to_days(p.h)
    GROUP BY 1, 2, 3
),
sp AS (
    SELECT s.channel, s.product, coalesce(z.zone, 'Europe') AS zone, sum(s.spend_eur) AS spend
    FROM marketing_spend s LEFT JOIN zone z USING (country), p
    WHERE s.date < p.obs_end - to_days(p.h)
    GROUP BY 1, 2, 3
)
SELECT m.channel, m.product, m.zone,
       count(*) FILTER (WHERE paid_cycles >= 1) AS payers,
       round(coalesce(any_value(sp.spend), 0), 0) AS spend_eur,
       round(any_value(rev.rev) - coalesce(any_value(sp.spend), 0), 0) AS contribution_180_eur,
       round(any_value(rev.rev) / nullif(any_value(sp.spend), 0), 2) AS roas_180
FROM m
LEFT JOIN rev USING (channel, product, zone)
LEFT JOIN sp USING (channel, product, zone)
WHERE m.channel IN ('Google Ads', 'Meta', 'TikTok', 'Affiliation')
GROUP BY 1, 2, 3
HAVING count(*) FILTER (WHERE paid_cycles >= 1) >= 30
ORDER BY contribution_180_eur DESC;

-- name: channel_unit_costs
-- Coût par visite contre coût par abonné payant (cohortes 2025) : le moins cher à l'achat
-- n'est pas forcément le moins cher par client.
WITH p AS (SELECT obs_end, 180 AS h FROM params),
v AS (
    SELECT channel, sum(spend_eur) AS spend, sum(sessions) AS paid_sessions
    FROM marketing_spend, p WHERE date < p.obs_end - to_days(p.h) AND sessions > 0 GROUP BY 1
),
y AS (
    SELECT channel, count(*) FILTER (WHERE paid_cycles >= 1) AS payers
    FROM customers, p WHERE signup_ts + to_days(p.h) <= p.obs_end GROUP BY 1
)
SELECT v.channel, round(v.spend / v.paid_sessions, 3) AS cost_per_visit,
       round(v.spend / y.payers, 2) AS media_cost_per_payer
FROM v JOIN y USING (channel)
ORDER BY cost_per_visit;
