import os
import sys
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

BASELINE_FAHP_SCORE = 1580.50
BASELINE_ENTROPY_SCORE = 2327.40

VARIANTS = {
    "Heavy_20": "simulation/data_output/vehicle_data_rerouted_Heavy_20.csv",
    "Primary_50": "simulation/data_output/vehicle_data_rerouted.csv",  # The primary run was saved here
    "Heavy_80": "simulation/data_output/vehicle_data_rerouted_Heavy_80.csv",
    "Broad_50": "simulation/data_output/vehicle_data_rerouted_Broad_50.csv"
}

SEEDS = [1, 2, 3, 4, 5]

def run_downstream_pipeline(df, seed):
    # Pass random_seed down to the algorithms
    fused = sensor_fusion(df, random_seed=seed)
    cluster = get_route_congestion(fused, random_seed=seed)
    
    # FAHP
    fahp = calculate_congestion_score(cluster)
    fahp_score = fahp.loc["!257", "congestion_score"]
    
    # Entropy
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster[col])]
    ewm_weights = calculate_entropy_weights(cluster, benefit_cols, cost_cols)
    entropy = calculate_score(cluster, ewm_weights)
    entropy_score = entropy.loc["!257", "score"]
    
    return fahp_score, entropy_score

def main():
    print("=== SEEDED ROBUSTNESS VERIFICATION ===")
    
    results = []
    
    for variant_name, filepath in VARIANTS.items():
        if not os.path.exists(filepath):
            print(f"File not found for {variant_name}: {filepath}")
            continue
            
        print(f"\nProcessing {variant_name}...")
        df = pd.read_csv(filepath)
        
        variant_fahp_scores = []
        variant_entropy_scores = []
        
        for seed in SEEDS:
            # print(f"  Running seed {seed}...")
            fahp_score, entropy_score = run_downstream_pipeline(df, seed=seed)
            variant_fahp_scores.append(fahp_score)
            variant_entropy_scores.append(entropy_score)
            
        mean_fahp = np.mean(variant_fahp_scores)
        std_fahp = np.std(variant_fahp_scores)
        mean_entropy = np.mean(variant_entropy_scores)
        std_entropy = np.std(variant_entropy_scores)
        
        mean_fahp_improv = ((BASELINE_FAHP_SCORE - mean_fahp) / BASELINE_FAHP_SCORE) * 100
        mean_entropy_improv = ((BASELINE_ENTROPY_SCORE - mean_entropy) / BASELINE_ENTROPY_SCORE) * 100
        
        results.append({
            "Variant": variant_name,
            "FAHP_Mean": round(mean_fahp, 2),
            "FAHP_Std": round(std_fahp, 2),
            "FAHP_Improv_%": round(mean_fahp_improv, 2),
            "Entropy_Mean": round(mean_entropy, 2),
            "Entropy_Std": round(std_entropy, 2),
            "Entropy_Improv_%": round(mean_entropy_improv, 2)
        })
        
    df_results = pd.DataFrame(results)
    
    print("\n=== FINAL SEEDED RESULTS ACROSS 5 ITERATIONS ===")
    print(df_results.to_string(index=False))
    
    # Save results
    out_file = "simulation/data_output/seeded_robustness_results.csv"
    df_results.to_csv(out_file, index=False)
    print(f"\nSaved seeded results to {out_file}")

if __name__ == "__main__":
    main()
