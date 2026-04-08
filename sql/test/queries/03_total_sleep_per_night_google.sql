/*
=========================================================
3. TOTAL SLEEP PER NIGHT — EXCLUDES AWAKE (Google / Fitbit)
=========================================================

Calculates total sleep using only core/deep/rem stages.
Groups by wake-up date to match Fitbit's labeling convention.

Only Fitbit sleep data is used. Timestamps are already local.
*/

WITH params AS (
    SELECT
        '2026-03-24'::date AS start_day,
        '2026-04-06'::date AS end_day
),
sleep_totals AS (
    SELECT
        DATE(sn.end_ts) AS day,
        SUM(
            EXTRACT(EPOCH FROM (ss.end_ts - ss.start_ts))
        ) AS total_sleep_seconds
    FROM sleep_session sn
    JOIN sleep_stage ss ON sn.sleep_session_id = ss.sleep_session_id
    JOIN data_source ds ON sn.source_id = ds.source_id
    CROSS JOIN params p
    WHERE ds.vendor = 'fitbit'
      AND DATE(sn.end_ts) >= p.start_day
      AND DATE(sn.end_ts) <= p.end_day
      AND ss.stage IN ('core', 'deep', 'rem')
    GROUP BY day
)
SELECT
    day,
    FLOOR(total_sleep_seconds / 3600) AS hours_slept,
    FLOOR((total_sleep_seconds::int % 3600) / 60) AS minutes_slept,
    ROUND(total_sleep_seconds / 3600.0, 2) AS total_hours_decimal
FROM sleep_totals
ORDER BY day;
