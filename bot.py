# -*- coding: utf-8 -*-
"""
Лабораторна робота №3
Тема: Створення telegram-боту з меню та запитом до AI
Варіант 5: БД "Співробітники, що мають комп'ютер"
"""

import os
import logging
from dotenv import load_dotenv
import asyncio

from google import genai
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- Завантаження .env ----------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise SystemExit("❌ TELEGRAM_TOKEN не задано у .env")
if not GEMINI_API_KEY:
    raise SystemExit("❌ GEMINI_API_KEY не задано у .env")

# ---------- Ініціалізація Gemini (новий SDK) ----------
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.5-flash-lite"

# ---------- Дані варіанта 5 ----------
VARIANT_DATA = {
    "student": "ст. Штифлюк Ольга гр. ІО-31",
    "it": (
        "IT-технології:\n"
        "• Front-end\n"
        "• Back-end\n"
        "• WEB-технології\n"
        "• Бази даних"
    ),
    "contacts": "тел. 050-55-55-55, e-mail: student@kpi.ua",
    "db_schema": (
        "БД «Співробітники та комп'ютери» (варіант 5):\n"
        "Поля: прізвище, номер кімнати, назва відділу, дані про комп'ютер."
    ),
}

# ---------- Логування ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Клавіатури ----------
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 Студент", "💻 IT-технології"],
        ["📞 Контакти", "🗄 БД: Співробітники"],
        ["🤖 Prompt AI"],
    ],
    resize_keyboard=True,
)

BACK_BUTTON = ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True)


# ---------- Хендлери ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вас вітає чат-бот! Виберіть відповідну команду",
        reply_markup=MAIN_MENU,
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    if text == "👤 Студент":
        await update.message.reply_text(VARIANT_DATA["student"], reply_markup=BACK_BUTTON)
    elif text == "💻 IT-технології":
        await update.message.reply_text(VARIANT_DATA["it"], reply_markup=BACK_BUTTON)
    elif text == "📞 Контакти":
        await update.message.reply_text(VARIANT_DATA["contacts"], reply_markup=BACK_BUTTON)
    elif text == "🗄 БД: Співробітники":
        await update.message.reply_text(VARIANT_DATA["db_schema"], reply_markup=BACK_BUTTON)
    elif text == "🤖 Prompt AI":
        await update.message.reply_text(
            "Введіть ваш запит до AI (наприклад: «Створи SQL-таблицю для БД "
            "співробітників з комп'ютерами»):",
            reply_markup=BACK_BUTTON,
        )
        context.user_data["awaiting_ai"] = True
    elif text == "⬅️ Назад":
        context.user_data["awaiting_ai"] = False
        await update.message.reply_text("Головне меню:", reply_markup=MAIN_MENU)
    else:
        if context.user_data.get("awaiting_ai"):
            await ask_ai(update, context)
        else:
            await update.message.reply_text(
                "Скористайтеся кнопками меню 👇", reply_markup=MAIN_MENU
            )


async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = update.message.text
    await update.message.chat.send_action("typing")

    system_context = (
        "Ти помічник студента КПІ з курсу «Основи WEB технологій». "
        "Контекст: БД «Співробітники, що мають комп'ютер» — поля: "
        "прізвище, номер кімнати, назва відділу, дані про комп'ютер. "
        "Відповідай українською, стисло.\n\n"
        f"Запит користувача: {prompt}"
    )

    answer = None
    delays = [2, 4, 8]

    for attempt, delay in enumerate(delays, start=1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=system_context,
            )
            answer = response.text or "Порожня відповідь від моделі."
            break
        except Exception as e:
            err = str(e)
            if "503" in err or "UNAVAILABLE" in err or "high demand" in err:
                logger.warning(f"Спроба {attempt} (503), чекаємо {delay}с...")
                await asyncio.sleep(delay)
            else:
                answer = f"⚠️ Помилка AI: {e}"
                break

    if answer is None:
        answer = "⚠️ AI тимчасово перевантажений. Спробуйте ще раз за хвилину."

    await update.message.reply_text(answer, reply_markup=MAIN_MENU)
    context.user_data["awaiting_ai"] = False


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команди:\n/start — меню\n/help — довідка\n\n"
        "Або просто користуйтеся кнопками.",
        reply_markup=MAIN_MENU,
    )


# ---------- Точка входу ----------
def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    logger.info("Бот запущено. Натисніть Ctrl+C для зупинки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()