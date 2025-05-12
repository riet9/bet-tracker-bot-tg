from telegram import Update
from telegram.ext import ContextTypes
import datetime
from utils.storage import get_user, save_data, LATVIA_TZ

# /bet (начало диалога)
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bet_step"] = "match"
    await update.message.reply_text("Введи название матча (пример: NaVi vs G2)")

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bet_step" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("❌ Ввод ставки отменён.")
    else:
        await update.message.reply_text("ℹ️ Сейчас ты не вводишь ставку.")

# Список активных ставок
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    pending_bets = [b for b in user["bets"] if b["status"] == "pending"]
    if not pending_bets:
        await update.message.reply_text("✅ Все ставки завершены!")
        return

    msg = "📋 <b>Твои активные ставки:</b>\n\n"
    for i, b in enumerate(pending_bets, 1):
        dt = datetime.datetime.fromisoformat(b["time"]) if isinstance(b["time"], str) else b["time"]
        msg += f"{i}. {b['match']} — {b['amount']}€ @ {b['coeff']} ({dt.strftime('%d.%m %H:%M')})\n"

    await update.message.reply_text(msg, parse_mode="HTML")

# Обработчик шагов при /bet
async def bet_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.today import process_today_lines

    if context.user_data.get("awaiting_today_input"):
        context.user_data.pop("awaiting_today_input")
        lines = update.message.text.splitlines()
        if len(lines) < 2:
            await update.message.reply_text("⚠️ Нужно минимум 2 строки: ставка и пояснение.")
            return
        await process_today_lines(update, context, lines)
        return

    # ... остальные шаги (match -> platform -> amount -> coeff) можно дописать отдельно, если нужно

# /delete и /undelete вынесем в buttons.py
