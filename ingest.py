import os
import sqlite3
import pandas as pd
import fastf1

os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")

DB = "f1.db"
YEARS = [2022, 2023, 2024, 2025]


def already_loaded(con, year, rnd):
    try:
        row = con.execute(
            "SELECT 1 FROM races WHERE year=? AND round=?", (year, rnd)
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False


def load_race(year, rnd, event_name, location):
    session = fastf1.get_session(year, rnd, "R")
    session.load(laps=True, telemetry=False, weather=True, messages=False)

    laps = session.laps.copy()
    weather = session.weather_data

    out = pd.DataFrame({
        "year": year,
        "round": rnd,
        "driver": laps["Driver"],
        "team": laps["Team"],
        "lap_number": laps["LapNumber"],
        "lap_time_s": laps["LapTime"].dt.total_seconds(),
        "stint": laps["Stint"],
        "compound": laps["Compound"],
        "tyre_life": laps["TyreLife"],
        "fresh_tyre": laps["FreshTyre"].fillna(False).astype(int),
        "in_lap": laps["PitInTime"].notna().astype(int),
        "out_lap": laps["PitOutTime"].notna().astype(int),
        "track_status": laps["TrackStatus"],
        "position": laps["Position"],
        "is_accurate": laps["IsAccurate"].fillna(False).astype(int),
        "deleted": laps["Deleted"].fillna(False).astype(int),
    })

    race = pd.DataFrame([{
        "year": year,
        "round": rnd,
        "event_name": event_name,
        "location": location,
        "total_laps": int(laps["LapNumber"].max()),
        "rainfall": int(weather["Rainfall"].any()),
        "avg_track_temp": float(weather["TrackTemp"].mean()),
        "avg_air_temp": float(weather["AirTemp"].mean()),
    }])
    return out, race


def main():
    con = sqlite3.connect(DB)
    for year in YEARS:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        for _, ev in schedule.iterrows():
            rnd = int(ev["RoundNumber"])
            if already_loaded(con, year, rnd):
                print(f"skip {year} R{rnd}")
                continue
            try:
                laps_df, race_df = load_race(year, rnd, ev["EventName"], ev["Location"])
                laps_df.to_sql("laps_raw", con, if_exists="append", index=False)
                race_df.to_sql("races", con, if_exists="append", index=False)
                print(f"loaded {year} R{rnd} {ev['EventName']} ({len(laps_df)} laps)")
            except Exception as e:
                print(f"FAILED {year} R{rnd} {ev['EventName']} -> {e}")
    con.close()


if __name__ == "__main__":
    main()