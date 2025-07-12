from fastapi import FastAPI

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