import time
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score
import sys
import os

# Adjust path to import fuzzy_kmeans
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fkm_clustering import fuzzy_kmeans

def run_comparison():
    print("=== TASK 2: BASELINE CLUSTERING COMPARISON ===")
    
    # 1. Load the per-route cluster results
    # We use cluster_results.csv which represents the per-route feature set
    cluster_file = "cluster_results.csv"
    if not os.path.exists(cluster_file):
        # try running from root directory path
        cluster_file = "algorithm/cluster_results.csv"
        
    if not os.path.exists(cluster_file):
        print(f"Error: {cluster_file} not found. Please run fkm_clustering.py first.")
        return
        
    print(f"Loading data from {cluster_file}...")
    df = pd.read_csv(cluster_file, index_col=0)
    
    # Extract numerical features used for clustering
    features = ['speed', 'co_emission', 'co2_emission', 'nox_emission', 'fuel_consumption']
    X = df[features].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    results = []
    
    # ------------------ 1. Fuzzy K-Means (FKM) ------------------
    print("Running Fuzzy K-Means...")
    start_time = time.perf_counter()
    # run FKM (k=3)
    centers, membership = fuzzy_kmeans(X_scaled, n_clusters=3, m=2, max_iter=100)
    fkm_time = (time.perf_counter() - start_time) * 1000
    
    # Convert soft membership to hard labels for validation metrics
    fkm_labels = np.argmax(membership, axis=1)
    
    # Compute metrics
    fkm_sil = silhouette_score(X_scaled, fkm_labels)
    fkm_db = davies_bouldin_score(X_scaled, fkm_labels)
    
    results.append({
        "Method": "Fuzzy K-Means (FKM)",
        "Silhouette Score": round(fkm_sil, 4),
        "Davies-Bouldin Index": round(fkm_db, 4),
        "Cluster Count": 3,
        "Runtime (ms)": round(fkm_time, 2)
    })
    
    # ------------------ 2. KMeans ------------------
    print("Running standard KMeans...")
    start_time = time.perf_counter()
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    kmeans_time = (time.perf_counter() - start_time) * 1000
    
    kmeans_labels = kmeans.labels_
    kmeans_sil = silhouette_score(X_scaled, kmeans_labels)
    kmeans_db = davies_bouldin_score(X_scaled, kmeans_labels)
    
    results.append({
        "Method": "K-Means",
        "Silhouette Score": round(kmeans_sil, 4),
        "Davies-Bouldin Index": round(kmeans_db, 4),
        "Cluster Count": 3,
        "Runtime (ms)": round(kmeans_time, 2)
    })
    
    # ------------------ 3. Gaussian Mixture Model (GMM) ------------------
    print("Running Gaussian Mixture Model (GMM)...")
    start_time = time.perf_counter()
    gmm = GaussianMixture(n_components=3, random_state=42)
    gmm.fit(X_scaled)
    gmm_time = (time.perf_counter() - start_time) * 1000
    
    gmm_labels = gmm.predict(X_scaled)
    gmm_sil = silhouette_score(X_scaled, gmm_labels)
    gmm_db = davies_bouldin_score(X_scaled, gmm_labels)
    
    results.append({
        "Method": "Gaussian Mixture Model (GMM)",
        "Silhouette Score": round(gmm_sil, 4),
        "Davies-Bouldin Index": round(gmm_db, 4),
        "Cluster Count": 3,
        "Runtime (ms)": round(gmm_time, 2)
    })
    
    # ------------------ 4. DBSCAN ------------------
    print("Tuning DBSCAN via grid search...")
    # Tune eps and min_samples
    best_sil = -1
    best_eps = 0.5
    best_min_samples = 5
    best_labels = None
    best_n_clusters = 0
    best_db_val = 0
    
    # Grid search loop
    for eps in np.linspace(0.1, 2.0, 20):
        for min_samples in range(2, 11):
            db = DBSCAN(eps=eps, min_samples=min_samples)
            labels = db.fit_predict(X_scaled)
            
            unique_labels = set(labels)
            n_clusters = len(unique_labels - {-1})
            
            if n_clusters > 1:
                # Calculate silhouette score on non-noise samples
                mask = labels != -1
                if np.sum(mask) > n_clusters:
                    score = silhouette_score(X_scaled[mask], labels[mask])
                    if score > best_sil:
                        best_sil = score
                        best_eps = eps
                        best_min_samples = min_samples
                        best_labels = labels
                        best_n_clusters = n_clusters
                        best_db_val = davies_bouldin_score(X_scaled[mask], labels[mask])
                        
    if best_labels is None:
        print("DBSCAN did not find a valid clustering during grid search. Using default parameters.")
        db = DBSCAN(eps=0.5, min_samples=5)
        best_labels = db.fit_predict(X_scaled)
        best_n_clusters = len(set(best_labels) - {-1})
        mask = best_labels != -1
        best_sil = silhouette_score(X_scaled[mask], best_labels[mask]) if best_n_clusters > 1 else -1.0
        best_db_val = davies_bouldin_score(X_scaled[mask], best_labels[mask]) if best_n_clusters > 1 else -1.0
    
    print(f"Optimal DBSCAN parameters found: eps={best_eps:.2f}, min_samples={best_min_samples} | Clusters={best_n_clusters}")
    
    # Measure optimal DBSCAN runtime
    start_time = time.perf_counter()
    db_optimal = DBSCAN(eps=best_eps, min_samples=best_min_samples)
    db_optimal.fit(X_scaled)
    db_time = (time.perf_counter() - start_time) * 1000
    
    results.append({
        "Method": "DBSCAN",
        "Silhouette Score": round(best_sil, 4),
        "Davies-Bouldin Index": round(best_db_val, 4),
        "Cluster Count": best_n_clusters,
        "Runtime (ms)": round(db_time, 2)
    })
    
    # ------------------ Output Results ------------------
    df_compare = pd.DataFrame(results)
    print("\n--- Clustering Algorithm Comparison Table ---")
    print(df_compare.to_string(index=False))
    
    # Save comparison to CSV
    output_path = "clustering_comparison.csv"
    if "algorithm" in os.getcwd():
        df_compare.to_csv(output_path, index=False)
    else:
        df_compare.to_csv("algorithm/clustering_comparison.csv", index=False)
        
    print(f"\nSaved comparative table to algorithm/clustering_comparison.csv")

if __name__ == "__main__":
    run_comparison()
