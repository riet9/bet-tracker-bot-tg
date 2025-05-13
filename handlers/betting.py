from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import datetime
from utils.storage import get_user, save_data, LATVIA_TZ
from utils.auth import require_auth

@require_auth
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["bet_step"] = "sport"

    keyboard = [
        [InlineKeyboardButton("CS2", callback_data="sport_CS2")],
        [InlineKeyboardButton("Футбол", callback_data="sport_Футбол")],
        [InlineKeyboardButton("Хоккей", callback_data="sport_Хоккей")],
        [InlineKeyboardButton("Другое", callback_data="sport_other")]
    ]

    await update.message.reply_text(
        "⚽ Выбери вид спорта:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bet_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        data = query.data

        if data.startswith("sport_"):
            sport = data.split("_")[1]
            if sport == "other":
                context.user_data["bet_step"] = "sport_manual"
                await query.message.reply_text("Введи вид спорта вручную:")
                return
            context.user_data["sport"] = sport
            context.user_data["bet_step"] = "match"
            await query.message.reply_text(f"✅ Вид спорта: {sport}")
            await query.message.reply_text("Введи матч (например: NaVi vs G2)")
            return

        if data.startswith("type_"):
            t = data.split("_")[1]
            if t in ["safe", "value"]:
                context.user_data["type"] = t
                await query.message.reply_text(f"✅ Тип ставки: #{t}")
            else:
                await query.message.reply_text("Тип ставки будет определён автоматически.")
            context.user_data["bet_step"] = "platform"
            keyboard = [
                [InlineKeyboardButton("Optibet", callback_data="platform_optibet")],
                [InlineKeyboardButton("Olybet", callback_data="platform_olybet")],
                [InlineKeyboardButton("Bonus", callback_data="platform_bonus")],
            ]
            await query.message.reply_text("Выбери платформу:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if data.startswith("platform_"):
            platform = data.split("_")[1]
            context.user_data["platform"] = platform
            context.user_data["bet_step"] = "reminder"
            await query.message.reply_text("🔔 Хочешь установить напоминание о проверке этой ставки?\nВведи дату и время в формате: ДД.ММ ЧЧ:ММ\nИли напиши 'нет'")
            return

    # === TEXT INPUT ===
    message = update.message.text.strip()
    step = context.user_data.get("bet_step")
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    if step == "sport_manual":
        context.user_data["sport"] = message
        context.user_data["bet_step"] = "match"
        await update.message.reply_text(f"✅ Вид спорта: {message}")
        await update.message.reply_text("Введи матч (например: NaVi vs G2)")
        return

    if step == "match":
        context.user_data["match"] = message
        context.user_data["bet_step"] = "amount"
        await update.message.reply_text("💰 Введи сумму ставки в €:")
        return

    if step == "amount":
        try:
            amount = float(message)
            if amount <= 0:
                raise ValueError
            context.user_data["amount"] = amount
            context.user_data["bet_step"] = "coeff"
            await update.message.reply_text("Введи коэффициент:")
        except:
            await update.message.reply_text("⚠️ Введи корректную сумму.")
        return

    if step == "coeff":
        try:
            coeff = float(message)
            if coeff < 1:
                raise ValueError
            context.user_data["coeff"] = coeff
            context.user_data["bet_step"] = "type"
            keyboard = [
                [InlineKeyboardButton("#safe", callback_data="type_safe")],
                [InlineKeyboardButton("#value", callback_data="type_value")],
                [InlineKeyboardButton("Пропустить", callback_data="type_auto")]
            ]
            await update.message.reply_text("Выбери тип ставки или пропусти:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await update.message.reply_text("⚠️ Введи корректный коэффициент.")
        return

    if step == "reminder":
        match = context.user_data["match"]
        now = datetime.datetime.now(LATVIA_TZ)
        if message.lower() in ["нет", "no"]:
            reminder_time = None
        else:
            try:
                dt = datetime.datetime.strptime(message, "%d.%m %H:%M").replace(tzinfo=LATVIA_TZ)
                if dt < now:
                    raise ValueError
                reminder_time = dt.isoformat()
            except:
                await update.message.reply_text("⚠️ Неверный формат. Используй ДД.ММ ЧЧ:ММ или 'нет'")
                return

        bet = {
            "sport": context.user_data["sport"],
            "match": context.user_data["match"],
            "amount": context.user_data["amount"],
            "coeff": context.user_data["coeff"],
            "type": context.user_data.get("type") or (
                "safe" if context.user_data["coeff"] <= 1.20 else
                "value" if 1.60 <= context.user_data["coeff"] <= 2.50 else
                "normal"
            ),
            "source": context.user_data["platform"],
            "status": "pending",
            "time": now
        }

        user["bets"].append(bet)
        user["banks"][context.user_data["platform"]] -= context.user_data["amount"]
        save_data()
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ Ставка добавлена: {bet['match']}, {bet['amount']}€, кэф {bet['coeff']} ({'#' + bet['type']})\n"
            f"💰 Банк {bet['source']}: {user['banks'][bet['source']]:.2f}€"
        )

        if reminder_time:
            context.application.job_queue.run_once(
                lambda ctx: ctx.bot.send_message(chat_id, f"🔔 Напоминание: не забудь проверить ставку: {match}"),
                when=dt - now
            )
            await update.message.reply_text(f"🔔 Напоминание установлено на {dt.strftime('%d.%m %H:%M')}")



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
