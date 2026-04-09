import os, httpx, logging, random, json
from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NearBot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CATEGORIES = {
    "all": {"name":"Viss tuvumā","emoji":"◉","osm_query":"""(
  nwr["amenity"](around:{radius},{lat},{lon});
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["tourism"](around:{radius},{lat},{lon});
  nwr["leisure"](around:{radius},{lat},{lon});
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["natural"~"beach|water|peak|spring|wood"](around:{radius},{lat},{lon});
);"""},
    "friends": {"name":"Ar draugiem","emoji":"👫","osm_query":"""(
  nwr["leisure"~"park|garden|beach_resort|picnic_table|playground|sports_centre|bowling_alley|escape_game|miniature_golf|water_park|amusement_arcade"](around:{radius},{lat},{lon});
  nwr["tourism"~"viewpoint|attraction|theme_park|zoo"](around:{radius},{lat},{lon});
  nwr["amenity"~"cinema|theatre|nightclub|bar|pub|ice_cream|bbq"](around:{radius},{lat},{lon});
  nwr["natural"~"beach|water"](around:{radius},{lat},{lon});
);"""},
    "water": {"name":"Ūdenstilpes","emoji":"〰","osm_query":"""(
  nwr["natural"~"beach|water|spring|wetland"](around:{radius},{lat},{lon});
  nwr["leisure"~"beach_resort|swimming_area|swimming_pool"](around:{radius},{lat},{lon});
  nwr["waterway"~"river|stream|canal|lake"](around:{radius},{lat},{lon});
  nwr["amenity"~"swimming_pool"](around:{radius},{lat},{lon});
);"""},
    "picnic": {"name":"Pikniki","emoji":"⌂","osm_query":"""(
  nwr["leisure"~"park|garden|nature_reserve|picnic_table|firepit"](around:{radius},{lat},{lon});
  nwr["tourism"="picnic_site"](around:{radius},{lat},{lon});
  nwr["amenity"~"bbq|bench"](around:{radius},{lat},{lon});
  nwr["natural"~"wood|forest|grassland|heath|scrub"](around:{radius},{lat},{lon});
);"""},
    "monuments": {"name":"Pieminekļi","emoji":"◈","osm_query":"""(
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["tourism"~"museum|gallery|artwork|attraction|monument"](around:{radius},{lat},{lon});
  nwr["amenity"~"place_of_worship|library|arts_centre"](around:{radius},{lat},{lon});
  nwr["man_made"~"obelisk|tower|lighthouse"](around:{radius},{lat},{lon});
);"""},
    "viewpoints": {"name":"Skatu punkti","emoji":"⊙","osm_query":"""(
  nwr["tourism"="viewpoint"](around:{radius},{lat},{lon});
  nwr["natural"~"peak|cliff|hill|ridge"](around:{radius},{lat},{lon});
  nwr["man_made"~"tower|observation_tower|lighthouse"](around:{radius},{lat},{lon});
);"""},
    "food": {"name":"Ēdiens","emoji":"◆","osm_query":"""(
  nwr["amenity"~"restaurant|cafe|fast_food|bar|pub|food_court|ice_cream|bakery|biergarten|juice_bar"](around:{radius},{lat},{lon});
  nwr["shop"~"bakery|pastry|deli|cheese|butcher|seafood|farm"](around:{radius},{lat},{lon});
);"""},
    "shopping": {"name":"Iepirkšanās","emoji":"◇","osm_query":"""(
  nwr["shop"](around:{radius},{lat},{lon});
  nwr["amenity"~"marketplace|pharmacy|bank|atm"](around:{radius},{lat},{lon});
);"""},
    "nature": {"name":"Daba","emoji":"❋","osm_query":"""(
  nwr["leisure"~"park|garden|nature_reserve|dog_park"](around:{radius},{lat},{lon});
  nwr["natural"~"wood|forest|grassland|heath|scrub|beach|water|spring|peak"](around:{radius},{lat},{lon});
  nwr["landuse"~"forest|meadow|grass|recreation_ground"](around:{radius},{lat},{lon});
);"""},
    "culture": {"name":"Kultūra","emoji":"◫","osm_query":"""(
  nwr["tourism"~"museum|gallery|attraction|artwork"](around:{radius},{lat},{lon});
  nwr["historic"](around:{radius},{lat},{lon});
  nwr["amenity"~"theatre|cinema|library|arts_centre|community_centre|place_of_worship"](around:{radius},{lat},{lon});
);"""},
    "sport": {"name":"Sports","emoji":"◎","osm_query":"""(
  nwr["leisure"~"fitness_centre|swimming_pool|stadium|sports_centre|ice_rink|golf_course|tennis|track|pitch|skate_park|climbing"](around:{radius},{lat},{lon});
  nwr["sport"](around:{radius},{lat},{lon});
  nwr["amenity"~"swimming_pool|gym"](around:{radius},{lat},{lon});
);"""},
}

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

# Meklē vietas attēlu pēc nosaukuma — vispirms Wikimedia, tad Google Images meklēšana
KNOWN_BRAND_PHOTOS = {
    "maxima":    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Maxima_logo.svg/320px-Maxima_logo.svg.png",
    "rimi":      "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Rimi_logo.svg/320px-Rimi_logo.svg.png",
    "lidl":      "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Lidl-Logo.svg/320px-Lidl-Logo.svg.png",
    "iki":       "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/IKI_logo.svg/320px-IKI_logo.svg.png",
    "mcdonald":  "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/McDonald%27s_Golden_Arches.svg/320px-McDonald%27s_Golden_Arches.svg.png",
    "kfc":       "https://upload.wikimedia.org/wikipedia/en/thumb/b/bf/KFC_logo.svg/320px-KFC_logo.svg.png",
    "burger king":"https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Smiley.svg/240px-Smiley.svg.png",
    "circle k":  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Circle_K_logo.svg/320px-Circle_K_logo.svg.png",
    "narvesen":  "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Narvesen.svg/320px-Narvesen.svg.png",
    "elvi":      "https://images.unsplash.com/photo-1567958451986-2de427a4a0be?w=400&q=80",
    "stockmann": "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=400&q=80",
    "top":       "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&q=80",
}


def get_brand_photo(name: str) -> str | None:
    """Atgriež zināma veikala/restorāna logo/foto pēc nosaukuma."""
    name_lower = name.lower()
    for brand, url in KNOWN_BRAND_PHOTOS.items():
        if brand in name_lower:
            return url
    return None


async def try_wikipedia_photo(name: str, lang: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action":"query","titles":name,"prop":"pageimages",
                        "piprop":"thumbnail","pithumbsize":600,"format":"json","redirects":1}
            )
            pages = resp.json().get("query",{}).get("pages",{})
            for page in pages.values():
                th = page.get("thumbnail")
                if th and th.get("source"):
                    return th["source"]
    except Exception:
        pass
    return None


async def get_photo_for_place(name: str, category: str) -> str:
    # 1. Zināms zīmols
    brand = get_brand_photo(name)
    if brand:
        return brand
    # 2. Wikipedia LV
    photo = await try_wikipedia_photo(name, "lv")
    if photo:
        return photo
    # 3. Wikipedia EN
    photo = await try_wikipedia_photo(name, "en")
    if photo:
        return photo
    # 4. Rezerves foto pēc kategorijas
    return FALLBACK_PHOTOS.get(category, FALLBACK_PHOTOS["all"])


async def fetch_places_from_osm(lat: float, lon: float, radius: int, category: str) -> list:
    cat_data = CATEGORIES.get(category, CATEGORIES["all"])
    osm_query_part = cat_data["osm_query"].format(radius=radius, lat=lat, lon=lon)
    query = f"[out:json][timeout:25];\n{osm_query_part}\nout center 50;"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://overpass-api.de/api/interpreter", data={"data": query})
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"Overpass error: {e}")
        return []

    places = []
    seen_names = set()

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = (tags.get("name") or tags.get("name:lv") or
                tags.get("name:en") or tags.get("name:ru"))
        if not name:
            type_val = (tags.get("amenity") or tags.get("shop") or tags.get("tourism") or
                        tags.get("historic") or tags.get("leisure") or tags.get("natural",""))
            if type_val:
                name = type_val.replace("_"," ").title()
            else:
                continue
        if name in seen_names:
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
            "id": str(element.get("id")), "name": name,
            "lat": lat_p, "lon": lon_p, "category": category,
            "tags": {
                "amenity": tags.get("amenity",""), "shop": tags.get("shop",""),
                "cuisine": tags.get("cuisine",""), "opening_hours": tags.get("opening_hours",""),
                "phone": tags.get("phone") or tags.get("contact:phone",""),
                "website": tags.get("website") or tags.get("contact:website",""),
                "tourism": tags.get("tourism",""), "leisure": tags.get("leisure",""),
                "historic": tags.get("historic",""), "natural": tags.get("natural",""),
                "description": tags.get("description",""),
            }
        }
        place["photo"] = await get_photo_for_place(name, category)
        places.append(place)
        if len(places) >= 20:
            break
    return places


async def generate_ai_description(place: dict, lang: str = "lv") -> str:
    tags = place.get("tags", {})
    info_parts = []
    for key in ["amenity","shop","cuisine","opening_hours","historic","natural","tourism","leisure"]:
        if tags.get(key):
            info_parts.append(f"{key}: {tags[key]}")
    if tags.get("description"):
        info_parts.append(f"apraksts: {tags['description']}")
    info_str = ", ".join(info_parts) if info_parts else "vieta"

    lang_prompts = {
        "lv": "Tu esi ceļotāju palīgs Latvijā. Raksti īsus, dzīvespriecīgus vietu aprakstus latviešu valodā. Maksimums 2 teikumi. Draudzīgi un interesanti. Nemin, ka esi AI.",
        "en": "You are a travel assistant in Latvia. Write short, lively place descriptions in English. Maximum 2 sentences. Friendly and interesting. Don't mention you are AI.",
        "ru": "Ты помощник путешественников в Латвии. Пишешь короткие живые описания на русском. Максимум 2 предложения. Дружелюбно. Не упоминай что ты AI.",
    }
    system_msg = lang_prompts.get(lang, lang_prompts["lv"])

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content": system_msg},
                {"role":"user","content":f"Apraksti vietu '{place['name']}'. Dati: {info_str}"}
            ],
            max_tokens=150, temperature=0.7
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        defaults = {"lv":"Interesanta vieta, ko ir vērts apmeklēt!",
                    "en":"An interesting place worth visiting!",
                    "ru":"Интересное место, которое стоит посетить!"}
        return defaults.get(lang, defaults["lv"])


# ── Manuālā meklēšana pēc nosaukuma ──
async def search_by_name_osm(query_text: str) -> list:
    """Meklē vietu OSM pēc brīva teksta (Nominatim)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query_text, "format": "json", "limit": 5,
                        "addressdetails": 1, "extratags": 1},
                headers={"User-Agent": "NearBot/1.0"}
            )
            results = resp.json()
    except Exception as e:
        logger.error(f"Nominatim error: {e}")
        return []

    places = []
    for r in results:
        name = r.get("display_name","").split(",")[0]
        lat_p = float(r.get("lat", 0))
        lon_p = float(r.get("lon", 0))
        category = "all"
        tags = r.get("extratags", {})
        place = {
            "id": f"nom_{r.get('place_id','')}",
            "name": name, "lat": lat_p, "lon": lon_p,
            "category": category,
            "address": r.get("display_name",""),
            "tags": {
                "amenity": tags.get("amenity",""), "shop": tags.get("shop",""),
                "tourism": tags.get("tourism",""), "leisure": tags.get("leisure",""),
                "historic": tags.get("historic",""), "natural": tags.get("natural",""),
                "cuisine":"", "opening_hours":"", "phone":"", "website":"", "description":"",
            }
        }
        place["photo"] = await get_photo_for_place(name, category)
        places.append(place)
    return places


# ══ API ENDPOINTS ══

@app.get("/api/places")
async def get_places(
    lat: float = Query(...), lon: float = Query(...),
    radius: int = Query(1000, ge=300, le=10000),
    category: str = Query("all"),
    lang: str = Query("lv")
):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Nepareiza kategorija")
    places = await fetch_places_from_osm(lat, lon, radius, category)
    if not places:
        return {"places": [], "message": "Vietas nav atrastas"}
    return {"places": places, "total": len(places)}


@app.get("/api/description")
async def get_description(
    place_id: str = Query(...), name: str = Query(...),
    amenity: str = Query(""), shop: str = Query(""),
    cuisine: str = Query(""), opening_hours: str = Query(""),
    historic: str = Query(""), natural: str = Query(""),
    tourism: str = Query(""), leisure: str = Query(""),
    lang: str = Query("lv"),
):
    place = {"id": place_id, "name": name, "tags": {
        "amenity":amenity,"shop":shop,"cuisine":cuisine,
        "opening_hours":opening_hours,"historic":historic,
        "natural":natural,"tourism":tourism,"leisure":leisure,
    }}
    return {"description": await generate_ai_description(place, lang)}


@app.get("/api/categories")
async def get_categories():
    return {"categories": [
        {"id":k,"name":v["name"],"emoji":v["emoji"]}
        for k,v in CATEGORIES.items()
    ]}


@app.get("/api/search")
async def search_place(q: str = Query(...), lang: str = Query("lv")):
    """Manuālā meklēšana pēc nosaukuma."""
    places = await search_by_name_osm(q)
    if not places:
        return {"places": [], "message": "Nekas nav atrasts"}
    return {"places": places, "total": len(places)}


@app.get("/api/random")
async def get_random_place(lat: float = Query(...), lon: float = Query(...),
                            lang: str = Query("lv")):
    places = await fetch_places_from_osm(lat, lon, 5000, "friends")
    if not places:
        places = await fetch_places_from_osm(lat, lon, 5000, "all")
    if not places:
        return {"place": None}
    place = random.choice(places)
    lang_prompts = {
        "lv": "Raksti noslēpumaini un vilinošu par vietu. 2 teikumi. Latviešu valodā.",
        "en": "Write mysteriously and enticingly about the place. 2 sentences. In English.",
        "ru": "Пиши загадочно и заманчиво про место. 2 предложения. На русском.",
    }
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content": lang_prompts.get(lang, lang_prompts["lv"])},
                {"role":"user","content":f"Apraksti vietu '{place['name']}' kā noslēpumainu piedzīvojumu"}
            ],
            max_tokens=120
        )
        place["ai_teaser"] = completion.choices[0].message.content.strip()
    except:
        teasers = {"lv":"Šī vieta slēpj savus noslēpumus...","en":"This place hides its secrets...","ru":"Это место скрывает свои секреты..."}
        place["ai_teaser"] = teasers.get(lang, teasers["lv"])
    return {"place": place}


# Lietotāja pievienotās vietas (saglabā atmiņā — vienkārša versija)
user_places = []

class UserPlace(BaseModel):
    name: str
    description: str
    lat: float
    lon: float
    photo_url: Optional[str] = None
    category: Optional[str] = "all"

@app.post("/api/user-places")
async def add_user_place(place: UserPlace):
    new_place = {
        "id": f"user_{len(user_places)+1}_{random.randint(1000,9999)}",
        "name": place.name,
        "description": place.description,
        "lat": place.lat, "lon": place.lon,
        "photo": place.photo_url or FALLBACK_PHOTOS.get(place.category, FALLBACK_PHOTOS["all"]),
        "category": place.category or "all",
        "user_added": True,
        "tags": {"amenity":"","shop":"","cuisine":"","opening_hours":"",
                 "phone":"","website":"","tourism":"","leisure":"",
                 "historic":"","natural":"","description": place.description}
    }
    user_places.append(new_place)
    return {"success": True, "place": new_place}

@app.get("/api/user-places")
async def get_user_places():
    return {"places": user_places}


app.mount("/", StaticFiles(directory=".", html=True), name="webapp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
