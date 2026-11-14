-- Taux d'acceptation sur les tentatives INITIALES (attempt_no = 1), par dimension __DIM__.
-- Paramètres : {{start}}, {{end}} (dates ISO), {{countries}} (liste de codes pays carte)
SELECT __DIM__ AS segment,
       count(*)                                         AS first_attempts,
       sum((outcome = 'approved')::INT)                 AS approved,
       round(avg((outcome = 'approved')::INT), 4)       AS acceptance_rate,
       round(avg((decline_type = 'soft')::INT), 4)      AS soft_decline_rate,
       round(avg((decline_type = 'hard')::INT), 4)      AS hard_decline_rate
FROM payment_attempts
WHERE attempt_no = 1
  AND ts_utc >= {{start}} AND ts_utc < {{end}}
  AND card_country IN {{countries}}
GROUP BY 1
ORDER BY first_attempts DESC;
