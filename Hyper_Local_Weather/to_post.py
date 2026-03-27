#!/usr/bin/env python3
import time
import json
import requests
import bme680
from datetime import datetime

# --- CONFIGURATION ---
# Replace '1' with the actual ID of the Location in your Django database
LOCATION_ID = 1 
POST_URL = "https://jcb.pythonanywhere.com/update/"
JSON_FILE = "sensor_data.json"
# ---------------------

try:
    sensor = bme680.BME680()
except IOError:
    print("BME680 sensor not found. Check your wiring.")
    exit(1)

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)

print(f"Reading BME680. Sending to {POST_URL}. Press Ctrl+C to exit.")

try:
    while True:
        if sensor.get_sensor_data():
            # Prepare data for local JSON storage
            current_time = datetime.now().isoformat()
            sensor_reading = {
                "timestamp": current_time,
                "temperature": round(sensor.data.temperature, 2),
                "pressure": round(sensor.data.pressure, 2),
                "humidity": round(sensor.data.humidity, 2),
                "gas": round(sensor.data.gas_resistance, 2)
            }

            # Prepare data for Django POST (Matching your view's keys)
            payload = {
                "location_id": LOCATION_ID,
                "temperature_c": sensor_reading["temperature"],
                "humidity": sensor_reading["humidity"]
            }

            print(f"Temp: {payload['temperature_c']}°C | Humidity: {payload['humidity']}%")

            # 1. Local Backup (JSON file)
            try:
                try:
                    with open(JSON_FILE, "r") as f:
                        all_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    all_data = []

                all_data.append(sensor_reading)
                with open(JSON_FILE, "w") as f:
                    json.dump(all_data, f, indent=4)
            except Exception as e:
                print(f"Local storage error: {e}")

            # 2. Send to Django
            try:
                # Note: We use data=payload to send as standard form data (request.POST)
                response = requests.post(POST_URL, data=payload, timeout=10)
                if response.status_code == 200:
                    print(f"Successfully sent to Django! Status: {response.status_code}")
                else:
                    print(f"Django error: {response.status_code} - {response.text}")
            except requests.RequestException as e:
                print(f"Network error (Site might be down): {e}")

        time.sleep(30)

except KeyboardInterrupt:
    print("\nExiting...")