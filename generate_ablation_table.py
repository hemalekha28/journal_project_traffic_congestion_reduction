import os
import sys
import time
import json
import pandas as pd
import numpy as np
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score

# Add algorithm directory to sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
algo_dir = os.path.join(base_dir, "algorithm")
if algo_dir not in sys.path:
    sys.path.append(algo_dir)

from fkm_clustering import fuzzy_kmeans
from fahp import calculate_congestion_score
from entropy_weight import calculate_entropy_weights
from compare_weighting_methods import calculate_score

def generate_ablation():
    print("=== TASK 2: GENERATING ABLATION COMPARISON TABLE ===")
    
    cluster_csv = os.path.join(algo_dir, "cluster_results.csv")
    fused_csv = os.path.join(algo_dir, "fused_data.csv")
    
    if not os.path.exists(cluster_csv) or not os.path.exists(fused_csv):
        print(f"Error: Missing {cluster_csv} or {fused_csv}")
        return
        
    cluster_df = pd.read_csv(cluster_csv, index_col=0)
    fused_df = pd.read_csv(fused_csv)
    
    features = ['speed', 'co_emission', 'co2_emission', 'nox_emission', 'fuel_consumption']
    
    rows = []
    
    # ---------------- Row 1: Base Paper (FAHP, 4 routes, SUMO, k=3) ----------------
    routes_4 = ['!0', '!1', '!2', '!3']
    cluster_4 = cluster_df.loc[cluster_df.index.isin(routes_4)]
    fused_4 = fused_df[fused_df['route_id'].isin(routes_4)]
    
    X_4 = StandardScaler().fit_transform(cluster_4[features].values)
    start_time = time.perf_counter()
    centers_4, mem_4 = fuzzy_kmeans(X_4, n_clusters=3, m=2, max_iter=100)
    fahp_scores_4 = calculate_congestion_score(cluster_4)
    t_row1 = time.perf_counter() - start_time
    
    labels_4 = np.argmax(mem_4, axis=1)
    sil_4 = silhouette_score(X_4, labels_4)
    db_4 = davies_bouldin_score(X_4, labels_4)
    
    groups_4 = [fused_4[fused_4['route_id'] == r]['speed'].values for r in routes_4 if len(fused_4[fused_4['route_id'] == r]) > 0]
    f_stat_4, _ = stats.f_oneway(*groups_4)
    
    rows.append({
        "weighting_method": "FAHP (Base Paper)",
        "route_count": 4,
        "data_source": "SUMO",
        "silhouette_score": round(float(sil_4), 4),
        "davies_bouldin_index": round(float(db_4), 4),
        "anova_f_value_speed": round(float(f_stat_4), 4),
        "computation_time_sec": round(float(t_row1), 4)
    })
    
    # ---------------- Row 2: Our Pipeline (FAHP, 359 routes, SUMO) ----------------
    X_359 = StandardScaler().fit_transform(cluster_df[features].values)
    start_time = time.perf_counter()
    centers_359, mem_359 = fuzzy_kmeans(X_359, n_clusters=3, m=2, max_iter=100)
    fahp_scores_359 = calculate_congestion_score(cluster_df)
    t_row2 = time.perf_counter() - start_time
    
    labels_359 = np.argmax(mem_359, axis=1)
    sil_359 = silhouette_score(X_359, labels_359)
    db_359 = davies_bouldin_score(X_359, labels_359)
    
    groups_359 = [fused_df[fused_df['route_id'] == r]['speed'].values for r in cluster_df.index if len(fused_df[fused_df['route_id'] == r]) > 0]
    f_stat_359, _ = stats.f_oneway(*groups_359)
    
    rows.append({
        "weighting_method": "FAHP (Our Pipeline)",
        "route_count": len(cluster_df),
        "data_source": "SUMO",
        "silhouette_score": round(float(sil_359), 4),
        "davies_bouldin_index": round(float(db_359), 4),
        "anova_f_value_speed": round(float(f_stat_359), 4),
        "computation_time_sec": round(float(t_row2), 4)
    })
    
    # ---------------- Row 3: Our Pipeline (Entropy Weighting, 359 routes, SUMO) ----------------
    start_time = time.perf_counter()
    benefit_cols = ['speed']
    cost_cols = [c for c in features if c != 'speed']
    ewm_weights = calculate_entropy_weights(cluster_df[features], benefit_cols, cost_cols)
    ewm_scores_359 = calculate_score(cluster_df, ewm_weights)
    t_row3_scoring = time.perf_counter() - start_time
    t_row3_total = t_row2 + t_row3_scoring
    
    rows.append({
        "weighting_method": "Entropy Weighting (Our Pipeline)",
        "route_count": len(cluster_df),
        "data_source": "SUMO",
        "silhouette_score": round(float(sil_359), 4),
        "davies_bouldin_index": round(float(db_359), 4),
        "anova_f_value_speed": round(float(f_stat_359), 4),
        "computation_time_sec": round(float(t_row3_total), 4)
    })
    
    # Create DataFrame
    ablation_df = pd.DataFrame(rows)
    
    # Save CSV artifact
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    out_csv = os.path.join(results_dir, "ablation_table.csv")
    ablation_df.to_csv(out_csv, index=False)
    
    print(f"\nSaved ablation table to {out_csv}\n")
    
    # Print formatted Markdown table to console
    def df_to_markdown(df):
        headers = df.columns.tolist()
        header_row = "| " + " | ".join(headers) + " |"
        sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append("| " + " | ".join(str(val) for val in row.values) + " |")
        return "\n".join([header_row, sep_row] + data_rows)

    print("### Ablation Comparison Table\n")
    print(df_to_markdown(ablation_df))

if __name__ == "__main__":
    generate_ablation()

