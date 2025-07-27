import math
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_optimized_endpoints(start_lat, start_lng, target_distance_km):
    """Generate endpoints ONLY for good directions (based on your data analysis)"""
    
    # Convert distance to coordinate deltas
    lat_delta = target_distance_km / 111.0  # degrees latitude
    lng_delta = target_distance_km / (111.0 * math.cos(math.radians(start_lat)))  # degrees longitude
    
    print(f"🧮 Optimized Math check:")
    print(f"   Target distance: {target_distance_km} km")
    print(f"   Latitude delta: {lat_delta:.6f} degrees")
    print(f"   Longitude delta: {lng_delta:.6f} degrees")
    print()
    
    # ONLY the good directions (eliminates East & Southeast)
    good_directions = [
        {"bearing": 0, "name": "North"},
        {"bearing": 45, "name": "Northeast"}, 
        {"bearing": 180, "name": "South"},
        {"bearing": 225, "name": "Southwest"},
        {"bearing": 270, "name": "West"},
        {"bearing": 315, "name": "Northwest"}
    ]
    
    endpoints = []
    
    print(f"📍 Generated OPTIMIZED endpoints from ({start_lat}, {start_lng}):")
    
    for direction_info in good_directions:
        bearing = direction_info["bearing"]
        direction_name = direction_info["name"]
        
        # Convert bearing to radians
        bearing_rad = math.radians(bearing)
        
        # Calculate new coordinates
        new_lat = start_lat + (lat_delta * math.cos(bearing_rad))
        new_lng = start_lng + (lng_delta * math.sin(bearing_rad))
        
        # Verify distance using Haversine
        actual_distance = calculate_distance(start_lat, start_lng, new_lat, new_lng)
        
        endpoint = {
            "lat": new_lat,
            "lng": new_lng,
            "bearing": bearing,
            "direction": direction_name,
            "calculated_distance": actual_distance
        }
        endpoints.append(endpoint)
        
        print(f"   {direction_name:>9}: ({new_lat:.4f}, {new_lng:.4f}) - {actual_distance:.2f}km")
    
    print(f"\n✅ Generated {len(endpoints)} optimized endpoints (eliminated East & Southeast)")
    return endpoints

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def test_google_routes_distance(start_lat, start_lng, end_lat, end_lng):
    """Test actual walking distance using Google Routes API"""
    
    api_key = os.getenv("GOOGLE_ROUTES_API_KEY")
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    }
    
    data = {
        "origin": {"location": {"latLng": {"latitude": start_lat, "longitude": start_lng}}},
        "destination": {"location": {"latLng": {"latitude": end_lat, "longitude": end_lng}}},
        "travelMode": "WALK"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if "routes" in result and result["routes"]:
            route = result["routes"][0]
            distance_meters = route.get("distanceMeters", 0)
            duration_seconds = int(route.get("duration", "0s").replace("s", ""))
            polyline = route.get("polyline", {}).get("encodedPolyline", "")  # ADD THIS
            
            return {
                "distance_km": distance_meters / 1000,
                "duration_minutes": duration_seconds / 60,
                "polyline": polyline,  # ADD THIS
                "success": True
            }
    except Exception as e:
        return {"error": str(e), "success": False}
    
    return {"error": "No routes found", "success": False}

def optimized_route_finder(start_lat, start_lng, target_distance):
    """NEW: Smart 2-phase approach based on your data analysis"""
    
    print("🚀 OPTIMIZED ROUTE FINDER - Smart 2-Phase Approach")
    print("=" * 60)
    
    # Central Park coordinates
    #start_lat = 40.714136
    #start_lng = -74.006595
    #target_distance = 5.0  # User wants 5km total
    
    print(f"📍 Starting point: Central Park ({start_lat}, {start_lng})")
    print(f"🎯 Target distance: {target_distance}km")
    print()
    
    all_routes = []
    
    # PHASE 1: Test optimal multiplier (0.4) with good directions only
    print("🔍 PHASE 1: Testing optimal multiplier (0.4) with 6 good directions")
    print("=" * 50)
    
    optimal_multiplier = 0.4
    one_way_distance = target_distance * optimal_multiplier
    
    print(f"One-way distance: {one_way_distance:.2f}km")
    
    # Use optimized endpoint generation (only 6 directions)
    endpoints = generate_optimized_endpoints(start_lat, start_lng, one_way_distance)
    endpoints = reverse_geocode_and_filter(endpoints)
    
    phase1_routes = []
    
    for endpoint in endpoints:
        print(f"   Testing {endpoint['direction']} route...")
        
        google_result = test_google_routes_distance(
            start_lat, start_lng, 
            endpoint["lat"], endpoint["lng"]
        )
        
        if google_result["success"]:
            one_way_actual = google_result["distance_km"]
            total_distance = one_way_actual * 2  # Out and back
            difference = abs(total_distance - target_distance)
            accuracy = 100 * (1 - difference / target_distance)
            
            route_info = {
                "direction": endpoint["direction"],
                "multiplier": optimal_multiplier,
                "one_way_planned": one_way_distance,
                "one_way_actual": one_way_actual,
                "total_distance": total_distance,
                "target_distance": target_distance,
                "distance_difference": difference,
                "accuracy": accuracy,
                "endpoint": {"lat": endpoint["lat"], "lng": endpoint["lng"]},
                "polyline": google_result.get("polyline", ""),  # ADD THIS LINE
                "phase": 1
            }
            phase1_routes.append(route_info)
            all_routes.append(route_info)
            
            print(f"      ✅ One-way: {one_way_actual:.2f}km → Total: {total_distance:.2f}km (accuracy: {accuracy:.1f}%)")
        else:
            print(f"      ❌ Route failed: {google_result.get('error', 'Unknown error')}")
    
    print()
    
    # Check Phase 1 results
    excellent_phase1 = [r for r in phase1_routes if r['accuracy'] >= 95]
    good_phase1 = [r for r in phase1_routes if r['accuracy'] >= 90]
    
    print(f"📊 Phase 1 Results:")
    print(f"   Excellent routes (≥95%): {len(excellent_phase1)}")
    print(f"   Good routes (≥90%): {len(good_phase1)}")
    print(f"   API calls used: 6")
    print()
    
    # PHASE 2: Only run if we need more good routes
    if len(excellent_phase1) >= 3:
        print("✅ SUCCESS: Found 3+ excellent routes in Phase 1! Stopping here.")
        final_routes = sorted(excellent_phase1, key=lambda x: x['accuracy'], reverse=True)
    elif len(good_phase1) >= 3:
        print("✅ SUCCESS: Found 3+ good routes in Phase 1! Stopping here.")
        final_routes = sorted(good_phase1, key=lambda x: x['accuracy'], reverse=True)
    else:
        print("🔍 PHASE 2: Testing backup multipliers for better coverage")
        print("=" * 50)
        
        backup_multipliers = [0.35, 0.45]  # Based on your data
        
        for multiplier in backup_multipliers:
            one_way_distance = target_distance * multiplier
            print(f"Testing multiplier {multiplier} (one-way: {one_way_distance:.2f}km)")
            
            endpoints = generate_optimized_endpoints(start_lat, start_lng, one_way_distance)
            endpoints = reverse_geocode_and_filter(endpoints)
            
            for endpoint in endpoints:
                print(f"   Testing {endpoint['direction']} route...")
                
                google_result = test_google_routes_distance(
                    start_lat, start_lng, 
                    endpoint["lat"], endpoint["lng"]
                )
                
                if google_result["success"]:
                    one_way_actual = google_result["distance_km"]
                    total_distance = one_way_actual * 2
                    difference = abs(total_distance - target_distance)
                    accuracy = 100 * (1 - difference / target_distance)
                    
                    route_info = {
                        "direction": endpoint["direction"],
                        "multiplier": multiplier,
                        "one_way_planned": one_way_distance,
                        "one_way_actual": one_way_actual,
                        "total_distance": total_distance,
                        "target_distance": target_distance,
                        "difference": difference,
                        "accuracy": accuracy,
                        "endpoint": {"lat": endpoint["lat"], "lng": endpoint["lng"]},
                        "phase": 2
                    }
                    
                    all_routes.append(route_info)
                    print(f"      ✅ One-way: {one_way_actual:.2f}km → Total: {total_distance:.2f}km (accuracy: {accuracy:.1f}%)")
                else:
                    print(f"      ❌ Route failed: {google_result.get('error', 'Unknown error')}")
            
            print()

        # Select final routes from all phases
        decent_routes = [r for r in all_routes if r['accuracy'] >= 80]
        final_routes = sorted(decent_routes, key=lambda x: x['accuracy'], reverse=True)
    
    # Display final results
    total_api_calls = len([r for r in all_routes if 'phase' in r])  # Count successful API calls
    
    print(f"🏆 FINAL TOP 3 ROUTES:")
    print("=" * 60)
    
    for i, route in enumerate(final_routes, 1):
        print(f"{i}. {route['direction']} Route (Phase {route['phase']}):")
        print(f"   📏 Total distance: {route['total_distance']:.2f}km (target: {route['target_distance']:.2f}km)")
        print(f"   🎯 Accuracy: {route['accuracy']:.1f}%")
        print(f"   📍 Endpoint: ({route['endpoint']['lat']:.4f}, {route['endpoint']['lng']:.4f})")
        print(f"   ⚙️  Used multiplier: {route['multiplier']} (one-way: {route['one_way_actual']:.2f}km)")
        print()
    
    print(f"💰 API Efficiency:")
    print(f"   Total API calls used: {total_api_calls}")
    print(f"   Vs original approach: {48} calls (saved {48-total_api_calls} calls = {((48-total_api_calls)/48)*100:.1f}% reduction)")
    
    return final_routes


def reverse_geocode_and_filter(endpoints):
    """
    Reverse geocode endpoints and filter out water/invalid locations
    
    Args:
        endpoints: List of endpoint dicts with 'lat', 'lng', 'direction' keys
        
    Returns:
        List of valid endpoints with added 'address' field
    """
    
    api_key = os.getenv("GOOGLE_ROUTES_API_KEY")  # Same key works for geocoding
    
    valid_endpoints = []
    
    print(f"🔍 Reverse geocoding {len(endpoints)} endpoints to filter out water locations...")
    
    for endpoint in endpoints:
        lat = endpoint['lat']
        lng = endpoint['lng']
        direction = endpoint['direction']
        
        # Google Geocoding API call
        geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lng}",
            'key': api_key
        }
        
        try:
            response = requests.get(geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result['status'] == 'OK' and result['results']:
                # Get the formatted address
                address = result['results'][0]['formatted_address']
                
                # Filter out water/invalid locations
                water_keywords = [
                    'North America',
                    'Atlantic Ocean', 
                    'Hudson River',
                    'East River',
                    'New York Harbor',
                    'Unnamed Road',
                    'Jersey',
                    'NJ',
                    'Long Island',
                    'Astoria',
                    '+',
                    'Plus Code'  # Google's plus codes often indicate water/remote areas
                ]
                
                # Check if address contains water keywords
                is_water = any(keyword in address for keyword in water_keywords)
                
                if is_water:
                    print(f"   ❌ {direction}: {address} (FILTERED - water/invalid)")
                else:
                    # Add address to endpoint and keep it
                    endpoint['address'] = address
                    valid_endpoints.append(endpoint)
                    print(f"   ✅ {direction}: {address}")
            else:
                print(f"   ❌ {direction}: No address found (FILTERED)")
                
        except Exception as e:
            print(f"   ❌ {direction}: Geocoding error - {str(e)} (FILTERED)")
    
    print(f"\n📊 Filtering Results:")
    print(f"   Original endpoints: {len(endpoints)}")
    print(f"   Valid endpoints: {len(valid_endpoints)}")
    print(f"   Filtered out: {len(endpoints) - len(valid_endpoints)}")
    
    return valid_endpoints

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Original single distance test")
    print("2. Original comprehensive test (48 API calls)")
    print("3. 🚀 NEW: Optimized smart route finder (6-18 API calls)")
    
    start_lat = float(input("Enter starting latitude: "))
    start_lng = float(input("Enter starting longitude: "))
    target_distance = float(input("Enter target distance: "))

    optimized_route_finder(start_lat, start_lng, target_distance)
