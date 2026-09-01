import sys
import os
import traci
import pandas as pd
import numpy as np

# Ensure algorithm directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'algorithm')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from algorithm.sensor_fusion import sensor_fusion
from algorithm.fkm_clustering import get_route_congestion
from algorithm.fahp import calculate_congestion_score
from algorithm.entropy_weight import calculate_entropy_weights
from algorithm.compare_weighting_methods import calculate_score

SUMO_CONFIG = "simulation/sumo_config/simulation.sumocfg"
BASELINE_FILE = "simulation/data_output/vehicle_data.csv"
REROUTED_FILE = "simulation/data_output/vehicle_data_rerouted.csv"

# Route !257 original edges (physical road segment)
ROUTE_257_EDGES = [
    '368732289', '876134933#1', '876134933#2', '1203439472#0', '1203439472#1', 
    '1208491992#0', '1208491992#1', '-506648334#12', '-506648334#11', '-506648334#10', 
    '368732307#0', '368732307#1', '368732307#2'
]

# The 16 heavy-overlap vehicles (>= 30% overlap)
HEAVY_OVERLAP_FLEET = [257, 29, 167, 166, 58, 143, 99, 332, 317, 95, 112, 85, 170, 168, 308, 344]
HEAVY_OVERLAP_FLEET_STR = [str(v) for v in HEAVY_OVERLAP_FLEET]

def run_simulation(reroute_percentage=0.50):
    print(f"\n--- Running SUMO Simulation (Reroute Percentage: {reroute_percentage * 100}%) ---")
    
    # 1. Select the specific subset of vehicles to reroute
    # Using fixed seed for deterministic reproducibility
    np.random.seed(42)
    num_to_reroute = int(len(HEAVY_OVERLAP_FLEET_STR) * reroute_percentage)
    vehs_to_reroute = set(np.random.choice(HEAVY_OVERLAP_FLEET_STR, num_to_reroute, replace=False))
    print(f"Total target fleet size (>=30% overlap): {len(HEAVY_OVERLAP_FLEET_STR)}")
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
    
    # We penalize the key congested edges to force findRoute to avoid them
    congested_edges = ['1203439472#0', '1203439472#1', '1208491992#0', '1208491992#1']
    
    while step < total_steps:
        traci.simulationStep()
        vehicles = traci.vehicle.getIDList()
        
        for vid in vehicles:
            try:
                # Check if this vehicle is in our reroute list and hasn't been rerouted yet
                if vid in vehs_to_reroute and vid not in rerouted_vehicles:
                    route_edges = traci.vehicle.getRoute(vid)
                    start_edge = route_edges[0]
                    end_edge = route_edges[-1]
                    
                    # Temporarily set high travel times on congested edges
                    for edge in congested_edges:
                        traci.edge.adaptTraveltime(edge, 9999.0)
                        
                    # Find alternative route avoiding the bottleneck
                    alt_route = traci.simulation.findRoute(start_edge, end_edge)
                    
                    # Reset travel times
                    for edge in congested_edges:
                        traci.edge.adaptTraveltime(edge, 0.0)
                        
                    if alt_route.edges:
                        traci.vehicle.setRoute(vid, list(alt_route.edges))
                        rerouted_vehicles.add(vid)
                        # Print when a vehicle is successfully rerouted
                        if vid == "257":
                            print(f"Step {step}: Rerouted vehicle {vid} (Route !257 original) to alternative: {list(alt_route.edges)}")
                        else:
                            print(f"Step {step}: Rerouted fleet vehicle {vid}")
                    else:
                        rerouted_vehicles.add(vid) # mark checked
                        
            except Exception as e:
                # print(f"Error rerouting vehicle {vid}: {e}")
                pass
                
            try:
                # Keep recorded route ID as !vid to stay compatible with FKM pipeline
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
                
        if step % 1000 == 0:
            print(f"Step {step}/{total_steps} | Vehicles: {len(vehicles)} | Records: {len(data)}")
            
        step += 1
        
    traci.close()
    df = pd.DataFrame(data)
    print(f"Simulation finished. Generated {len(df)} records. Total vehicles rerouted: {len(rerouted_vehicles)}")
    return df

def compute_edge_metrics(df, edges):
    df_edges = df.copy()
    df_edges['edge_id'] = df_edges['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    df_edges = df_edges[df_edges['edge_id'].isin(edges)]
    
    if len(df_edges) == 0:
        return {
            "avg_speed": 0.0,
            "total_travel_time": 0.0,
            "total_co2": 0.0,
            "total_fuel": 0.0
        }
        
    avg_speed = df_edges['speed'].mean() * 3.6  # convert m/s to km/h
    total_travel_time = len(df_edges)  # count of records = vehicle-seconds
    total_co2 = df_edges['co2_emission'].sum() / 1000.0  # mg to g
    total_fuel = df_edges['fuel_consumption'].sum() / 1000.0  # ml to L
    
    return {
        "avg_speed": round(avg_speed, 2),
        "total_travel_time": round(total_travel_time, 2),
        "total_co2": round(total_co2, 2),
        "total_fuel": round(total_fuel, 2)
    }

def main():
    print("=== TASK 1: SCENARIO B - FLEET REROUTING VALIDATION (50% of 16-vehicle target) ===")
    
    # 1. Load baseline (pre-rerouting) data
    if os.path.exists(BASELINE_FILE):
        print(f"Loading existing baseline data from {BASELINE_FILE}")
        df_pre = pd.read_csv(BASELINE_FILE)
    else:
        print(f"Error: baseline data not found at {BASELINE_FILE}")
        return
        
    # 2. Run simulation with 50% fleet rerouting
    df_post = run_simulation(reroute_percentage=0.50)
    os.makedirs(os.path.dirname(REROUTED_FILE), exist_ok=True)
    df_post.to_csv(REROUTED_FILE, index=False)
    print(f"Post-rerouting data saved to {REROUTED_FILE}")
    
    # 3. Compute metrics on Route !257 edges (aggregating all active traffic on those edges)
    metrics_pre = compute_edge_metrics(df_pre, ROUTE_257_EDGES)
    metrics_post = compute_edge_metrics(df_post, ROUTE_257_EDGES)
    
    # 4. Create comparison table
    comparison_data = []
    for metric, key in [
        ("Average Speed (km/h)", "avg_speed"),
        ("Total Travel Time (veh-s)", "total_travel_time"),
        ("Total CO2 Emission (g)", "total_co2"),
        ("Total Fuel Consumption (L)", "total_fuel")
    ]:
        val_pre = metrics_pre[key]
        val_post = metrics_post[key]
        pct_change = ((val_post - val_pre) / val_pre) * 100 if val_pre > 0 else 0
            
        comparison_data.append({
            "Metric": metric,
            "Pre-Rerouting (Baseline)": val_pre,
            "Post-Rerouting": val_post,
            "Percentage Change (%)": round(pct_change, 2)
        })
        
    df_compare = pd.DataFrame(comparison_data)
    print("\n--- Route !257 Bottleneck Edges Before/After Comparison Table ---")
    print(df_compare.to_string(index=False))
    
    # 5. Run downstream scoring to show Route !257 score and rank drop
    print("\nRunning downstream pipeline on post-rerouting data...")
    # A. Sensor Fusion
    print("  Running Sensor Fusion...")
    fused_post = sensor_fusion(df_post)
    # B. FKM Clustering
    print("  Running Fuzzy K-Means Clustering...")
    cluster_post = get_route_congestion(fused_post)
    
    # C. FAHP Scores
    print("  Calculating FAHP scores...")
    fahp_post = calculate_congestion_score(cluster_post)
    fahp_post_score = fahp_post.loc["!257", "congestion_score"]
    fahp_post_rank = fahp_post.loc["!257", "rank"]
    
    # D. Entropy Scores
    print("  Calculating Entropy weights & scores...")
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster_post.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster_post[col])]
    ewm_weights = calculate_entropy_weights(cluster_post, benefit_cols, cost_cols)
    entropy_post = calculate_score(cluster_post, ewm_weights)
    entropy_post_score = entropy_post.loc["!257", "score"]
    entropy_post_rank = entropy_post.loc["!257", "rank"]
    
    print("\n--- Route !257 Congestion Score & Rank Comparison ---")
    score_comparison = pd.DataFrame([
        {
            "Method": "FAHP Score",
            "Pre-Rerouting": 1580.5,
            "Post-Rerouting": fahp_post_score,
            "Improvement (%)": round(((1580.5 - fahp_post_score) / 1580.5) * 100, 2)
        },
        {
            "Method": "FAHP Rank",
            "Pre-Rerouting": "1 (of 359)",
            "Post-Rerouting": f"{fahp_post_rank} (of 359)",
            "Improvement": "Rank Change"
        },
        {
            "Method": "Entropy Score",
            "Pre-Rerouting": 2327.4,
            "Post-Rerouting": entropy_post_score,
            "Improvement (%)": round(((2327.4 - entropy_post_score) / 2327.4) * 100, 2)
        },
        {
            "Method": "Entropy Rank",
            "Pre-Rerouting": "1 (of 359)",
            "Post-Rerouting": f"{entropy_post_rank} (of 359)",
            "Improvement": "Rank Change"
        }
    ])
    print(score_comparison.to_string(index=False))

if __name__ == "__main__":
    main()
