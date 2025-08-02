import openai
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

# to be called in main

class SafetyAnalysisAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        self.client = openai.OpenAI(api_key=api_key)

    def preprocess_for_llm(route_data):
        for route in route_data["route_options"]:
            if "polyline" in route:
                del route["polyline"] 
        return route_data


    def route_recommendation_llm_call(self, running_metadata) -> Dict:
        """
        Get LLM route recommendations based on safety and accuracy data
        WIP -- next session
        """
        return {}

    def _extract_top_recommendation(self, analysis_text: str, routes: List[Dict]) -> Dict:
        """
        Try to extract which route the LLM recommended
        """
        analysis_lower = analysis_text.lower()
        
        for route in routes:
            direction = route["direction"].lower()
            route_id = str(route["id"])
            
            if any(phrase in analysis_lower for phrase in [
                f"recommend route {route_id}",
                f"choose route {route_id}",
                f"recommend {direction}",
                f"choose {direction}", 
                f"route {route_id}",
                f"{direction} route"
            ]):
                return {
                    "id": route["id"],
                    "direction": route["direction"],
                    "safety_score": route["safety"]["score"],
                    "accuracy": route["accuracy"]
                }
        
        # default to highest combined score if can't parse
        best_route = max(routes, key=lambda x: (x["safety"]["score"] + x["accuracy"]) / 2)
        return {
            "id": best_route["id"],
            "direction": best_route["direction"],
            "safety_score": best_route["safety"]["score"],
            "accuracy": best_route["accuracy"]
        }

    def get_route_recommendations(self, running_metadata) -> Dict:
        """
        Main function to call for route recommendations
        Replace the old crash_data_llm_call with this function
        """
        return self.route_recommendation_llm_call(running_metadata)