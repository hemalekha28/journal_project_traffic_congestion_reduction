"""
SAFETY NET — not part of the official pipeline.

If SUMO install/setup eats too much time today, run this to generate
a realistic-looking vehicle_data.csv so you can test sensor_fusion.py,
fkm_clustering.py, and fahp.py right away. Swap in the real SUMO output
the moment it's ready — nothing downstream changes.
"""
import numpy as np
import pandas as pd
import os

np.random.seed(42)

ROUTES = ["route1", "route2", "route3", "route4"]
N_VEHICLES_PER_ROUTE = 14
N_STEPS = 200  # lighter than a full 3600-step SUMO run, fine for testing

# Route 2 gets intentionally worse readings (lower speed, higher emissions)
# so the pipeline has a clear "congested route" to detect, like the base paper.
ROUTE_PROFILES = {
    "route1": {"speed": (12, 3), "co": (110, 30), "co2": (7500, 1500), "nox": (3, 1), "fuel": (3.3, 1)},
    "route2": {"speed": (7, 2),  "co": (150, 30), "co2": (9500, 1500), "nox": (4, 1), "fuel": (4.2, 1)},
    "route3": {"speed": (13, 3), "co": (100, 25), "co2": (6800, 1300), "nox": (3, 1), "fuel": (3.4, 1)},
    "route4": {"speed": (14, 3), "co": (95, 25),  "co2": (6500, 1200), "nox": (2.5, 1), "fuel": (3.0, 1)},
}

rows = []
for route in ROUTES:
    p = ROUTE_PROFILES[route]
    for v in range(N_VEHICLES_PER_ROUTE):
        vid = f"{route}_veh{v}"
        for step in range(0, N_STEPS, 20):  # sample every 20 steps
            rows.append({
                "time_step": step,
                "vehicle_id": vid,
                "route_id": route,
                "speed": max(0.5, round(np.random.normal(*p["speed"]), 3)),
                "co_emission": max(0, round(np.random.normal(*p["co"]), 3)),
                "co2_emission": max(0, round(np.random.normal(*p["co2"]), 3)),
                "nox_emission": max(0, round(np.random.normal(*p["nox"]), 3)),
                "fuel_consumption": max(0, round(np.random.normal(*p["fuel"]), 3)),
                "noise": round(np.random.uniform(50, 75), 3),
                "pos_x": round(np.random.uniform(0, 1000), 3),
                "pos_y": round(np.random.uniform(0, 1000), 3),
                "lane_id": f"{route}_lane0",
                "waiting_time": round(np.random.uniform(0, 20), 3),
                "acceleration": round(np.random.normal(0, 1), 3),
            })

df = pd.DataFrame(rows)
os.makedirs("data_output", exist_ok=True)
df.to_csv("data_output/vehicle_data.csv", index=False)
print(f"Fallback data written: data_output/vehicle_data.csv ({len(df)} rows)")
print(df.groupby("route_id")[["speed", "co2_emission"]].mean())
