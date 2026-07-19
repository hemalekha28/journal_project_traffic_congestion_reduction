import pandas as pd

def prepare_chicago_data():
    raw_df = pd.read_csv("chicago_raw.csv")
    
    print("Preparing Chicago Traffic Data for Algorithm Pipeline...")
    
    # Check what parameters are available vs original SUMO parameters
    original_sumo_params = ['speed', 'co_emission', 'co2_emission', 'nox_emission', 'fuel_consumption']
    print("\n--- Parameter Mapping ---")
    
    # Speed is available
    if 'speed' in raw_df.columns:
        print("MATCHED: 'speed' exists in both real and simulated data.")
    
    # Missing parameters
    missing = [p for p in original_sumo_params if p != 'speed']
    print(f"NO REAL-DATA EQUIVALENT for: {missing}")
    
    # New real data parameters we can use
    new_params = ['bus_count', 'message_count']
    print(f"NEW REAL-DATA PARAMETERS available for congestion scoring: {new_params}")
    
    # FKM clustering expects a 'route_id' column, and then the numeric parameters.
    # We will map 'segment_id' -> 'route_id'
    # And we fill NaN with 0 or drop them.
    prepared_df = raw_df[['segment_id', 'speed', 'bus_count', 'message_count']].copy()
    prepared_df = prepared_df.rename(columns={'segment_id': 'route_id'})
    
    # Convert types, handle missing
    prepared_df['route_id'] = prepared_df['route_id'].astype(str)
    for col in ['speed', 'bus_count', 'message_count']:
        prepared_df[col] = pd.to_numeric(prepared_df[col], errors='coerce').fillna(0)
        
    # Exclude route_ids with fewer than 3 records (FKM clustering needs >=3 rows)
    counts = prepared_df['route_id'].value_counts()
    valid_routes = counts[counts >= 3].index
    prepared_df = prepared_df[prepared_df['route_id'].isin(valid_routes)]
    
    print(f"\nPrepared {len(prepared_df)} valid records across {len(valid_routes)} segments.")
    
    # Save prepared dataset
    out_path = "chicago_prepared.csv"
    prepared_df.to_csv(out_path, index=False)
    print(f"Saved to {out_path} for FKM clustering.")

if __name__ == '__main__':
    prepare_chicago_data()
