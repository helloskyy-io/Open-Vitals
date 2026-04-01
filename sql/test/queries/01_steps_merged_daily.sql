/*
=========================================================
1. STEPS PER DAY (MERGED WATCH + IPHONE)
=========================================================

Merges watch and iPhone steps while avoiding obvious overlap.

NOTE:
- End timestamp is exclusive.
- Grouping is in America/New_York local time.
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
