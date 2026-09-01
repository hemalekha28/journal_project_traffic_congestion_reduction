import pandas as pd
import numpy as np
import scipy.stats as stats
import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fahp import FAHP_WEIGHTS

def run_topsis(df, weights, benefit_cols, cost_cols):
    """Implement TOPSIS algorithm on the given dataframe"""
    features = benefit_cols + cost_cols
    
    # 1. Normalize the decision matrix (Vector Normalization)
    norm_df = df[features].copy()
    for col in features:
        denom = np.sqrt(np.sum(df[col] ** 2))
        if denom == 0:
            norm_df[col] = 0.0
        else:
            norm_df[col] = df[col] / denom
            
    # 2. Multiply by weights
    weighted_df = norm_df.copy()
    for col in features:
        weighted_df[col] = norm_df[col] * weights[col]
        
    # 3. Determine positive ideal (PIS) and negative ideal (NIS) solutions
    pis = {}
    nis = {}
    for col in benefit_cols:
        pis[col] = weighted_df[col].max()
        nis[col] = weighted_df[col].min()
    for col in cost_cols:
        pis[col] = weighted_df[col].min()
        nis[col] = weighted_df[col].max()
        
    # 4. Compute distances
    d_plus = []
    d_minus = []
    closeness = []
    
    for idx, row in weighted_df.iterrows():
        dist_plus = np.sqrt(sum((row[col] - pis[col]) ** 2 for col in features))
        dist_minus = np.sqrt(sum((row[col] - nis[col]) ** 2 for col in features))
        
        c_i = dist_minus / (dist_plus + dist_minus) if (dist_plus + dist_minus) > 0 else 0.0
        
        d_plus.append(dist_plus)
        d_minus.append(dist_minus)
        closeness.append(c_i)
        
    res_df = pd.DataFrame(index=df.index)
    res_df['topsis_score'] = closeness
    # Rank: lowest closeness score (closest to ideal worst/congested) gets rank 1
    res_df['topsis_rank'] = res_df['topsis_score'].rank(ascending=True, method='min').astype(int)
    
    return res_df

def main():
    print("=== TASK 3: THREE-WAY WEIGHTING COMPARISON (TOPSIS) ===")
    
    # 1. Load data
    cluster_file = "cluster_results.csv"
    if not os.path.exists(cluster_file):
        cluster_file = "algorithm/cluster_results.csv"
        
    if not os.path.exists(cluster_file):
        print(f"Error: {cluster_file} not found. Please run fkm_clustering.py first.")
        return
        
    cluster_df = pd.read_csv(cluster_file, index_col=0)
    
    # Define benefit and cost criteria
    benefit_cols = ['speed']
    cost_cols = ['co_emission', 'co2_emission', 'nox_emission', 'fuel_consumption']
    
    # 2. Get FAHP Weights
    fahp_weights = FAHP_WEIGHTS
    print("\nFAHP Weights:")
    for k, v in fahp_weights.items():
        print(f"  {k}: {v}")
        
    # Run TOPSIS with FAHP Weights
    topsis_fahp = run_topsis(cluster_df, fahp_weights, benefit_cols, cost_cols)
    topsis_fahp.rename(columns={'topsis_score': 'TOPSIS_FAHP_score', 'topsis_rank': 'TOPSIS_FAHP_rank'}, inplace=True)
    
    # 3. Load EWM Weights
    ewm_file = "entropy_weights.csv"
    if not os.path.exists(ewm_file):
        ewm_file = "algorithm/entropy_weights.csv"
        
    try:
        ewm_weights_df = pd.read_csv(ewm_file)
        ewm_weights = dict(zip(ewm_weights_df['parameter'], ewm_weights_df['weight']))
        print("\nEntropy weights:")
        for k, v in ewm_weights.items():
            print(f"  {k}: {v:.4f}")
            
        # Run TOPSIS with Entropy Weights
        topsis_entropy = run_topsis(cluster_df, ewm_weights, benefit_cols, cost_cols)
        topsis_entropy.rename(columns={'topsis_score': 'TOPSIS_Entropy_score', 'topsis_rank': 'TOPSIS_Entropy_rank'}, inplace=True)
    except FileNotFoundError:
        print("Warning: entropy_weights.csv not found, skipping Entropy TOPSIS.")
        topsis_entropy = None

    # 4. Load baseline FAHP and Entropy rankings
    comp_file = "weighting_comparison.csv"
    if not os.path.exists(comp_file):
        comp_file = "algorithm/weighting_comparison.csv"
        
    try:
        baseline_comp = pd.read_csv(comp_file, index_col=0)
    except FileNotFoundError:
        print(f"Error: {comp_file} not found. Please run compare_weighting_methods.py first.")
        return
        
    # Combine everything
    combined_ranks = baseline_comp.join(topsis_fahp)
    if topsis_entropy is not None:
        combined_ranks = combined_ranks.join(topsis_entropy)
        
    # Output to TOPSIS comparison CSV
    output_path = "topsis_comparison.csv"
    if "algorithm" in os.getcwd():
        combined_ranks.to_csv(output_path)
    else:
        combined_ranks.to_csv("algorithm/topsis_comparison.csv")
        
    print(f"\nSaved combined ranking comparison to topsis_comparison.csv")
    
    # 5. Analyze and display rankings
    print("\n--- Route Rankings for Key Routes ---")
    key_routes = ["!257", "!341"]
    cols_to_show = ['FAHP_score', 'FAHP_rank', 'entropy_score', 'entropy_rank', 'TOPSIS_FAHP_score', 'TOPSIS_FAHP_rank']
    if topsis_entropy is not None:
        cols_to_show += ['TOPSIS_Entropy_score', 'TOPSIS_Entropy_rank']
        
    print(combined_ranks.loc[key_routes, cols_to_show])
    
    # Confirm/Deny Route !257 and !341 ranks
    t_fahp_rank_257 = combined_ranks.loc["!257", "TOPSIS_FAHP_rank"]
    t_fahp_rank_341 = combined_ranks.loc["!341", "TOPSIS_FAHP_rank"]
    total_routes = len(combined_ranks)
    
    print("\n--- Congestion Hypotheses Validation ---")
    print(f"Route !257 (Target Congested Route):")
    print(f"  - FAHP Rank: {combined_ranks.loc['!257', 'FAHP_rank']}")
    print(f"  - Entropy Rank: {combined_ranks.loc['!257', 'entropy_rank']}")
    print(f"  - TOPSIS (FAHP) Rank: {t_fahp_rank_257}")
    if t_fahp_rank_257 == 1:
        print("  -> CONFIRMED: Route !257 is ranked #1 (most congested) under TOPSIS (FAHP) too.")
    else:
        print(f"  -> DENIED: Route !257 is ranked #{t_fahp_rank_257} under TOPSIS (FAHP).")
        
    print(f"Route !341 (Target Best Route):")
    print(f"  - FAHP Rank: {combined_ranks.loc['!341', 'FAHP_rank']}")
    print(f"  - Entropy Rank: {combined_ranks.loc['!341', 'entropy_rank']}")
    print(f"  - TOPSIS (FAHP) Rank: {t_fahp_rank_341}")
    if t_fahp_rank_341 == total_routes:
        print("  -> CONFIRMED: Route !341 is ranked last (least congested) under TOPSIS (FAHP) too.")
    else:
        print(f"  -> DENIED: Route !341 is ranked #{t_fahp_rank_341} under TOPSIS (FAHP).")

    # 6. Rank Correlation Analysis (Spearman's Rho)
    print("\n--- Spearman Rank Correlation Analysis ---")
    # Correlations between ranks (lower rank = more congested)
    fahp_rank = combined_ranks['FAHP_rank']
    entropy_rank = combined_ranks['entropy_rank']
    topsis_fahp_rank = combined_ranks['TOPSIS_FAHP_rank']
    
    rho_fahp_entropy, p_fahp_entropy = stats.spearmanr(fahp_rank, entropy_rank)
    rho_fahp_topsis, p_fahp_topsis = stats.spearmanr(fahp_rank, topsis_fahp_rank)
    rho_entropy_topsis, p_entropy_topsis = stats.spearmanr(entropy_rank, topsis_fahp_rank)
    
    print(f"FAHP Rank vs Entropy Rank:   rho = {rho_fahp_entropy:.4f} (p-value: {p_fahp_entropy:.4e})")
    print(f"FAHP Rank vs TOPSIS Rank:    rho = {rho_fahp_topsis:.4f} (p-value: {p_fahp_topsis:.4e})")
    print(f"Entropy Rank vs TOPSIS Rank: rho = {rho_entropy_topsis:.4f} (p-value: {p_entropy_topsis:.4e})")
    
    # 7. Print Top 5 / Bottom 5 agreement
    print("\n--- Top 5 Most Congested Routes ---")
    print("FAHP:")
    print(list(combined_ranks.sort_values('FAHP_rank').head(5).index))
    print("Entropy:")
    print(list(combined_ranks.sort_values('entropy_rank').head(5).index))
    print("TOPSIS (FAHP):")
    print(list(combined_ranks.sort_values('TOPSIS_FAHP_rank').head(5).index))
    
    print("\n--- Bottom 5 Least Congested Routes ---")
    print("FAHP:")
    print(list(combined_ranks.sort_values('FAHP_rank', ascending=False).head(5).index))
    print("Entropy:")
    print(list(combined_ranks.sort_values('entropy_rank', ascending=False).head(5).index))
    print("TOPSIS (FAHP):")
    print(list(combined_ranks.sort_values('TOPSIS_FAHP_rank', ascending=False).head(5).index))

if __name__ == "__main__":
    main()
