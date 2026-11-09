import fastf1
import os

os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")

session = fastf1.get_session(2023, "Monza", "R")
session.load()

laps = session.laps
print(laps.shape)
print(laps.columns.tolist())
print(laps[["Driver", "LapNumber", "LapTime", "Compound", "TyreLife", "Stint", "PitInTime"]].head(15))