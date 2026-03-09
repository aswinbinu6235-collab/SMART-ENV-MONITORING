import numpy as np
import joblib
from datetime import datetime
import time
from google import genai

class MLEngine:
    def __init__(self):
        # Directly initialize the client with your actual API key
        self.client = genai.Client(api_key="AIzaSyDa2cQMin5upmviA3xuV9m7xS5n192Vdyw")
        
        # API Rate Limit Protectors
        self.last_gemini_call = 0
        self.cached_gemini_thought = "Awaiting initial environmental scan..."
        
        try:
            self.reg = joblib.load('reg_model.pkl')
            self.clf = joblib.load('clf_model.pkl')
            self.anom = joblib.load('anomaly_model.pkl')
        except:
            print("⚠️ Note: .pkl models not found. Using algorithmic fallbacks.")

    def calculate_health_score(self, aqi):
        score = 100 - (aqi / 500 * 100)
        return round(max(0, score), 1)

    def calculate_comfort_index(self, temp, hum, pres):
        t_factor = max(0, 100 - abs(temp - 23.5) * 5)
        h_factor = max(0, 100 - abs(hum - 50) * 2)
        return round((t_factor * 0.6) + (h_factor * 0.4), 1)

    def estimate_carbon_footprint(self, gas_ppm, dust_mg):
        return round((gas_ppm * 0.44) + (dust_mg * 0.12), 2)

    def predict_future(self, current_val, history):
        if len(history) < 2: return [current_val] * 6
        slope = (history[-1] - history[0]) / len(history)
        return [round(current_val + (slope * i * 5), 2) for i in range(1, 7)]

    def get_status_text(self, aqi):
        if aqi < 50: return "Healthy ✅"
        if aqi < 150: return "Warning ⚠️"
        return "Hazardous 🚨"

    def environmental_agent(self, data, forecasts):
        thoughts = []
        actions = []
        
        if data['aqi'] > 100:
            thoughts.append("AQI threshold exceeded. Activating warning LED.")
            actions.append({"device": "led", "state": 1, "reason": "High AQI"})
        else:
            actions.append({"device": "led", "state": 0, "reason": "Safe AQI"})

        if data['dust'] > 0.05 or forecasts['dust_pred'][-1] > (data['dust'] * 1.2):
            thoughts.append("Particulate surge detected/predicted. Engaging Buzzer.")
            actions.append({"device": "buzzer", "state": 1, "reason": "Dust/Smoke mitigation"})
        else:
            actions.append({"device": "buzzer", "state": 0, "reason": "Stable conditions"})

        return {"thoughts": thoughts, "actions": actions}

    def gemini_reasoning(self, data):
        current_time = time.time()
        
        # Cooldown Check: Returns cached thought if 60 seconds haven't passed
        if current_time - self.last_gemini_call < 60:
            return self.cached_gemini_thought
            
        # Lock the timer immediately to prevent spamming the API on errors
        self.last_gemini_call = current_time 
        
        try:
            prompt = (
                f"You are the AI-Eco Sentinel Agent in Bengaluru. "
                f"Live Data: Temp {data['temp']}°C, Humidity {data['hum']}%, "
                f"AQI {data['aqi']}, Dust {round(data['dust']*1000, 2)} ug/m3. "
                f"Provide a 1-sentence expert environmental insight."
            )
            response = self.client.models.generate_content(
                model="gemini-1.5-flash-8b", 
                contents=prompt
            )
            self.cached_gemini_thought = response.text
            return self.cached_gemini_thought
        except Exception as e:
            return "Gemini API Cooldown Active. Restoring in 60s..."