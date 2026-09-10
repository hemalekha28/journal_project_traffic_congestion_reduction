import os
import json
import pandas as pd
from scipy.stats import spearmanr, kendalltau
from fahp import FAHP_WEIGHTS

def calculate_score(route_means_df, weights):
    """Calculate congestion score per route using provided weights"""
    scores = {}
    for route_id, row in route_means_df.iterrows():
        score = sum([
            row[param] * weight
            for param, weight in weights.items()
            if param in row
        ])
        scores[route_id] = round(score, 4)
        
    scores_df = pd.DataFrame.from_dict(
        scores, orient='index', columns=['score']
    )
    scores_df = scores_df.sort_values('score', ascending=False)
    scores_df['rank'] = range(1, len(scores_df) + 1)
    return scores_df

def main():
    # Resolve paths regardless of CWD
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))
    
    cluster_file = os.path.join(base_dir, "cluster_results.csv")
    if not os.path.exists(cluster_file):
        cluster_file = "cluster_results.csv"
        
    cluster_df = pd.read_csv(cluster_file, index_col=0)
    
    # 1. FAHP Scores
    fahp_results = calculate_score(cluster_df, FAHP_WEIGHTS)
    fahp_results.rename(columns={'score': 'FAHP_score', 'rank': 'FAHP_rank'}, inplace=True)
    
    # 2. Entropy Scores
    ewm_file = os.path.join(base_dir, "entropy_weights.csv")
    if not os.path.exists(ewm_file):
        ewm_file = "entropy_weights.csv"
        
    try:
        ewm_weights_df = pd.read_csv(ewm_file)
        ewm_weights = dict(zip(ewm_weights_df['parameter'], ewm_weights_df['weight']))
    except FileNotFoundError:
        print("entropy_weights.csv not found. Please run entropy_weight.py first.")
        return
        
    ewm_results = calculate_score(cluster_df, ewm_weights)
    ewm_results.rename(columns={'score': 'entropy_score', 'rank': 'entropy_rank'}, inplace=True)
    
    # 3. Combine side-by-side
    comparison_df = fahp_results.join(ewm_results)
    comparison_df = comparison_df[['FAHP_score', 'FAHP_rank', 'entropy_score', 'entropy_rank']]
    
    # Output to csv
    out_csv = os.path.join(base_dir, "weighting_comparison.csv")
    comparison_df.to_csv(out_csv)
    print(f"Saved comparison to {out_csv}\n")
    
    print("--- Top 5 Routes Comparison ---")
    print(comparison_df.head(5))
    
    # 4. Check agreement on the most congested route
    fahp_top = comparison_df[comparison_df['FAHP_rank'] == 1].index[0]
    ewm_top = comparison_df[comparison_df['entropy_rank'] == 1].index[0]
    
    print("\n--- Agreement Analysis ---")
    print(f"FAHP Most Congested Route: {fahp_top}")
    print(f"EWM Most Congested Route: {ewm_top}")
    
    if fahp_top == ewm_top:
        print(f"CONCLUSION: Both methods AGREE that route {fahp_top} is the most congested.")
        print("This validates EWM as a viable, data-driven alternative to the subjective FAHP.")
    else:
        print(f"CONCLUSION: The methods DISAGREE on the most congested route.")
        print(f"This is likely due to the difference in weights: FAHP heavily weights speed ({FAHP_WEIGHTS.get('speed', 0)}), while EWM provides a more balanced weighting based on actual data variance.")
        
    # 5. Compute Spearman's rho and Kendall's tau rank correlation
    spearman_res = spearmanr(comparison_df['FAHP_rank'], comparison_df['entropy_rank'])
    kendall_res = kendalltau(comparison_df['FAHP_rank'], comparison_df['entropy_rank'])
    n_routes = len(comparison_df)
    
    rank_metrics = {
        "spearman_rho": float(spearman_res.statistic if hasattr(spearman_res, 'statistic') else spearman_res[0]),
        "spearman_p": float(spearman_res.pvalue if hasattr(spearman_res, 'pvalue') else spearman_res[1]),
        "kendall_tau": float(kendall_res.statistic if hasattr(kendall_res, 'statistic') else kendall_res[0]),
        "kendall_p": float(kendall_res.pvalue if hasattr(kendall_res, 'pvalue') else kendall_res[1]),
        "n_routes": int(n_routes)
    }
    
    results_dir = os.path.join(root_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    json_path = os.path.join(results_dir, "rank_agreement.json")
    
    with open(json_path, 'w') as f:
        json.dump(rank_metrics, f, indent=4)
        
    print(f"\nRank agreement (n={rank_metrics['n_routes']}): Spearman rho={rank_metrics['spearman_rho']:.4f} (p={rank_metrics['spearman_p']:.4e}), Kendall tau={rank_metrics['kendall_tau']:.4f} (p={rank_metrics['kendall_p']:.4e})")

if __name__ == '__main__':
    main()

