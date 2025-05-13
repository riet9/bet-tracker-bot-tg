from telegram import Update
from telegram.ext import ContextTypes
from handlers.core import start
from handlers.betting import bet_step_handler
from utils.storage import get_user

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    # Авто-восстановление авторизации
    if "authorized" not in context.user_data and "login" in user:
        context.user_data["authorized"] = True
        context.user_data["login"] = user["login"]

    if not context.user_data.get("authorized"):
        await start(update, context)
    else:
        await bet_step_handler(update, context)
