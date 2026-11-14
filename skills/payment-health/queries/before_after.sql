-- Acceptation (tentatives initiales) avant et après une date de rupture, par PSP.
-- Paramètres : {{start}}, {{split}}, {{end}}, {{countries}}
SELECT psp,
       count(*) FILTER (WHERE ts_utc < {{split}})                                   AS n_before,
       round(avg((outcome = 'approved')::INT) FILTER (WHERE ts_utc < {{split}}), 4)  AS acceptance_before,
       count(*) FILTER (WHERE ts_utc >= {{split}})                                  AS n_after,
       round(avg((outcome = 'approved')::INT) FILTER (WHERE ts_utc >= {{split}}), 4) AS acceptance_after,
       round(avg((outcome = 'approved')::INT) FILTER (WHERE ts_utc >= {{split}})
             - avg((outcome = 'approved')::INT) FILTER (WHERE ts_utc < {{split}}), 4) AS change_pts
FROM payment_attempts
WHERE attempt_no = 1 AND ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}}
GROUP BY 1 ORDER BY 1;
