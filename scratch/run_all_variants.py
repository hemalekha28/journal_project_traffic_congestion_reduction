import xml.etree.ElementTree as ET
import sys
import os
import traci
import pandas as pd
import numpy as np

# Ensure algorithm directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'algorithm')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from algorithm.sensor_fusion import sensor_fusion
from algorithm.fkm_clustering import get_route_congestion
from algorithm.fahp import calculate_congestion_score
from algorithm.entropy_weight import calculate_entropy_weights
from algorithm.compare_weighting_methods import calculate_score

SUMO_CONFIG = "simulation/sumo_config/simulation.sumocfg"
routes_filepath = "simulation/sumo_config/routes.rou.xml"
BASELINE_FILE = "simulation/data_output/vehicle_data.csv"

ROUTE_257_EDGES = [
    '368732289', '876134933#1', '876134933#2', '1203439472#0', '1203439472#1', 
    '1208491992#0', '1208491992#1', '-506648334#12', '-506648334#11', '-506648334#10', 
    '368732307#0', '368732307#1', '368732307#2'
]

HEAVY_OVERLAP_FLEET = ['257', '29', '167', '166', '58', '143', '99', '332', '317', '95', '112', '85', '170', '168', '308', '344']

def get_broad_overlap_fleet():
    # Identify vehicles that actually traversed these edges in baseline
    df_sim = pd.read_csv(BASELINE_FILE)
    df_sim['edge_id'] = df_sim['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    simulated_vehs = df_sim[df_sim['edge_id'].isin(ROUTE_257_EDGES)]['vehicle_id'].unique()
    simulated_vehs_str = set(str(v) for v in simulated_vehs)
    
    # Parse XML
    tree = ET.parse(routes_filepath)
    root = tree.getroot()
    route_257_set = set(ROUTE_257_EDGES)
    
    broad_fleet = []
    for veh in root.findall('vehicle'):
        veh_id = veh.get('id')
        if veh_id not in simulated_vehs_str:
            continue
        edges = veh.find('route').get('edges').split()
        # >= 15% overlap means >= 2 edges out of 13
        if len(set(edges).intersection(route_257_set)) >= 2:
            broad_fleet.append(veh_id)
    return broad_fleet

def run_simulation(target_fleet, reroute_percentage, run_name):
    print(f"\n--- Running SUMO Simulation for {run_name} (Percentage: {reroute_percentage * 100}%) ---")
    
    # Select the specific subset of vehicles to reroute (fixed seed)
    np.random.seed(42)
    num_to_reroute = int(len(target_fleet) * reroute_percentage)
    vehs_to_reroute = set(np.random.choice(target_fleet, num_to_reroute, replace=False))
    print(f"Target fleet size: {len(target_fleet)}")
    print(f"Selected vehicles to reroute ({len(vehs_to_reroute)}): {sorted(list(vehs_to_reroute))}")
    
    traci.start([
        "sumo",
        "-c", SUMO_CONFIG,
        "--no-warnings",
        "--no-step-log"
    ])
    
    data = []
    step = 0
    total_steps = 3600
    rerouted_vehicles = set()
    congested_edges = ['1203439472#0', '1203439472#1', '1208491992#0', '1208491992#1']
    
    while step < total_steps:
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()
        
        for vid in vehicles:
            try:
                if vid in vehs_to_reroute and vid not in rerouted_vehicles:
                    route_edges = traci.vehicle.getRoute(vid)
                    start_edge = route_edges[0]
                    end_edge = route_edges[-1]
                    
                    for edge in congested_edges:
                        traci.edge.adaptTraveltime(edge, 9999.0)
                    alt_route = traci.simulation.findRoute(start_edge, end_edge)
                    for edge in congested_edges:
                        traci.edge.adaptTraveltime(edge, 0.0)
                        
                    if alt_route.edges:
                        traci.vehicle.setRoute(vid, list(alt_route.edges))
                        rerouted_vehicles.add(vid)
            except Exception:
                pass
                
            try:
                rec_route = f"!{vid}"
                row = {
                    "time_step": step,
                    "vehicle_id": vid,
                    "route_id": rec_route,
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
                pass
            
        step += 1
        
    traci.close()
    df = pd.DataFrame(data)
    print(f"Simulation finished. Rerouted vehicles count: {len(rerouted_vehicles)}")
    return df

def compute_edge_metrics(df, edges):
    df_edges = df.copy()
    df_edges['edge_id'] = df_edges['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    df_edges = df_edges[df_edges['edge_id'].isin(edges)]
    
    if len(df_edges) == 0:
        return {"avg_speed": 0.0, "total_travel_time": 0.0, "total_co2": 0.0, "total_fuel": 0.0}
        
    avg_speed = df_edges['speed'].mean() * 3.6  # km/h
    total_travel_time = len(df_edges)  # veh-s
    total_co2 = df_edges['co2_emission'].sum() / 1000.0  # g
    total_fuel = df_edges['fuel_consumption'].sum() / 1000.0  # L
    
    return {
        "avg_speed": round(avg_speed, 2),
        "total_travel_time": round(total_travel_time, 2),
        "total_co2": round(total_co2, 2),
        "total_fuel": round(total_fuel, 2)
    }

def run_downstream_pipeline(df):
    fused = sensor_fusion(df)
    cluster = get_route_congestion(fused)
    
    # FAHP
    fahp = calculate_congestion_score(cluster)
    fahp_score = fahp.loc["!257", "congestion_score"]
    fahp_rank = fahp.loc["!257", "rank"]
    
    # Entropy
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster[col])]
    ewm_weights = calculate_entropy_weights(cluster, benefit_cols, cost_cols)
    entropy = calculate_score(cluster, ewm_weights)
    entropy_score = entropy.loc["!257", "score"]
    entropy_rank = entropy.loc["!257", "rank"]
    
    return fahp_score, int(fahp_rank), entropy_score, int(entropy_rank)

def main():
    print("=== SCENARIO B: AUTOMATION OF ALL VARIANTS ===")
    
    # 1. Get fleets
    broad_fleet = get_broad_overlap_fleet()
    print(f"Broad fleet size (>=15% overlap): {len(broad_fleet)}")
    
    df_pre = pd.read_csv(BASELINE_FILE)
    metrics_pre = compute_edge_metrics(df_pre, ROUTE_257_EDGES)
    
    # Define runs
    runs = [
        # (Fleet, percentage, run_name)
        (broad_fleet, 0.50, "Broad_50"),
        (HEAVY_OVERLAP_FLEET, 0.20, "Heavy_20"),
        (HEAVY_OVERLAP_FLEET, 0.80, "Heavy_80")
    ]
    
    results = []
    
    for fleet, pct, name in runs:
        df_post = run_simulation(fleet, pct, name)
        
        # Save trajectory data
        filename = f"simulation/data_output/vehicle_data_rerouted_{name}.csv"
        df_post.to_csv(filename, index=False)
        print(f"Saved trajectory data to {filename}")
        
        # Compute edge metrics
        metrics_post = compute_edge_metrics(df_post, ROUTE_257_EDGES)
        
        # Downstream pipeline
        fahp_score, fahp_rank, ent_score, ent_rank = run_downstream_pipeline(df_post)
        
        results.append({
            "Run": name,
            "Fleet_Size": len(fleet),
            "Rerouted_Pct": pct * 100,
            "Avg_Speed_kmh": metrics_post["avg_speed"],
            "Travel_Time_vehs": metrics_post["total_travel_time"],
            "CO2_g": metrics_post["total_co2"],
            "Fuel_L": metrics_post["total_fuel"],
            "FAHP_Score": round(fahp_score, 4),
            "FAHP_Rank": fahp_rank,
            "Entropy_Score": round(ent_score, 4),
            "Entropy_Rank": ent_rank
        })
        
    df_results = pd.DataFrame(results)
    
    # Add pre-rerouting (baseline) for reference
    # Downstream scores for baseline: FAHP=1580.50 (Rank 1), Entropy=2327.40 (Rank 1)
    baseline_row = {
        "Run": "Baseline",
        "Fleet_Size": 0,
        "Rerouted_Pct": 0.0,
        "Avg_Speed_kmh": metrics_pre["avg_speed"],
        "Travel_Time_vehs": metrics_pre["total_travel_time"],
        "CO2_g": metrics_pre["total_co2"],
        "Fuel_L": metrics_pre["total_fuel"],
        "FAHP_Score": 1580.50,
        "FAHP_Rank": 1,
        "Entropy_Score": 2327.40,
        "Entropy_Rank": 1
    }
    
    df_results = pd.concat([pd.DataFrame([baseline_row]), df_results], ignore_index=True)
    
    print("\n=== FINAL ALL VARIANTS RESULTS TABLE ===")
    print(df_results.to_string(index=False))
    
    df_results.to_csv("simulation/data_output/rerouting_all_variants_comparison.csv", index=False)
    print("\nSaved comparison CSV to simulation/data_output/rerouting_all_variants_comparison.csv")

if __name__ == "__main__":
    main()
