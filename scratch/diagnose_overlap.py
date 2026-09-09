import xml.etree.ElementTree as ET
import os
import pandas as pd
import numpy as np

routes_filepath = "simulation/sumo_config/routes.rou.xml"
vehicle_data_path = "simulation/data_output/vehicle_data.csv"

# Route !257 edges
ROUTE_257_EDGES = [
    '368732289', '876134933#1', '876134933#2', '1203439472#0', '1203439472#1', 
    '1208491992#0', '1208491992#1', '-506648334#12', '-506648334#11', '-506648334#10', 
    '368732307#0', '368732307#1', '368732307#2'
]

def main():
    if not os.path.exists(routes_filepath):
        print(f"Error: {routes_filepath} not found.")
        return
    if not os.path.exists(vehicle_data_path):
        print(f"Error: {vehicle_data_path} not found.")
        return

    # 1. Identify vehicles that actually traversed these edges in the baseline simulation
    df_sim = pd.read_csv(vehicle_data_path)
    df_sim['edge_id'] = df_sim['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    simulated_vehs = df_sim[df_sim['edge_id'].isin(ROUTE_257_EDGES)]['vehicle_id'].unique()
    simulated_vehs_str = set(str(v) for v in simulated_vehs)
    
    # 2. Parse XML to get their full route overlap
    tree = ET.parse(routes_filepath)
    root = tree.getroot()

    route_257_set = set(ROUTE_257_EDGES)
    num_route_257_edges = len(ROUTE_257_EDGES)

    vehicle_data = []

    for veh in root.findall('vehicle'):
        veh_id = veh.get('id')
        
        # Only process active vehicles that actually traversed Route !257 edges in simulation
        if veh_id not in simulated_vehs_str:
            continue
            
        route_elem = veh.find('route')
        if route_elem is not None:
            edges = route_elem.get('edges').split()
        else:
            continue
            
        veh_edges_set = set(edges)
        intersection = veh_edges_set.intersection(route_257_set)
        
        overlap_count = len(intersection)
        fraction_of_257 = overlap_count / num_route_257_edges
        fraction_of_veh = overlap_count / len(edges)
        
        vehicle_data.append({
            "vehicle_id": int(veh_id),
            "total_edges_in_trip": len(edges),
            "overlapping_edges_count": overlap_count,
            "fraction_of_257_edges": round(fraction_of_257, 4),
            "fraction_of_veh_edges": round(fraction_of_veh, 4)
        })

    df = pd.DataFrame(vehicle_data)
    df = df.sort_values(by="fraction_of_257_edges", ascending=False)
    
    print("\n=== STEP 1 DIAGNOSTIC REPORT: ACTIVE FLEET OVERLAP ANALYSIS ===")
    print(f"Route !257 Edge Count: {num_route_257_edges}")
    print(f"Total active vehicles traversing Route !257 edges during simulation: {len(df)}")
    
    # Overlap thresholds
    v_50 = df[df['fraction_of_257_edges'] >= 0.50]
    v_30 = df[df['fraction_of_257_edges'] >= 0.30]
    v_15 = df[df['fraction_of_257_edges'] >= 0.15]
    
    print(f"\nActive vehicles sharing >= 50% of !257 edges (>= 7 edges): {len(v_50)}")
    print(f"Active vehicles sharing >= 30% of !257 edges (>= 4 edges): {len(v_30)}")
    print(f"Active vehicles sharing >= 15% of !257 edges (>= 2 edges): {len(v_15)}")
    
    print("\n--- Summary Statistics for Active Fleet Overlap ---")
    print("1. Fraction of Route !257 edges shared by active vehicles:")
    print(f"   - Min:  {df['fraction_of_257_edges'].min() * 100:.2f}% ({df['overlapping_edges_count'].min()} edges)")
    print(f"   - Max:  {df['fraction_of_257_edges'].max() * 100:.2f}% ({df['overlapping_edges_count'].max()} edges)")
    print(f"   - Mean: {df['fraction_of_257_edges'].mean() * 100:.2f}% ({df['overlapping_edges_count'].mean():.2f} edges)")
    
    print("2. Fraction of active vehicle's own route that overlaps with !257's edges:")
    print(f"   - Min:  {df['fraction_of_veh_edges'].min() * 100:.2f}%")
    print(f"   - Max:  {df['fraction_of_veh_edges'].max() * 100:.2f}%")
    print(f"   - Mean: {df['fraction_of_veh_edges'].mean() * 100:.2f}%")
    
    print("\n--- Top 20 Active Vehicles by Overlap ---")
    print(df.head(20).to_string(index=False))

    print("\n--- Full List of Active Vehicle IDs ---")
    print(sorted(df['vehicle_id'].tolist()))

if __name__ == '__main__':
    main()
