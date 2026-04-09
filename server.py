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

# ══════════════════════════════════════════════
# КАТЕГОРИИ — широкие запросы чтобы найти ВСЕГДА
# Используем nwr = node + way + relation чтобы не пропустить ничего
# ══════════════════════════════════════════════
CATEGORIES = {
    "all": {
        "name": "Всё рядом", "emoji": "🗺️",
        # Самый широкий запрос — всё что есть рядом с именем
        "osm_query": """(
  nwr["amenity"](around:{radius},{lat},{lon});
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["tourism"](around:{radius},{lat},{lon});
  nwr["leisure"](around:{radius},{lat},{lon});
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["natural"~"beach|water|peak|spring|wood"](around:{radius},{lat},{lon});
);"""
    },
    "friends": {
        "name": "С друзьями", "emoji": "👫",
        "osm_query": """(
  nwr["leisure"~"park|garden|beach_resort|picnic_table|playground|sports_centre|bowling_alley|escape_game|miniature_golf|water_park|amusement_arcade"](around:{radius},{lat},{lon});
  nwr["tourism"~"viewpoint|attraction|theme_park|zoo"](around:{radius},{lat},{lon});
  nwr["amenity"~"cinema|theatre|nightclub|bar|pub|ice_cream|bbq"](around:{radius},{lat},{lon});
  nwr["natural"~"beach|water"](around:{radius},{lat},{lon});
);"""
    },
    "water": {
        "name": "Водоёмы", "emoji": "🏖️",
        "osm_query": """(
  nwr["natural"~"beach|water|spring|wetland"](around:{radius},{lat},{lon});
  nwr["leisure"~"beach_resort|swimming_area|swimming_pool"](around:{radius},{lat},{lon});
  nwr["waterway"~"river|stream|canal|lake"](around:{radius},{lat},{lon});
  nwr["amenity"~"swimming_pool"](around:{radius},{lat},{lon});
);"""
    },
    "picnic": {
        "name": "Пикник", "emoji": "🧺",
        "osm_query": """(
  nwr["leisure"~"park|garden|nature_reserve|picnic_table|firepit"](around:{radius},{lat},{lon});
  nwr["tourism"="picnic_site"](around:{radius},{lat},{lon});
  nwr["amenity"~"bbq|bench"](around:{radius},{lat},{lon});
  nwr["natural"~"wood|forest|grassland|heath|scrub"](around:{radius},{lat},{lon});
);"""
    },
    "monuments": {
        "name": "Памятники", "emoji": "🗿",
        "osm_query": """(
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["tourism"~"museum|gallery|artwork|attraction|monument"](around:{radius},{lat},{lon});
  nwr["amenity"~"place_of_worship|library|arts_centre"](around:{radius},{lat},{lon});
  nwr["man_made"~"obelisk|tower|lighthouse"](around:{radius},{lat},{lon});
);"""
    },
    "viewpoints": {
        "name": "Смотровые", "emoji": "🔭",
        "osm_query": """(
  nwr["tourism"="viewpoint"](around:{radius},{lat},{lon});
  nwr["natural"~"peak|cliff|hill|ridge"](around:{radius},{lat},{lon});
  nwr["man_made"~"tower|observation_tower|lighthouse"](around:{radius},{lat},{lon});
);"""
    },
    "food": {
        "name": "Еда", "emoji": "🍕",
        "osm_query": """(
  nwr["amenity"~"restaurant|cafe|fast_food|bar|pub|food_court|ice_cream|bakery|biergarten|juice_bar|coffee"](around:{radius},{lat},{lon});
  nwr["shop"~"bakery|pastry|deli|cheese|butcher|seafood|farm"](around:{radius},{lat},{lon});
);"""
    },
    "shopping": {
        "name": "Шопинг", "emoji": "🛍️",
        "osm_query": """(
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["amenity"~"marketplace|pharmacy|bank|atm"](around:{radius},{lat},{lon});
);"""
    },
    "nature": {
        "name": "Природа", "emoji": "🌿",
        "osm_query": """(
  nwr["leisure"~"park|garden|nature_reserve|dog_park"](around:{radius},{lat},{lon});
  nwr["natural"~"wood|forest|grassland|heath|scrub|beach|water|spring|peak"](around:{radius},{lat},{lon});
  nwr["landuse"~"forest|meadow|grass|recreation_ground"](around:{radius},{lat},{lon});
);"""
    },
    "culture": {
        "name": "Культура", "emoji": "🏛️",
        "osm_query": """(
  nwr["tourism"~"museum|gallery|attraction|artwork"](around:{radius},{lat},{lon});
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["amenity"~"theatre|cinema|library|arts_centre|community_centre|place_of_worship"](around:{radius},{lat},{lon});
);"""
    },
    "sport": {
        "name": "Спорт", "emoji": "⚽",
        "osm_query": """(
  nwr["leisure"~"fitness_centre|swimming_pool|stadium|sports_centre|ice_rink|golf_course|tennis|track|pitch|skate_park|climbing"](around:{radius},{lat},{lon});
  nwr["sport"](around:{radius},{lat},{lon});
  nwr["amenity"~"swimming_pool|gym"](around:{radius},{lat},{lon});
);"""
    },
}

# ══════════════════════════════════════════════
# РЕЗЕРВНЫЕ ФОТО ПО КАТЕГОРИЯМ (Unsplash)
# ══════════════════════════════════════════════
FALLBACK_PHOTOS = {
    "all":        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&q=80",
    "friends":    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
    "water":      "https://images.unsplash.com/photo-1439405326854-014607f694d7?w=600&q=80",
    "picnic":     "https://images.unsplash.com/photo-1526401485004-46910ecc8e51?w=600&q=80",
    "monuments":  "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
    "viewpoints": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&q=80",
    "food":       "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",
    "shopping":   "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=80",
    "nature":     "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&q=80",
    "culture":    "https://images.unsplash.com/photo-1605649487212-47bdab064df7?w=600&q=80",
    "sport":      "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80",
}

EXTRA_PHOTOS = {
    "water":   ["https://images.unsplash.com/photo-1501854140801-50d01698950b?w=600&q=80",
                "https://images.unsplash.com/photo-1495567720989-cebdbdd97913?w=600&q=80"],
    "food":    ["https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&q=80",
                "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?w=600&q=80"],
    "nature":  ["https://images.unsplash.com/photo-1448375240586-882707db888b?w=600&q=80",
                "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&q=80"],
    "shopping":["https://images.unsplash.com/photo-1567958451986-2de427a4a0be?w=600&q=80",
                "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=600&q=80"],
    "culture": ["https://images.unsplash.com/photo-1566438480900-0609be27a4be?w=600&q=80",
                "https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=600&q=80"],
}


async def get_photo_for_place(name: str, category: str) -> str:
    photo = await try_wikipedia_photo(name, "ru")
    if photo:
        return photo
    photo = await try_wikipedia_photo(name, "en")
    if photo:
        return photo
    extras = EXTRA_PHOTOS.get(category, [])
    if extras:
        return random.choice(extras)
    return FALLBACK_PHOTOS.get(category, FALLBACK_PHOTOS["all"])


async def try_wikipedia_photo(name: str, lang: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action":"query","titles":name,"prop":"pageimages",
                        "piprop":"thumbnail","pithumbsize":600,"format":"json","redirects":1}
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
    # out center — возвращает координаты центра для way/relation
    # 50 — максимум объектов
    query = f"[out:json][timeout:25];\n{osm_query_part}\nout center 50;"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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

        # Берём название на любом языке
        name = (tags.get("name") or tags.get("name:ru") or
                tags.get("name:lv") or tags.get("name:en"))

        # Если нет имени — генерируем из типа
        if not name:
            amenity = tags.get("amenity", "")
            shop = tags.get("shop", "")
            tourism = tags.get("tourism", "")
            historic = tags.get("historic", "")
            leisure = tags.get("leisure", "")
            natural = tags.get("natural", "")
            # Используем тип как запасное имя
            type_val = amenity or shop or tourism or historic or leisure or natural
            if type_val:
                name = type_val.replace("_", " ").title()
            else:
                continue  # совсем нет данных — пропускаем

        if name in seen_names:
            continue
        seen_names.add(name)

        # Координаты
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
                "amenity":       tags.get("amenity", ""),
                "shop":          tags.get("shop", ""),
                "cuisine":       tags.get("cuisine", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "phone":         tags.get("phone") or tags.get("contact:phone", ""),
                "website":       tags.get("website") or tags.get("contact:website", ""),
                "tourism":       tags.get("tourism", ""),
                "leisure":       tags.get("leisure", ""),
                "historic":      tags.get("historic", ""),
                "natural":       tags.get("natural", ""),
                "description":   tags.get("description", ""),
            }
        }

        place["photo"] = await get_photo_for_place(name, category)
        places.append(place)

        if len(places) >= 20:
            break

    return places


async def generate_ai_description(place: dict) -> str:
    tags = place.get("tags", {})
    info_parts = []
    for key in ["amenity","shop","cuisine","opening_hours","historic","natural","tourism","leisure"]:
        if tags.get(key):
            info_parts.append(f"{key}: {tags[key]}")
    if tags.get("description"):
        info_parts.append(f"описание: {tags['description']}")
    info_str = ", ".join(info_parts) if info_parts else "место"

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":"Ты помощник в Латвии. Пишешь короткие живые описания мест на русском. Максимум 2 предложения. Дружелюбно и интересно. Не упоминай что ты AI."},
                {"role":"user","content":f"Опиши место '{place['name']}'. Данные: {info_str}"}
            ],
            max_tokens=150, temperature=0.7
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "Интересное место, которое стоит посетить!"


@app.get("/api/places")
async def get_places(
    lat: float = Query(...), lon: float = Query(...),
    radius: int = Query(1000, ge=300, le=10000),
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
    place_id: str = Query(...), name: str = Query(...),
    amenity: str = Query(""), shop: str = Query(""),
    cuisine: str = Query(""), opening_hours: str = Query(""),
    historic: str = Query(""), natural: str = Query(""),
    tourism: str = Query(""), leisure: str = Query(""),
):
    place = {"id": place_id, "name": name, "tags": {
        "amenity": amenity, "shop": shop, "cuisine": cuisine,
        "opening_hours": opening_hours, "historic": historic,
        "natural": natural, "tourism": tourism, "leisure": leisure,
    }}
    return {"description": await generate_ai_description(place)}


@app.get("/api/categories")
async def get_categories():
    return {"categories": [
        {"id": k, "name": v["name"], "emoji": v["emoji"]}
        for k, v in CATEGORIES.items()
    ]}


@app.get("/api/random")
async def get_random_place(lat: float = Query(...), lon: float = Query(...)):
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
                {"role":"system","content":"Пиши загадочно и заманчиво про место. 2 предложения. На русском."},
                {"role":"user","content":f"Опиши место '{place['name']}' как загадочное приключение"}
            ],
            max_tokens=120
        )
        place["ai_teaser"] = completion.choices[0].message.content.strip()
    except:
        place["ai_teaser"] = "Это место скрывает свои секреты..."
    return {"place": place}


app.mount("/", StaticFiles(directory=".", html=True), name="webapp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
