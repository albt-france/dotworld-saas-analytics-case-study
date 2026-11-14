-- Efficacité des nouvelles tentatives du marchand (MIT) après un refus initial « soft »,
-- par code initial et par délai ; plus les relances interdites après un refus « hard ».
-- Paramètres : {{start}}, {{end}}, {{countries}}
WITH a AS (
    SELECT *,
           first_value(decline_code) OVER w AS first_code,
           first_value(decline_type) OVER w AS first_type,
           lag(decline_type) OVER w         AS prev_type
    FROM payment_attempts
    WHERE ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}}
    WINDOW w AS (PARTITION BY payment_id ORDER BY attempt_no)
)
SELECT CASE WHEN prev_type = 'hard' THEN 'RELANCE APRÈS REFUS DÉFINITIF' ELSE first_code END AS first_code,
       retry_delay_days AS delay_days,
       count(*) AS retries,
       round(avg((outcome = 'approved')::INT), 4) AS success_rate
FROM a
WHERE attempt_no >= 2 AND initiator = 'MIT'
GROUP BY 1, 2
HAVING count(*) >= 30
ORDER BY 1, 2;
