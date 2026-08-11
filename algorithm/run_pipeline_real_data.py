import pandas as pd
from fkm_clustering import get_route_congestion
from entropy_weight import calculate_entropy_weights
from compare_weighting_methods import calculate_score

def main():
    print("Running pipeline on real Chicago data...")
    
    # 1. Run FKM Clustering on chicago_prepared.csv
    fused_df = pd.read_csv("../data_ingestion/chicago_prepared.csv")
    cluster_results = get_route_congestion(fused_df)
    
    print("\nReal Data Cluster Results:")
    print(cluster_results.head())
    
    # 2. Run Entropy Weight Method on cluster_results
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster_results.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster_results[col])]
    
    ewm_weights = calculate_entropy_weights(cluster_results, benefit_cols, cost_cols)
    print("\nEWM Weights for Real Data:")
    for param, weight in ewm_weights.items():
        print(f"  {param}: {weight:.4f}")
        
    # 3. Calculate scores
    scores_df = calculate_score(cluster_results, ewm_weights)
    
    print("\nTop 5 Congested Routes (Real Data):")
    print(scores_df.head())
    
    # Output to congestion_results_real_data.csv
    scores_df.to_csv("congestion_results_real_data.csv")
    print("\nSaved final scores to congestion_results_real_data.csv")

if __name__ == '__main__':
    main()
