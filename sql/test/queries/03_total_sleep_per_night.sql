/*
=========================================================
3. TOTAL SLEEP PER NIGHT (EXCLUDES AWAKE)
=========================================================

Calculates total sleep using only core/deep/rem and excludes awake/asleep
(to avoid double counting).
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
),
sleep_totals AS (
    SELECT
        sd.sleep_day,
        SUM(
            LEAST(st.end_local, sd.window_end_local)
            - GREATEST(st.start_local, sd.window_start_local)
        ) AS total_sleep_interval
    FROM sleep_days sd
    JOIN sleep_stage_local st
        ON st.end_local > sd.window_start_local
       AND st.start_local < sd.window_end_local
    WHERE st.stage IN ('core', 'deep', 'rem')
    GROUP BY sd.sleep_day
)
SELECT
    sleep_day AS day,
    FLOOR(EXTRACT(EPOCH FROM total_sleep_interval) / 3600) AS hours_slept,
    FLOOR((EXTRACT(EPOCH FROM total_sleep_interval) % 3600) / 60) AS minutes_slept,
    ROUND(EXTRACT(EPOCH FROM total_sleep_interval) / 3600.0, 2) AS total_hours_decimal
FROM sleep_totals
ORDER BY sleep_day;
