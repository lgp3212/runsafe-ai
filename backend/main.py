from fastapi import FastAPI
import requests
import math
from datetime import datetime, timedelta
from ai_agents import SafetyAnalysisAgent
#from test_google_routes import GoogleRoutesAPI
import get_routes
import polyline
import polyline_safety_analysis as p

app = FastAPI(title="runsafe-ai", version="0.1.0")
#google_routes = GoogleRoutesAPI()
# safety_ai = SafetyAnalysisAgent() # initialize, get API key

safety_ai = None

def decode_route_polyline(encoded_polyline):
    """Decode Google's polyline to get all route coordinates"""
    if not encoded_polyline:
        return []
    
    try:
        # Decode polyline to list of [lat, lng] coordinates
        coordinates = polyline.decode(encoded_polyline)
        return [{"lat": lat, "lng": lng} for lat, lng in coordinates]
    except Exception as e:
        print(f"Error decoding polyline: {e}")
        return []

def sample_route_points(route_points, max_samples=10):
    """Sample points along route to avoid too many API calls"""
    if not route_points or len(route_points) <= max_samples:
        return route_points
    
    # Take evenly spaced points along the route
    step = len(route_points) // max_samples
    sampled_points = []
    
    for i in range(0, len(route_points), step):
        sampled_points.append({
            **route_points[i],
            "route_index": i,
            "route_progress": round((i / len(route_points)) * 100, 1)  # Percentage along route
        })
    
    # Always include the last point
    if route_points[-1] not in sampled_points:
        sampled_points.append({
            **route_points[-1],
            "route_index": len(route_points) - 1,
            "route_progress": 100.0
        })
    
    return sampled_points

def get_safety_ai():
    global safety_ai
    if safety_ai is None:
        try:
            safety_ai = SafetyAnalysisAgent()
        except Exception as e:
            print(f"Could not initialize AI agent: {e}")
            return None
    return safety_ai

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
    
def euc_distance(lat1: float, lng1: float, lat2: float, lng2: float): # utils?
    R = 6371
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

@app.get("/api/crashes/near-me")
def get_crashes_near_me(lat: float, lng: float, radius_km: float = 1.0, days_back: int = 30):
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
    params = {
        "$limit": 500,  # bringing in more records
        "$order": "crash_date DESC",
        "$where": f"latitude IS NOT NULL AND longitude IS NOT NULL AND crash_date >= '{cutoff_date}'"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            all_crashes = response.json()

            nearby_crashes = [] # filter to within radius
            for crash in all_crashes:
                try: 
                    crash_lat = float(crash.get("latitude", 0))
                    crash_lng = float(crash.get("longitude", 0))

                    distance = euc_distance(lat, lng, crash_lat, crash_lng)

                    if distance <= radius_km:
                        clean_crash = {
                            "crash_id": crash.get("collision_id"),
                            "date": crash.get("crash_date"),
                            "distance_km": round(distance, 2),
                            "location": {
                                "lat": crash_lat,
                                "lng": crash_lng
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
                            },
                            "contributing_factors": [
                                crash.get("contributing_factor_vehicle_1", ""),
                                crash.get("contributing_factor_vehicle_2", "")
                            ]
                        }
                        nearby_crashes.append(clean_crash)
                except (ValueError, TypeError):
                    continue

            # sort by distance
            nearby_crashes.sort(key=lambda x: x["distance_km"]) 

            # safety summary
            total_crashes = len(nearby_crashes)
            pedestrian_injuries = sum(crash["injuries"]["pedestrians"] for crash in nearby_crashes)
            cyclist_injuries = sum(crash["injuries"]["cyclists"] for crash in nearby_crashes)
            total_fatalities = sum(crash["fatalities"]["total"] for crash in nearby_crashes)

            return {
                "search_location": {"lat": lat, "lng": lng},
                "search_radius_km": radius_km,
                "days_searched": days_back,
                "summary": {
                    "total_crashes": total_crashes,
                    "pedestrian_injuries": pedestrian_injuries,
                    "cyclist_injuries": cyclist_injuries,
                    "total_fatalities": total_fatalities,
                    "safety_concern_level": "Critical" if total_fatalities > 0 else "High" if pedestrian_injuries > 0 or cyclist_injuries > 0 else "Moderate" if total_crashes >= 3 else "Low"
                },
                "crashes": nearby_crashes[:20],  # Limit to 20 closest crashes
                "data_source": "NYC Vision Zero / Motor Vehicle Collisions"
            }
        
        else: 
            return {"error": f"NYC API returned status {response.status_code}"}
        
    except Exception as e:
        return {"error": f"Failed to fetch nearby crashes: {str(e)}"}
    
@app.get("/api/safety/ai-analysis")
def get_ai_safety_analysis(lat: float, lng: float, radius_km: float = 0.5):
    """Get AI-powered safety analysis for runners"""
    
    # Get the crash data
    crash_response = get_crashes_near_me(lat, lng, radius_km)
    
    # Try to get AI analysis
    ai_agent = get_safety_ai()
    if ai_agent:
        location_context = f"Location: {lat}, {lng} (radius: {radius_km}km)"
        ai_insights = ai_agent.analyze_crash_data(crash_response, location_context)
    else:
        ai_insights = {
            "ai_analysis": "AI analysis temporarily unavailable",
            "recommendations": ["Review crash data manually"],
            "confidence": "low"
        }
    
    return {
        "location": {"lat": lat, "lng": lng, "radius_km": radius_km},
        "crash_data": crash_response["summary"],
        "ai_insights": ai_insights,
        "powered_by": "GPT-4o-mini + NYC Vision Zero Data"
    }

@app.get("/api/routes/generate")
@app.get("/api/routes/generate")
def generate_running_routes(start_lat: float, start_lng: float, target_distance_km: float = 5.0):
    """Generate routes with detailed polyline-based safety analysis"""
    
    # Use the new polyline-based function
    enhanced_routes = p.generate_running_routes_with_polyline_safety(
        start_lat, 
        start_lng, 
        target_distance_km,
        get_routes.optimized_route_finder,  # Your route generation function
        get_crashes_near_me  # Your crash data function
    )
    
    return {
        "start_location": {"lat": start_lat, "lng": start_lng},
        "target_distance_km": target_distance_km,
        "route_options": enhanced_routes,
        "total_routes_generated": len(enhanced_routes),
        "analysis_method": "Polyline-based safety analysis with 8 sample points per route"
    }

def get_safety_level(safety_score):
    """Convert numeric safety score to descriptive level"""
    if safety_score >= 90:
        return "Very Safe"
    elif safety_score >= 75:
        return "Safe"
    elif safety_score >= 60:
        return "Moderate Risk"
    elif safety_score >= 40:
        return "Higher Risk"
    else:
        return "High Risk"