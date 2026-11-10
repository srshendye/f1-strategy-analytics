import sqlite3
import pandas as pd
import statsmodels.formula.api as smf
import numpy as np

con = sqlite3.connect("f1.db")
df = pd.read_sql("SELECT * FROM laps_clean", con)

MIN_LAPS = 40 #need to run at least 40 laps on one type of compound in a race to have a significant amount of data to work with 
MIN_SPREAD = 10 #need to have different tyre wear in order to accurately fit lap time as a function of tire wear (softs might fail this test)

results  = []

for (year, rnd), race_laps in df.groupby(["year", "round"]):
   
    ok = []
    for compound, table in race_laps.groupby("compound"):
        enough_laps = len(table) >= MIN_LAPS
        wide_spread = (table["tyre_life"].max() - table["tyre_life"].min()) >= MIN_SPREAD
        if enough_laps and wide_spread: 
            ok.append(compound)
    if not ok: 
        continue

    filtered_race_laps = race_laps[race_laps["compound"].isin(ok)].copy() #filter to only use the compounds that meet our filter bounds

    terms = ["C(driver)", "lap_number"]
    if len(ok) > 1: #if more than one tire passes the filter
        terms.append("C(compound)")

    for compound in ok:
        filtered_race_laps[f"tl_{compound}"] = np.where(
            filtered_race_laps["compound"] == compound,
            filtered_race_laps["tyre_life"],
            0,
        )
        terms.append(f"tl_{compound}") #tyre life compound - seperates each compound into its own grouping

    #turn each drivers code and stint number into a unique id (using factorize)
    #clustering the same stints together because neighbouring laps are not independent data points
    stint_id = filtered_race_laps["driver"] + "_" + filtered_race_laps["stint"].astype(int).astype(str)
    clusters = pd.factorize(stint_id)[0]

    try:
        model = smf.ols("lap_time_s ~ " + " + ".join(terms), data=filtered_race_laps).fit(
            cov_type="cluster", cov_kwds={"groups": clusters}
        )
    except Exception as e:
        print("failed", year, rnd, e)
        continue

     #store params per compound and confidence intervals
    ci = model.conf_int()
    for compound in ok:
        key = f"tl_{compound}"
        results.append({
            "year": year,
            "round": rnd,
            "event_name": filtered_race_laps["event_name"].iloc[0],
            "location": filtered_race_laps["location"].iloc[0],
            "compound": compound,
            "deg_s_per_lap": model.params[key],
            "ci_low": ci.loc[key, 0],
            "ci_high": ci.loc[key, 1],
            "fuel_s_per_lap": model.params["lap_number"],
            "n_laps": int(model.nobs),
            "r2": model.rsquared,
        })

#save results to SQL db so we dont have to run the model everytime to look at rsults
out = pd.DataFrame(results)
out.to_sql("degradation", con, if_exists="replace", index=False)
print(out.groupby("compound")["deg_s_per_lap"].describe().round(3))
print(len(out), "race and compound fits saved")
    

