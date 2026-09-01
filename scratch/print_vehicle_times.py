import pandas as pd

ROUTE_257_EDGES = [
    '368732289', '876134933#1', '876134933#2', '1203439472#0', '1203439472#1', 
    '1208491992#0', '1208491992#1', '-506648334#12', '-506648334#11', '-506648334#10', 
    '368732307#0', '368732307#1', '368732307#2'
]

def main():
    print("Loading datasets...")
    df_pre = pd.read_csv("simulation/data_output/vehicle_data.csv")
    df_post = pd.read_csv("simulation/data_output/vehicle_data_rerouted.csv")
    
    # Pre-process
    df_pre['edge_id'] = df_pre['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    df_post['edge_id'] = df_post['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
    
    df_pre_edges = df_pre[df_pre['edge_id'].isin(ROUTE_257_EDGES)]
    df_post_edges = df_post[df_post['edge_id'].isin(ROUTE_257_EDGES)]
    
    # Calculate vehicle durations
    dur_pre = df_pre_edges.groupby('vehicle_id').size().to_dict()
    dur_post = df_post_edges.groupby('vehicle_id').size().to_dict()
    
    # Combine active vehicles
    all_vehs = sorted(list(set(list(dur_pre.keys()) + list(dur_post.keys()))))
    
    print(f"\n=== VEHICLE-LEVEL TIME-ON-EDGE VERIFICATION ===")
    print(f"Total Unique Vehicles on segment: {len(all_vehs)}")
    
    print("\nVehicle ID | Pre-Rerouting Time (s) | Post-Rerouting Time (s) | Change (s)")
    print("-" * 65)
    
    changed_vehs = []
    
    for v in all_vehs:
        t_pre = dur_pre.get(v, 0)
        t_post = dur_post.get(v, 0)
        change = t_post - t_pre
        
        if change != 0:
            changed_vehs.append(v)
            print(f"{v:10d} | {t_pre:21d} | {t_post:22d} | {change:+10d}")
            
    print("-" * 65)
    print(f"Number of vehicles with changed travel time: {len(changed_vehs)}")
    print(f"List of changed vehicles: {changed_vehs}")
    
    print(f"\nTotal edge travel time (Baseline):  {sum(dur_pre.values())} veh-s")
    print(f"Total edge travel time (Rerouted):  {sum(dur_post.values())} veh-s")
    print(f"Net change:                        {sum(dur_post.values()) - sum(dur_pre.values())} veh-s")

if __name__ == "__main__":
    main()
