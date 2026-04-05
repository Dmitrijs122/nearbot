import os
import httpx
import asyncio
import logging
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from groq import Groq
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём FastAPI приложение (это наш веб-сервер)
app = FastAPI(title="NearBot API")

# Разрешаем запросы с любых доменов (нужно для Telegram WebApp)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Клиент Groq для AI описаний
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─────────────────────────────────────────────
# КАТЕГОРИИ МЕСТ
# Каждая категория — это набор тегов OpenStreetMap
# ─────────────────────────────────────────────
CATEGORIES = {
    "food": {
        "name": "Еда и кафе",
        "emoji": "🍕",
        # OSM теги: amenity=restaurant, cafe, fast_food, bar, pub
        "osm_query": '(node["amenity"~"restaurant|cafe|fast_food|bar|pub"](around:{radius},{lat},{lon}););'
    },
    "entertainment": {
        "name": "Развлечения",
        "emoji": "🎮",
        "osm_query": '(node["leisure"~"bowling_alley|escape_game|miniature_golf|water_park|sports_centre"](around:{radius},{lat},{lon}); node["amenity"~"cinema|theatre|nightclub"](around:{radius},{lat},{lon}););'
    },
    "nature": {
        "name": "Природа и парки",
        "emoji": "🌿",
        "osm_query": '(node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon}); way["leisure"~"park|garden"](around:{radius},{lat},{lon}););'
    },
    "culture": {
        "name": "Культура",
        "emoji": "🏛️",
        "osm_query": '(node["tourism"~"museum|gallery|attraction|monument|artwork"](around:{radius},{lat},{lon}); node["historic"~"memorial|monument|castle|ruins"](around:{radius},{lat},{lon}););'
    },
    "shopping": {
        "name": "Шопинг",
        "emoji": "🛍️",
        "osm_query": '(node["shop"~"mall|supermarket|department_store|clothes|shoes"](around:{radius},{lat},{lon}););'
    },
    "sport": {
        "name": "Спорт",
        "emoji": "⚽",
        "osm_query": '(node["leisure"~"fitness_centre|swimming_pool|stadium|sports_centre|ice_rink"](around:{radius},{lat},{lon}); way["leisure"~"pitch|sports_centre"](around:{radius},{lat},{lon}););'
    },
    "all": {
        "name": "Всё рядом",
        "emoji": "🗺️",
        "osm_query": '(node["amenity"~"restaurant|cafe|bar|cinema|theatre"](around:{radius},{lat},{lon}); node["tourism"~"museum|attraction|gallery"](around:{radius},{lat},{lon}); node["leisure"~"park|sports_centre"](around:{radius},{lat},{lon}););'
    }
}


async def fetch_places_from_osm(lat: float, lon: float, radius: int, category: str) -> list:
    """
    Запрашивает места из OpenStreetMap через Overpass API.
    Overpass API — это бесплатная база данных всех мест мира, без регистрации.
    
    lat, lon — координаты пользователя
    radius — радиус поиска в метрах
    category — категория мест (food, nature и т.д.)
    """
    
    # Берём шаблон запроса для нужной категории
    cat_data = CATEGORIES.get(category, CATEGORIES["all"])
    osm_query_part = cat_data["osm_query"].format(
        radius=radius, lat=lat, lon=lon
    )
    
    # Формируем полный запрос на языке Overpass QL
    # [out:json] — ответ в формате JSON
    # [timeout:15] — максимум 15 секунд на запрос
    query = f"""
    [out:json][timeout:15];
    {osm_query_part}
    out center 30;
    """
    # "out center 30" — вернуть максимум 30 мест, с координатами центра

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query}  # Отправляем запрос
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"Ошибка Overpass API: {e}")
        return []

    places = []
    seen_names = set()  # Чтобы не дублировать одинаковые места

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")  # Название места

        # Пропускаем места без названия или дубликаты
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        # Получаем координаты (у way/relation есть "center")
        if element["type"] == "node":
            lat_place = element.get("lat")
            lon_place = element.get("lon")
        else:
            center = element.get("center", {})
            lat_place = center.get("lat")
            lon_place = center.get("lon")

        if not lat_place or not lon_place:
            continue

        # Формируем объект места
        place = {
            "id": str(element.get("id")),
            "name": name,
            "lat": lat_place,
            "lon": lon_place,
            "category": category,
            "tags": {
                # Берём полезные теги из OSM
                "amenity": tags.get("amenity", ""),
                "cuisine": tags.get("cuisine", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "phone": tags.get("phone") or tags.get("contact:phone", ""),
                "website": tags.get("website") or tags.get("contact:website", ""),
                "description": tags.get("description", ""),
                "tourism": tags.get("tourism", ""),
                "leisure": tags.get("leisure", ""),
            }
        }

        # Ищем фото через Wikimedia (Википедия) — бесплатно, без ключей
        photo = await get_wikimedia_photo(name)
        place["photo"] = photo

        places.append(place)

        # Останавливаемся на 15 местах — чтобы не грузить сервер
        if len(places) >= 15:
            break

    return places


async def get_wikimedia_photo(place_name: str) -> str | None:
    """
    Ищет фото места в Wikimedia Commons (база фото Википедии).
    Это абсолютно бесплатно и без регистрации.
    
    Возвращает URL фотографии или None если фото нет.
    """
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            # Запрашиваем страницу Википедии по названию места
            response = await client.get(
                "https://ru.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": place_name,
                    "prop": "pageimages",      # Хотим главное изображение
                    "piprop": "thumbnail",     # В формате thumbnail
                    "pithumbsize": 600,        # Размер 600px
                    "format": "json",
                    "redirects": 1             # Следуем перенаправлениям
                }
            )
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page in pages.values():
                thumbnail = page.get("thumbnail")
                if thumbnail:
                    return thumbnail.get("source")  # URL фото
    except Exception as e:
        logger.warning(f"Wikimedia фото не найдено для '{place_name}': {e}")
    
    return None  # Фото не найдено


async def generate_ai_description(place: dict) -> str:
    """
    Генерирует AI описание места через Groq API (бесплатно).
    Groq использует модель llama-3.3-70b-versatile.
    
    place — словарь с данными о месте
    """
    # Собираем информацию о месте для AI
    tags = place.get("tags", {})
    info_parts = []
    
    if tags.get("amenity"):
        info_parts.append(f"тип: {tags['amenity']}")
    if tags.get("cuisine"):
        info_parts.append(f"кухня: {tags['cuisine']}")
    if tags.get("opening_hours"):
        info_parts.append(f"часы работы: {tags['opening_hours']}")
    if tags.get("description"):
        info_parts.append(f"описание: {tags['description']}")
    
    info_str = ", ".join(info_parts) if info_parts else "нет доп. информации"
    
    try:
        # Отправляем запрос к Groq AI
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Бесплатная модель Groq
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помощник для путешественников. "
                        "Пишешь короткие, живые описания мест на русском языке. "
                        "Максимум 2 предложения. Стиль — дружелюбный и интересный. "
                        "Не упоминай что ты AI."
                    )
                },
                {
                    "role": "user",
                    "content": f"Напиши описание места '{place['name']}'. Данные: {info_str}"
                }
            ],
            max_tokens=150,
            temperature=0.7  # Немного творчества, но не слишком
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка Groq AI: {e}")
        # Если AI недоступен — возвращаем базовое описание
        return f"Интересное место в вашем районе. Загляните сюда!"


# ─────────────────────────────────────────────
# API ЭНДПОИНТЫ (адреса, на которые обращается фронтенд)
# ─────────────────────────────────────────────

@app.get("/api/places")
async def get_places(
    lat: float = Query(..., description="Широта пользователя"),
    lon: float = Query(..., description="Долгота пользователя"),
    radius: int = Query(1000, ge=500, le=10000, description="Радиус поиска в метрах"),
    category: str = Query("all", description="Категория мест")
):
    """
    Главный эндпоинт — возвращает список мест рядом с пользователем.
    Пример: GET /api/places?lat=56.86&lon=24.35&radius=2000&category=food
    """
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Неверная категория")
    
    logger.info(f"Поиск мест: lat={lat}, lon={lon}, radius={radius}, category={category}")
    
    # Получаем места из OpenStreetMap
    places = await fetch_places_from_osm(lat, lon, radius, category)
    
    if not places:
        return {"places": [], "message": "Места не найдены в этом радиусе"}
    
    return {"places": places, "total": len(places)}


@app.get("/api/description")
async def get_description(
    place_id: str = Query(...),
    name: str = Query(...),
    amenity: str = Query(""),
    cuisine: str = Query(""),
    opening_hours: str = Query(""),
):
    """
    Генерирует AI описание для конкретного места.
    Вызывается когда пользователь открывает карточку места.
    """
    place = {
        "id": place_id,
        "name": name,
        "tags": {
            "amenity": amenity,
            "cuisine": cuisine,
            "opening_hours": opening_hours,
        }
    }
    description = await generate_ai_description(place)
    return {"description": description}


@app.get("/api/categories")
async def get_categories():
    """Возвращает список всех доступных категорий."""
    return {
        "categories": [
            {"id": k, "name": v["name"], "emoji": v["emoji"]}
            for k, v in CATEGORIES.items()
        ]
    }


@app.get("/api/random")
async def get_random_place(
    lat: float = Query(...),
    lon: float = Query(...)
):
    """
    Режим 'Удиви меня' — возвращает случайное нестандартное место.
    Ищет необычные достопримечательности в радиусе 5км.
    """
    import random
    places = await fetch_places_from_osm(lat, lon, 5000, "culture")
    if not places:
        places = await fetch_places_from_osm(lat, lon, 5000, "all")
    if not places:
        return {"place": None}
    
    # Выбираем случайное место
    place = random.choice(places)
    
    # Генерируем интригующее описание
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты создаёшь интригующие описания мест как для приключения. "
                        "Пиши загадочно и заманчиво. Максимум 2 предложения. "
                        "На русском языке."
                    )
                },
                {
                    "role": "user",
                    "content": f"Опиши место '{place['name']}' как загадочное приключение"
                }
            ],
            max_tokens=120
        )
        place["ai_teaser"] = completion.choices[0].message.content.strip()
    except:
        place["ai_teaser"] = f"Это место скрывает свои секреты... Ты готов узнать больше?"
    
    return {"place": place}


# Отдаём статичные файлы фронтенда (HTML, CSS, JS)
# Это работает когда мы кладём index.html в папку webapp/
app.mount("/", StaticFiles(directory=".", html=True), name="webapp")


if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер на порту 8000
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
