from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

import psycopg


@dataclass(frozen=True)
class ParamSet:
    name: str
    watch_cluster_gap_min: int
    watch_pad_before_min: int
    watch_pad_after_min: int


APPLE_TOTALS = {
    "2026-01-01": 3232,
    "2026-01-02": 9107,
    "2026-01-03": 10275,
    "2026-01-04": 11806,
    "2026-01-05": 3850,
    "2026-01-06": 8427,
    "2026-01-07": 8074,
}


PARAM_SETS: list[ParamSet] = [
    ParamSet("p_5_10_2", 5, 10, 2),
    ParamSet("p_5_11_1", 5, 11, 1),
    ParamSet("p_5_12_2", 5, 12, 2),
    ParamSet("p_5_12_1", 5, 12, 1),
    ParamSet("p_5_13_2", 5, 13, 2),
    ParamSet("p_4_12_2", 4, 12, 2),
    ParamSet("p_6_12_2", 6, 12, 2),
    ParamSet("p_5_3_1", 5, 3, 1),
]


SQL = """
WITH params AS (
    SELECT
        %(start_ts)s::timestamptz AS start_ts,
        %(end_ts)s::timestamptz AS end_ts,
        make_interval(mins => %(watch_cluster_gap_min)s) AS watch_cluster_gap,
        make_interval(mins => %(watch_pad_before_min)s) AS watch_pad_before,
        make_interval(mins => %(watch_pad_after_min)s) AS watch_pad_after
),

base_steps AS (
    SELECT
        s.steps_id,
        s.start_ts,
        s.end_ts,
        s.steps,
        CASE
            WHEN ds.product LIKE '%%Watch%%' THEN 'watch'
            WHEN ds.product LIKE '%%iPhone%%' THEN 'iphone'
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
"""


def run_param_set(
    conn: psycopg.Connection,
    param_set: ParamSet,
    start_ts: str,
    end_ts: str,
) -> list[dict]:
    query_params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "watch_cluster_gap_min": param_set.watch_cluster_gap_min,
        "watch_pad_before_min": param_set.watch_pad_before_min,
        "watch_pad_after_min": param_set.watch_pad_after_min,
    }

    with conn.cursor() as cur:
        cur.execute(SQL, query_params)
        rows = cur.fetchall()

    results: list[dict] = []
    for day, watch_steps, iphone_steps, merged_total_steps in rows:
        day_str = str(day)
        apple_total = APPLE_TOTALS.get(day_str)
        diff = None if apple_total is None else int(merged_total_steps) - apple_total
        abs_diff = None if diff is None else abs(diff)

        results.append(
            {
                "param_name": param_set.name,
                "watch_cluster_gap_min": param_set.watch_cluster_gap_min,
                "watch_pad_before_min": param_set.watch_pad_before_min,
                "watch_pad_after_min": param_set.watch_pad_after_min,
                "day": day_str,
                "watch_steps": int(watch_steps),
                "iphone_steps": int(iphone_steps),
                "merged_total_steps": int(merged_total_steps),
                "apple_total": apple_total,
                "diff": diff,
                "abs_diff": abs_diff,
            }
        )

    return results


def score_results(results: Iterable[dict]) -> dict:
    rows = list(results)
    scored_rows = [r for r in rows if r["abs_diff"] is not None]
    total_abs_error = sum(r["abs_diff"] for r in scored_rows)
    max_abs_error = max((r["abs_diff"] for r in scored_rows), default=0)
    signed_error = sum(r["diff"] for r in scored_rows)

    return {
        "param_name": rows[0]["param_name"] if rows else None,
        "watch_cluster_gap_min": rows[0]["watch_cluster_gap_min"] if rows else None,
        "watch_pad_before_min": rows[0]["watch_pad_before_min"] if rows else None,
        "watch_pad_after_min": rows[0]["watch_pad_after_min"] if rows else None,
        "total_abs_error": total_abs_error,
        "max_abs_error": max_abs_error,
        "signed_error_sum": signed_error,
    }


def write_csv(path: str, rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    # Replace this with your actual connection info string / env-driven value
    conninfo = "host=localhost port=5432 user=openvitals dbname=openvitals password=openvitals"

    start_ts = "2026-01-01 00:00:00-05"
    end_ts = "2026-01-08 00:00:00-05"

    all_rows: list[dict] = []
    summaries: list[dict] = []

    with psycopg.connect(conninfo) as conn:
        for param_set in PARAM_SETS:
            print(
                f"Running {param_set.name} "
                f"(gap={param_set.watch_cluster_gap_min}, "
                f"before={param_set.watch_pad_before_min}, "
                f"after={param_set.watch_pad_after_min})"
            )

            rows = run_param_set(conn, param_set, start_ts, end_ts)
            all_rows.extend(rows)
            summaries.append(score_results(rows))

    summaries.sort(
        key=lambda x: (
            x["total_abs_error"],
            x["max_abs_error"],
            abs(x["signed_error_sum"]),
        )
    )

    print("\nTop parameter sets:")
    for summary in summaries[:10]:
        print(
            f"{summary['param_name']}: "
            f"gap={summary['watch_cluster_gap_min']} "
            f"before={summary['watch_pad_before_min']} "
            f"after={summary['watch_pad_after_min']} | "
            f"total_abs_error={summary['total_abs_error']} "
            f"max_abs_error={summary['max_abs_error']} "
            f"signed_error_sum={summary['signed_error_sum']}"
        )

    best_name = summaries[0]["param_name"]
    best_rows = [r for r in all_rows if r["param_name"] == best_name]

    print(f"\nBest daily breakdown: {best_name}")
    for row in best_rows:
        print(
            f"{row['day']} | "
            f"watch={row['watch_steps']} "
            f"iphone={row['iphone_steps']} "
            f"merged={row['merged_total_steps']} "
            f"apple={row['apple_total']} "
            f"diff={row['diff']}"
        )

    write_csv("step_param_test_detailed.csv", all_rows)
    write_csv("step_param_test_summary.csv", summaries)
    print("\nWrote step_param_test_detailed.csv and step_param_test_summary.csv")


if __name__ == "__main__":
    main()