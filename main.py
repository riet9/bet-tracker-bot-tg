from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import os

# Импортируем хендлеры из модулей (после их создания)
from handlers.core import start, info, bank_command, users_count
from handlers.betting import bet, cancel, pending, delete, undelete, bet_step_handler
from handlers.today import today, prompt, prompt_button_handler
from handlers.stats import stats, summary, safe_stats, value_stats, top_type, history, graph, export
from handlers.buttons import button_handler
from utils.storage import load_data
from handlers.reminders import morning_reminder

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if __name__ == '__main__':
    load_data()
    app = ApplicationBuilder().token(TOKEN).build()

    app.job_queue.run_daily(
        morning_reminder,
        time=datetime.time(hour=9, minute=0),
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("undelete", undelete))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("result", button_handler))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("safe_stats", safe_stats))
    app.add_handler(CommandHandler("value_stats", value_stats))
    app.add_handler(CommandHandler("top_type", top_type))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("prompt", prompt))

    app.add_handler(CallbackQueryHandler(prompt_button_handler, pattern="^send_prompt$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet_step_handler))

    app.run_polling()