/*
=========================================================
1. STEPS PER DAY (Google / Fitbit)
=========================================================

Returns daily step count using Fitbit watch as the primary source.
Falls back to Google Fit phone data (Pixel 8 Pro) only on days
where the Fitbit watch recorded fewer than 500 steps (e.g. left
on charger).

Google Fit phone data is less accurate (phantom steps, double-counting)
but better than nothing on watch-off days.

NOTE:
- Fitbit timestamps are already in the user's local time.
- Google Fit timestamps are UTC (nanosecond epoch converted).
  For daily aggregation this is close enough.
*/

WITH params AS (
    SELECT
        '2026-03-24'::date AS start_day,
        '2026-04-06'::date AS end_day
),
fitbit_daily AS (
    SELECT
        DATE(s.start_ts) AS day,
        SUM(s.steps) AS steps
    FROM steps_sample s
    JOIN data_source ds ON s.source_id = ds.source_id
    WHERE ds.vendor = 'fitbit' AND ds.product = 'Fitbit'
    GROUP BY day
),
phone_daily AS (
    SELECT
        DATE(s.start_ts) AS day,
        SUM(s.steps) AS steps
    FROM steps_sample s
    JOIN data_source ds ON s.source_id = ds.source_id
    WHERE ds.vendor = 'google' AND ds.product = 'Pixel 8 Pro'
    GROUP BY day
)
SELECT
    COALESCE(f.day, ph.day) AS day,
    CASE
        WHEN COALESCE(f.steps, 0) >= 500 THEN f.steps
        ELSE COALESCE(ph.steps, f.steps)
    END AS total_steps,
    CASE
        WHEN COALESCE(f.steps, 0) >= 500 THEN 'fitbit_watch'
        WHEN ph.steps IS NOT NULL THEN 'pixel_phone_fallback'
        ELSE 'fitbit_watch'
    END AS source_used
FROM fitbit_daily f
FULL OUTER JOIN phone_daily ph ON f.day = ph.day
CROSS JOIN params p
WHERE COALESCE(f.day, ph.day) >= p.start_day
  AND COALESCE(f.day, ph.day) <= p.end_day
ORDER BY day;
