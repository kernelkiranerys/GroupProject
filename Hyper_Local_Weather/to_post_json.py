#!/usr/bin/env python3
import time
import json
import requests
import bme680
from datetime import datetime

# Initialize the BME680 sensor
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

# JSON file to save data
json_file = "sensor_data.json"

# Dummy URL for POST request
post_url = "http://example.com:8000/data"

print("Reading BME680 sensor data. Press Ctrl+C to exit.")

try:
    while True:
        if sensor.get_sensor_data():
            # Read sensor values
            data = {
                "timestamp": datetime.now().isoformat(),
                "temperature": round(sensor.data.temperature, 2),
                "pressure": round(sensor.data.pressure, 2),
                "humidity": round(sensor.data.humidity, 2),
                "gas": round(sensor.data.gas_resistance, 2)
            }

            # Print to console
            print(f"Temperature: {data['temperature']} °C")
            print(f"Pressure:    {data['pressure']} hPa")
            print(f"Humidity:    {data['humidity']} %")
            print(f"Gas:         {data['gas']} Ω")
            print("-" * 30)

            # Append data to JSON file (always runs)
            try:
                # Load existing data if file exists
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

            # Send POST request (failure doesn't stop script)
            try:
                response = requests.post(post_url, json=data, timeout=5)
                print(f"POST request sent. Status code: {response.status_code}")
            except requests.RequestException as e:
                print(f"Warning: POST request failed: {e}")
                # Continue execution without stopping

        # Wait 30 seconds
        time.sleep(30)

except KeyboardInterrupt:
    print("Exiting...")