from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not context.user_data.get("authorized"):
            await update.message.reply_text("🔒 Сначала авторизуйся через /start.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

#from utils.auth import require_auth