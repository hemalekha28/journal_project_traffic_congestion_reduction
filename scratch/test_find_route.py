import traci
import os
import sys

# Ensure Cwd is set correctly
SUMO_CONFIG = "simulation/sumo_config/simulation.sumocfg"

def main():
    print("Testing traci findRoute...")
    traci.start([
        "sumo",
        "-c", SUMO_CONFIG,
        "--no-warnings",
        "--no-step-log"
    ])
    
    # 1. Normal route
    route_normal = traci.simulation.findRoute("368732289", "368732307#2")
    print("Normal route edges:", list(route_normal.edges))
    
    # 2. Penalize congested edges
    congested_edges = ['1203439472#0', '1203439472#1', '1208491992#0', '1208491992#1']
    for edge in congested_edges:
        traci.edge.adaptTraveltime(edge, 9999.0)
        
    route_avoid = traci.simulation.findRoute("368732289", "368732307#2")
    print("Avoid congested edges route:", list(route_avoid.edges))
    
    # Reset
    for edge in congested_edges:
        traci.edge.adaptTraveltime(edge, 0.0)
        
    traci.close()

if __name__ == "__main__":
    main()
