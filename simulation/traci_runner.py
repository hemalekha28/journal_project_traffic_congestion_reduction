import traci
import pandas as pd
import os

SUMO_CONFIG = "sumo_config/simulation.sumocfg"
OUTPUT_FILE = "data_output/vehicle_data.csv"


def run_simulation():
    print("Starting SUMO simulation...")

    traci.start([
        "sumo",  # use "sumo-gui" to watch it visually
        "-c", SUMO_CONFIG,
        "--no-warnings",
        "--no-step-log"
    ])

    data = []
    step = 0
    total_steps = 3600  # 1 hour

    print(f"Running {total_steps} steps...")

    while step < total_steps:
        traci.simulationStep()

        vehicles = traci.vehicle.getIDList()

        for vid in vehicles:
            try:
                row = {
                    "time_step": step,
                    "vehicle_id": vid,
                    "route_id": traci.vehicle.getRouteID(vid),
                    "speed": round(traci.vehicle.getSpeed(vid), 3),
                    "co_emission": round(traci.vehicle.getCOEmission(vid), 3),
                    "co2_emission": round(traci.vehicle.getCO2Emission(vid), 3),
                    "nox_emission": round(traci.vehicle.getNOxEmission(vid), 3),
                    "fuel_consumption": round(traci.vehicle.getFuelConsumption(vid), 3),
                    "noise": round(traci.vehicle.getNoiseEmission(vid), 3),
                    "pos_x": round(traci.vehicle.getPosition(vid)[0], 3),
                    "pos_y": round(traci.vehicle.getPosition(vid)[1], 3),
                    "lane_id": traci.vehicle.getLaneID(vid),
                    "waiting_time": round(traci.vehicle.getWaitingTime(vid), 3),
                    "acceleration": round(traci.vehicle.getAcceleration(vid), 3)
                }
                data.append(row)
            except Exception:
                pass  # skip if vehicle data unavailable

        if step % 300 == 0:
            print(f"Progress: {step}/{total_steps} steps | "
                  f"Vehicles: {len(vehicles)} | Records: {len(data)}")

        step += 1

    traci.close()
    print("Simulation complete!")

    os.makedirs("data_output", exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Data saved to {OUTPUT_FILE}")
    print(f"Total records: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(df.head())

    return df


if __name__ == "__main__":
    run_simulation()
