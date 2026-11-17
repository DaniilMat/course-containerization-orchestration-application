from contextlib import asynccontextmanager, closing
import json
import os
import time

import httpx
import psycopg2
import redis
from fastapi import FastAPI
from pydantic import BaseModel

OWNER = os.getenv("APP_OWNER", "anonymous")
SECRET_KEY = os.getenv("APP_SECRET", "default_secret")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "120"))
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def db_exec(query, params=None, fetch=False):
    """Выполняет запрос в PostgreSQL и закрывает соединение."""
    with closing(psycopg2.connect(DATABASE_URL, connect_timeout=3)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if fetch else None


def init_db():
    for _ in range(10):
        try:
            db_exec(
                "CREATE TABLE IF NOT EXISTS notes "
                "(id SERIAL PRIMARY KEY, text TEXT NOT NULL)"
            )
            return
        except Exception:
            time.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Personal Assistant", lifespan=lifespan)


class Note(BaseModel):
    text: str


@app.get("/")
async def root():
    return {
        "message": f"👋 Привет, {OWNER}!",
        "service": "personal-assistant",
        "version": "1.0",
        "endpoints": ["/me", "/notes", "/weather/{city}", "/cache/stats", "/secret/{key}"],
    }


@app.get("/health")
def health():
    try:
        db_exec("SELECT 1")
        db = "connected"
    except Exception:
        db = "unavailable"
    return {
        "status": "healthy" if db == "connected" else "unhealthy",
        "owner": OWNER,
        "database": db,
    }


@app.get("/me")
async def me():
    return {
        "owner": OWNER,
        "secret_prefix": SECRET_KEY[:6]
        if SECRET_KEY != "default_secret"
        else "NOT_SET",
    }


@app.get("/secret/{key}")
async def secret(key: str):
    """Secret endpoint - checking environment variables"""
    if key == SECRET_KEY:
        return {
            "flag": f"LAB2_SUCCESS_{OWNER.upper()}",
            "message": "The secret key is correct!",
        }
    return {
        "error": "The secret key is incorrect",
        "hint": "Check the APP_SECRET environment variable",
    }


WEATHER_CODES: dict[int, str] = {
    0: "☀️ Ясно", 1: "🌤 Малооблачно", 2: "⛅ Переменная облачность",
    3: "☁️ Пасмурно", 45: "🌫 Туман", 48: "🌫 Изморозь",
    51: "🌦 Лёгкая морось", 53: "🌦 Морось", 55: "🌧 Сильная морось",
    61: "🌧 Небольшой дождь", 63: "🌧 Дождь", 65: "🌧 Сильный дождь",
    71: "🌨 Небольшой снег", 73: "🌨 Снег", 75: "❄️ Сильный снег",
    80: "🌦 Ливень", 81: "🌧 Сильный ливень", 82: "⛈ Штормовой ливень",
    95: "⛈ Гроза", 96: "⛈ Гроза с градом", 99: "⛈ Сильная гроза с градом",
}


@app.get("/weather/{city}")
async def weather(city: str):
    cache_key = f"weather:{OWNER}:{city.lower()}"

    # Проверяем кэш
    cached = redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["source"] = "cache"
        return data

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            geo_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "ru"},
            )
            geo_data = geo_resp.json()

            if not geo_data.get("results"):
                return {"error": f"City «{city}» not found"}

            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            city_name = location.get("name", city)
            country = location.get("country", "")

            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                },
            )
            weather_data = weather_resp.json()["current"]
            code = weather_data.get("weather_code", -1)

            result = {
                "city": city_name,
                "country": country,
                "coordinates": {"lat": lat, "lon": lon},
                "temperature_c": weather_data["temperature_2m"],
                "humidity_pct": weather_data["relative_humidity_2m"],
                "wind_km_h": weather_data["wind_speed_10m"],
                "condition": WEATHER_CODES.get(code, f"Code {code}"),
                "source": "api",
            }
    except Exception as e:
        # ошибки внешнего API в кэш не кладём
        return {"error": f"Failed to get weather: {type(e).__name__}: {e}"}

    # Сохраняем в кэш
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


@app.get("/cache/stats")
async def cache_stats():
    keys = redis_client.keys(f"weather:{OWNER}:*")
    return {
        "owner": OWNER,
        "ttl_seconds": CACHE_TTL,
        "cached_count": len(keys),
        "cached_cities": sorted(k.split(":")[-1] for k in keys),
    }


@app.post("/notes")
def create_note(note: Note):
    rows = db_exec(
        "INSERT INTO notes (text) VALUES (%s) RETURNING id",
        (note.text,),
        fetch=True,
    )
    total = db_exec("SELECT COUNT(*) FROM notes", fetch=True)[0][0]
    return {"status": "saved", "note_id": rows[0][0], "total": total}


@app.get("/notes")
def list_notes():
    rows = db_exec("SELECT text FROM notes ORDER BY id", fetch=True)
    notes = [r[0] for r in rows]
    return {"notes": notes, "count": len(notes)}
