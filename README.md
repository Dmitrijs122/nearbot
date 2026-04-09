# 📍 NearBot — Pilna uzstādīšanas instrukcija

## Ko dara šī lietotne
Telegram Mini App vietu meklēšanai ap lietotāju.
- Meklēšana pēc kategorijas (ēdiens, daba, veikali, pieminekļi u.c.)
- Manuālā meklēšana pēc nosaukuma
- Lietotāja pievienotas vietas
- Foto no Wikipedia un Unsplash
- AI apraksti latviešu/angļu/krievu valodā (Groq)
- Gaišs un tumšs dizains
- Trīs valodas: LV / EN / RU

---

## 📁 Projekta struktūra
```
nearbot/
├── bot.py           → Telegram bots
├── server.py        → API serveris (FastAPI)
├── start.py         → Palaiž visu kopā
├── index.html       → Lietotnes saskarnes fails
├── requirements.txt → Python bibliotēkas
└── .env.example     → Vides mainīgo paraugs
```

---

## 🔑 1. SOLIS — Izveido Telegram botu

1. Atver Telegram, atrod **@BotFather**
2. Raksti `/newbot`
3. Ievadi **bota nosaukumu** (piemēram: `NearBot Salaspils`)
4. Ievadi **username** (jābeigt ar `bot`, piemēram: `nearbot_salaspils_bot`)
5. BotFather nosūtīs **tokenu** — garu ciparu un burtu virkni:
   ```
   1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   ⚠️ Saglabā šo tokenu — tas nepieciešams vides mainīgajiem.

---

## 🤖 2. SOLIS — Iegūsti Groq API atslēgu (AI aprakstiem)

1. Atver pārlūku → ej uz **https://console.groq.com**
2. Spied **Sign Up** → reģistrējies ar Google vai e-pastu
3. Pēc ielogošanās → kreisajā izvēlnē spied **API Keys**
4. Spied **Create API Key**
5. Ievadi jebkādu nosaukumu (piemēram `nearbot`) → spied Create
6. Nokopē atslēgu — tā izskatās šādi:
   ```
   gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   ⚠️ Šī atslēga parādās **tikai vienu reizi**! Saglabā uzreiz.
7. Groq ir pilnīgi bezmaksas — karte nav nepieciešama!

---

## 🚀 3. SOLIS — Augšupielādē kodu uz GitHub

1. Ej uz **github.com** → piesakies vai reģistrējies
2. Spied **New repository**
3. Nosauc repozitoriju: `nearbot`
4. Izvēlies **Public** → spied **Create repository**
5. Spied **"Add file"** → **"Upload files"**
6. Ievelc visus failus no arhīva uz GitHub lapu
7. Spied **"Commit changes"** ✅

---

## 🌐 4. SOLIS — Izvietošana uz Render.com (bezmaksas)

### 4.1 — Reģistrācija Render

1. Ej uz **render.com** → spied **"Get Started for Free"**
2. Ienāc ar **GitHub** kontu

### 4.2 — Izveido Web Service

1. Spied **New +** → izvēlies **Web Service**
2. Izvēlies savu repozitoriju `nearbot` → spied **Connect**
3. Aizpildi laukus:

| Lauks | Vērtība |
|-------|---------|
| Name | `nearbot` |
| Region | `Frankfurt (EU Central)` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python start.py` |

4. Spied **Create Web Service**
5. Pagaidi 2–3 minūtes — augšā parādīsies tavs URL:
   ```
   https://nearbot.onrender.com
   ```
   ⚠️ Saglabā šo URL!

### 4.3 — Pievieno vides mainīgos Render

1. Render → tavs serviss → cilne **Environment**
2. Spied **Add Environment Variable** trīs reizes:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | Tokens no BotFather |
| `GROQ_API_KEY` | Atslēga no Groq |
| `WEBAPP_URL` | `https://nearbot.onrender.com` |

3. Spied **Save Changes** — Render restartēsies automātiski

---

## 🔗 5. SOLIS — Piesaisti mini-lietotni botam

1. Atgriezies pie **@BotFather** Telegram
2. Raksti `/mybots`
3. Izvēlies savu botu
4. Spied **Bot Settings** → **Menu Button**
5. Spied **Configure menu button**
6. Ievadi URL: `https://nearbot.onrender.com`
7. Ievadi pogas tekstu: `🗺️ Atvērt NearBot`

---

## ❓ Biežākās problēmas

**Bots neatbild:**
- Pārbaudi vai `TELEGRAM_TOKEN` ir pareizs
- Skatīt žurnālus Render (cilne Logs)

**Vietas nav atrastas:**
- Atļauj ģeolokāciju Telegram iestatījumos
- Mēģini palielināt rādiusu
- Izmēģini kategoriju "Viss"

**Render "aizmieg" pēc 15 minūtēm:**
- Bezmaksas Render plānā serviss aizmieg pēc neaktivitātes
- Pirmais pieprasījums var aizņemt 30–60 sekundes (pamošanās)
- Risinājums: uzstādīt UptimeRobot (bezmaksas) — pingot serveri ik 10 minūtes

---

## 💡 Kā darbojas lietotne

```
Lietotājs atver botu
    ↓
Nospiež pogu → atveras mini-lietotne (index.html)
    ↓
Izvēlas kategoriju un rādiusu
    ↓
Nospiež "Atrast vietas" → pārlūks pieprasa ģeolokāciju
    ↓
JavaScript sūta pieprasījumu uz serveri:
  GET /api/places?lat=56.86&lon=24.35&radius=2000&category=food
    ↓
Serveris (Python/FastAPI) pieprasa OpenStreetMap (Overpass API)
    ↓
Katrai vietai meklē foto Wikipedia / Unsplash
    ↓
Atgriež vietu sarakstu ar koordinātām un foto
    ↓
Frontendam (JavaScript) zīmē kartītes
    ↓
Katrai kartītei atsevišķi ielādē AI aprakstu caur Groq
```

---

*Created by Coldbar*
