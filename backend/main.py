from fastapi import FastAPI
import requests

app = FastAPI(title="runsafe-ai", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to RunSafe AI!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/safety/score")
def get_safety_score(lat: float, lng: float):
    # mock data (wip)
    return {
        "location": {"lat": lat, "lng": lng},
        "safety_score": 8,
        "factors": ["high foot traffic", "near police station"],
        "last_updated": "2025-07-21"
    }

@app.post("/api/routes/analyze")
def analyze_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    distance_km = abs(end_lat - start_lat) + abs(end_lng - start_lng) * 100
    # mock data (wip)
    overall_score = 7
    warnings = []
    
    if distance_km > 5:
        warnings.append("long route, consider breaking into segments")
        
    return {
        "route": {
            "start": {"lat": start_lat, "lng": start_lng},
            "end": {"lat": end_lat, "lng": end_lng},
            "estimated_distance_km": round(distance_km, 2) 
        },
        "safety_analysis": {
            "overall_score": overall_score,
            "segment_scores": [8, 6, 7, 9],  # mock data (wip)
            "safe_features": ["well-lit streets", "regular foot traffic"],
            "warnings": warnings,
            "best_time": "6:00 AM - 7:00 AM (peak runner hours)"
        },
        "recommendations": [
            "share your route with a friend",
            "consider running with a partner on this route"
        ]
    }

# replacing the mock data --> real crime data apis, langgraph ai agents, 
    # mapping services, ML models, dynamic recommendations

@app.get("/api/crashes/recent")
def get_recent_crashes(limit: int = 10):
    url = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
    params = {
        "$limit": limit,
        "$order": "crash_date DESC",
        "$where": "latitude IS NOT NULL AND longitude IS NOT NULL"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            crashes = response.json()

            clean_crashes = []
            for crash in crashes:
                clean_crash = {
                    "crash_id": crash.get("collision_id"),
                    "date": crash.get("crash_date"),
                    "location": {
                        "lat": float(crash.get("latitude", 0)),
                        "lng": float(crash.get("longitude", 0))
                    },
                    "street": crash.get("on_street_name", "Unknown"),
                    "borough": crash.get("borough", "Unknown"),
                    "injuries": {
                        "pedestrians": int(crash.get("number_of_pedestrians_injured", 0)),
                        "cyclists": int(crash.get("number_of_cyclist_injured", 0)),
                        "total": int(crash.get("number_of_persons_injured", 0))
                    },
                    "fatalities": {
                        "pedestrians": int(crash.get("number_of_pedestrians_killed", 0)),
                        "cyclists": int(crash.get("number_of_cyclist_killed", 0)),
                        "total": int(crash.get("number_of_persons_killed", 0))
                    }
                }
                clean_crashes.append(clean_crash)
            
            return {
                "total_crashes": len(clean_crashes),
                "data_source": "NYC Vision Zero / Motor Vehicle Collisions",
                "crashes": clean_crashes
            }
        else:
            return {"error": f"NYC API returned status {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}