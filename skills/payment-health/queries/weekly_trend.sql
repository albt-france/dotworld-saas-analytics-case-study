-- Tendance hebdomadaire de l'acceptation (tentatives initiales) par PSP.
-- Paramètres : {{start}}, {{end}}, {{countries}}
SELECT date_trunc('week', ts_utc)::DATE AS week, psp,
       count(*) AS first_attempts,
       round(avg((outcome = 'approved')::INT), 4) AS acceptance_rate
FROM payment_attempts
WHERE attempt_no = 1 AND ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}}
GROUP BY 1, 2
ORDER BY 1, 2;
