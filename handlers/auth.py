from telegram import Update
from telegram.ext import ContextTypes
from handlers.core import start
from handlers.betting import bet_step_handler

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("authorized"):
        await start(update, context)  # продолжаем процесс авторизации
    else:
        await bet_step_handler(update, context)  # если авторизован — передаём обработку ставкам
