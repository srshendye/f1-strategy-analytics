WITH base AS (
    SELECT l.*
    FROM laps_raw l
        JOIN races r ON l.year = r.year
        AND l.round = r.round
    WHERE r.rainfall = 0
        AND l.track_status = '1'
        AND l.in_lap = 0
        AND l.out_lap = 0
        AND l.lap_number > 1
        AND l.lap_time_s IS NOT NULL
        AND l.tyre_life IS NOT NULL
        AND l.compound IN ('SOFT', 'MEDIUM', 'HARD')
),
ref AS (
    SELECT year,
        round,
        MIN(lap_time_s) AS best_lap
    FROM base
    GROUP BY year,
        round
)
SELECT COUNT(*) AS total,
    SUM(b.lap_time_s > ref.best_lap * 1.03) AS over_103,
    SUM(b.lap_time_s > ref.best_lap * 1.05) AS over_105,
    SUM(b.lap_time_s > ref.best_lap * 1.07) AS over_107
FROM base b
    JOIN ref USING (year, round);