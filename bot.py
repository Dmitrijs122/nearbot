import os
import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логов — чтобы видеть ошибки в консоли
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Читаем переменные окружения из .env файла
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")  # Адрес нашего фронтенда


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start — приветствие и кнопка открытия мини-апп.
    Когда пользователь пишет /start, бот отвечает с кнопкой WebApp.
    """
    user_name = update.effective_user.first_name  # Имя пользователя

    # Кнопка, которая открывает мини-апп прямо в Telegram
    keyboard = [[
        InlineKeyboardButton(
            text="🗺️ Открыть NearBot",
            web_app=WebAppInfo(url=WEBAPP_URL)  # Ссылка на наш сайт
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Привет, {user_name}! 👋\n\n"
        "🗺️ *NearBot* — найди интересные места рядом!\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help — список команд бота."""
    await update.message.reply_text(
        "📋 *Команды NearBot:*\n\n"
        "/start — Открыть приложение\n"
        "/help — Показать помощь\n\n"
        "Просто открой приложение и разреши доступ к геолокации!",
        parse_mode="Markdown"
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на любые другие сообщения."""
    keyboard = [[
        InlineKeyboardButton(
            text="🗺️ Открыть NearBot",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Нажми кнопку, чтобы открыть карту мест 👇",
        reply_markup=reply_markup
    )


def main():
    """Главная функция — запускает бота."""
    if not BOT_TOKEN:
        raise ValueError("❌ Нет TELEGRAM_TOKEN в переменных окружения!")
    if not WEBAPP_URL:
        raise ValueError("❌ Нет WEBAPP_URL в переменных окружения!")

    # Создаём приложение бота
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчик всех остальных текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("✅ NearBot запущен!")
    # Запускаем бота (polling — бот сам опрашивает Telegram)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
