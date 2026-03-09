from flask import Flask, render_template, request, jsonify, send_file
from ml_engine import MLEngine
from collections import deque
from datetime import datetime
import csv
import os

app = Flask(__name__)
ml = MLEngine()

history = {k: deque(maxlen=20) for k in ['temp', 'hum', 'pres', 'gas', 'co', 'dust']}
latest_data = {
    "temp": 0, "hum": 0, "pres": 0, "gas": 0, "co": 0, "dust": 0,
    "aqi": 0, "health_score": 100, "status": "Syncing...", 
    "comfort": 0, "carbon": 0, "uptime": "0h 0m",
    "agent_thoughts": [], "agent_actions": []
}
start_time = datetime.now()
LOG_FILE = "sensor_log.csv"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/latest")
def get_latest():
    uptime = datetime.now() - start_time
    latest_data["uptime"] = f"{uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m"
    forecasts = {f"{k}_pred": ml.predict_future(latest_data.get(k, 0), list(history[k])) for k in history.keys()}
    
    agent_output = ml.environmental_agent(latest_data, forecasts)
    gemini_insight = ml.gemini_reasoning(latest_data)
    
    latest_data["agent_thoughts"] = [f"GEMINI: {gemini_insight}"] + agent_output["thoughts"]
    latest_data["agent_actions"] = agent_output["actions"]
    
    return jsonify({**latest_data, **forecasts})

@app.route("/chat", methods=["POST"])
def chat():
    # parse JSON body safely – using silent=True avoids a 400 on malformed JSON
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return jsonify({"response": "Invalid chat request (no message provided)."}), 400
    user_query = data.get("message")
    context = (
        f"CONTEXT: You are the AI-Eco Sentinel, an environmental monitoring agent. "
        f"Live Data in Bengaluru: Temp={latest_data['temp']}C, AQI={latest_data['aqi']}, "
        f"Humidity={latest_data['hum']}%, Dust={round(latest_data['dust']*1000, 2)} ug/m3, "
        f"CO={latest_data['co']} PPM, Gas/Air Quality={latest_data['gas']} PPM. "
        f"Answer the user's question concisely and scientifically based ONLY on this data."
    )
    
    try:
        response = ml.client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"{context}\n\nUser Question: {user_query}"
        )
        return jsonify({"response": response.text})
    except Exception as e:
        # log the detailed exception for debugging (avoid non-ASCII)
        print(f"Gemini Chat Error: {e}")
        msg = str(e)
        # if it's a quota issue, suggest checking billing/limits
        if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
            fallback = (
                "⚠️ Gemini quota exhausted or billing issue. "
                "Check your Google Cloud console for limits. "
                f"(Details: {msg})"
            )
        else:
            fallback = (
                "⚠️ Gemini service unavailable. "
                "Please try again later or check your API key/network. "
                f"(Details: {msg})"
            )
        # always return 200 so frontend can parse JSON
        return jsonify({"response": fallback}), 200

@app.route("/download")
def download_file():
    if os.path.exists(LOG_FILE):
        return send_file(LOG_FILE, as_attachment=True)
    else:
        return "<h3>⚠️ No data logged yet.</h3><p>Wait for the ESP32 to send its first reading.</p>", 404

@app.route("/data", methods=["POST"])
def receive_data():
    global latest_data
    try:
        incoming = request.json
        for k in history:
            if k in incoming:
                val = float(incoming.get(k, 0))
                history[k].append(val)
                latest_data[k] = val

        aqi = (latest_data['gas']*0.4) + (latest_data['co']*0.3) + (latest_data['dust']*100)
        latest_data.update({
            "aqi": round(aqi, 1),
            "health_score": ml.calculate_health_score(aqi),
            "status": ml.get_status_text(aqi),
            "comfort": ml.calculate_comfort_index(latest_data['temp'], latest_data['hum'], latest_data['pres']),
            "carbon": ml.estimate_carbon_footprint(latest_data['gas'], latest_data['dust'])
        })
        
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Temp', 'Hum', 'Pres', 'Gas', 'CO', 'Dust', 'AQI'])
            writer.writerow([datetime.now()] + [latest_data[k] for k in ['temp', 'hum', 'pres', 'gas', 'co', 'dust']] + [aqi])

        forecasts = {f"{k}_pred": ml.predict_future(latest_data.get(k, 0), list(history[k])) for k in history.keys()}
        agent_output = ml.environmental_agent(latest_data, forecasts)
        
        return jsonify({"status": "success", "commands": agent_output["actions"]}), 200

    except Exception as e:
        print(f"⚠️ Agentic Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)