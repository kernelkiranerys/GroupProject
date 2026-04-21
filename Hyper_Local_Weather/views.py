import json
import time
import math
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from urllib import error, parse, request as urllib_request
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import Location, WeatherReading, Profile
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Avg
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect
from .forms import (
    SignUpForm,
    ChangeProfileForm,
    ProfileUpdateForm,
    UserUpdateForm,
    PasswordChangeForm
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.core.serializers import serialize
from django.contrib.auth.models import User
from django.contrib import messages

UK_AQ_LOCATIONS = [
    {'name': 'Leeds', 'latitude': 53.8008, 'longitude': -1.5491},
    {'name': 'London', 'latitude': 51.5072, 'longitude': -0.1276},
    {'name': 'Manchester', 'latitude': 53.4808, 'longitude': -2.2426},
    {'name': 'Birmingham', 'latitude': 52.4862, 'longitude': -1.8904},
    {'name': 'Liverpool', 'latitude': 53.4084, 'longitude': -2.9916},
    {'name': 'Newcastle', 'latitude': 54.9783, 'longitude': -1.6178},
    {'name': 'Glasgow', 'latitude': 55.8642, 'longitude': -4.2518},
    {'name': 'Bristol', 'latitude': 51.4545, 'longitude': -2.5879},
    {'name': 'Cardiff', 'latitude': 51.4816, 'longitude': -3.1791},
    {'name': 'Belfast', 'latitude': 54.5973, 'longitude': -5.9301},
]

LEEDS_BOUNDS = {
    'north': 53.915,
    'south': 53.735,
    'east': -1.360,
    'west': -1.665,
}

LEEDS_GRID_SIZE = 12
LEEDS_CACHE_TTL_SECONDS = 600
_LEEDS_GRID_CACHE = {
    'expires_at': 0,
    'payload': None,
}

UK_SENSOR_CACHE_TTL_SECONDS = 900
UK_SENSOR_WORKERS = 2
IQAIR_WORKERS = 6
UK_STATION_HEX_SIZE_KM = 2.0
UK_MIN_HEX_SPACING_KM = 3.8
_UK_SENSOR_CACHE = {
    'expires_at': 0,
    'payload': None,
}

UK_MAP_CENTER = {'latitude': 54.5, 'longitude': -2.6}
LEEDS_OUTDOOR_COORDS = {'latitude': 53.8008, 'longitude': -1.5491}
DEFAULT_OUTDOOR_COORDS = {'latitude': 51.5085, 'longitude': -0.1257}

IQAIR_BACKFILL_POINTS = [
    {'name': 'Leeds', 'latitude': 53.8008, 'longitude': -1.5491},
    {'name': 'London', 'latitude': 51.5072, 'longitude': -0.1276},
    {'name': 'Manchester', 'latitude': 53.4808, 'longitude': -2.2426},
    {'name': 'Birmingham', 'latitude': 52.4862, 'longitude': -1.8904},
    {'name': 'Liverpool', 'latitude': 53.4084, 'longitude': -2.9916},
    {'name': 'Newcastle', 'latitude': 54.9783, 'longitude': -1.6178},
    {'name': 'Glasgow', 'latitude': 55.8642, 'longitude': -4.2518},
    {'name': 'Edinburgh', 'latitude': 55.9533, 'longitude': -3.1883},
    {'name': 'Bristol', 'latitude': 51.4545, 'longitude': -2.5879},
    {'name': 'Cardiff', 'latitude': 51.4816, 'longitude': -3.1791},
    {'name': 'Belfast', 'latitude': 54.5973, 'longitude': -5.9301},
    {'name': 'Aberdeen', 'latitude': 57.1497, 'longitude': -2.0943},
    {'name': 'Swansea', 'latitude': 51.6214, 'longitude': -3.9436},
    {'name': 'Plymouth', 'latitude': 50.3755, 'longitude': -4.1427},
    {'name': 'Norwich', 'latitude': 52.6309, 'longitude': 1.2974},
    {'name': 'Sheffield', 'latitude': 53.3811, 'longitude': -1.4701},
    {'name': 'Nottingham', 'latitude': 52.9548, 'longitude': -1.1581},
    {'name': 'Southampton', 'latitude': 50.9097, 'longitude': -1.4044},
    {'name': 'Cambridge', 'latitude': 52.2053, 'longitude': 0.1218},
    {'name': 'Hull', 'latitude': 53.7676, 'longitude': -0.3274},
]


def _aq_zone_from_pm25(pm25_value):
    """Return a 3-band zone for PM2.5 in ug/m3."""
    if pm25_value <= 12:
        return {'zone': 'good', 'label': 'Good', 'color': '#2ecc71'}
    if pm25_value <= 35.4:
        return {'zone': 'moderate', 'label': 'Moderate', 'color': '#f39c12'}
    return {'zone': 'poor', 'label': 'Poor', 'color': '#e74c3c'}


def _get_openaq_api_key():
    return (getattr(settings, 'OPENAQ_API_KEY', '') or '').strip()


def _get_iqair_api_key():
    return (getattr(settings, 'IQAIR_API_KEY', '') or '').strip()


def _get_enable_defra_provider():
    return str(getattr(settings, 'ENABLE_DEFRA_PROVIDER', 'true')).strip().lower() in ('1', 'true', 'yes', 'on')


def _openaq_request(url):
    api_key = _get_openaq_api_key()
    if not api_key:
        raise PermissionError('Missing OPENAQ_API_KEY')

    req = urllib_request.Request(url)
    req.add_header('Accept', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('X-API-Key', api_key)
    with urllib_request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))


def _aqius_to_pm25(aqius):
    # Convert US AQI to approximate PM2.5 concentration using EPA breakpoints.
    breakpoints = [
        (0, 50, 0.0, 12.0),
        (51, 100, 12.1, 35.4),
        (101, 150, 35.5, 55.4),
        (151, 200, 55.5, 150.4),
        (201, 300, 150.5, 250.4),
        (301, 400, 250.5, 350.4),
        (401, 500, 350.5, 500.4),
    ]

    for i_low, i_high, c_low, c_high in breakpoints:
        if i_low <= aqius <= i_high:
            ratio = (aqius - i_low) / (i_high - i_low)
            return round(c_low + (ratio * (c_high - c_low)), 1)
    return None


def _extract_coordinates(item):
    coordinates = item.get('coordinates')
    if isinstance(coordinates, dict):
        lat = coordinates.get('latitude')
        lon = coordinates.get('longitude')
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return float(lat), float(lon)

    location = item.get('location')
    if isinstance(location, dict):
        nested = location.get('coordinates')
        if isinstance(nested, dict):
            lat = nested.get('latitude')
            lon = nested.get('longitude')
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                return float(lat), float(lon)

    lat = item.get('latitude')
    lon = item.get('longitude')
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon)

    return None, None


def _extract_pm25(item):
    def _is_pm25(name):
        if not isinstance(name, str):
            return False
        normalized = name.lower().replace('.', '').replace('_', '')
        return normalized in ('pm25', 'pm2.5')

    measurements = item.get('measurements')
    if isinstance(measurements, list):
        for entry in measurements:
            if not isinstance(entry, dict):
                continue
            parameter_name = entry.get('parameter') or entry.get('name')
            if _is_pm25(parameter_name) and isinstance(entry.get('value'), (int, float)):
                return float(entry['value'])

    parameters = item.get('parameters')
    if isinstance(parameters, list):
        for entry in parameters:
            if not isinstance(entry, dict):
                continue
            parameter_name = entry.get('parameter') or entry.get('name')
            if not _is_pm25(parameter_name):
                continue
            if isinstance(entry.get('lastValue'), (int, float)):
                return float(entry['lastValue'])
            if isinstance(entry.get('value'), (int, float)):
                return float(entry['value'])

    sensors = item.get('sensors')
    if isinstance(sensors, list):
        for sensor in sensors:
            if not isinstance(sensor, dict):
                continue
            parameter_name = sensor.get('parameter') or sensor.get('name')
            if not _is_pm25(parameter_name):
                continue
            latest = sensor.get('latest')
            if isinstance(latest, dict) and isinstance(latest.get('value'), (int, float)):
                return float(latest['value'])
            if isinstance(sensor.get('value'), (int, float)):
                return float(sensor['value'])

    return None


def _fetch_openaq_uk_sensor_points():
    location_url = 'https://api.openaq.org/v3/locations?countries_id=79&parameters_id=2&limit=1000&page=1'
    payload = _openaq_request(location_url)
    items = payload.get('results') if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    sensor_requests = []
    for item in items:
        if not isinstance(item, dict):
            continue

        lat, lon = _extract_coordinates(item)
        if lat is None or lon is None:
            continue

        sensor_candidates = item.get('sensors') or []
        pm25_sensor_id = None
        for sensor in sensor_candidates:
            if not isinstance(sensor, dict):
                continue
            parameter = sensor.get('parameter')
            parameter_name = None
            if isinstance(parameter, dict):
                parameter_name = parameter.get('name')
            if isinstance(parameter_name, str) and parameter_name.lower() == 'pm25':
                pm25_sensor_id = sensor.get('id')
                break

        if not pm25_sensor_id:
            continue

        sensor_requests.append({
            'sensor_id': pm25_sensor_id,
            'location_name': item.get('name') or item.get('locality') or f'OpenAQ sensor {pm25_sensor_id}',
            'latitude': lat,
            'longitude': lon,
        })

    def _load_sensor_latest(req_info):
        sensor_url = f"https://api.openaq.org/v3/sensors/{req_info['sensor_id']}"
        try:
            sensor_payload = _openaq_request(sensor_url)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, PermissionError):
            return None

        results = sensor_payload.get('results') if isinstance(sensor_payload, dict) else None
        if not isinstance(results, list) or not results:
            return None

        sensor = results[0]
        if not isinstance(sensor, dict):
            return None

        latest = sensor.get('latest') or {}
        value = latest.get('value') if isinstance(latest, dict) else None
        if not isinstance(value, (int, float)):
            return None

        coords = latest.get('coordinates') if isinstance(latest, dict) else None
        if isinstance(coords, dict):
            lat = coords.get('latitude', req_info['latitude'])
            lon = coords.get('longitude', req_info['longitude'])
        else:
            lat = req_info['latitude']
            lon = req_info['longitude']

        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None

        return {
            'id': f"openaq-{req_info['sensor_id']}",
            'name': req_info.get('location_name') or f"OpenAQ sensor {req_info['sensor_id']}",
            'latitude': float(lat),
            'longitude': float(lon),
            'pm25': round(float(value), 1),
            'source': 'openaq',
        }

    extracted = []
    with ThreadPoolExecutor(max_workers=UK_SENSOR_WORKERS) as executor:
        futures = [executor.submit(_load_sensor_latest, req) for req in sensor_requests]
        for future in as_completed(futures):
            point = future.result()
            if point:
                extracted.append(point)

    deduped = {}
    for point in extracted:
        key = (round(point['latitude'], 5), round(point['longitude'], 5))
        deduped[key] = point

    return list(deduped.values())


def _fetch_iqair_backfill_points():
    api_key = _get_iqair_api_key()
    if not api_key:
        return []

    def _load_point(seed):
        params = parse.urlencode({
            'lat': seed['latitude'],
            'lon': seed['longitude'],
            'key': api_key,
        })
        url = f'https://api.airvisual.com/v2/nearest_city?{params}'
        try:
            with urllib_request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None

        if payload.get('status') != 'success':
            return None

        data = payload.get('data') or {}
        current = data.get('current') or {}
        pollution = current.get('pollution') or {}
        aqius = pollution.get('aqius')
        if not isinstance(aqius, (int, float)):
            return None

        pm25 = _aqius_to_pm25(float(aqius))
        if pm25 is None:
            return None

        location = data.get('location') or {}
        coordinates = location.get('coordinates') if isinstance(location, dict) else None
        if isinstance(coordinates, list) and len(coordinates) == 2:
            lon = coordinates[0]
            lat = coordinates[1]
        else:
            lat = seed['latitude']
            lon = seed['longitude']

        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None

        return {
            'id': f"iqair-{seed['name'].lower().replace(' ', '-')}",
            'name': seed['name'],
            'latitude': float(lat),
            'longitude': float(lon),
            'pm25': pm25,
            'source': 'iqair',
        }

    points = []
    with ThreadPoolExecutor(max_workers=IQAIR_WORKERS) as executor:
        futures = [executor.submit(_load_point, seed) for seed in IQAIR_BACKFILL_POINTS]
        for future in as_completed(futures):
            point = future.result()
            if point:
                points.append(point)

    deduped = {}
    for point in points:
        key = (round(point['latitude'], 5), round(point['longitude'], 5), point.get('source'))
        deduped[key] = point
    return list(deduped.values())


def _fetch_defra_pm25_points():
    if not _get_enable_defra_provider():
        return []

    url = 'https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries?phenomenon=6001&expanded=true&limit=1000'
    try:
        with urllib_request.urlopen(url, timeout=25) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    points = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        last_value = item.get('lastValue') or {}
        value = last_value.get('value') if isinstance(last_value, dict) else None
        if not isinstance(value, (int, float)):
            continue

        station = item.get('station') or {}
        station_props = station.get('properties') if isinstance(station, dict) else None
        station_geom = station.get('geometry') if isinstance(station, dict) else None
        coordinates = station_geom.get('coordinates') if isinstance(station_geom, dict) else None
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        c0 = coordinates[0]
        c1 = coordinates[1]
        if not isinstance(c0, (int, float)) or not isinstance(c1, (int, float)):
            continue

        # DEFRA payload for this endpoint uses [lat, lon, elevation].
        lat = float(c0)
        lon = float(c1)
        if abs(lat) > 90 or abs(lon) > 180:
            continue

        station_id = station_props.get('id') if isinstance(station_props, dict) else None
        station_label = station_props.get('label') if isinstance(station_props, dict) else None
        point_id = f'defra-{station_id}' if station_id is not None else f"defra-{item.get('id', 'unknown')}"

        points.append({
            'id': point_id,
            'name': station_label or f"DEFRA station {station_id or item.get('id', 'unknown')}",
            'latitude': lat,
            'longitude': lon,
            'pm25': round(float(value), 1),
            'source': 'defra',
        })

    deduped = {}
    for point in points:
        key = (round(point['latitude'], 5), round(point['longitude'], 5), point.get('source'))
        deduped[key] = point
    return list(deduped.values())


def _latlon_to_xy_km(latitude, longitude, reference_latitude):
    x = longitude * 111.32 * math.cos(math.radians(reference_latitude))
    y = latitude * 110.57
    return x, y


def _xy_km_to_latlon(x, y, reference_latitude):
    latitude = y / 110.57
    longitude = x / (111.32 * math.cos(math.radians(reference_latitude)))
    return latitude, longitude


def _offset_latlon_km(latitude, longitude, offset_x_km, offset_y_km, reference_latitude):
    center_x, center_y = _latlon_to_xy_km(latitude, longitude, reference_latitude)
    return _xy_km_to_latlon(center_x + offset_x_km, center_y + offset_y_km, reference_latitude)


def _distance_km(lat1, lon1, lat2, lon2, reference_latitude):
    x1, y1 = _latlon_to_xy_km(lat1, lon1, reference_latitude)
    x2, y2 = _latlon_to_xy_km(lat2, lon2, reference_latitude)
    return math.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))


def _find_non_overlapping_center(base_lat, base_lon, placed_centers, min_spacing_km, reference_latitude):
    def _fits(candidate_lat, candidate_lon):
        for placed_lat, placed_lon in placed_centers:
            if _distance_km(candidate_lat, candidate_lon, placed_lat, placed_lon, reference_latitude) < min_spacing_km:
                return False
        return True

    if _fits(base_lat, base_lon):
        return base_lat, base_lon

    # Expand outward in a deterministic spiral until a non-overlapping position is found.
    radius_step_km = 0.7
    for ring in range(1, 10):
        radius_km = ring * radius_step_km
        spokes = 12 + (ring * 6)
        for i in range(spokes):
            angle = (2 * math.pi * i) / spokes
            cand_lat, cand_lon = _offset_latlon_km(
                base_lat,
                base_lon,
                radius_km * math.cos(angle),
                radius_km * math.sin(angle),
                reference_latitude,
            )
            if _fits(cand_lat, cand_lon):
                return cand_lat, cand_lon

    # If all candidates collide, keep the original station position.
    return base_lat, base_lon


def _axial_round(q, r):
    x = q
    z = r
    y = -x - z
    rx = round(x)
    ry = round(y)
    rz = round(z)

    x_diff = abs(rx - x)
    y_diff = abs(ry - y)
    z_diff = abs(rz - z)

    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


def _point_to_axial(latitude, longitude, size_km, reference_latitude):
    x, y = _latlon_to_xy_km(latitude, longitude, reference_latitude)
    q = ((math.sqrt(3) / 3) * x - (1 / 3) * y) / size_km
    r = ((2 / 3) * y) / size_km
    return _axial_round(q, r)


def _axial_to_center_latlon(q, r, size_km, reference_latitude):
    x = size_km * math.sqrt(3) * (q + (r / 2))
    y = size_km * 1.5 * r
    return _xy_km_to_latlon(x, y, reference_latitude)


def _hex_points_from_axial(q, r, size_km, reference_latitude):
    center_lat, center_lon = _axial_to_center_latlon(q, r, size_km, reference_latitude)
    points = []
    for deg in (0, 60, 120, 180, 240, 300):
        rad = math.radians(deg)
        px = size_km * math.cos(rad)
        py = size_km * math.sin(rad)
        vertex_lat, vertex_lon = _xy_km_to_latlon(
            _latlon_to_xy_km(center_lat, center_lon, reference_latitude)[0] + px,
            _latlon_to_xy_km(center_lat, center_lon, reference_latitude)[1] + py,
            reference_latitude,
        )
        points.append({'latitude': round(vertex_lat, 6), 'longitude': round(vertex_lon, 6)})
    return points, center_lat, center_lon


def _hex_points_from_center(center_lat, center_lon, size_km, reference_latitude):
    center_x, center_y = _latlon_to_xy_km(center_lat, center_lon, reference_latitude)
    points = []
    for deg in (0, 60, 120, 180, 240, 300):
        rad = math.radians(deg)
        px = size_km * math.cos(rad)
        py = size_km * math.sin(rad)
        vertex_lat, vertex_lon = _xy_km_to_latlon(center_x + px, center_y + py, reference_latitude)
        points.append({'latitude': round(vertex_lat, 6), 'longitude': round(vertex_lon, 6)})
    return points


def _build_uk_sensor_hex_payload():
    now_epoch = time.time()
    if _UK_SENSOR_CACHE['payload'] and _UK_SENSOR_CACHE['expires_at'] > now_epoch:
        return _UK_SENSOR_CACHE['payload']

    openaq_points = []
    iqair_points = []
    defra_points = []
    try:
        openaq_points = _fetch_openaq_uk_sensor_points()
    except (PermissionError, error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        stale_payload = _UK_SENSOR_CACHE.get('payload')
        if stale_payload:
            stale_payload['message'] = 'Showing cached sensor data due to provider limits. Refresh later for updates.'
            return stale_payload
        openaq_points = []

    iqair_points = _fetch_iqair_backfill_points()
    defra_points = _fetch_defra_pm25_points()
    sensor_points = openaq_points + iqair_points + defra_points

    if not sensor_points:
        payload = {
            'scope': 'uk-sensors',
            'generated_at': timezone.now().isoformat(),
            'sensor_count': 0,
            'hex_count': 0,
            'cells': [],
            'message': 'No sensor data available. Add OPENAQ_API_KEY and optionally IQAIR_API_KEY, then refresh.',
        }
        _UK_SENSOR_CACHE['payload'] = payload
        _UK_SENSOR_CACHE['expires_at'] = now_epoch + 30
        return payload

    reference_latitude = UK_MAP_CENTER['latitude']
    hex_size_km = UK_STATION_HEX_SIZE_KM
    source_priority = {'defra': 0, 'openaq': 1, 'iqair': 2}
    ordered_sensors = sorted(
        sensor_points,
        key=lambda s: (
            source_priority.get(s.get('source', 'unknown'), 99),
            s.get('name', ''),
            s.get('id', ''),
        ),
    )

    cells = []
    placed_centers = []
    for sensor in ordered_sensors:
        base_lat = sensor['latitude']
        base_lon = sensor['longitude']
        center_lat, center_lon = _find_non_overlapping_center(
            base_lat,
            base_lon,
            placed_centers,
            UK_MIN_HEX_SPACING_KM,
            reference_latitude,
        )
        placed_centers.append((center_lat, center_lon))

        zone = _aq_zone_from_pm25(sensor['pm25'])
        cells.append({
            'id': sensor.get('id') or f"sensor-{len(cells) + 1}",
            'name': sensor.get('name') or 'Air quality station',
            'hex_points': _hex_points_from_center(center_lat, center_lon, hex_size_km, reference_latitude),
            'center': {
                'latitude': round(center_lat, 6),
                'longitude': round(center_lon, 6),
            },
            'original_center': {
                'latitude': round(base_lat, 6),
                'longitude': round(base_lon, 6),
            },
            'display_offset_km': round(_distance_km(base_lat, base_lon, center_lat, center_lon, reference_latitude), 3),
            'pm25': sensor['pm25'],
            'sensor_count': 1,
            'zone': zone['zone'],
            'zone_label': zone['label'],
            'zone_color': zone['color'],
            'source': sensor.get('source', 'unknown'),
            'source_counts': {sensor.get('source', 'unknown'): 1},
        })

    payload = {
        'scope': 'uk-sensors',
        'generated_at': timezone.now().isoformat(),
        'sensor_count': len(sensor_points),
        'openaq_sensor_count': len(openaq_points),
        'iqair_sensor_count': len(iqair_points),
        'defra_sensor_count': len(defra_points),
        'hex_count': len(cells),
        'cells': cells,
        'message': None,
    }

    _UK_SENSOR_CACHE['payload'] = payload
    _UK_SENSOR_CACHE['expires_at'] = now_epoch + UK_SENSOR_CACHE_TTL_SECONDS
    return payload


def _fetch_open_meteo_pm25(latitude, longitude):
    params = parse.urlencode({
        'latitude': latitude,
        'longitude': longitude,
        'current': 'pm2_5',
    })
    url = f'https://air-quality-api.open-meteo.com/v1/air-quality?{params}'
    with urllib_request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode('utf-8'))
    current = payload.get('current') or {}
    pm25 = current.get('pm2_5')
    if pm25 is None:
        return None
    return round(float(pm25), 1)


def _fetch_open_meteo_air_quality(latitude, longitude):
    params = parse.urlencode({
        'latitude': latitude,
        'longitude': longitude,
        'current': 'pm2_5,pm10,nitrogen_dioxide,ozone,european_aqi',
        'hourly': 'pm2_5',
        'past_days': 1,
        'timezone': 'UTC',
    })
    url = f'https://air-quality-api.open-meteo.com/v1/air-quality?{params}'
    with urllib_request.urlopen(url, timeout=6) as response:
        payload = json.loads(response.read().decode('utf-8'))

    current = payload.get('current') or {}
    hourly = payload.get('hourly') or {}

    pm25 = current.get('pm2_5')
    if pm25 is None:
        hourly_pm25 = [v for v in (hourly.get('pm2_5') or []) if isinstance(v, (int, float))]
        if hourly_pm25:
            recent_slice = hourly_pm25[-6:] if len(hourly_pm25) >= 6 else hourly_pm25
            pm25 = sum(recent_slice) / len(recent_slice)

    if pm25 is None:
        raise ValueError('Missing live pm2_5 value')

    return {
        'pm25': round(float(pm25), 1),
        'pm10': round(float(current.get('pm10')), 1) if current.get('pm10') is not None else None,
        'no2': round(float(current.get('nitrogen_dioxide')), 1) if current.get('nitrogen_dioxide') is not None else None,
        'ozone': round(float(current.get('ozone')), 1) if current.get('ozone') is not None else None,
        'european_aqi': int(round(float(current.get('european_aqi')))) if current.get('european_aqi') is not None else None,
    }


def _fetch_open_meteo_outdoor_weather(latitude, longitude):
    """Fetch latest outdoor temperature, humidity, and pressure (hPa) from Open-Meteo."""
    params = parse.urlencode({
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m,relative_humidity_2m,pressure_msl',
        'models': 'ukmo_seamless',
        'timezone': 'UTC',
    })
    url = f'https://api.open-meteo.com/v1/forecast?{params}'
    with urllib_request.urlopen(url, timeout=6) as response:
        payload = json.loads(response.read().decode('utf-8'))

    hourly = payload.get('hourly') or {}
    temperatures = [v for v in (hourly.get('temperature_2m') or []) if isinstance(v, (int, float))]
    humidities = [v for v in (hourly.get('relative_humidity_2m') or []) if isinstance(v, (int, float))]
    pressures = [v for v in (hourly.get('pressure_msl') or []) if isinstance(v, (int, float))]

    latest_temperature = temperatures[-1] if temperatures else None
    latest_humidity = humidities[-1] if humidities else None
    latest_pressure = pressures[-1] if pressures else None

    if latest_temperature is None and latest_humidity is None and latest_pressure is None:
        raise ValueError('Missing outdoor weather values from Open-Meteo')

    return {
        'temperature_c': round(float(latest_temperature), 1) if latest_temperature is not None else None,
        'humidity': round(float(latest_humidity), 1) if latest_humidity is not None else None,
        'pressure_hpa': round(float(latest_pressure), 1) if latest_pressure is not None else None,
    }


def _aq_zone_from_measurement(pm25_value, european_aqi=None):
    if european_aqi is not None:
        if european_aqi <= 40:
            return {'zone': 'good', 'label': 'Good', 'color': '#2ecc71'}
        if european_aqi <= 80:
            return {'zone': 'moderate', 'label': 'Moderate', 'color': '#f39c12'}
        return {'zone': 'poor', 'label': 'Poor', 'color': '#e74c3c'}
    return _aq_zone_from_pm25(pm25_value)


def _hexagon_points(center_lat, center_lon, lat_radius, lon_radius):
    points = []
    for deg in (0, 60, 120, 180, 240, 300):
        rad = math.radians(deg)
        points.append({
            'latitude': round(center_lat + (lat_radius * math.sin(rad)), 6),
            'longitude': round(center_lon + (lon_radius * math.cos(rad)), 6),
        })
    return points


def _build_leeds_grid_cells():
    lat_step = (LEEDS_BOUNDS['north'] - LEEDS_BOUNDS['south']) / LEEDS_GRID_SIZE
    lon_step = (LEEDS_BOUNDS['east'] - LEEDS_BOUNDS['west']) / LEEDS_GRID_SIZE

    cells = []
    for row in range(LEEDS_GRID_SIZE):
        for col in range(LEEDS_GRID_SIZE):
            south = round(LEEDS_BOUNDS['south'] + (row * lat_step), 6)
            north = round(LEEDS_BOUNDS['south'] + ((row + 1) * lat_step), 6)
            west = round(LEEDS_BOUNDS['west'] + (col * lon_step), 6)
            east = round(LEEDS_BOUNDS['west'] + ((col + 1) * lon_step), 6)

            center_lat = round((south + north) / 2, 6)
            center_lon = round((west + east) / 2, 6)
            lat_radius = round(lat_step * 0.40, 6)
            lon_radius = round(lon_step * 0.40, 6)

            cells.append({
                'id': f'cell-{row}-{col}',
                'row': row,
                'col': col,
                'south': south,
                'north': north,
                'west': west,
                'east': east,
                'center_lat': center_lat,
                'center_lon': center_lon,
                'hex_points': _hexagon_points(center_lat, center_lon, lat_radius, lon_radius),
            })

    return cells


def _build_live_leeds_grid_payload():
    now_epoch = time.time()
    if _LEEDS_GRID_CACHE['payload'] and _LEEDS_GRID_CACHE['expires_at'] > now_epoch:
        return _LEEDS_GRID_CACHE['payload']

    cells = _build_leeds_grid_cells()
    enriched_cells = []
    live_count = 0
    unavailable_count = 0

    for cell in cells:
        source = 'open-meteo'
        measurement = None
        try:
            measurement = _fetch_open_meteo_air_quality(cell['center_lat'], cell['center_lon'])
            live_count += 1
        except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
            source = 'unavailable'
            unavailable_count += 1

        pm25_value = measurement['pm25'] if measurement else None
        european_aqi = measurement['european_aqi'] if measurement else None
        zone = _aq_zone_from_measurement(pm25_value, european_aqi) if measurement else {
            'zone': 'unavailable',
            'label': 'Unavailable',
            'color': '#6b7280',
        }

        enriched_cells.append({
            'id': cell['id'],
            'bounds': {
                'south': cell['south'],
                'north': cell['north'],
                'west': cell['west'],
                'east': cell['east'],
            },
            'hex_points': cell['hex_points'],
            'center': {
                'latitude': cell['center_lat'],
                'longitude': cell['center_lon'],
            },
            'pm25': pm25_value,
            'pm10': measurement['pm10'] if measurement else None,
            'no2': measurement['no2'] if measurement else None,
            'ozone': measurement['ozone'] if measurement else None,
            'european_aqi': european_aqi,
            'zone': zone['zone'],
            'zone_label': zone['label'],
            'zone_color': zone['color'],
            'source': source,
        })

    payload = {
        'city': 'Leeds',
        'bounds': LEEDS_BOUNDS,
        'grid_size': LEEDS_GRID_SIZE,
        'generated_at': timezone.now().isoformat(),
        'live_cells': live_count,
        'unavailable_cells': unavailable_count,
        'cells': enriched_cells,
    }

    _LEEDS_GRID_CACHE['payload'] = payload
    _LEEDS_GRID_CACHE['expires_at'] = now_epoch + LEEDS_CACHE_TTL_SECONDS
    return payload

@login_required
def account(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        if 'update-profile-submit' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Your account has been updated!')
                return redirect('Hyper_Local_Weather:account')
        elif 'change-password-submit' in request.POST:
            pass_form = PasswordChangeForm(request.POST, user=request.user)
            if pass_form.is_valid():
                user = pass_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('Hyper_Local_Weather:account')
            else:
                messages.error(request, 'Please correct the error below.')
        else:
            u_form = UserUpdateForm(instance=request.user)
            p_form = ProfileUpdateForm(instance=profile)
            pass_form = PasswordChangeForm(user=request.user)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)
        pass_form = PasswordChangeForm(user=request.user)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'pass_form': pass_form,
    }

    return render(request, 'Hyper_Local_Weather/account.html', context)


@login_required
def update_avatar(request):
    if request.method == 'POST':
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=request.user)

        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if p_form.is_valid():
            p_form.save()
            messages.success(request, 'Your avatar has been updated!')
        else:
            messages.error(request, 'Please correct the error below.')
    return redirect('Hyper_Local_Weather:account')

def historical(request):
    readings = WeatherReading.objects.all().order_by('-timestamp')
    context = {
        'readings': readings
    }
    return render(request, 'Hyper_Local_Weather/historical.html', context)

def auth_page(request):
    """Unified authentication page for both login and signup"""
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('Hyper_Local_Weather:index')
    
    signup_form = SignUpForm()
    login_error = None
    signup_error = None
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'login-submit' in request.POST or request.POST.get('action') == 'login':
            # Handle login
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('Hyper_Local_Weather:index')
            else:
                login_error = "Invalid username or password."
        
        elif 'signup-submit' in request.POST or request.POST.get('action') == 'signup':
            # Handle signup
            signup_form = SignUpForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user)
                return redirect('Hyper_Local_Weather:index')
            else:
                signup_error = "Please correct the errors below."
    
    context = {
        'form': None,
        'signup_form': signup_form,
        'login_error': login_error,
        'signup_error': signup_error,
    }
    
    return render(request, 'registration/auth.html', context)

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('Hyper_Local_Weather:index')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

def index(request, date=None):
    view_mode = request.GET.get('mode', 'outdoor')
    if view_mode not in ('indoor', 'outdoor'):
        view_mode = 'outdoor'

    # MOCK DATA FALLBACKS:
    # Keep these values obvious and centralized so they can be replaced
    # with live sensor/public API data later.
    mock_values = {
        'indoor_temp': 22,
        'outdoor_temp': 23,
        'air_quality': 50,
        'humidity': 63,
        'pressure_hpa': 1013,
    }

    locations = Location.objects.all()
    locations_with_readings = []
    for loc in locations:
        latest_reading = WeatherReading.objects.filter(location=loc).order_by('-timestamp').first()
        locations_with_readings.append({
            'pk': loc.pk,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'latest_reading': {
                'air_quality': latest_reading.air_quality if latest_reading else None
            }
        })

    if date:
        current_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        current_date = timezone.now().date()

    # Get latest indoor and outdoor temperatures
    indoor_location = Location.objects.filter(name__icontains='indoor').first()
    outdoor_location = Location.objects.filter(name__icontains='outdoor').first()

    latest_indoor_reading = None
    if indoor_location:
        latest_indoor_reading = WeatherReading.objects.filter(
            location=indoor_location,
            timestamp__date=current_date
        ).order_by('-timestamp').first()

    latest_outdoor_reading = None
    if outdoor_location:
        latest_outdoor_reading = WeatherReading.objects.filter(
            location=outdoor_location,
            timestamp__date=current_date
        ).order_by('-timestamp').first()

    # Leeds-only outdoor mode for now (geolocation can replace this later).
    outdoor_latitude = LEEDS_OUTDOOR_COORDS['latitude']
    outdoor_longitude = LEEDS_OUTDOOR_COORDS['longitude']
    live_outdoor_weather = None
    live_outdoor_air_quality = None
    try:
        live_outdoor_weather = _fetch_open_meteo_outdoor_weather(outdoor_latitude, outdoor_longitude)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        live_outdoor_weather = None

    try:
        live_outdoor_air_quality = _fetch_open_meteo_air_quality(outdoor_latitude, outdoor_longitude)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        live_outdoor_air_quality = None

    active_reading = latest_indoor_reading if view_mode == 'indoor' else latest_outdoor_reading

    indoor_temp_value = latest_indoor_reading.temperature_c if latest_indoor_reading else mock_values['indoor_temp']
    outdoor_temp_value = (
        live_outdoor_weather['temperature_c']
        if live_outdoor_weather and live_outdoor_weather.get('temperature_c') is not None
        else latest_outdoor_reading.temperature_c if latest_outdoor_reading else mock_values['outdoor_temp']
    )
    if view_mode == 'outdoor':
        api_aqi = None
        if live_outdoor_air_quality:
            if live_outdoor_air_quality.get('european_aqi') is not None:
                api_aqi = live_outdoor_air_quality.get('european_aqi')
            elif live_outdoor_air_quality.get('pm25') is not None:
                # Keep AQI scale readable for current UI thresholds.
                api_aqi = round(float(live_outdoor_air_quality.get('pm25')) * 2.0)

        air_quality_value = (
            api_aqi
            if api_aqi is not None
            else latest_outdoor_reading.air_quality if latest_outdoor_reading and latest_outdoor_reading.air_quality is not None else mock_values['air_quality']
        )
        humidity_value = (
            live_outdoor_weather['humidity']
            if live_outdoor_weather and live_outdoor_weather.get('humidity') is not None
            else latest_outdoor_reading.humidity if latest_outdoor_reading else mock_values['humidity']
        )
        pressure_value = (
            live_outdoor_weather['pressure_hpa']
            if live_outdoor_weather and live_outdoor_weather.get('pressure_hpa') is not None
            else latest_outdoor_reading.pressure_hpa if latest_outdoor_reading else mock_values['pressure_hpa']
        )
        is_mock_air_quality = api_aqi is None and (latest_outdoor_reading is None or latest_outdoor_reading.air_quality is None)
        is_mock_humidity = (live_outdoor_weather is None or live_outdoor_weather.get('humidity') is None) and latest_outdoor_reading is None
        is_mock_pressure = (live_outdoor_weather is None or live_outdoor_weather.get('pressure_hpa') is None) and latest_outdoor_reading is None
    else:
        air_quality_value = (
            active_reading.air_quality
            if active_reading and active_reading.air_quality is not None
            else mock_values['air_quality']
        )
        humidity_value = active_reading.humidity if active_reading else mock_values['humidity']
        pressure_value = active_reading.pressure_hpa if active_reading else mock_values['pressure_hpa']
        is_mock_air_quality = active_reading is None or active_reading.air_quality is None
        is_mock_humidity = active_reading is None
        is_mock_pressure = active_reading is None

    past_week_temps = []
    for i in range(6, -1, -1):
        day = current_date - timedelta(days=i)
        avg_temp_data = WeatherReading.objects.filter(timestamp__date=day).aggregate(avg_temp=Avg('temperature_c'))
        
        avg_temp = avg_temp_data['avg_temp']
        
        past_week_temps.append({
            'day_name': day.strftime('%a')[0],
            'avg_temp': round(avg_temp) if avg_temp is not None else 'N/A'
        })

    previous_week = current_date - timedelta(weeks=1)
    next_week = current_date + timedelta(weeks=1)

    is_current_week = next_week > timezone.now().date()


    context = {
        'locations': locations_with_readings,
        'view_mode': view_mode,
        'latest_indoor_temp': indoor_temp_value,
        'latest_outdoor_temp': outdoor_temp_value,
        'current_air_quality': air_quality_value,
        'current_humidity': humidity_value,
        'current_pressure': pressure_value,
        'is_mock_indoor_temp': latest_indoor_reading is None,
        'is_mock_outdoor_temp': (live_outdoor_weather is None or live_outdoor_weather.get('temperature_c') is None) and latest_outdoor_reading is None,
        'is_mock_air_quality': is_mock_air_quality,
        'is_mock_humidity': is_mock_humidity,
        'is_mock_pressure': is_mock_pressure,
        'past_week_temps': past_week_temps,
        'current_date': current_date,
        'previous_week': previous_week.strftime('%Y-%m-%d'),
        'next_week': next_week.strftime('%Y-%m-%d'),
        'is_current_week': is_current_week,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'past_week_temps': past_week_temps,
            'current_date': current_date.strftime('%b %d, %Y'),
            'previous_week': previous_week.strftime('%Y-%m-%d'),
            'next_week': next_week.strftime('%Y-%m-%d'),
            'is_current_week': is_current_week,
        })

    return render(request, 'Hyper_Local_Weather/index.html', context)

# AJAX endpoint to update location
@csrf_exempt
def update_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            location = {
                'lat': data.get('lat'),
                'lon': data.get('lon')
            }
            request.session['location'] = location
            return JsonResponse({'status': 'success', 'location': location})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def _parse_pi_timestamp(value):
    if not value:
        return timezone.now()

    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, timezone.get_current_timezone())

    if not isinstance(value, str):
        return timezone.now()

    candidate = value.strip().replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return timezone.now()

    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _coerce_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@csrf_exempt
def ingest_pi_reading(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        data = request.POST.dict()

    temperature_c = _coerce_decimal(data.get('temperature_c') or data.get('temperature'))
    humidity = _coerce_decimal(data.get('humidity'))
    pressure_hpa = _coerce_decimal(data.get('pressure_hpa') or data.get('pressure'))
    if temperature_c is None or humidity is None or pressure_hpa is None:
        return JsonResponse(
            {'status': 'error', 'message': 'temperature_c, humidity, and pressure_hpa are required'},
            status=400,
        )

    gas_resistance = _coerce_decimal(data.get('gas_resistance_ohms') or data.get('gas') or data.get('air_quality'))
    latitude = _coerce_decimal(data.get('latitude'))
    longitude = _coerce_decimal(data.get('longitude'))
    device_id = (data.get('device_id') or 'raspberry-pi').strip() or 'raspberry-pi'
    location_name = (data.get('location_name') or device_id).strip() or device_id
    location_id = data.get('location_id')

    location = None
    if location_id not in (None, ''):
        try:
            location = Location.objects.get(pk=location_id)
        except (Location.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid location_id'}, status=400)
    elif latitude is not None and longitude is not None:
        location, _ = Location.objects.update_or_create(
            name=location_name,
            defaults={'latitude': latitude, 'longitude': longitude},
        )
    else:
        return JsonResponse(
            {'status': 'error', 'message': 'location_id or latitude/longitude are required'},
            status=400,
        )

    reading = WeatherReading.objects.create(
        location=location,
        timestamp=_parse_pi_timestamp(data.get('timestamp')),
        temperature_c=float(temperature_c),
        humidity=float(humidity),
        pressure_hpa=float(pressure_hpa),
        air_quality=float(gas_resistance) if gas_resistance is not None else None,
    )

    return JsonResponse(
        {
            'status': 'success',
            'reading_id': reading.pk,
            'location_id': location.pk,
            'location_name': location.name,
        },
        status=201,
    )


def uk_air_quality_data(request):
    points = []
    for location in UK_AQ_LOCATIONS:
        pm25_value = None
        data_source = 'fallback'

        try:
            pm25_value = _fetch_open_meteo_pm25(location['latitude'], location['longitude'])
            data_source = 'open-meteo'
        except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
            # Use a deterministic fallback for local demos when API is unavailable.
            pm25_value = round(8 + (abs(location['latitude']) + abs(location['longitude'])) % 28, 1)

        zone = _aq_zone_from_pm25(pm25_value)

        points.append({
            'name': location['name'],
            'latitude': location['latitude'],
            'longitude': location['longitude'],
            'pm25': pm25_value,
            'zone': zone['zone'],
            'zone_label': zone['label'],
            'zone_color': zone['color'],
            'source': data_source,
        })

    return JsonResponse({'points': points})


def leeds_air_quality_grid(request):
    payload = _build_live_leeds_grid_payload()
    return JsonResponse(payload)


def uk_sensor_hex_data(request):
    payload = _build_uk_sensor_hex_payload()
    return JsonResponse(payload)


def location_detail(request, pk):
    location = get_object_or_404(Location, pk=pk)
    return render(request, 'Hyper_Local_Weather/location_detail.html', {'location': location})


@login_required
def settings_page(request):
    # --- Avatar Selection Logic ---
    avatar_dir = os.path.join(settings.BASE_DIR, 'static', 'User_Icons')
    try:
        avatars = [f for f in os.listdir(avatar_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    except FileNotFoundError:
        avatars = []

    # --- Form and Message Initialization ---
    profile_form = ChangeProfileForm(instance=request.user)
    password_form = PasswordChangeForm()
    profile_success = profile_error = password_success = password_error = None
    avatar_success = None

    # --- Handle POST Requests ---
    if request.method == 'POST':
        if 'change_avatar' in request.POST:
            selected_avatar = request.POST.get('avatar')
            if selected_avatar:
                try:
                    profile, created = Profile.objects.get_or_create(user=request.user)
                    profile.image = os.path.join('User_Icons', selected_avatar)
                    profile.save()
                    avatar_success = 'Profile picture updated successfully.'
                except Exception as e:
                    pass  # Consider logging the error e

        elif 'update_profile' in request.POST:
            profile_form = ChangeProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                profile_success = 'Profile updated successfully.'
            else:
                profile_error = 'Please correct the errors below.'

        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                if request.user.check_password(password_form.cleaned_data['current_password']):
                    request.user.set_password(password_form.cleaned_data['new_password'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    password_success = 'Password changed successfully.'
                    password_form = PasswordChangeForm()
                else:
                    password_form.add_error('current_password', 'Current password is incorrect.')
                    password_error = 'Please correct the errors below.'
            else:
                password_error = 'Please correct the errors below.'

    # --- Prepare Context for Template ---
    context = {
        'avatars': avatars,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_success': profile_success,
        'profile_error': profile_error,
        'password_success': password_success,
        'password_error': password_error,
        'avatar_success': avatar_success,
    }
    
    return render(request, 'Hyper_Local_Weather/settings.html', context)


@user_passes_test(lambda u: u.is_active and u.is_staff)
def authorisations(request):
    action_success = action_error = None

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        if user_id and action in ('grant', 'revoke'):
            try:
                target = User.objects.get(pk=user_id)
                if action == 'grant':
                    target.is_staff = True
                    target.save()
                    action_success = f"Staff access granted to {target.username}."
                elif target.pk != request.user.pk:
                    target.is_staff = False
                    target.save()
                    action_success = f"Staff access removed from {target.username}."
                else:
                    action_error = "You cannot remove your own staff access."
            except User.DoesNotExist:
                action_error = "User not found."

    users = User.objects.all().order_by('username')
    return render(request, 'Hyper_Local_Weather/authorisations.html', {
        'users': users,
        'action_success': action_success,
        'action_error': action_error,
    })


@login_required
def account(request):
    """User account settings page."""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                return redirect('Hyper_Local_Weather:account')
        elif 'change_password' in request.POST:
            pass_form = PasswordChangeForm(request.POST)
            if pass_form.is_valid():
                user = request.user
                current_password = pass_form.cleaned_data['current_password']
                if user.check_password(current_password):
                    user.set_password(pass_form.cleaned_data['new_password'])
                    user.save()
                    update_session_auth_hash(request, user)  # Important!
                    return redirect('Hyper_Local_Weather:account')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)
        pass_form = PasswordChangeForm()

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'pass_form': pass_form,
    }

    return render(request, 'Hyper_Local_Weather/account.html', context)
