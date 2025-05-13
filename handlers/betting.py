from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
from utils.storage import get_user, save_data, LATVIA_TZ
from utils.auth import require_auth

# /bet (начало диалога)
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
        "⚽ Выбери вид спорта для ставки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

    if context.user_data.get("bet_step") == "sport_manual":
        sport = update.message.text.strip()
        context.user_data["sport"] = sport
        context.user_data["bet_step"] = "type"
        await update.message.reply_text(f"✅ Вид спорта: {sport}")
        # сюда потом добавим следующий шаг
        return


    if context.user_data.get("awaiting_today_input"):
        context.user_data.pop("awaiting_today_input")
        lines = update.message.text.splitlines()
        if len(lines) < 2:
            await update.message.reply_text("⚠️ Нужно минимум 2 строки: ставка и пояснение.")
            return
        await process_today_lines(update, context, lines)
        return

    step = context.user_data.get("bet_step")
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    if step == "match":
        match = update.message.text.strip()
        words = match.split()
        if len(words) == 2 and "vs" not in match.lower():
            match = f"{words[0]} vs {words[1]}"
        context.user_data["match"] = match
        context.user_data["bet_step"] = "platform"
        await update.message.reply_text("Выбери платформу (optibet / olybet / bonus):")

    elif step == "platform":
        platform = update.message.text.lower().strip()
        if platform not in ["optibet", "olybet", "bonus"]:
            await update.message.reply_text("❌ Введи: optibet, olybet или bonus.")
            return
        context.user_data["platform"] = platform
        context.user_data["bet_step"] = "amount"
        await update.message.reply_text("Введи сумму ставки в € (например: 2.5)")

    elif step == "amount":
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                await update.message.reply_text("⚠️ Сумма должна быть больше 0.")
                return

            platform = context.user_data["platform"]
            if amount > user["banks"][platform]:
                await update.message.reply_text(f"⚠️ У тебя только {user['banks'][platform]:.2f}€ на {platform}.")
                return

            context.user_data["amount"] = amount
            context.user_data["bet_step"] = "coeff"

            percentage = (amount / user["banks"][platform]) * 100
            warning = f"\n⚠️ Это {percentage:.1f}% от банка {platform}. Уверен?" if percentage >= 20 else ""
            await update.message.reply_text(f"Введи коэффициент (например: 1.85){warning}")
        except:
            await update.message.reply_text("⚠️ Введи корректное число.")

    elif step == "coeff":
        try:
            coeff = float(update.message.text.strip())
            if coeff < 1:
                await update.message.reply_text("⚠️ Коэффициент должен быть не меньше 1.00")
                return

            context.user_data["coeff"] = coeff
            context.user_data["bet_step"] = "reminder"
            await update.message.reply_text(
                "🔔 Хочешь установить напоминание о проверке этой ставки?\n"
                "Введи дату и время в формате: <b>ДД.ММ ЧЧ:ММ</b>\n"
                "Или напиши <b>нет</b>, если не нужно.", parse_mode="HTML"
            )
        except:
            await update.message.reply_text("⚠️ Введи корректный коэффициент.")

    elif step == "reminder":
        answer = update.message.text.strip().lower()
        match = context.user_data["match"]
        now = datetime.datetime.now(LATVIA_TZ)

        if answer in ["нет", "no"]:
            reminder_time = None
        else:
            try:
                naive_dt = datetime.datetime.strptime(answer, "%d.%m %H:%M")
                dt = naive_dt.replace(tzinfo=LATVIA_TZ)

                if dt.astimezone(datetime.timezone.utc) <= now.astimezone(datetime.timezone.utc):
                    await update.message.reply_text(
                        f"⚠️ Указанное время уже прошло. Напоминание не установлено.\n"
                        f"Сейчас: <b>{now.strftime('%d.%m %H:%M')}</b>\n"
                        f"Попробуй снова или напиши <b>нет</b>.",
                        parse_mode="HTML"
                    )
                    return
                reminder_time = dt.isoformat()
            except:
                await update.message.reply_text("⚠️ Неверный формат. Используй ДД.ММ ЧЧ:ММ")
                return

        bet = {
            "match": context.user_data["match"],
            "amount": context.user_data["amount"],
            "coeff": context.user_data["coeff"],
            "status": "pending",
            "time": now,
            "type": (
                "safe" if context.user_data["coeff"] <= 1.20 else
                "value" if 1.60 <= context.user_data["coeff"] <= 2.50 else
                "normal"
            ),
            "source": context.user_data["platform"]
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
