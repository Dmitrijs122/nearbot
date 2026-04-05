#!/usr/bin/env python3
"""
start.py — главный файл запуска.
Запускает и API сервер (FastAPI) и Telegram бота одновременно.

На Render.com в настройках Start Command укажи:
  python start.py
"""

import asyncio
import threading
import os
from dotenv import load_dotenv

load_dotenv()


def run_bot():
    """Запускает Telegram бота в отдельном потоке."""
    # Импортируем здесь, чтобы не было конфликтов с asyncio
    import subprocess
    subprocess.run(["python", "bot.py"])


def run_server():
    """Запускает FastAPI сервер."""
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Запускаем сервер в основном потоке
    run_server()
