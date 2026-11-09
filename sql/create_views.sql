DROP VIEW IF EXISTS laps_clean;
DROP VIEW IF EXISTS race_conditions;
CREATE VIEW race_conditions AS
SELECT year,
    round,
    ROUND(
        100.0 * SUM(compound IN ('INTERMEDIATE', 'WET')) / COUNT(*),
        1
    ) AS pct_wet_tire_laps
FROM laps_raw
GROUP BY year,
    round;
CREATE VIEW laps_clean AS WITH base AS (
    SELECT l.*,
        r.event_name,
        r.location,
        r.avg_track_temp,
        r.total_laps
    FROM laps_raw l
        JOIN races r ON l.year = r.year
        AND l.round = r.round
        JOIN race_conditions rc ON l.year = rc.year
        AND l.round = rc.round
    WHERE rc.pct_wet_tire_laps < 5
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
SELECT b.*
FROM base b
    JOIN ref USING (year, round)
WHERE b.lap_time_s <= ref.best_lap * 1.07;