/*
=========================================================
2. SLEEP BY STAGE (NIGHT-OF LOGIC)
=========================================================

Each "day" represents sleep for that night:
2026-01-01 = sleep from Jan 1 @ 8PM to Jan 2 @ 8AM.

All stages are included for visibility (awake included).
*/

WITH params AS (
    SELECT
        '2026-01-01'::date AS start_day,
        '2026-01-07'::date AS end_day
),
sleep_days AS (
    SELECT
        gs::date AS sleep_day,
        (gs::date + time '20:00') AS window_start_local,
        ((gs::date + 1) + time '08:00') AS window_end_local
    FROM params p,
         generate_series(p.start_day, p.end_day, interval '1 day') AS gs
),
sleep_stage_local AS (
    SELECT
        stage,
        start_ts AT TIME ZONE 'America/New_York' AS start_local,
        end_ts   AT TIME ZONE 'America/New_York' AS end_local
    FROM sleep_stage
)
SELECT
    sd.sleep_day AS day,
    st.stage,
    SUM(
        LEAST(st.end_local, sd.window_end_local)
        - GREATEST(st.start_local, sd.window_start_local)
    ) AS total_duration
FROM sleep_days sd
JOIN sleep_stage_local st
    ON st.end_local > sd.window_start_local
   AND st.start_local < sd.window_end_local
GROUP BY
    sd.sleep_day,
    st.stage
ORDER BY
    sd.sleep_day,
    st.stage;
