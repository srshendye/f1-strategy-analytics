import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

con = sqlite3.connect("f1.db")
df = pd.read_sql("SELECT * FROM laps_clean", con)
print(df.shape)
print(sorted(df.location.unique()))

race = df[(df.year == 2023) & (df.location == "Monza")]
print(race.groupby("compound").size())

os.makedirs("figures", exist_ok=True)
colors = {"SOFT": "red", "MEDIUM": "gold", "HARD": "grey"}

fig, ax = plt.subplots(figsize=(9, 5))
for comp, g in race.groupby("compound"):
    ax.scatter(g["tyre_life"], g["lap_time_s"], s=10, alpha=0.5, label=comp, color=colors[comp])
ax.set_xlabel("Tyre age (laps)")
ax.set_ylabel("Lap time (s)")
ax.set_title("Monza 2023, raw lap time vs tyre age")
ax.legend()
plt.savefig("figures/monza_2023_raw.png", dpi=150)
plt.show()