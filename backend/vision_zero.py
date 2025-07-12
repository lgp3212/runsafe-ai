import pandas as pd
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import math

def explore_nyc_data():
    url = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
    params = {
        "$limit": 20,
        "$order": "crash_date DESC"
    }
    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"Got {len(data)} records")

            records_coord = []
            records_sans_coord = []

            for i, record in enumerate(data):
                has_lat = "latitude" in record and record["latitude"]
                has_lng = "longitude" in record and record["longitude"]

                if has_lat and has_lng:
                    records_coord.append(record)
                    if len(records_coord) <= 3:
                        print(f"📍 Record {i+1} WITH coordinates:")
                        print(f"   Location: {record['latitude']}, {record['longitude']}")
                        print(f"   Date: {record.get('crash_date')}")
                        print(f"   Street: {record.get('on_street_name', 'Unknown')}")
                        print(f"   Pedestrians injured: {record.get('number_of_pedestrians_injured', '0')}")
                        print()
                else:
                    records_sans_coord.append(record)
            print(f"Summary:")
            print(f"   • Records WITH coordinates: {len(records_coord)}")
            print(f"   • Records WITHOUT coordinates: {len(records_sans_coord)}")
        else:
            print(f"Error: {response.status_code}")
    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    explore_nyc_data()
