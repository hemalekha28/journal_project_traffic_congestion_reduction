import sys
import os

# Test importing the algorithm modules
try:
    from algorithm.sensor_fusion import sensor_fusion
    from algorithm.fkm_clustering import get_route_congestion
    from algorithm.fahp import calculate_congestion_score
    from algorithm.entropy_weight import calculate_entropy_weights
    from algorithm.compare_weighting_methods import calculate_score
    print("All algorithm imports successful!")
except Exception as e:
    print("Import failed:", e)
