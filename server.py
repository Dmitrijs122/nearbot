import os
import httpx
import logging
import random
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NearBot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CATEGORIES = {
    "friends": {
        "name": "С друзьями",
        "emoji": "👫",
        "osm_query": '(node["leisure"~"park|garden|beach_resort|picnic_table"](around:{radius},{lat},{lon}); node["tourism"~"viewpoint|attraction"](around:{radius},{lat},{lon}); node["amenity"~"bbq"](around:{radius},{lat},{lon}); way["leisure"~"park|garden|beach"](around:{radius},{lat},{lon}); way["natural"~"beach|water"](around:{radius},{lat},{lon}););'
    },
    "water": {
        "name": "Водоёмы",
        "emoji": "🏖️",
        "osm_query": '(node["natural"~"beach|spring"](around:{radius},{lat},{lon}); node["leisure"~"beach_resort|swimming_area"](around:{radius},{lat},{lon}); way["natural"~"water|beach"](around:{radius},{lat},{lon}); way["waterway"~"river|stream|canal"](around:{radius},{lat},{lon}); relation["natural"="water"](around:{radius},{lat},{lon}););'
    },
    "picnic": {
        "name": "Пикник",
        "emoji": "🧺",
        "osm_query": '(node["leisure"="picnic_table"](around:{radius},{lat},{lon}); node["amenity"~"bbq|bench"](around:{radius},{lat},{lon}); node["tourism"="picnic_site"](around:{radius},{lat},{lon}); node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon}); way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon}););'
    },
    "monuments": {
        "name": "Памятники",
        "emoji": "🗿",
        "osm_query": '(node["historic"~"memorial|monument|ruins|castle|archaeological_site"](around:{radius},{lat},{lon}); node["tourism"~"artwork|attraction"](around:{radius},{lat},{lon}); node["man_made"="obelisk"](around:{radius},{lat},{lon}););'
    },
    "viewpoints": {
        "name": "Смотровые",
        "emoji": "🔭",
        "osm_query": '(node["tourism"="viewpoint"](around:{radius},{lat},{lon}); node["natural"~"peak|cliff|hill"](around:{radius},{lat},{lon}); way["natural"~"cliff|ridge"](around:{radius},{lat},{lon}););'
    },
    "food": {
        "name": "Еда",
        "emoji": "🍕",
        "osm_query": '(node["amenity"~"restaurant|cafe|fast_food|bar|pub|ice_cream"](around:{radius},{lat},{lon}););'
    },
    "nature": {
        "name": "Природа",
        "emoji": "🌿",
        "osm_query": '(node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon}); way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon}); way["natural"~"wood|forest"](around:{radius},{lat},{lon}););'
    },
    "culture": {
        "name": "Культура",
        "emoji": "🏛️",
        "osm_query": '(node["tourism"~"museum|gallery|attraction"](around:{radius},{lat},{lon}); node["historic"~"memorial|monument|castle|ruins"](around:{radius},{lat},{lon}); node["amenity"~"library|arts_centre"](around:{radius},{lat},{lon}););'
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "osm_query": '(node["leisure"~"fitness_centre|swimming_pool|stadium|sports_centre|ice_rink"](around:{radius},{lat},{lon}); way["leisure"~"pitch|sports_centre|track"](around:{radius},{lat},{lon}););'
    },
    "all": {
        "name": "Всё рядом",
        "emoji": "🗺️",
        "osm_query": '(node["amenity"~"restaurant|cafe|bar"](around:{radius},{lat},{lon}); node["tourism"~"museum|attraction|viewpoint"](around:{radius},{lat},{lon}); node["leisure"~"park|beach_resort"](around:{radius},{lat},{lon}); node["historic"~"memorial|monument"](around:{radius},{lat},{lon}); node["natural"~"beach"](around:{radius},{lat},{lon}););'
    }
}

# Резервные фото по категориям — красивые фото из Unsplash (бесплатно, без ключа)
FALLBACK_PHOTOS = {
    "water":      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=80",
    "picnic":     "https://images.unsplash.com/photo-1526401485004-46910ecc8e51?w=600&q=80",
    "monuments":  "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
    "viewpoints": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&q=80",
    "friends":    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
    "food":       "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",
    "nature":     "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&q=80",
    "culture":    "https://images.unsplash.com/photo-1605649487212-47bdab064df7?w=600&q=80",
    "sport":      "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80",
    "all":        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&q=80",
}

# Дополнительные фото для каждой категории (случайно выбирается одно)
EXTRA_PHOTOS = {
    "water": [
        "https://images.unsplash.com/photo-1439405326854-014607f694d7?w=600&q=80",
        "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=600&q=80",
        "https://images.unsplash.com/photo-1495567720989-cebdbdd97913?w=600&q=80",
    ],
    "picnic": [
        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=600&q=80",
        "https://images.unsplash.com/photo-1414609245224-aea4b59e3f31?w=600&q=80",
    ],
    "monuments": [
        "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80",
        "https://images.unsplash.com/photo-1525874684015-58379d421a52?w=600&q=80",
    ],
    "nature": [
        "https://images.unsplash.com/photo-1448375240586-882707db888b?w=600&q=80",
        "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&q=80",
    ],
    "friends": [
        "https://images.unsplash.com/photo-1543269664-56d93c1b41a6?w=600&q=80",
        "https://images.unsplash.com/photo-1511988617509-a57c8a288659?w=600&q=80",
    ],
}


async def get_photo_for_place(name: str, category: str) -> str:
    """
    Ищет фото места тремя способами по очереди:
    1. Wikipedia API — ищет фото по названию места
    2. Wikimedia Commons — ищет фото в базе Википедии
    3. Красивое резервное фото по категории из Unsplash
    """
    # Способ 1: Wikipedia на русском
    photo = await try_wikipedia_photo(name, "ru")
    if photo:
        return photo

    # Способ 2: Wikipedia на английском
    photo = await try_wikipedia_photo(name, "en")
    if photo:
        return photo

    # Способ 3: резервное фото по категории
    extras = EXTRA_PHOTOS.get(category, [])
    if extras:
        return random.choice(extras)
    return FALLBACK_PHOTOS.get(category, FALLBACK_PHOTOS["all"])


async def try_wikipedia_photo(name: str, lang: str) -> str | None:
    """Пробует найти фото в Wikipedia на указанном языке."""
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            resp = await client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": name,
                    "prop": "pageimages",
                    "piprop": "thumbnail",
                    "pithumbsize": 600,
                    "format": "json",
                    "redirects": 1
                }
            )
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                t = page.get("thumbnail")
                if t and t.get("source"):
                    return t["source"]
    except Exception:
        pass
    return None


async def fetch_places_from_osm(lat: float, lon: float, radius: int, category: str) -> list:
    cat_data = CATEGORIES.get(category, CATEGORIES["all"])
    osm_query_part = cat_data["osm_query"].format(radius=radius, lat=lat, lon=lon)
    query = f"[out:json][timeout:20];\n{osm_query_part}\nout center 30;"

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query}
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"Overpass error: {e}")
        return []

    places = []
    seen_names = set()

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:ru") or tags.get("name:en")
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        if element["type"] == "node":
            lat_p, lon_p = element.get("lat"), element.get("lon")
        else:
            center = element.get("center", {})
            lat_p, lon_p = center.get("lat"), center.get("lon")

        if not lat_p or not lon_p:
            continue

        place = {
            "id": str(element.get("id")),
            "name": name,
            "lat": lat_p,
            "lon": lon_p,
            "category": category,
            "tags": {
                "amenity": tags.get("amenity", ""),
                "cuisine": tags.get("cuisine", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "phone": tags.get("phone") or tags.get("contact:phone", ""),
                "website": tags.get("website") or tags.get("contact:website", ""),
                "tourism": tags.get("tourism", ""),
                "leisure": tags.get("leisure", ""),
                "historic": tags.get("historic", ""),
                "natural": tags.get("natural", ""),
                "description": tags.get("description", ""),
            }
        }

        # Получаем фото (Wikipedia или резервное красивое фото)
        place["photo"] = await get_photo_for_place(name, category)
        places.append(place)

        if len(places) >= 15:
            break

    return places


async def generate_ai_description(place: dict) -> str:
    tags = place.get("tags", {})
    info_parts = []
    for key in ["amenity", "cuisine", "opening_hours", "historic", "natural", "tourism", "leisure"]:
        if tags.get(key):
            info_parts.append(f"{key}: {tags[key]}")
    if tags.get("description"):
        info_parts.append(f"описание: {tags['description']}")
    info_str = ", ".join(info_parts) if info_parts else "нет доп. информации"

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помощник для путешественников в Латвии. "
                        "Пишешь короткие живые описания мест на русском языке. "
                        "Максимум 2 предложения. Стиль дружелюбный и интересный. "
                        "Не упоминай что ты AI."
                    )
                },
                {
                    "role": "user",
                    "content": f"Напиши описание места '{place['name']}'. Данные: {info_str}"
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "Интересное место, которое стоит посетить!"


@app.get("/api/places")
async def get_places(
    lat: float = Query(...),
    lon: float = Query(...),
    radius: int = Query(1000, ge=500, le=10000),
    category: str = Query("all")
):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Неверная категория")
    logger.info(f"Поиск: lat={lat}, lon={lon}, radius={radius}, cat={category}")
    places = await fetch_places_from_osm(lat, lon, radius, category)
    if not places:
        return {"places": [], "message": "Места не найдены"}
    return {"places": places, "total": len(places)}


@app.get("/api/description")
async def get_description(
    place_id: str = Query(...),
    name: str = Query(...),
    amenity: str = Query(""),
    cuisine: str = Query(""),
    opening_hours: str = Query(""),
    historic: str = Query(""),
    natural: str = Query(""),
    tourism: str = Query(""),
    leisure: str = Query(""),
):
    place = {
        "id": place_id,
        "name": name,
        "tags": {
            "amenity": amenity, "cuisine": cuisine,
            "opening_hours": opening_hours, "historic": historic,
            "natural": natural, "tourism": tourism, "leisure": leisure,
        }
    }
    description = await generate_ai_description(place)
    return {"description": description}


@app.get("/api/categories")
async def get_categories():
    return {
        "categories": [
            {"id": k, "name": v["name"], "emoji": v["emoji"]}
            for k, v in CATEGORIES.items()
        ]
    }


@app.get("/api/random")
async def get_random_place(lat: float = Query(...), lon: float = Query(...)):
    import random
    places = await fetch_places_from_osm(lat, lon, 5000, "friends")
    if not places:
        places = await fetch_places_from_osm(lat, lon, 5000, "all")
    if not places:
        return {"place": None}
    place = random.choice(places)
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Пиши загадочно и заманчиво про место. 2 предложения. На русском."},
                {"role": "user", "content": f"Опиши место '{place['name']}' как загадочное приключение"}
            ],
            max_tokens=120
        )
        place["ai_teaser"] = completion.choices[0].message.content.strip()
    except:
        place["ai_teaser"] = "Это место скрывает свои секреты... Ты готов узнать больше?"
    return {"place": place}


app.mount("/", StaticFiles(directory=".", html=True), name="webapp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
