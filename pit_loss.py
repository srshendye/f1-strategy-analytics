import sqlite3
import pandas as pd

con = sqlite3.connect("f1.db")

#read consecutive laps (join on consecutive lap numbers) so that we can estimate pit loss per driver/per track
#make sure we only use stops under green flag conditions
stops = pd.read_sql("""
    SELECT i.year, i.round, i.driver, i.lap_number AS in_lap_no,
           i.lap_time_s AS in_time, o.lap_time_s AS out_time
    FROM laps_raw i
    JOIN laps_raw o
      ON i.year = o.year AND i.round = o.round AND i.driver = o.driver
     AND o.lap_number = i.lap_number + 1
    WHERE i.in_lap = 1 AND o.out_lap = 1
      AND i.lap_time_s IS NOT NULL AND o.lap_time_s IS NOT NULL
      AND i.track_status = '1' AND o.track_status = '1'
""", con)
print(len(stops), "green flag stops found")

#2182 green flag stops found

#get clean laps from drivers 
clean = pd.read_sql(
    "SELECT year, round, driver, lap_number, lap_time_s FROM laps_clean", con
)

near = stops.merge(clean, on=["year", "round", "driver"])
# print(stops)
# print("break")
# print(clean)
# print("break")
# print(near)


near = near[(near["lap_number"] - near["in_lap_no"]).abs() <= 6]
# print("break")
# print(near)

ref = (
    near.groupby(["year", "round", "driver", "in_lap_no"])["lap_time_s"]
    .median()
    .rename("ref_time")
    .reset_index()
)

# print("break")
# print(ref)


stops = stops.merge(ref, on=["year", "round", "driver","in_lap_no"])
stops["pit_loss"] = stops["in_time"] + stops["out_time"] - 2*stops["ref_time"]

#sanity filter - pitloss shouldnt be more than 40 for a hypthetically clean lap
stops = stops[(stops["pit_loss"] > 10) & (stops["pit_loss"] < 40)]

print(len(stops), "stops kept after sanity filter")

#1895 stops kept after sanity filter

races = pd.read_sql("SELECT year, round, location FROM races", con)
stops = stops.merge(races, on=["year", "round"])

print(stops)
#create summary table - median for pit loss
summary = (
    stops.groupby("location")["pit_loss"]
    .agg(["median", "count"])
    .round(3)
    .rename(columns={"median": "pit_loss_s", "count": "n_stops"})
    .reset_index()
    .sort_values("pit_loss_s")
)

print("summary\n", summary )

#save summary to sql db as pit loss info 
summary.to_sql("pit_loss", con, if_exists="replace", index=False)