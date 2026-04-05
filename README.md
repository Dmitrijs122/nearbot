# 📍 NearBot — Полная инструкция по запуску

## Что делает это приложение
Telegram Mini App для поиска интересных мест рядом с пользователем.
- Поиск мест через OpenStreetMap (бесплатно, без карты)
- Фото мест через Wikimedia (Википедия, бесплатно)
- AI описания через Groq (бесплатно)
- Сохранение любимых мест
- Режим "Удиви меня" — случайное место

---

## 📁 Структура проекта
```
nearbot/
├── bot.py           → Telegram бот
├── server.py        → API сервер (FastAPI)
├── start.py         → Запуск всего сразу
├── webapp/
│   └── index.html   → Фронтенд (мини-апп)
├── requirements.txt → Python зависимости
├── .env.example     → Шаблон переменных
└── .env             → Твои секреты (создай сам)
```

---

## 🔑 ШАГ 1 — Создать Telegram бота

1. Открой Telegram, найди **@BotFather**
2. Напиши `/newbot`
3. Введи **имя бота** (например: `NearBot Salaspils`)
4. Введи **username** (должен заканчиваться на `bot`, например: `nearbot_salaspils_bot`)
5. BotFather пришлёт тебе **токен** — это длинная строка вида:
   ```
   1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   ⚠️ Сохрани этот токен, он нужен для `.env`

---

## 🤖 ШАГ 2 — Получить Groq API ключ (AI описания)

1. Открой браузер → зайди на **https://console.groq.com**
2. Нажми **Sign Up** → зарегистрируйся через Google или email
3. После входа → в левом меню нажми **API Keys**
4. Нажми **Create API Key**
5. Введи любое название (например `nearbot`)
6. Скопируй ключ — он выглядит так:
   ```
   gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   ⚠️ Этот ключ показывается только один раз! Сохрани сразу.
7. Всё — Groq полностью бесплатен, карта не нужна!

---

## 🚀 ШАГ 3 — Задеплоить на Render.com (бесплатный хостинг)

### 3.1 — Загрузи код на GitHub

1. Зайди на **https://github.com** → войди или зарегистрируйся
2. Нажми **New repository** (зелёная кнопка)
3. Назови репозиторий: `nearbot`
4. Нажми **Create repository**
5. На своём компьютере открой терминал/командную строку в папке nearbot:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/ТВОЙ_НИК/nearbot.git
   git push -u origin main
   ```

### 3.2 — Создай аккаунт на Render.com

1. Зайди на **https://render.com**
2. Нажми **Get Started for Free**
3. Войди через GitHub (так проще всего)

### 3.3 — Создай Web Service на Render

1. На главной Render нажми **New +** → **Web Service**
2. Выбери свой репозиторий `nearbot`
3. Заполни поля:
   - **Name**: `nearbot`
   - **Region**: `Frankfurt (EU Central)` — ближе к Латвии
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python start.py`
4. Нажми **Create Web Service**
5. Render начнёт деплой — подожди 2-3 минуты
6. После деплоя вверху появится твой URL:
   ```
   https://nearbot.onrender.com
   ```
   ⚠️ Скопируй этот URL — он нужен для `.env`

### 3.4 — Добавь переменные окружения в Render

1. В Render → твой сервис → вкладка **Environment**
2. Нажми **Add Environment Variable** для каждой переменной:

   | Key | Value |
   |-----|-------|
   | `TELEGRAM_TOKEN` | Токен от BotFather |
   | `GROQ_API_KEY` | Ключ от Groq |
   | `WEBAPP_URL` | `https://nearbot.onrender.com` |

3. Нажми **Save Changes** — Render автоматически перезапустится

---

## 🤖 ШАГ 4 — Прикрепить мини-апп к боту

1. Вернись к **@BotFather** в Telegram
2. Напиши `/mybots`
3. Выбери своего бота
4. Нажми **Bot Settings** → **Menu Button**
5. Нажми **Configure menu button**
6. Введи URL: `https://nearbot.onrender.com`
7. Введи текст кнопки: `Открыть NearBot`
8. Готово! Теперь в боте будет кнопка внизу

---

## 💻 ЛОКАЛЬНЫЙ ЗАПУСК (для тестирования)

Если хочешь запустить на своём компьютере:

```bash
# 1. Установи Python 3.10+ если ещё нет

# 2. Перейди в папку проекта
cd nearbot

# 3. Создай .env файл
cp .env.example .env
# Открой .env и заполни своими ключами

# 4. Установи зависимости
pip install -r requirements.txt

# 5. Запусти
python start.py
```

Для теста мини-апп в браузере: открой http://localhost:8000

---

## ❓ Частые проблемы

**Бот не отвечает:**
- Проверь что `TELEGRAM_TOKEN` правильный
- Посмотри логи в Render (вкладка Logs)

**Места не находятся:**
- Проверь что разрешил доступ к геолокации в Telegram
- Попробуй увеличить радиус
- OpenStreetMap может не иметь данных в некоторых регионах

**Фото не загружаются:**
- Это нормально, Wikimedia не для всех мест имеет фото
- Показывается эмодзи категории вместо фото

**Render засыпает через 15 минут:**
- На бесплатном тарифе Render "засыпает" при неактивности
- Первый запрос может занять 30-60 секунд (просыпание)
- Для решения: можно настроить UptimeRobot (бесплатно) чтобы пинговал сервер каждые 10 минут

---

## 💡 Как работает приложение

```
Пользователь открывает бота
    ↓
Нажимает кнопку → открывается мини-апп (index.html)
    ↓
Выбирает категорию и радиус
    ↓
Нажимает "Найти места" → браузер запрашивает геолокацию
    ↓
Фронтенд (JavaScript) отправляет запрос на наш сервер:
  GET /api/places?lat=56.86&lon=24.35&radius=2000&category=food
    ↓
Сервер (Python/FastAPI) запрашивает OpenStreetMap (Overpass API)
    ↓
Для каждого места ищет фото в Wikimedia (Wikipedia)
    ↓
Возвращает список мест с координатами и фото
    ↓
Фронтенд рисует карточки
    ↓
Для каждой карточки отдельно загружает AI описание через Groq
```
