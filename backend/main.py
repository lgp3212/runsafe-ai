from fastapi import FastAPI
from datetime import datetime, timedelta
from ai_agents import SafetyAnalysisAgent

# from test_google_routes import GoogleRoutesAPI
import get_routes
import polyline_safety_analysis as p

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
        p.get_crashes_near_me,
    )

    # prep metadata for LLM
    route_metadata = {
        "start_location": {"lat": start_lat, "lng": start_lng},
        "target_distance_km": target_distance_km,
        "route_options": enhanced_routes,
    }

    return route_metadata

    """
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
    """
