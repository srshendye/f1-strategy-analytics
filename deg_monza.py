import sqlite3
import pandas as pd
import statsmodels.formula.api as smf

con = sqlite3.connect("f1.db")
df = pd.read_sql("SELECT * FROM laps_clean", con)
race = df[(df.year == 2023) & (df.location == "Monza")].copy()

print(race.shape)
print(race[["driver", "lap_number", "compound", "tyre_life", "lap_time_s"]].head())


m1 = smf.ols("lap_time_s ~ tyre_life", data=race).fit()
print(m1.summary())

# account for fuel burn with the lap number
# hypothetically, as lap number gets higher, lap time should improve
# should improve the tyre_life coefficient accuracy because it has the opposite effect to the lap number (as tyre_life goes up, lap time should be slower) 
m2 = smf.ols("lap_time_s ~ tyre_life + lap_number", data=race).fit()

print(m2.params.round(4))
print("R2 before", round(m1.rsquared, 3), "| after", round(m2.rsquared, 3))

#RESULT:
#R2 before 0.035 | after 0.312 
#indicates that the model has improved because the R2 has increased - more of the variation is explainable by the model by adding another variable



# account for the driver of the car
# C(driver) - this syntax flattens/splits this collumn by treating each text format code for a driver into a boolean category - attaches a coeeficient to each driver 
# neg coefficient in this case implies that a driver is faster than the baseline driver - baseline driver is the first one in the set - all are given a relative coeffient to this driver

m3 = smf.ols("lap_time_s ~ tyre_life + lap_number + C(driver)", data=race).fit()
keep = ["tyre_life", "lap_number"]
print(m3.params[keep].round(4))
print(m3.conf_int().loc[keep].round(4))
print("R2", round(m2.rsquared, 3), "->", round(m3.rsquared, 3))


#account for different rates of deg per compound 
# tyre_life:C(compound) seperates the interaction between 
m4 = smf.ols(
    "lap_time_s ~ C(driver) + lap_number + C(compound) + tyre_life:C(compound)",
    data=race,
).fit()
keep = [p for p in m4.params.index if p == "lap_number" or "tyre_life" in p]
print(m4.params[keep].round(4))
print(m4.conf_int().loc[keep].round(4))
print("R2", round(m3.rsquared, 3), "->", round(m4.rsquared, 3))


#RESULTS
#R2 0.659 -> 0.659
#no movement - splitting the compound deg rates wasn't significant in this case as our results held steady 

