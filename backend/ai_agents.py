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

    def analyze_crash_data(self, crash_data: Dict, location_context: str = "") -> Dict:
        summary = crash_data.get("summary", {})
        crashes = crash_data.get("crashes", [])
        prompt = f"""
        You are a running safety expert analyzing crash data for a runner planning a route.

        LOCATION: {location_context}
        RECENT CRASH DATA (last 30 days):
        - Total crashes: {summary.get("total_crashes", 0)}
        - Pedestrian injuries: {summary.get("pedestrian_injuries", 0)}
        - Cyclist injuries: {summary.get("cyclist_injuries", 0)}
        - Total fatalities: {summary.get("total_fatalities", 0)}

        SPECIFIC INCIDENTS:
        """
        for crash in crashes[:3]:  # closest 3 crashes
            prompt += f"""
        - {crash.get("distance_km", 0):.2f}km away on {crash.get("street", "Unknown Street")}
        - Date: {crash.get("date", "Unknown")}
        - Injuries: {crash.get("injuries", {}).get("total", 0)} total, {crash.get("injuries", {}).get("pedestrians", 0)} pedestrians
        - Cause: {", ".join(crash.get("contributing_factors", []))}
        """
        
        prompt += """

        Provide a runner-specific safety analysis with:
        1. Overall safety assessment for runners in this area
        2. Specific risks based on the crash patterns
        3. Practical recommendations for safe running
        4. Best times/conditions to run here
        5. Any areas or streets to avoid

        Be conversational, helpful, and focused on pedestrian safety. Keep it under 200 words.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert running safety advisor who analyzes traffic data to help runners stay safe."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300, # word count
                temperature=0.7 # creativity level 
            )
            
            ai_analysis = response.choices[0].message.content
            
            # extract key recommendations (simple keyword extraction)
            recommendations = self._extract_recommendations(ai_analysis)
            
            return {
                "ai_analysis": ai_analysis,
                "recommendations": recommendations,
                "confidence": "high" if summary.get("total_crashes", 0) > 0 else "moderate",
                "analysis_type": "crash_pattern_analysis"
            }
            
        except Exception as e:
            return {
                "ai_analysis": f"Unable to generate AI analysis: {str(e)}",
                "recommendations": ["Check crash data manually", "Exercise caution"],
                "confidence": "low",
                "analysis_type": "error"
            }
    
    def _extract_recommendations(self, analysis_text: str) -> List[str]:
        # keyword-based extraction (WIP)
        recommendations = []
        
        lines = analysis_text.split("\n")
        for line in lines:
            if any(keyword in line.lower() for keyword in ["recommend", "avoid", "use", "stay", "choose"]):
                clean_line = line.strip("- ").strip()
                if len(clean_line) > 10:  # filter out very short lines
                    recommendations.append(clean_line)
        
        return recommendations[:5]  # limit to 5 recommendations