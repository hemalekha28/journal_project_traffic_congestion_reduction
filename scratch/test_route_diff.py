import xml.etree.ElementTree as ET
import traci
import os

SUMO_CONFIG = "simulation/sumo_config/simulation.sumocfg"
routes_filepath = "simulation/sumo_config/routes.rou.xml"

congested_edges = ['1203439472#0', '1203439472#1', '1208491992#0', '1208491992#1']
heavy_fleet = ['257', '29', '167', '166', '58', '143', '99', '332', '317', '95', '112', '85', '170', '168', '308', '344']

def main():
    if not os.path.exists(routes_filepath):
        print(f"Error: {routes_filepath} not found.")
        return

    # Parse XML routes
    tree = ET.parse(routes_filepath)
    root = tree.getroot()
    
    veh_routes = {}
    for veh in root.findall('vehicle'):
        vid = veh.get('id')
        if vid in heavy_fleet:
            route_elem = veh.find('route')
            if route_elem is not None:
                veh_routes[vid] = route_elem.get('edges').split()

    traci.start([
        "sumo",
        "-c", SUMO_CONFIG,
        "--no-warnings",
        "--no-step-log"
    ])
    
    for vid in heavy_fleet:
        route = veh_routes[vid]
        start = route[0]
        end = route[-1]
        
        orig_congested = [e for e in route if e in congested_edges]
        
        # Penalize congested edges
        for e in congested_edges:
            traci.edge.adaptTraveltime(e, 9999.0)
            
        alt_route = list(traci.simulation.findRoute(start, end).edges)
        
        # Reset travel times
        for e in congested_edges:
            traci.edge.adaptTraveltime(e, 0.0)
            
        alt_congested = [e for e in alt_route if e in congested_edges]
        
        print(f"Veh {vid}:")
        print(f"  Orig: len {len(route)}, congested: {orig_congested}")
        print(f"  Alt:  len {len(alt_route)}, congested: {alt_congested}")
        
    traci.close()

if __name__ == "__main__":
    main()
