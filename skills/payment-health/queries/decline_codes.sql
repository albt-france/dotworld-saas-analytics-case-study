-- Quels codes de refus expliquent une variation ? Taux de chaque code (en % des tentatives
-- initiales) avant et après une date de rupture, par PSP.
-- Paramètres : {{start}}, {{split}}, {{end}} (dates ISO), {{countries}}
WITH a AS (
    SELECT *, ts_utc >= {{split}} AS after_split
    FROM payment_attempts
    WHERE attempt_no = 1 AND ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}}
),
tot AS (
    SELECT psp,
           count(*) FILTER (WHERE NOT after_split) AS n_before,
           count(*) FILTER (WHERE after_split)     AS n_after
    FROM a GROUP BY 1
)
SELECT a.psp, a.decline_code, any_value(a.decline_type) AS decline_type,
       round(count(*) FILTER (WHERE NOT a.after_split) / any_value(t.n_before), 4) AS rate_before,
       round(count(*) FILTER (WHERE a.after_split) / any_value(t.n_after), 4)      AS rate_after,
       round(count(*) FILTER (WHERE a.after_split) / any_value(t.n_after)
             - count(*) FILTER (WHERE NOT a.after_split) / any_value(t.n_before), 4) AS change_pts
FROM a JOIN tot t USING (psp)
WHERE a.decline_code IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, change_pts DESC;
