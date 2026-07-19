import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def fuzzy_kmeans(data, n_clusters=3, m=2, max_iter=100):
    """Fuzzy K-Means Clustering (matches base paper's FKM formulation)"""
    n_samples = len(data)

    membership = np.random.dirichlet(np.ones(n_clusters), size=n_samples)

    centers = np.zeros((n_clusters, data.shape[1]))

    for iteration in range(max_iter):
        for j in range(n_clusters):
            weights = membership[:, j] ** m
            centers[j] = np.average(data, axis=0, weights=weights)

        new_membership = np.zeros((n_samples, n_clusters))
        for i in range(n_samples):
            for j in range(n_clusters):
                dist_ij = np.linalg.norm(data[i] - centers[j])
                if dist_ij == 0:
                    new_membership[i, :] = 0
                    new_membership[i, j] = 1.0
                    break
                total = sum([
                    (dist_ij / max(np.linalg.norm(data[i] - centers[k]), 1e-10)) ** (2 / (m - 1))
                    for k in range(n_clusters)
                ])
                new_membership[i, j] = 1 / total

        if np.max(np.abs(new_membership - membership)) < 1e-5:
            print(f"Converged at iteration {iteration}")
            membership = new_membership
            break

        membership = new_membership

    return centers, membership


def get_route_congestion(fused_df):
    """Get congestion level per route using FKM"""

    parameters = [
        'speed', 'co_emission',
        'co2_emission', 'nox_emission',
        'fuel_consumption'
    ]

    route_results = {}

    for route_id in fused_df['route_id'].unique():
        route_data = fused_df[fused_df['route_id'] == route_id][parameters].values

        if len(route_data) < 3:
            continue

        scaler = StandardScaler()
        route_scaled = scaler.fit_transform(route_data)

        centers, membership = fuzzy_kmeans(route_scaled, n_clusters=3)

        mean_center = np.mean(centers, axis=0)
        mean_original = scaler.inverse_transform(mean_center.reshape(1, -1))[0]

        route_results[route_id] = {
            param: round(mean_original[i], 4)
            for i, param in enumerate(parameters)
        }

    return pd.DataFrame(route_results).T


if __name__ == "__main__":
    fused_df = pd.read_csv("fused_data.csv")
    results = get_route_congestion(fused_df)
    print("FKM Clustering Results:")
    print(results)
    results.to_csv("cluster_results.csv")
