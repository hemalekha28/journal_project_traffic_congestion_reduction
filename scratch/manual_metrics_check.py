import pandas as pd

ROUTE_257_EDGES = [
    '368732289', '876134933#1', '876134933#2', '1203439472#0', '1203439472#1', 
    '1208491992#0', '1208491992#1', '-506648334#12', '-506648334#11', '-506648334#10', 
    '368732307#0', '368732307#1', '368732307#2'
]

def main():
    print("Loading pre-rerouting data...")
    df_pre = pd.read_csv("simulation/data_output/vehicle_data.csv")
    
    print("Loading post-rerouting data...")
    df_post = pd.read_csv("simulation/data_output/vehicle_data_rerouted.csv")
    
    for label, df in [("PRE (Baseline)", df_pre), ("POST (Rerouted)", df_post)]:
        df['edge_id'] = df['lane_id'].apply(lambda x: str(x).split('_')[0] if pd.notna(x) else '')
        df_edges = df[df['edge_id'].isin(ROUTE_257_EDGES)]
        
        avg_speed = df_edges['speed'].mean() * 3.6
        total_time = len(df_edges)
        total_co2 = df_edges['co2_emission'].sum() / 1000.0
        total_fuel = df_edges['fuel_consumption'].sum() / 1000.0
        
        print(f"\nResults for {label}:")
        print(f"  - Record Count: {len(df_edges)}")
        print(f"  - Average Speed (km/h): {avg_speed:.4f}")
        print(f"  - Total Travel Time (veh-s): {total_time:.4f}")
        print(f"  - Total CO2 (g): {total_co2:.4f}")
        print(f"  - Total Fuel (L): {total_fuel:.4f}")
        
        # Check active vehicles contributing
        vehs = df_edges['vehicle_id'].unique()
        print(f"  - Unique vehicles on these edges: {len(vehs)}")
        # print(f"  - Vehicle IDs: {sorted(list(vehs))}")

if __name__ == "__main__":
    main()
