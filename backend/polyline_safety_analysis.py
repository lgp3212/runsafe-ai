import polyline  # pip install polyline
import math

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

def analyze_route_safety_detailed(route, get_crashes_function):
    """
    Comprehensive safety analysis using full route polyline
    
    Args:
        route: Route dict with 'polyline' field
        get_crashes_function: Function to get crash data (like get_crashes_near_me)
    
    Returns:
        Enhanced route with detailed safety analysis
    """
    
    # Decode the polyline to get all route points
    encoded_polyline = route.get('polyline', '')
    route_points = decode_route_polyline(encoded_polyline)
    
    if not route_points:
        return {
            **route,
            "safety_analysis": {
                "error": "Could not decode route path",
                "overall_safety_score": 50,  # Neutral score
                "safety_level": "Unknown"
            }
        }
    
    print(f"   🗺️  Analyzing {len(route_points)} points along {route.get('direction', 'Unknown')} route")
    
    # Sample points to avoid too many API calls (max 8-10 points)
    sample_points = sample_route_points(route_points, max_samples=8)
    
    print(f"   📍 Checking safety at {len(sample_points)} key points along route")
    
    # Analyze safety at each sample point
    segment_analyses = []
    all_crashes = []
    
    for i, point in enumerate(sample_points):
        # Get crash data near this point (smaller radius since we're checking multiple points)
        crashes_response = get_crashes_function(
            point["lat"], 
            point["lng"], 
            radius_km=0.3,  # Smaller radius since we're sampling along route
            days_back=30
        )
        
        # Calculate safety score for this segment
        segment_safety = calculate_safety_score(crashes_response["summary"], {})
        
        segment_analysis = {
            "point_index": i,
            "route_progress": point.get("route_progress", 0),
            "coordinates": {"lat": point["lat"], "lng": point["lng"]},
            "crashes_nearby": crashes_response["summary"]["total_crashes"],
            "pedestrian_injuries": crashes_response["summary"]["pedestrian_injuries"],
            "safety_score": segment_safety,
            "safety_level": get_safety_level(segment_safety)
        }
        
        segment_analyses.append(segment_analysis)
        all_crashes.extend(crashes_response["crashes"])
        
        print(f"      Point {i+1}: {segment_safety:.0f}/100 safety score ({crashes_response['summary']['total_crashes']} crashes)")
    
    # Calculate overall route safety metrics
    safety_scores = [seg["safety_score"] for seg in segment_analyses]
    overall_safety = sum(safety_scores) / len(safety_scores)
    min_safety = min(safety_scores)
    max_safety = max(safety_scores)
    
    # Identify dangerous segments (below 60 safety score)
    dangerous_segments = [seg for seg in segment_analyses if seg["safety_score"] < 60]
    
    # Get AI analysis for the entire route
    combined_crash_summary = {
        "total_crashes": sum(seg["crashes_nearby"] for seg in segment_analyses),
        "pedestrian_injuries": sum(seg["pedestrian_injuries"] for seg in segment_analyses),
        "cyclist_injuries": 0,  # Would need to extract from crashes if needed
        "total_fatalities": 0   # Would need to extract from crashes if needed
    }
    
    return {
        **route,
        "route_analysis": {
            "total_route_points": len(route_points),
            "analyzed_segments": len(segment_analyses),
            "route_length_km": route.get('actual_distance_km', 0)
        },
        "safety_analysis": {
            "overall_safety_score": round(overall_safety, 1),
            "safety_level": get_safety_level(overall_safety),
            "min_safety_score": min_safety,
            "max_safety_score": max_safety,
            "safety_variation": round(max_safety - min_safety, 1),
            "dangerous_segments": len(dangerous_segments),
            "segment_details": segment_analyses,
            "crash_summary": combined_crash_summary,
            "safety_recommendations": generate_route_safety_recommendations(
                overall_safety, dangerous_segments, segment_analyses
            )
        }
    }

def calculate_safety_score(start_summary, end_summary):
    """Calculate safety score from 0-100 based on crash data"""
    
    total_crashes = start_summary.get("total_crashes", 0) + end_summary.get("total_crashes", 0)
    total_injuries = (start_summary.get("pedestrian_injuries", 0) + end_summary.get("pedestrian_injuries", 0) + 
                     start_summary.get("cyclist_injuries", 0) + end_summary.get("cyclist_injuries", 0))
    total_fatalities = start_summary.get("total_fatalities", 0) + end_summary.get("total_fatalities", 0)
    
    # Start with 100 and subtract points for safety issues
    safety_score = 100
    
    # Deduct points for incidents
    safety_score -= (total_crashes * 50)        # -8 per crash
    safety_score -= (total_injuries * 75)      # -15 per injury
    safety_score -= (total_fatalities * 100)    # -40 per fatality
    
    # Ensure score stays between 0-100
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

def generate_route_safety_recommendations(overall_safety, dangerous_segments, segment_analyses):
    """Generate safety recommendations based on route analysis"""
    
    recommendations = []
    
    if overall_safety >= 85:
        recommendations.append("This route has excellent safety ratings")
        recommendations.append("Good choice for solo running")
    elif overall_safety >= 70:
        recommendations.append("This route is generally safe for running")
        recommendations.append("Consider running during daylight hours")
    else:
        recommendations.append("This route has some safety concerns")
        recommendations.append("Strongly recommend running with a partner")
        recommendations.append("Avoid running alone, especially at night")
    
    if dangerous_segments:
        recommendations.append(f"Be extra cautious around {len(dangerous_segments)} segments with higher crash rates")
        
        # Identify which parts of route are most dangerous
        for seg in dangerous_segments:
            progress = seg["route_progress"]
            if progress < 25:
                recommendations.append("Exercise caution at the beginning of your route")
            elif progress > 75:
                recommendations.append("Exercise caution near the end of your route")
            else:
                recommendations.append(f"Exercise caution around the {progress:.0f}% mark of your route")
    
    # Check for highly variable safety
    safety_scores = [seg["safety_score"] for seg in segment_analyses]
    if max(safety_scores) - min(safety_scores) > 30:
        recommendations.append("Safety conditions vary significantly along this route")
        recommendations.append("Stay alert as you transition between different areas")
    
    return recommendations[:6]  # Limit to 6 recommendations

# Updated main route generation function
def generate_running_routes_with_polyline_safety(start_lat, start_lng, target_distance_km, get_routes_function, get_crashes_function):
    """
    Main function to generate routes with detailed polyline-based safety analysis
    """
    
    print(f"🎯 Generating routes with detailed safety analysis...")
    
    # Generate accurate routes
    routes = get_routes_function(start_lat, start_lng, target_distance_km)
    
    if not routes:
        return {"error": "No routes generated"}
    
    # Analyze each route using polyline data
    enhanced_routes = []
    
    for route in routes:
        print(f"\n🔍 Analyzing {route.get('direction', 'Unknown')} route...")
        
        # Add detailed safety analysis using polyline
        enhanced_route = analyze_route_safety_detailed(route, get_crashes_function)
        
        # Calculate combined score (route accuracy + safety)
        route_accuracy = route.get('accuracy', route.get('accuracy_percent', 0))
        safety_score = enhanced_route["safety_analysis"]["overall_safety_score"]
        
        # Weighted combined score (60% accuracy, 40% safety for detailed analysis)
        combined_score = (route_accuracy * 0.4) + (safety_score * 0.6)
        enhanced_route["combined_score"] = round(combined_score, 1)
        
        enhanced_routes.append(enhanced_route)
        
        print(f"   ✅ Combined Score: {combined_score:.1f} (Accuracy: {route_accuracy:.1f}, Safety: {safety_score:.1f})")
    
    # Sort by combined score
    enhanced_routes.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return enhanced_routes