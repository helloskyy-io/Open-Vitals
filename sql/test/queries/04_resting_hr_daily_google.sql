/*
=========================================================
4. RESTING HEART RATE DAILY AVERAGE (Google / Fitbit)
=========================================================

Returns daily resting heart rate from Fitbit resting HR records.

Fitbit provides one pre-computed resting HR value per day,
so AVG is effectively a pass-through (one reading per day).

NOTE:
- End timestamp is exclusive.
- Fitbit timestamps are already in the user's local time
  (no timezone offset in the export), so no AT TIME ZONE
  conversion is applied.
- vendor_type = 'fitbit.resting_heart_rate' targets
  the explicit daily resting HR values from Fitbit.
*/

WITH params AS (
    SELECT
        '2025-10-09'::timestamp AS start_ts,
        '2026-04-07'::timestamp AS end_ts
)
SELECT
    DATE(hr.ts) AS day,
    ROUND(AVG(hr.bpm), 0) AS avg_resting_hr
FROM hr_sample hr
JOIN source_event se
    ON hr.source_event_id = se.source_event_id
CROSS JOIN params p
WHERE hr.ts >= p.start_ts
  AND hr.ts < p.end_ts
  AND se.vendor_type = 'fitbit.resting_heart_rate'
GROUP BY day
ORDER BY day;
