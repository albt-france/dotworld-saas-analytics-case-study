-- CAC, LTV et ROAS par canal (ou campagne) à un horizon donné, sans biais de censure.
-- Seules les inscriptions observées pendant {{horizon}} jours entiers sont gardées, et les
-- dépenses sont prises sur la même fenêtre de dates.
-- Paramètres : {{start}}, {{end}} (inscriptions), {{horizon}} (jours), {{products}}
WITH p AS (SELECT obs_end, {{horizon}} AS h FROM params),
m AS (
    SELECT c.*, c.__DIM__ AS segment FROM customers c, p
    WHERE c.signup_ts >= {{start}} AND c.signup_ts < {{end}}
      AND c.signup_ts + to_days(p.h) <= p.obs_end
      AND c.product IN {{products}}
),
rev AS (
    SELECT m.segment, sum(e.amount_eur) AS revenue
    FROM m JOIN revenue_events e USING (signup_id), p
    WHERE e.event_ts < m.signup_ts + to_days(p.h)
    GROUP BY 1
),
win AS (SELECT min(signup_ts) AS d0, max(signup_ts) AS d1 FROM m),
sp AS (
    SELECT s.__DIM__ AS segment, sum(s.spend_eur) AS spend
    FROM marketing_spend s, win
    WHERE s.date >= CAST(win.d0 AS DATE) AND s.date <= CAST(win.d1 AS DATE) AND s.product IN {{products}}
    GROUP BY 1
)
SELECT m.segment,
       count(*) AS signups,
       count(*) FILTER (WHERE m.paid_cycles >= 1) AS payers,
       round(coalesce(any_value(sp.spend), 0), 0) AS spend_eur,
       round(coalesce(any_value(sp.spend), 0) / nullif(count(*) FILTER (WHERE m.paid_cycles >= 1), 0), 2) AS cac_eur,
       round(any_value(rev.revenue) / nullif(count(*) FILTER (WHERE m.paid_cycles >= 1), 0), 2) AS ltv_per_payer,
       round(any_value(rev.revenue) / nullif(any_value(sp.spend), 0), 2) AS roas,
       round(any_value(rev.revenue) - coalesce(any_value(sp.spend), 0), 0) AS contribution_eur
FROM m
LEFT JOIN rev USING (segment)
LEFT JOIN sp USING (segment)
GROUP BY 1
ORDER BY spend_eur DESC;
