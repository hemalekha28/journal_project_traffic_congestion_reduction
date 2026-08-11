import pandas as pd
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
    cluster_df = pd.read_csv("cluster_results.csv", index_col=0)
    
    # 1. FAHP Scores
    fahp_results = calculate_score(cluster_df, FAHP_WEIGHTS)
    fahp_results.rename(columns={'score': 'FAHP_score', 'rank': 'FAHP_rank'}, inplace=True)
    
    # 2. Entropy Scores
    try:
        ewm_weights_df = pd.read_csv("entropy_weights.csv")
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
    comparison_df.to_csv("weighting_comparison.csv")
    print("Saved comparison to weighting_comparison.csv\n")
    
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
        
if __name__ == '__main__':
    main()
