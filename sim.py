import sqlite3
import itertools
import pandas as pd

con = sqlite3.connect("f1.db")
deg = pd.read_sql("SELECT * FROM degradation", con)
pit = pd.read_sql("SELECT * FROM pit_loss", con)
#get number of laps per track
races = pd.read_sql("SELECT location, MAX(total_laps) AS total_laps FROM races GROUP BY location", con)

#sanity filter - because the pace offset had some noisy data
deg = deg[deg["pace_offset_s"].between(-2, 1)]

COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]
#keep only hards as a baseline - global bc independent circuits were noisy 
OFFSET = deg[deg["ref_compound"] == "HARD"].groupby("compound")["pace_offset_s"].median().to_dict()
#global fallback values - deg per compound, fuel loss - speed gain, pit loss time 
WEAR_GLOBAL = deg.groupby("compound")["deg_s_per_lap"].median().to_dict()
FUEL_GLOBAL = deg["fuel_s_per_lap"].median()
PIT_GLOBAL = pit["pit_loss_s"].median()


def params(location):
    #filter for specific track 
    d = deg[deg["location"] == location]
    wear = {}
    #get compound wear coefficient per circuit - take the median value
    for c in COMPOUNDS:
        w = d.loc[d["compound"] == c, "deg_s_per_lap"].median()
        wear[c] = w if pd.notna(w) else WEAR_GLOBAL[c]
   #get fuel time loss per lap or use global median if data DNE
    fuel = d["fuel_s_per_lap"].median()
    if pd.isna(fuel):
        fuel = FUEL_GLOBAL
    #use pit stop data that has at least 15 stops to create the avg per location
    row = pit[(pit["location"] == location) & (pit["n_stops"] >= 15)]
    #use pit loss time (first entry) if the data exists 
    pit_loss = row["pit_loss_s"].iloc[0] if len(row) else PIT_GLOBAL
    #return coefficient dictionary for a location
    return {"wear": wear, "fuel": fuel, "pit": pit_loss}


def race_time(strategy, p):
    total, lap = 0.0, 0
    #loop through the strategy - compunds and stint length, enumerate with index i
    for i, (comp, n) in enumerate(strategy):
        #iterate through the laps in the stint 
        for age in range(1, n + 1):
            lap += 1 #update lap counter
            total += OFFSET.get(comp, 0.0) + p["wear"][comp] * age + p["fuel"] * lap #update time counter - using params - only using offsets, doesnt consider the entire length of a lap

        #if the stint is not the last one, add back pit loss time
        if i < len(strategy) - 1:
            total += p["pit"]
    return total


def splits(total_laps, stints, min_stint, step):
    if stints == 2:
        #for a one stop - max range of pit laps considered is the min stint length to the race total-min stint + 1 (becuase range exlcudes the last value). we iterate in steps so dont have to consider every lap as a possible pit window (although probably should IRL)
        for a in range(min_stint, total_laps - min_stint + 1, step):
            yield (a, total_laps - a) #using yield to avoid having to pass back a large data struct - returns a tuple of the two stint lengths
    else: #two stop branch 

        #hypothetical max stint length - includes 2 min stints
        for a in range(min_stint, total_laps - 2 * min_stint + 1, step):
            #choose all b's based on what a is 
            for b in range(min_stint, total_laps - a - min_stint + 1, step):
                yield (a, b, total_laps - a - b)

#p = track related params 
#stops - one or two stop strategy
def best_strategy(p, total_laps, stops, min_stint=8, step=2):
    best = (float("inf"), None) #hold the best strat (time) - start at infinity so can only improve, and strategy tuple of compounds and stint lengths

    #create an iterable set of all possible combos of compounds (len equiv to stops+1 which is stints)
    for comps in itertools.product(COMPOUNDS, repeat=stops + 1):
        if len(set(comps)) < 2: #remove all tuples that repeat compunds (i.e. (SOFT, SOFT) will be removed bc the set length is only 1)
            continue

        #iterate thru all possible combos of stint length 
        for lens in splits(total_laps, stops + 1, min_stint, step):
            #combine the stint lengths with the compound the stint would be on 
            strategy = list(zip(comps, lens))
            #determine estimated race time with that strategy and location params
            t = race_time(strategy, p)
            #update current best time and strat if it beats current best
            if t < best[0]:
                best = (t, strategy)
    return best


#TEST 
location = "Baku"
total_laps = int(races.loc[races["location"] == location, "total_laps"].iloc[0])
p = params(location)
print(location, total_laps, "laps")
print("wear", {c: round(float(w), 3) for c, w in p["wear"].items()})
print("fuel", round(float(p["fuel"]), 3), "pit", round(float(p["pit"]), 1))

results = {}
for stops in (1, 2):
    t, strategy = best_strategy(p, total_laps, stops)
    print(t)
    results[stops] = t
    print(stops, "stop", round(t, 1), strategy)
print("two stop minus one stop", round(results[2] - results[1], 1), "seconds")
if (results[2] < results[1]):
    print("two stop is faster")
else:
    print("one stop is faster")