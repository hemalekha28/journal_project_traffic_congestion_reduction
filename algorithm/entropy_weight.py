import pandas as pd
import numpy as np
import json

def calculate_entropy_weights(df, benefit_cols, cost_cols):
    """
    Calculate entropy weights purely driven by data variance (objective method),
    unlike FAHP which uses subjective expert pairwise comparisons.
    """
    n = len(df)
    
    # Normalization matrix
    Y = pd.DataFrame(index=df.index, columns=benefit_cols + cost_cols)
    
    # 1. Normalize the data
    # We add a small epsilon to avoid log(0)
    eps = 1e-6
    
    for col in benefit_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max == col_min:
            Y[col] = 1.0 # No variance
        else:
            Y[col] = (df[col] - col_min + eps) / (col_max - col_min + eps * 2)
            
    for col in cost_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max == col_min:
            Y[col] = 1.0
        else:
            Y[col] = (col_max - df[col] + eps) / (col_max - col_min + eps * 2)
            
    # 2. Compute proportions p_ij
    p = Y.div(Y.sum(axis=0), axis=1)
    
    # 3. Compute entropy e_j
    k = 1.0 / np.log(n)
    # p * ln(p)
    p_ln_p = p * np.log(p)
    e = -k * p_ln_p.sum(axis=0)
    
    # 4. Compute degree of divergence d_j
    d = 1 - e
    
    # 5. Compute weights w_j
    w = d / d.sum()
    
    return w.to_dict()

def main():
    print("Running Entropy Weight Method (EWM)...")
    try:
        cluster_df = pd.read_csv("cluster_results.csv", index_col=0)
    except FileNotFoundError:
        print("Error: cluster_results.csv not found.")
        return
        
    benefit_cols = ['speed']
    cost_cols = [col for col in cluster_df.columns if col not in benefit_cols and pd.api.types.is_numeric_dtype(cluster_df[col])]
    
    print(f"Benefit cols: {benefit_cols}")
    print(f"Cost cols: {cost_cols}")
    criteria_df = cluster_df[benefit_cols + cost_cols].copy()
    
    weights = calculate_entropy_weights(criteria_df, benefit_cols, cost_cols)
    
    print("\nCalculated Entropy Weights:")
    for param, weight in weights.items():
        print(f"  {param}: {weight:.4f}")
        
    # Save as CSV so it can be loaded dynamically, similar to how FAHP might be represented
    # Outputting to entropy_weights.csv in two columns: parameter, weight
    weights_df = pd.DataFrame(list(weights.items()), columns=['parameter', 'weight'])
    weights_df.to_csv("entropy_weights.csv", index=False)
    print("\nSaved weights to entropy_weights.csv")

if __name__ == '__main__':
    main()
