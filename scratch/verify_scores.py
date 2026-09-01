import pandas as pd
import numpy as np
import os
import sys

# Ensure algorithm directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'algorithm')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from algorithm.sensor_fusion import sensor_fusion
from algorithm.fkm_clustering import get_route_congestion
from algorithm.fahp import calculate_congestion_score, FAHP_WEIGHTS
from algorithm.entropy_weight import calculate_entropy_weights
from algorithm.compare_weighting_methods import calculate_score

def main():
    post_file = "simulation/data_output/vehicle_data_rerouted.csv"
    if not os.path.exists(post_file):
        print(f"Error: {post_file} not found.")
        return
        
    print(f"Loading post-rerouting data from {post_file}...")
    df_post = pd.read_csv(post_file)
    
    print("Running Sensor Fusion...")
    fused_post = sensor_fusion(df_post)
    
    print("Running Fuzzy K-Means...")
    cluster_post = get_route_congestion(fused_post)
    
    print("Calculating FAHP scores...")
    fahp_post = calculate_congestion_score(cluster_post)
    
    print("Calculating Entropy weights & scores...")
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster_post.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster_post[col])]
    ewm_weights = calculate_entropy_weights(cluster_post, benefit_cols, cost_cols)
    entropy_post = calculate_score(cluster_post, ewm_weights)
    
    print("\n=== VERIFIED DOWNSTREAM RESULTS (Route !257) ===")
    print("FAHP:")
    print(f"  - Score: {fahp_post.loc['!257', 'congestion_score']}")
    print(f"  - Rank:  {fahp_post.loc['!257', 'rank']} (of {len(fahp_post)})")
    
    print("Entropy:")
    print(f"  - Score: {entropy_post.loc['!257', 'score']}")
    print(f"  - Rank:  {entropy_post.loc['!257', 'rank']} (of {len(entropy_post)})")

if __name__ == "__main__":
    main()
