import pandas as pd

# FAHP weights taken from base paper (Mohanty et al. 2025, Table 11)
# Speed carries the highest priority weight, then fuel consumption.
FAHP_WEIGHTS = {
    'speed': 0.6098,
    'fuel_consumption': 0.2521,
    'co2_emission': 0.0802,
    'nox_emission': 0.0425,
    'co_emission': 0.0154
}


def calculate_congestion_score(route_means_df):
    """Calculate congestion score per route using FAHP weights"""

    scores = {}

    for route_id, row in route_means_df.iterrows():
        score = sum([
            row[param] * weight
            for param, weight in FAHP_WEIGHTS.items()
            if param in row
        ])
        scores[route_id] = round(score, 4)

    scores_df = pd.DataFrame.from_dict(
        scores, orient='index', columns=['congestion_score']
    )
    scores_df = scores_df.sort_values('congestion_score', ascending=False)
    scores_df['rank'] = range(1, len(scores_df) + 1)
    scores_df['status'] = scores_df['congestion_score'].apply(
        lambda x: 'HIGH' if x > scores_df['congestion_score'].quantile(0.66)
        else ('MEDIUM' if x > scores_df['congestion_score'].quantile(0.33)
        else 'LOW')
    )

    return scores_df


if __name__ == "__main__":
    cluster_df = pd.read_csv("cluster_results.csv", index_col=0)
    result = calculate_congestion_score(cluster_df)
    print("\nFAHP Congestion Results:")
    print(result)
    result.to_csv("congestion_results.csv")
