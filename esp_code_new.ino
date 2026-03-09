#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <ArduinoJson.h>

/* ========== CONFIGURATION ========== */
const char* ssid = "iQOO Neo9 Pro";
const char* password = "123456789";
const char* serverName = "http://10.222.50.1:5000/data";

#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34
#define MQ7_PIN 35
#define DUST_LED 32
#define DUST_VO 33
#define LED_PIN 2      // Internal Warning LED
#define BUZZER_PIN 5   // External Action Buzzer

DHT dht(DHTPIN, DHTTYPE);
Adafruit_BMP280 bmp;

unsigned long lastSendTime = 0;
const long sendInterval = 3000; 

void setup() {
  Serial.begin(115200);
  dht.begin();
  if (!bmp.begin(0x76)) Serial.println("BMP280 not found!");
  
  pinMode(DUST_LED, OUTPUT);
  digitalWrite(DUST_LED, HIGH); 
  
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT); 
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nAgentic System Online");
}

void handleAgentActions(String payload) {
  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) return;

  JsonArray commands = doc["commands"];
  for (JsonObject cmd : commands) {
    String device = cmd["device"];
    int state = cmd["state"];
    if (device == "led") digitalWrite(LED_PIN, state);     //
    if (device == "buzzer") digitalWrite(BUZZER_PIN, state); //
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED && (millis() - lastSendTime > sendInterval)) {
    // 1. Capture All Sensor Data
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    
    // Check if DHT sensor is providing valid data
    if (isnan(temp) || isnan(hum)) {
      Serial.println("Failed to read from DHT sensor!");
      temp = 0; hum = 0;
    }

    float pres = bmp.readPressure() / 100.0F;

    // --- UPDATED DUST CALIBRATION FOR 0.52V BASELINE ---
    digitalWrite(DUST_LED, LOW);
    delayMicroseconds(280);
    float dustAnalog = analogRead(DUST_VO);
    delayMicroseconds(40);
    digitalWrite(DUST_LED, HIGH);
    
    float dustVoltage = dustAnalog * (3.3 / 4095.0);
    // Lowered offset to 0.08 to match your measured clean air voltage
    float dustDensity = (0.17 * dustVoltage - 0.08); 
    if (dustDensity < 0) dustDensity = 0;

    float gasPPM = map(analogRead(MQ135_PIN), 0, 4095, 0, 1000); 
    float coPPM = map(analogRead(MQ7_PIN), 0, 4095, 0, 500);

    // 2. Prepare JSON Payload
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    String json = "{\"temp\":" + String(temp) + ",\"hum\":" + String(hum) + 
                  ",\"pres\":" + String(pres) + ",\"gas\":" + String(gasPPM) + 
                  ",\"co\":" + String(coPPM) + ",\"dust\":" + String(dustDensity, 4) + "}";

    // 3. POST Data and PROCESS Agent Decisions
    int httpResponseCode = http.POST(json);
    if (httpResponseCode > 0) {
      String response = http.getString();
      handleAgentActions(response); 
    }
    http.end();
    lastSendTime = millis();
  }
}