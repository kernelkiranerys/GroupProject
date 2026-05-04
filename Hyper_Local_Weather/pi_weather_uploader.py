#!/usr/bin/env python3

"""Read BME680 weather data, optionally attach GPS, and post to a web server.

This script combines the earlier sensor-only and sensor-plus-GPS scripts into a
single uploader with:
- configurable POST URL and payload format
- local JSONL backup
- optional GPS support
- retry-based posting
- graceful fallback when GPS is unavailable
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import bme680


DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_BACKUP_FILE = Path("sensor_readings.jsonl")
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_SENSOR_INIT_ATTEMPTS = 5
DEFAULT_SENSOR_INIT_DELAY_SECONDS = 2


@dataclass(frozen=True)
class Config:
    post_url: str
    post_mode: str
    interval_seconds: int
    backup_path: Path
    device_id: str
    location_id: Optional[str]
    location_name: Optional[str]
    static_latitude: Optional[float]
    static_longitude: Optional[float]
    timeout_seconds: int
    retry_attempts: int
    require_gps: bool


class GpsReader:
    def __init__(self) -> None:
        self._gps = self._initialise()

    @staticmethod
    def _initialise() -> Any:
        try:
            import smbus2

            sys.modules["smbus"] = smbus2
            from pa1010d import PA1010D
        except ImportError as exc:
            raise RuntimeError(f"GPS dependencies are unavailable: {exc}") from exc

        return PA1010D()

    def read(self) -> Dict[str, Optional[float]]:
        self._gps.update()
        return {
            "latitude": _coerce_float(getattr(self._gps, "latitude", None)),
            "longitude": _coerce_float(getattr(self._gps, "longitude", None)),
            "altitude_m": _coerce_float(getattr(self._gps, "altitude", None)),
        }


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description="Read BME680 data and post it to a server.")
    parser.add_argument(
        "--post-url",
        default=os.getenv("WEATHER_POST_URL", "https://jcb.pythonanywhere.com/api/pi-readings/"),
        help="Destination URL for readings.",
    )
    parser.add_argument(
        "--post-mode",
        choices=("json", "form"),
        default=os.getenv("WEATHER_POST_MODE", "json").strip().lower(),
        help="Send payload as JSON or form data.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("WEATHER_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))),
        help="Delay between readings.",
    )
    parser.add_argument(
        "--backup-path",
        default=os.getenv("WEATHER_BACKUP_PATH", str(DEFAULT_BACKUP_FILE)),
        help="Local JSONL backup file.",
    )
    parser.add_argument(
        "--device-id",
        default=os.getenv("WEATHER_DEVICE_ID", os.getenv("HOSTNAME", "raspberry-pi")),
        help="Stable identifier for this device.",
    )
    parser.add_argument(
        "--location-id",
        default=os.getenv("WEATHER_LOCATION_ID"),
        help="Optional server-side location identifier.",
    )
    parser.add_argument(
        "--location-name",
        default=os.getenv("WEATHER_LOCATION_NAME", "Indoor Sensor"),
        help="Location name used when posting by coordinates.",
    )
    parser.add_argument(
        "--latitude",
        type=float,
        default=_coerce_float(os.getenv("WEATHER_LATITUDE")),
        help="Optional fixed latitude used when GPS is unavailable.",
    )
    parser.add_argument(
        "--longitude",
        type=float,
        default=_coerce_float(os.getenv("WEATHER_LONGITUDE")),
        help="Optional fixed longitude used when GPS is unavailable.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("WEATHER_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
        help="HTTP timeout for POST requests.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=int(os.getenv("WEATHER_RETRY_ATTEMPTS", str(DEFAULT_RETRY_ATTEMPTS))),
        help="How many times to retry a failed POST.",
    )
    parser.add_argument(
        "--require-gps",
        action="store_true",
        default=os.getenv("WEATHER_REQUIRE_GPS", "false").strip().lower() in {"1", "true", "yes", "on"},
        help="Exit if GPS hardware cannot be initialized.",
    )

    args = parser.parse_args()

    if args.interval_seconds < 1:
        parser.error("--interval-seconds must be at least 1")
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    if args.retry_attempts < 1:
        parser.error("--retry-attempts must be at least 1")

    return Config(
        post_url=args.post_url,
        post_mode=args.post_mode,
        interval_seconds=args.interval_seconds,
        backup_path=Path(args.backup_path).expanduser(),
        device_id=args.device_id,
        location_id=args.location_id,
        location_name=(args.location_name or "").strip() or None,
        static_latitude=args.latitude,
        static_longitude=args.longitude,
        timeout_seconds=args.timeout_seconds,
        retry_attempts=args.retry_attempts,
        require_gps=args.require_gps,
    )


def configure_logging() -> None:
    log_level = os.getenv("WEATHER_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def initialise_sensor() -> bme680.BME680:
    last_error: Optional[Exception] = None
    for attempt in range(1, DEFAULT_SENSOR_INIT_ATTEMPTS + 1):
        try:
            sensor = bme680.BME680()
            sensor.set_humidity_oversample(bme680.OS_2X)
            sensor.set_pressure_oversample(bme680.OS_4X)
            sensor.set_temperature_oversample(bme680.OS_8X)
            sensor.set_filter(bme680.FILTER_SIZE_3)
            return sensor
        except Exception as exc:  # pragma: no cover - hardware specific
            last_error = exc
            logging.warning("BME680 init attempt %s/%s failed: %s", attempt, DEFAULT_SENSOR_INIT_ATTEMPTS, exc)
            time.sleep(DEFAULT_SENSOR_INIT_DELAY_SECONDS)

    raise RuntimeError(f"BME680 sensor could not be initialized: {last_error}")


def initialise_gps(require_gps: bool) -> Optional[GpsReader]:
    try:
        return GpsReader()
    except Exception as exc:  # pragma: no cover - hardware specific
        if require_gps:
            raise RuntimeError(f"GPS is required but could not be initialized: {exc}") from exc
        logging.warning("GPS disabled: %s", exc)
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def collect_reading(sensor: bme680.BME680, gps: Optional[GpsReader], config: Config) -> Dict[str, Any]:
    if not sensor.get_sensor_data():
        raise RuntimeError("BME680 returned no sensor data")

    gps_data = {"latitude": None, "longitude": None, "altitude_m": None}
    if gps is not None:
        try:
            gps_data = gps.read()
        except Exception as exc:  # pragma: no cover - hardware specific
            logging.warning("GPS read failed, continuing without coordinates: %s", exc)

    # Fall back to static coordinates for indoor uploads when GPS is unavailable.
    if gps_data["latitude"] is None and config.static_latitude is not None:
        gps_data["latitude"] = config.static_latitude
    if gps_data["longitude"] is None and config.static_longitude is not None:
        gps_data["longitude"] = config.static_longitude

    timestamp = datetime.now(timezone.utc).isoformat()
    temperature_c = round(float(sensor.data.temperature), 2)
    pressure_hpa = round(float(sensor.data.pressure), 2)
    humidity = round(float(sensor.data.humidity), 2)
    gas_resistance = round(float(sensor.data.gas_resistance), 2)

    reading: Dict[str, Any] = {
        "timestamp": timestamp,
        "device_id": config.device_id,
        "location_id": config.location_id,
        "location_name": config.location_name,
        "temperature_c": temperature_c,
        "temperature": temperature_c,
        "pressure_hpa": pressure_hpa,
        "pressure": pressure_hpa,
        "humidity": humidity,
        "gas_resistance_ohms": gas_resistance,
        "gas": gas_resistance,
        "latitude": gps_data["latitude"],
        "longitude": gps_data["longitude"],
        "altitude_m": gps_data["altitude_m"],
    }
    return reading


def append_backup(path: Path, reading: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(reading, ensure_ascii=True))
        handle.write("\n")


def emit_reading_feedback(reading: Dict[str, Any]) -> None:
    logging.info("----- Sensor reading -----")
    logging.info("Device: %s", reading.get("device_id"))
    logging.info("Timestamp: %s", reading.get("timestamp"))
    logging.info("Temperature: %.2f C", reading["temperature_c"])
    logging.info("Pressure: %.2f hPa", reading["pressure_hpa"])
    logging.info("Humidity: %.2f %%", reading["humidity"])
    logging.info("Gas resistance: %.2f ohms", reading["gas_resistance_ohms"])

    latitude = reading.get("latitude")
    longitude = reading.get("longitude")
    altitude_m = reading.get("altitude_m")
    if latitude is None or longitude is None:
        logging.info("GPS: unavailable")
    else:
        if altitude_m is None:
            logging.info("GPS: lat=%s lon=%s", latitude, longitude)
        else:
            logging.info("GPS: lat=%s lon=%s alt=%s m", latitude, longitude, altitude_m)

    if reading.get("location_id") is not None:
        logging.info("Location ID: %s", reading.get("location_id"))
    logging.info("-------------------------")


def post_reading(session: requests.Session, config: Config, reading: Dict[str, Any]) -> requests.Response:
    payload = {key: value for key, value in reading.items() if value is not None}
    payload["source"] = "raspberry-pi"

    last_error: Optional[Exception] = None
    for attempt in range(1, config.retry_attempts + 1):
        try:
            if config.post_mode == "form":
                response = session.post(config.post_url, data=payload, timeout=config.timeout_seconds)
            else:
                response = session.post(config.post_url, json=payload, timeout=config.timeout_seconds)

            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            logging.warning(
                "POST attempt %s/%s failed: %s",
                attempt,
                config.retry_attempts,
                exc,
            )
            if attempt < config.retry_attempts:
                time.sleep(min(2 ** attempt, 30))

    raise RuntimeError(f"All POST attempts failed: {last_error}")


def run() -> int:
    configure_logging()
    config = parse_args()

    logging.info("Using POST URL: %s", config.post_url)
    logging.info("Backup file: %s", config.backup_path)

    try:
        sensor = initialise_sensor()
    except Exception as exc:
        logging.error("Sensor initialization failed: %s", exc)
        return 1

    gps = initialise_gps(config.require_gps)
    if gps is None:
        logging.info("GPS support is disabled or unavailable")
    else:
        logging.info("GPS support enabled")

    session = requests.Session()
    session.headers.update({"User-Agent": f"weather-uploader/{config.device_id}"})

    logging.info("Starting upload loop")
    try:
        while True:
            try:
                reading = collect_reading(sensor, gps, config)
            except Exception as exc:
                logging.warning("Skipping reading because collection failed: %s", exc)
                time.sleep(config.interval_seconds)
                continue

            append_backup(config.backup_path, reading)
            emit_reading_feedback(reading)

            try:
                response = post_reading(session, config, reading)
                logging.info("POST succeeded with HTTP %s", response.status_code)
            except Exception as exc:
                logging.warning("Reading saved locally, but POST failed: %s", exc)

            time.sleep(config.interval_seconds)
    except KeyboardInterrupt:
        logging.info("Exiting on Ctrl+C")
        return 0


if __name__ == "__main__":
    raise SystemExit(run())