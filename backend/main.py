from fastapi import FastAPI
import requests
import math
from datetime import datetime, timedelta
from ai_agents import SafetyAnalysisAgent

# from test_google_routes import GoogleRoutesAPI
import get_routes
import polyline
import polyline_safety_analysis as p
from constants import SafetyApi

app = FastAPI(title="runsafe-ai", version="0.1.0")

safety_ai = None


def get_safety_ai():
    global safety_ai
    if safety_ai is None:
        try:
            print("Attempting to initialize SafetyAnalysisAgent...")
            safety_ai = SafetyAnalysisAgent()
            print("SafetyAnalysisAgent initialized successfully!")
        except Exception as e:
            print(f"Could not initialize AI agent: {e}")
            print(f"Error type: {type(e)}")
            import traceback

            traceback.print_exc()
            return None
    return safety_ai


def euc_distance(lat1: float, lng1: float, lat2: float, lng2: float):  # utils?
    R = 6371
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


@app.get("/api/crashes/near-me")
def get_crashes_near_me(
    lat: float, lng: float, radius_km: float = 1.0, days_back: int = 60, sapi=SafetyApi
):
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = sapi.URL.value
    params = {
        "$limit": 500,  # bringing in more records
        "$order": "crash_date DESC",
        "$where": f"latitude IS NOT NULL AND longitude IS NOT NULL AND crash_date >= '{cutoff_date}'",
    }
    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            all_crashes = response.json()

            nearby_crashes = []  # filter to within radius
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
                            "location": {"lat": crash_lat, "lng": crash_lng},
                            "injuries": int(crash.get("number_of_persons_injured", 0)),
                            "fatalities": int(crash.get("number_of_persons_killed", 0)),
                        }
                        nearby_crashes.append(clean_crash)
                except (ValueError, TypeError):
                    continue

            # safety summary
            total_crashes = len(nearby_crashes)
            injuries = sum(crash["injuries"] for crash in nearby_crashes)
            total_fatalities = sum(crash["fatalities"] for crash in nearby_crashes)

            return {
                "search_location": {"lat": lat, "lng": lng},
                "search_radius_km": radius_km,
                "days_searched": days_back,
                "summary": {
                    "total_crashes": total_crashes,
                    "total_injuries": injuries,
                    "total_fatalities": total_fatalities,
                    "safety_concern_level": (
                        "Critical"
                        if total_fatalities > 0
                        else (
                            "High"
                            if injuries > 0
                            else "Moderate" if total_crashes >= 3 else "Low"
                        )
                    ),
                },
                "data_source": "NYC Vision Zero / Motor Vehicle Collisions",
            }

        else:
            return {"error": f"NYC API returned status {response.status_code}"}

    except Exception as e:
        return {"error": f"Failed to fetch nearby crashes: {str(e)}"}


@app.get("/api/safety/ai-analysis")
def get_ai_safety_analysis(lat: float, lng: float, target_distance_km: float = 0.5):
    """Get AI-powered safety analysis for runners"""

    # Get the crash data
    running_metadata = generate_running_routes(lat, lng, target_distance_km)

    # Try to get AI analysis
    ai_agent = get_safety_ai()
    if ai_agent:
        ai_insights = ai_agent.crash_data_llm_call(running_metadata)
    else:
        ai_insights = {
            "ai_analysis": "AI analysis temporarily unavailable",
            "recommendations": ["Review crash data manually"],
            "confidence": "low",
        }

    return {
        "location": {"lat": lat, "lng": lng, "radius_km": target_distance_km},
        "ai_insights": ai_insights,
        "powered_by": "GPT-4o-mini + NYC Vision Zero Data",
    }


@app.get("/api/routes/generate")
def generate_running_routes(
    start_lat: float, start_lng: float, target_distance_km: float = 5.0
):
    """Generate routes and get AI recommendations"""

    # Generate routes with safety analysis
    enhanced_routes = p.generate_running_routes_with_polyline_safety(
        start_lat,
        start_lng,
        target_distance_km,
        get_routes.optimized_route_finder,
        get_crashes_near_me,
    )

    # prep metadata for LLM
    route_metadata = {
        "start_location": {"lat": start_lat, "lng": start_lng},
        "target_distance_km": target_distance_km,
        "route_options": enhanced_routes,
    }

    ai_agent = get_safety_ai()
    if ai_agent:
        try:
            ai_recommendations = ai_agent.get_route_recommendations(route_metadata)
        except Exception as e:
            ai_recommendations = {
                "ai_analysis": f"AI analysis failed: {str(e)}",
                "recommended_route": None,
                "confidence": "low",
                "analysis_type": "error",
            }
    else:
        ai_recommendations = {
            "ai_analysis": "AI analysis temporarily unavailable",
            "recommended_route": None,
            "confidence": "low",
            "analysis_type": "unavailable",
        }

    return {
        "location": {
            "coordinates": f"{start_lat}, {start_lng}",
            "target_distance_km": target_distance_km,
        },
        "ai_recommendations": ai_recommendations,
        "routes_analyzed": len(enhanced_routes),
        "powered_by": "GPT-4o-mini + NYC Vision Zero Data",
    }
