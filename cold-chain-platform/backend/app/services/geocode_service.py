import hashlib
import json
import urllib.parse
import urllib.request

from app.core.config import settings

DEPOT_POINT = {"lat": 32.3036, "lng": 118.3168}

LOCAL_GEOCODE_BOOK = {
    "滁州冷链中心": (32.3036, 118.3168),
    "明光路生鲜点": (32.3110, 118.3296),
    "清流路商超": (32.2868, 118.3332),
    "凤凰路门店": (32.3039, 118.3078),
    "会峰路门店": (32.2765, 118.3029),
    "丰乐大道门店": (32.2997, 118.2930),
    "琅琊区菜市场": (32.2945, 118.3160),
    "腰铺镇配送点": (32.2178, 118.2630),
    "城南农贸点": (32.2520, 118.3415),
    "南京大学": (32.1136, 118.9596),
    "东南大学": (32.0617, 118.8057),
    "南京农业大学": (32.0334, 118.8447),
}


def local_geocode(place: str | None) -> dict | None:
    if not place:
        return None
    for name, (lat, lng) in LOCAL_GEOCODE_BOOK.items():
        if name in place or place in name:
            return {"lat": lat, "lng": lng, "source": "local"}
    return None


def amap_geocode(place: str | None) -> dict | None:
    if not place or not settings.amap_key:
        return None
    query = urllib.parse.urlencode({"key": settings.amap_key, "address": place, "city": "滁州"})
    url = f"https://restapi.amap.com/v3/geocode/geo?{query}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    geocodes = payload.get("geocodes") or []
    if not geocodes:
        return None
    location = geocodes[0].get("location", "")
    try:
        lng_text, lat_text = location.split(",", 1)
        return {"lat": float(lat_text), "lng": float(lng_text), "source": "amap"}
    except ValueError:
        return None


def fallback_geocode(place: str | None) -> dict:
    digest = hashlib.sha1((place or "unknown").encode("utf-8")).hexdigest()
    lat_offset = (int(digest[:4], 16) / 0xFFFF - 0.5) * 0.10
    lng_offset = (int(digest[4:8], 16) / 0xFFFF - 0.5) * 0.12
    return {
        "lat": round(DEPOT_POINT["lat"] + lat_offset, 6),
        "lng": round(DEPOT_POINT["lng"] + lng_offset, 6),
        "source": "fallback",
    }


def geocode_destination(destination_name: str | None, destination_address: str | None = None) -> dict:
    place = destination_address or destination_name or ""
    return local_geocode(place) or local_geocode(destination_name) or amap_geocode(place) or fallback_geocode(place)
