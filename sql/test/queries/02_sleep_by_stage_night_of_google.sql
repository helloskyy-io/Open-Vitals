/*
=========================================================
2. SLEEP BY STAGE PER NIGHT (Google / Fitbit)
=========================================================

Fitbit labels sleep by the WAKE-UP date (dateOfSleep in their API).
So we group stages by DATE(session.end_ts).

Fitbit timestamps are already in the user's local time,
so no AT TIME ZONE conversion is applied.

Only Fitbit sleep data is used.
*/

WITH params AS (
    SELECT
        '2026-03-24'::date AS start_day,
        '2026-04-06'::date AS end_day
)
SELECT
    DATE(sn.end_ts) AS day,
    ss.stage,
    ROUND(SUM(
        EXTRACT(EPOCH FROM (ss.end_ts - ss.start_ts)) / 60.0
    ), 1) AS total_minutes
FROM sleep_session sn
JOIN sleep_stage ss ON sn.sleep_session_id = ss.sleep_session_id
JOIN data_source ds ON sn.source_id = ds.source_id
CROSS JOIN params p
WHERE ds.vendor = 'fitbit'
  AND DATE(sn.end_ts) >= p.start_day
  AND DATE(sn.end_ts) <= p.end_day
GROUP BY day, ss.stage
ORDER BY day, ss.stage;
