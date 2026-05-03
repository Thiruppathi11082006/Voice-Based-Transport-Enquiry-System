import folium
import polyline
import requests
from folium.plugins import AntPath, TimestampedGeoJson
from streamlit_folium import st_folium


CITY_COORDS = {
    "chennai": (13.0827, 80.2707),
    "trichy": (10.7905, 78.7047),
    "madurai": (9.9252, 78.1198),
    "coimbatore": (11.0168, 76.9558),
    "salem": (11.6643, 78.1460),
    "tirunelveli": (8.7139, 77.7567),
    "erode": (11.3410, 77.7172),
    "vellore": (12.9165, 79.1325),
    "thanjavur": (10.7870, 79.1378),
    "thoothukudi": (8.7642, 78.1348),
    "tiruppur": (11.1085, 77.3411),
    "dindigul": (10.3673, 77.9803),
    "karur": (10.9601, 78.0766),
    "virudhunagar": (9.5851, 77.9570),
    "nilgiris": (11.4102, 76.6950),
    "nagercoil": (8.1833, 77.4119),
    "tiruvannamalai": (12.2253, 79.0747),
    "kumbakonam": (10.9601, 79.3845),
    "nagapattinam": (10.7667, 79.8333),
}

VOICE_CORRECTIONS = {
    "pretty": "trichy",
    "tree": "trichy",
    "maduri": "madurai",
    "combatore": "coimbatore",
    "selam": "salem",
    "nellai": "tirunelveli",
    "tuticorin": "thoothukudi",
    "toothukudi": "thoothukudi",
    "vellor": "vellore",
    "tanjavur": "thanjavur",
    "thanjore": "thanjavur",
    "tripur": "tiruppur",
    "dindugal": "dindigul",
    "nagarkoil": "nagercoil",
    "kumbakonum": "kumbakonam",
}


def apply_voice_corrections(text):
    fixed = text.lower().strip()
    for wrong, correct in VOICE_CORRECTIONS.items():
        fixed = fixed.replace(wrong, correct)
    return fixed


def extract_cities_from_text(text, supported_cities):
    words = text.split()
    if "from" in words and "to" in words:
        try:
            source = words[words.index("from") + 1]
            destination = words[words.index("to") + 1]
            if source in supported_cities and destination in supported_cities:
                return source, destination
        except IndexError:
            return None, None
    found = [city for city in supported_cities if city in words]
    return (found[0], found[1]) if len(found) >= 2 else (None, None)


def get_route_details(src, dst):
    start, end = CITY_COORDS[src], CITY_COORDS[dst]
    url = f"https://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full&geometries=polyline"
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        route = response.json()["routes"][0]
        return {
            "start": start,
            "end": end,
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60,
            "geometry": polyline.decode(route["geometry"]),
        }
    except Exception:
        return {"start": start, "end": end, "distance_km": 0, "duration_min": 0, "geometry": [start, end]}


def render_route_map(route_data, src, dst, key_suffix="primary", vehicle_name=None, vehicle_type=None):
    center = ((route_data["start"][0] + route_data["end"][0]) / 2, (route_data["start"][1] + route_data["end"][1]) / 2)
    route_map = folium.Map(location=center, zoom_start=7, control_scale=True)
    folium.Marker(route_data["start"], tooltip=src.title(), icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(route_data["end"], tooltip=dst.title(), icon=folium.Icon(color="red")).add_to(route_map)
    folium.PolyLine(route_data["geometry"], color="#1d4ed8", weight=4, opacity=0.45).add_to(route_map)
    AntPath(route_data["geometry"], color="#1d4ed8", pulse_color="#f97316", weight=6, delay=900, dash_array=[18, 22], opacity=0.9).add_to(route_map)

    if route_data["geometry"] and vehicle_name and vehicle_type:
        sampled = route_data["geometry"][:: max(1, len(route_data["geometry"]) // 24)]
        if sampled[-1] != route_data["geometry"][-1]:
            sampled.append(route_data["geometry"][-1])
        checkpoints = [
            f"Departed {src.title()}",
            f"Crossing outer {src.title()}",
            "Moving through central corridor",
            f"Approaching {dst.title()}",
            f"Near {dst.title()}",
        ]
        icon_url = "https://cdn-icons-png.flaticon.com/512/61/61231.png" if str(vehicle_type).lower() == "train" else "https://cdn-icons-png.flaticon.com/512/3448/3448339.png"
        features = []
        for idx, (lat, lon) in enumerate(sampled):
            checkpoint = checkpoints[min(len(checkpoints) - 1, int((idx / max(1, len(sampled) - 1)) * len(checkpoints)))]
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "time": f"2026-01-01T00:00:{idx:02d}Z",
                        "popup": f"{vehicle_name} ({vehicle_type})<br>Current location: {checkpoint}<br>Status: Running on schedule",
                        "iconstyle": {"iconUrl": icon_url, "iconSize": [28, 28]},
                    },
                }
            )
        TimestampedGeoJson(
            {"type": "FeatureCollection", "features": features},
            period="PT1S",
            add_last_point=True,
            auto_play=True,
            loop=True,
            max_speed=1,
            loop_button=True,
            date_options="ss",
            time_slider_drag_update=True,
        ).add_to(route_map)
        route_map.get_root().html.add_child(
            folium.Element(
                f"""
                <div style="position:absolute;right:14px;bottom:14px;z-index:9999;background:rgba(255,255,255,0.94);
                border:1px solid #dbeafe;border-radius:12px;padding:10px 12px;min-width:220px;
                box-shadow:0 8px 18px rgba(15,23,42,0.15);font-family:Arial,sans-serif;">
                    <div style="font-weight:700;color:#0f172a;">Virtual Live Tracking</div>
                    <div style="font-size:12px;color:#475569;margin-top:2px;">{vehicle_name} | {vehicle_type}</div>
                    <div style="font-size:13px;color:#0f172a;font-weight:700;margin-top:8px;">Current location</div>
                    <div style="font-size:13px;color:#334155;">Animated on route map</div>
                </div>
                """
            )
        )
    st_folium(route_map, height=460, width=None, key=f"map_{src}_{dst}_{key_suffix}")
