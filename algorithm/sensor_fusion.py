import numpy as np
import pandas as pd
from scipy import stats


def grubbs_test(data, alpha=0.05):
    """Remove outliers using Grubbs test"""
    n = len(data)
    if n < 3:
        return data

    mean = np.mean(data)
    std = np.std(data, ddof=1)

    if std == 0:
        return data

    g_scores = np.abs(data - mean) / std
    t_crit = stats.t.ppf(1 - alpha / (2 * n), n - 2)
    g_critical = (n - 1) / np.sqrt(n) * np.sqrt(
        t_crit ** 2 / (n - 2 + t_crit ** 2)
    )

    return data[g_scores <= g_critical]


def sensor_fusion(df):
    """
    Fuse multiple sensor readings into a single value.
    Simulates 4 sensors per vehicle by adding small noise
    around the SUMO-reported value, then fuses with Grubbs
    outlier removal + weighted averaging (matches base paper).
    """
    fused_data = []

    parameters = [
        'speed', 'co_emission',
        'co2_emission', 'nox_emission',
        'fuel_consumption'
    ]

    for _, row in df.iterrows():
        fused_row = {
            'vehicle_id': row['vehicle_id'],
            'route_id': row['route_id'],
            'time_step': row['time_step']
        }

        for param in parameters:
            base_value = row[param]

            sensor_readings = np.array([
                base_value + np.random.normal(0, 0.05 * abs(base_value) + 0.001)
                for _ in range(4)
            ])

            clean_readings = grubbs_test(sensor_readings)

            weights = np.ones(len(clean_readings))
            weights = weights / weights.sum()
            fused_value = np.dot(weights, clean_readings)

            fused_row[param] = round(fused_value, 4)

        fused_data.append(fused_row)

    return pd.DataFrame(fused_data)


if __name__ == "__main__":
    df = pd.read_csv("../simulation/data_output/vehicle_data.csv")
    fused_df = sensor_fusion(df)
    fused_df.to_csv("fused_data.csv", index=False)
    print("Sensor fusion complete")
    print(fused_df.head())
