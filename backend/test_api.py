import requests
import sys

BASE_URL = "http://localhost:5000/api"

def test_status():
    print("Testing GET /api/status...")
    response = requests.get(f"{BASE_URL}/status")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("PASS: /api/status returned 200 OK")

def test_congestion():
    print("Testing GET /api/congestion...")
    response = requests.get(f"{BASE_URL}/congestion")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json().get("data", {})
    
    # We expect some routes in the dictionary. Let's just verify it's a dict and has > 0 items.
    assert isinstance(data, dict), "Expected data to be a dictionary of routes"
    assert len(data) > 0, "Expected at least 1 route in data"
    
    for route_id, info in data.items():
        assert "status" in info, f"Route {route_id} missing 'status'"
        assert info["status"] in ["HIGH", "MEDIUM", "LOW"], f"Route {route_id} has invalid status {info['status']}"
    
    print(f"PASS: /api/congestion returned valid data for {len(data)} routes with HIGH/MEDIUM/LOW statuses")
    
    # Get the first route to test the detail endpoint
    first_route_id = list(data.keys())[0]
    return first_route_id

def test_single_route(valid_route_id):
    print(f"Testing GET /api/congestion/{valid_route_id}...")
    response = requests.get(f"{BASE_URL}/congestion/{valid_route_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"PASS: /api/congestion/{valid_route_id} returned 200 OK")
    
    print("Testing GET /api/congestion/route99 (invalid)...")
    response = requests.get(f"{BASE_URL}/congestion/route99")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    print("PASS: /api/congestion/route99 returned 404 Not Found")

def test_refresh():
    print("Testing POST /api/refresh...")
    response = requests.post(f"{BASE_URL}/refresh")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "diff" in data, "Expected diff in response"
    print("PASS: /api/refresh executed pipeline successfully and returned diff.")

if __name__ == "__main__":
    try:
        test_status()
        valid_route = test_congestion()
        test_single_route(valid_route)
        test_refresh()
        print("\nAll tests passed successfully! 🚀")
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\nFAIL: Could not connect to server. Is Flask running on port 5000?")
        sys.exit(1)
