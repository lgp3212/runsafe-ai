import polyline  # pip install polyline


def decode_route_polyline(encoded_polyline):
    """Decode Google's polyline to get all route coordinates"""
    if not encoded_polyline:
        return []
    try:
        coordinates = polyline.decode(encoded_polyline)
        return [{"lat": lat, "lng": lng} for lat, lng in coordinates]
    except Exception as e:
        print(f"Error decoding polyline: {e}")
        return []


def sample_route_points(route_points, max_samples=10):
    """Sample points along route to avoid too many API calls"""
    if not route_points or len(route_points) <= max_samples:
        return route_points

    # evenly spacef points
    step = len(route_points) // max_samples
    sampled_points = []

    for i in range(0, len(route_points), step):
        sampled_points.append(
            {
                **route_points[i],
                "route_index": i,
                "route_progress": round(
                    (i / len(route_points)) * 100, 1
                ),  # Percentage along route
            }
        )

    # always include the last point
    if route_points[-1] not in sampled_points:
        sampled_points.append(
            {
                **route_points[-1],
                "route_index": len(route_points) - 1,
                "route_progress": 100.0,
            }
        )

    return sampled_points


def analyze_route_safety_detailed(route, get_crashes_function):
    """
    Comprehensive safety analysis using full route polyline

    Args:
        route: Route dict with 'polyline' field
        get_crashes_function: Function to get crash data (like get_crashes_near_me)

    Returns:
        Enhanced route with detailed safety analysis
    """

    encoded_polyline = route.get("polyline", "")
    route_points = decode_route_polyline(encoded_polyline)

    if not route_points:
        return {
            **route,
            "safety_analysis": {
                "error": "Could not decode route path",
                "overall_safety_score": 50,
                "dangerous_segments": [],
            },
        }

    # sample 5 to avoid lots of api calls
    sample_points = sample_route_points(route_points, max_samples=5)
    segment_analyses = []  # analyze safety at each sample point

    for i, point in enumerate(sample_points):
        print(f"Processing point {i+1}/{len(sample_points)}: {point}")

        # get crash data near this point (smaller radius since we're checking multiple points)
        crashes_response = get_crashes_function(
            point["lat"],
            point["lng"],
            radius_km=0.5,  # WIP - smaller radius since we're sampling along route
            days_back=60,
        )
        print(f"Got crashes response for point {i+1}")
        segment_safety = calculate_safety_score(crashes_response)

        segment_analysis = {
            "point_index": i,
            "route_progress": point.get("route_progress", 0),
            "coordinates": {"lat": point["lat"], "lng": point["lng"]},
            "crashes_nearby": crashes_response["summary"]["total_crashes"],
            "injuries": crashes_response["summary"]["total_injuries"],
            "safety_score": segment_safety,
            "safety_level": get_safety_level(segment_safety),
        }
        segment_analyses.append(segment_analysis)

    # calculate overall route safety metrics
    safety_scores = [seg["safety_score"] for seg in segment_analyses]
    overall_safety = sum(safety_scores) / len(safety_scores)

    dangerous_segments = [seg for seg in segment_analyses if seg["safety_score"] < 60]
    return {
        **route,
        "safety_analysis": {
            "overall_safety_score": round(overall_safety, 1),
            "safety_level": get_safety_level(overall_safety),
            "dangerous_segments": dangerous_segments,
        },
    }


def calculate_safety_score(dict):
    """Calculate safety score from 0-100 based on crash data"""

    summary = dict["summary"]

    total_crashes = summary.get("total_crashes", 0)
    total_injuries = summary.get("total_injuries", 0)
    total_fatalities = summary.get("total_fatalities", 0)

    # start with 100 and subtract points for safety issues
    safety_score = 100
    print("still no error? 3")
    print()
    safety_score -= total_crashes * 25
    safety_score -= total_injuries * 50
    safety_score -= total_fatalities * 75

    # ensure score stays between 0-100
    return max(0, min(100, safety_score))


def get_safety_level(safety_score):
    """Convert numeric safety score to descriptive level"""
    if safety_score >= 85:
        return "Very Safe"
    elif safety_score >= 70:
        return "Safe"
    elif safety_score >= 55:
        return "Moderate Risk"
    elif safety_score >= 40:
        return "Higher Risk"
    else:
        return "High Risk"


def generate_running_routes_with_polyline_safety(
    start_lat, start_lng, target_distance_km, get_routes_function, get_crashes_function
):
    """
    Main function to generate routes with detailed polyline-based safety analysis
    """
    routes = get_routes_function(start_lat, start_lng, target_distance_km)
    if not routes:
        return {}

    enhanced_routes = []
    for route in routes:
        enhanced_route = analyze_route_safety_detailed(route, get_crashes_function)
        enhanced_routes.append(enhanced_route)
    return enhanced_routes
