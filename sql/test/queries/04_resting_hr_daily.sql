/*
=========================================================
4. RESTING HEART RATE DAILY AVERAGE
=========================================================

Returns daily average resting heart rate from Apple resting HR records.

NOTE:
- End timestamp is exclusive.
- Grouping is in America/New_York local time.
*/

WITH params AS (
    SELECT
        '2026-01-01 00:00:00-05'::timestamptz AS start_ts,
        '2026-01-08 00:00:00-05'::timestamptz AS end_ts
)
SELECT
    DATE(hr.ts AT TIME ZONE 'America/New_York') AS day,
    ROUND(AVG(hr.bpm), 0) AS avg_resting_hr
FROM hr_sample hr
JOIN source_event se
    ON hr.source_event_id = se.source_event_id
CROSS JOIN params p
WHERE hr.ts >= p.start_ts
  AND hr.ts < p.end_ts
  AND se.vendor_type = 'HKQuantityTypeIdentifierRestingHeartRate'
GROUP BY day
ORDER BY day;
