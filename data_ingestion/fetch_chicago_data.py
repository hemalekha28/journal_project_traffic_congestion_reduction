import pandas as pd
import requests
import time

def fetch_chicago_traffic_data():
    """
    Fetch the most recent 1000 records from the Chicago Traffic Tracker historical segment dataset.
    """
    url = "https://data.cityofchicago.org/resource/4g9f-3jbs.json"
    params = {
        "$limit": 5000,
        "$order": "time DESC"
    }
    
    print(f"Fetching data from {url}...")
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return None
        
    data = response.json()
    df = pd.DataFrame(data)
    
    print("\nData successfully fetched!")
    print("\nActual Schema (Column Names):")
    print(df.columns.tolist())
    
    print("\nSample of 5 rows:")
    print(df.head(5))
    
    # Save raw pull
    output_path = "chicago_raw.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved raw data to {output_path}")

if __name__ == '__main__':
    fetch_chicago_traffic_data()
