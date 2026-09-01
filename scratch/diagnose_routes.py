import xml.etree.ElementTree as ET
import os

routes_filepath = "simulation/sumo_config/routes.rou.xml"

def main():
    if not os.path.exists(routes_filepath):
        print(f"Error: {routes_filepath} not found.")
        return

    print("Parsing SUMO routes file...")
    tree = ET.parse(routes_filepath)
    root = tree.getroot()

    # In SUMO routes.rou.xml, vehicles are defined as:
    # <vehicle id="X" depart="Y">
    #     <route edges="..."/>
    # </vehicle>
    # When a route is defined inline, SUMO assigns the route ID "!X" to it.
    
    route_to_vehs = {}
    vehicle_count = 0
    
    for veh in root.findall('vehicle'):
        vehicle_count += 1
        veh_id = veh.get('id')
        
        # Check if the route is defined inline or referenced
        route_elem = veh.find('route')
        if route_elem is not None:
            # Inline route -> route ID is "!vehicle_id"
            route_id = "!" + veh_id
        else:
            # Referenced route -> read the route attribute
            route_id = veh.get('route')
            
        if route_id:
            route_to_vehs.setdefault(route_id, []).append(veh_id)

    print("\n=== DIAGNOSTIC REPORT (Step 1) ===")
    print(f"Total vehicle elements parsed: {vehicle_count}")
    print(f"Total unique route IDs identified: {len(route_to_vehs)}")
    
    # Check if there are any routes with multiple vehicles
    multi_veh_routes = {r: v for r, v in route_to_vehs.items() if len(v) > 1}
    print(f"Routes assigned to > 1 vehicle: {len(multi_veh_routes)}")
    
    # Check specifically for Route !257
    print(f"\nRoute '!257' status:")
    vehs_on_257 = route_to_vehs.get("!257", [])
    print(f"  - Exists in file: {'Yes' if '!257' in route_to_vehs else 'No'}")
    print(f"  - Vehicles assigned: {vehs_on_257}")
    print(f"  - Total vehicle count on Route !257: {len(vehs_on_257)}")
    
    # Print distribution summary
    counts = [len(v) for v in route_to_vehs.values()]
    print(f"\nRoute fleet size distribution:")
    print(f"  - Max vehicles on any route: {max(counts) if counts else 0}")
    print(f"  - Min vehicles on any route: {min(counts) if counts else 0}")
    print(f"  - Number of single-vehicle routes: {counts.count(1)}")

if __name__ == '__main__':
    main()
