from telegram.ext import ContextTypes
from utils.storage import get_user

# Напоминание вручную, после ставки (через JobQueue)
async def remind_result(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    match = data["match"]
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 Напоминание: не забудь ввести результат ставки: {match}\nНапиши /result"
    )

# Утреннее напоминание составить прогноз
async def morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    # ❗Здесь ты можешь сделать рассылку всем пользователям или задать конкретный chat_id
    chat_id = "2047828228"  # Пример: твой chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌅 Доброе утро! Готовим прогноз 🎯\n\n"
            "Скопируй это в ChatGPT:\n\n"
            "Найди 0–2 максимально надёжные #safe ставки (1.10–1.20) и 0–5 логичных value-ставок (1.60–2.50) "
            "на сегодня по CS2, футболу и хоккею. Если есть действительно ценные ставки в других дисциплинах — тоже включи.\n\n"
            "Формат каждой ставки:\n"
            "Матч – исход @коэффициент\n"
            "Пояснение (1–2 строки)\n\n"
            "❗️Без лишнего текста. Только список."
        ),
        parse_mode="HTML"
    )
