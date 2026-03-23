/*
=========================================================
Open Vitals - Core Validation Queries
=========================================================

These queries validate the 3 main domains:

1. Steps
2. Sleep (night-of logic)
3. Heart Rate

Time range is adjustable via the params CTE.

NOTE:
- End timestamp is exclusive (use next day at 00:00)
- All grouping is done in America/New_York local time
=========================================================
*/


/*
=========================================================
1. STEPS PER DAY (RAW TOTAL)
=========================================================

Sums all step intervals per day.

NOTE:
This currently includes all sources (watch + phone),
so totals may be inflated. This is intentional for
initial ingestion validation.
*/

WITH params AS (
    SELECT
        '2026-01-01 00:00:00-05'::timestamptz AS start_ts,
        '2026-01-08 00:00:00-05'::timestamptz AS end_ts,
        interval '5 minutes'  AS watch_cluster_gap,
        interval '10 minutes' AS watch_pad_before,
        interval '2 minutes'  AS watch_pad_after
),

base_steps AS (
    SELECT
        s.steps_id,
        s.start_ts,
        s.end_ts,
        s.steps,
        CASE
            WHEN ds.product LIKE '%Watch%' THEN 'watch'
            WHEN ds.product LIKE '%iPhone%' THEN 'iphone'
        END AS source_type
    FROM steps_sample s
    JOIN data_source ds
        ON s.source_id = ds.source_id
    CROSS JOIN params p
    WHERE s.end_ts > p.start_ts
      AND s.start_ts < p.end_ts
),

watch_intervals AS (
    SELECT
        b.steps_id,
        b.start_ts,
        b.end_ts,
        b.steps,
        LAG(b.end_ts) OVER (ORDER BY b.start_ts, b.end_ts, b.steps_id) AS prev_end
    FROM base_steps b
    WHERE b.source_type = 'watch'
),

watch_clustered AS (
    SELECT
        wi.*,
        SUM(
            CASE
                WHEN wi.prev_end IS NULL THEN 1
                WHEN wi.start_ts - wi.prev_end > (SELECT watch_cluster_gap FROM params) THEN 1
                ELSE 0
            END
        ) OVER (ORDER BY wi.start_ts, wi.end_ts, wi.steps_id) AS cluster_id
    FROM watch_intervals wi
),

watch_clusters AS (
    SELECT
        wc.cluster_id,
        MIN(wc.start_ts) AS cluster_start,
        MAX(wc.end_ts)   AS cluster_end
    FROM watch_clustered wc
    GROUP BY wc.cluster_id
),

watch_dominance_windows AS (
    SELECT
        cluster_id,
        cluster_start - (SELECT watch_pad_before FROM params) AS window_start,
        cluster_end   + (SELECT watch_pad_after  FROM params) AS window_end
    FROM watch_clusters
),

watch_daily AS (
    SELECT
        DATE(wi.start_ts AT TIME ZONE 'America/New_York') AS day,
        SUM(wi.steps) AS watch_steps
    FROM watch_intervals wi
    GROUP BY 1
),

iphone_intervals AS (
    SELECT
        b.steps_id,
        b.start_ts,
        b.end_ts,
        b.steps
    FROM base_steps b
    WHERE b.source_type = 'iphone'
),

iphone_seconds AS (
    SELECT
        ii.steps_id,
        gs.second_ts,
        ii.steps::numeric
            / GREATEST(EXTRACT(EPOCH FROM (ii.end_ts - ii.start_ts)), 1) AS steps_per_second
    FROM iphone_intervals ii
    CROSS JOIN LATERAL generate_series(
        ii.start_ts,
        ii.end_ts - interval '1 second',
        interval '1 second'
    ) AS gs(second_ts)
),

iphone_valid_seconds AS (
    SELECT
        isec.second_ts,
        isec.steps_per_second
    FROM iphone_seconds isec
    WHERE NOT EXISTS (
        SELECT 1
        FROM watch_dominance_windows wdw
        WHERE isec.second_ts >= wdw.window_start
          AND isec.second_ts <  wdw.window_end
    )
),

iphone_daily AS (
    SELECT
        DATE(second_ts AT TIME ZONE 'America/New_York') AS day,
        FLOOR(SUM(steps_per_second)) AS iphone_steps
    FROM iphone_valid_seconds
    GROUP BY 1
)

SELECT
    COALESCE(w.day, i.day) AS day,
    COALESCE(w.watch_steps, 0) AS watch_steps,
    COALESCE(i.iphone_steps, 0) AS iphone_steps,
    COALESCE(w.watch_steps, 0) + COALESCE(i.iphone_steps, 0) AS merged_total_steps
FROM watch_daily w
FULL OUTER JOIN iphone_daily i
    ON w.day = i.day
ORDER BY day;


/*
=========================================================
2. SLEEP BY STAGE (NIGHT-OF LOGIC)
=========================================================

Each "day" represents sleep for that night:

Example:
2026-01-01 = sleep from Jan 1 @ 8PM → Jan 2 @ 8AM

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



/*
=========================================================
3. TOTAL SLEEP PER NIGHT (EXCLUDES AWAKE)
=========================================================

Calculates total sleep using only:
- core
- deep
- rem

Excludes:
- awake
- asleep (to avoid double counting)

This represents actual sleep time per night.
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



/*
=========================================================
4. HEART RATE DAILY STATS
=========================================================

Returns min, max, average heart rate per day.

Uses correct end-of-day handling and local time grouping.
*/

WITH params AS (
    SELECT
        '2026-01-01 00:00:00-05'::timestamptz AS start_ts,
        '2026-01-08 00:00:00-05'::timestamptz AS end_ts
)
SELECT
    DATE(hr.ts AT TIME ZONE 'America/New_York') AS day,
    MIN(hr.bpm) AS min_bpm,
    MAX(hr.bpm) AS max_bpm,
    ROUND(AVG(hr.bpm), 2) AS avg_bpm,
    COUNT(*) AS sample_count
FROM hr_sample hr
CROSS JOIN params p
WHERE hr.ts >= p.start_ts
  AND hr.ts < p.end_ts
GROUP BY DATE(hr.ts AT TIME ZONE 'America/New_York')
ORDER BY day;

