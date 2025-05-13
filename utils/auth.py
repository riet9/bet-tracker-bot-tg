from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import get_user

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("auth_step"):
            return  # пользователь в процессе авторизации

        chat_id = str(update.effective_chat.id)
        user = get_user(chat_id)

        # Восстанавливаем авторизацию из user["login"]
        if not context.user_data.get("authorized"):
            if "login" in user:
                context.user_data["authorized"] = True
                context.user_data["login"] = user["login"]
            else:
                from handlers.core import start
                return await start(update, context)

        return await func(update, context)
    return wrapper