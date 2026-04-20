#!/usr/bin/env python3
import sys
import smbus2  # Trick PA1010D into finding smbus inside venv

# Trick pa1010d into thinking smbus exists
sys.modules['smbus'] = smbus2

import time
import json
import requests
import bme680
from pa1010d import PA1010D
from datetime import datetime

# ----------------------------
# Initialize BME680 sensor
# ----------------------------
try:
    sensor = bme680.BME680()
except IOError:
    print("BME680 sensor not found. Check your wiring.")
    exit(1)

# Set up oversampling (optional, improves accuracy)
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)

# ----------------------------
# Initialize PA1010D GPS
# ----------------------------
try:
    gps = PA1010D()
except Exception as e:
    print(f"PA1010D GPS sensor not found: {e}")
    exit(1)

# ----------------------------
# JSON file & POST URL
# ----------------------------
json_file = "sensor_data.json"
post_url = "http://example.com:8000/data"

print("Reading BME680 + GPS sensor data. Press Ctrl+C to exit.")

# ----------------------------
# Main loop
# ----------------------------
try:
    while True:
        if sensor.get_sensor_data():
            # Update GPS first
            gps.update()

            # Read sensor values
            data = {
                "timestamp": datetime.now().isoformat(),
                "temperature": round(sensor.data.temperature, 2),
                "pressure": round(sensor.data.pressure, 2),
                "humidity": round(sensor.data.humidity, 2),
                "gas": round(sensor.data.gas_resistance, 2),
                # GPS data
                "latitude": gps.latitude,
                "longitude": gps.longitude,
                "altitude_m": gps.altitude
            }

            # ----------------------------
            # Print to console
            # ----------------------------
            print(f"Temperature: {data['temperature']} °C")
            print(f"Pressure:    {data['pressure']} hPa")
            print(f"Humidity:    {data['humidity']} %")
            print(f"Gas:         {data['gas']} Ω")
            print(f"Latitude:    {data['latitude']}")
            print(f"Longitude:   {data['longitude']}")
            print(f"Altitude:    {data['altitude_m']} m")
            print("-" * 30)

            # ----------------------------
            # Append to JSON file
            # ----------------------------
            try:
                try:
                    with open(json_file, "r") as f:
                        all_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    all_data = []

                all_data.append(data)

                with open(json_file, "w") as f:
                    json.dump(all_data, f, indent=4)
            except Exception as e:
                print(f"Error writing to JSON file: {e}")

            # ----------------------------
            # Send POST request
            # ----------------------------
            try:
                response = requests.post(post_url, json=data, timeout=5)
                print(f"POST request sent. Status code: {response.status_code}")
            except requests.RequestException as e:
                print(f"Warning: POST request failed: {e}")

        # Wait 30 seconds
        time.sleep(30)

except KeyboardInterrupt:
    print("Exiting...")