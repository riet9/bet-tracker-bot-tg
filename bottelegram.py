import logging
import os
import datetime
import csv
import json
import matplotlib.pyplot as plt

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

DATA_FILE = "users_data.json"
users_data = {}

def load_data():
    global users_data
    try:
        with open(DATA_FILE, "r") as f:
            users_data = json.load(f)
    except FileNotFoundError:
        users_data = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users_data, f, indent=2, default=str)

def get_user(chat_id: str):
    chat_id = str(chat_id)
    if chat_id not in users_data:
        users_data[chat_id] = {"bank": 10.0, "bets": []}
    return users_data[chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    get_user(chat_id)
    save_data()
    await update.message.reply_text(
        "👋 Привет! Я бот для отслеживания твоих ставок.\n"
        "Напиши /bet чтобы добавить ставку.\n"
        "Напиши /info, чтобы узнать, что я умею."
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 <b>Список доступных команд:</b>\n\n"
        "👤 У тебя личный профиль — ставки и банк видны только тебе\n\n"
        "🟢 /start — запустить бота\n"
        "🟢 /bet — добавить ставку по шагам (матч, сумма, кэф)\n"
        "🟢 /result — ввести результат ставки (✅/❌)\n"
        "🟢 /stats — твоя статистика (winrate, ROI, банк)\n"
        "🟢 /graph — график роста банка\n"
        "🟢 /summary — дневной/недельный/месячный отчёт\n"
        "🟢 /safe_stats, /value_stats — аналитика по типу ставок\n"
        "🟢 /top_type — сравнение стратегий\n"
        "🟢 /history #safe — история ставок по типу\n"
        "🟢 /bank [сумма] — установить или узнать банк\n"
        "🟢 /export — экспортировать историю в .csv\n"
        "🟢 /users_count — сколько человек использует бота\n"
        "🟢 /cancel — отменить ввод ставки\n",
        parse_mode="HTML"
    )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    if context.args:
        try:
            new_bank = float(context.args[0])
            if new_bank < 0:
                await update.message.reply_text("⚠️ Банк не может быть отрицательным.")
                return
            user["bank"] = new_bank
            save_data()
            await update.message.reply_text(f"✅ Новый банк установлен: {new_bank:.2f}€")
        except:
            await update.message.reply_text("⚠️ Введи число. Пример:\n/bank 15")
    else:
        await update.message.reply_text(f"💰 Текущий банк: {user['bank']:.2f}€")

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bet_step"] = "match"
    await update.message.reply_text("Введи название матча (пример: NaVi vs G2)")

async def bet_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    step = context.user_data.get("bet_step")

    if step == "match":
        context.user_data["match"] = update.message.text.strip()
        context.user_data["bet_step"] = "amount"
        await update.message.reply_text("Введи сумму ставки в € (например: 2.5)")

    elif step == "amount":
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                await update.message.reply_text("⚠️ Сумма должна быть больше 0.")
                return
            if amount > user["bank"]:
                await update.message.reply_text(f"⚠️ У тебя только {user['bank']:.2f}€.")
                return
            context.user_data["amount"] = amount
            context.user_data["bet_step"] = "coeff"

            percentage = (amount / user["bank"]) * 100
            warning = f"\n⚠️ Это {percentage:.1f}% от банка. Уверен?" if percentage >= 20 else ""
            await update.message.reply_text(f"Введи коэффициент (например: 1.85){warning}")
        except:
            await update.message.reply_text("⚠️ Введи корректное число.")

    elif step == "coeff":
        try:
            coeff = float(update.message.text.strip())
            if coeff < 1:
                await update.message.reply_text("⚠️ Коэффициент должен быть не меньше 1.00")
                return

            match = context.user_data["match"]
            amount = context.user_data["amount"]
            bet_time = datetime.datetime.now()

            if coeff <= 1.20:
                bet_type = "safe"
            elif 1.60 <= coeff <= 2.50:
                bet_type = "value"
            else:
                bet_type = "normal"

            user["bets"].append({
                "match": match,
                "amount": amount,
                "coeff": coeff,
                "status": "pending",
                "time": bet_time,
                "type": bet_type
            })

            user["bank"] -= amount
            context.user_data.clear()
            save_data()

            context.application.job_queue.run_once(
                remind_result,
                when=datetime.timedelta(hours=24),
                data={"chat_id": chat_id, "match": match}
            )

            await update.message.reply_text(
                f"✅ Ставка добавлена: {match}, {amount}€, кэф {coeff} ({'#' + bet_type})\n"
                f"💰 Новый банк: {user['bank']:.2f}€"
            )
        except:
            await update.message.reply_text("⚠️ Введи корректный коэффициент.")
async def remind_result(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    match = data["match"]
    await context.bot.send_message(chat_id=chat_id,
        text=f"🔔 Напоминание: не забудь ввести результат ставки: {match}\nНапиши /result")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    keyboard = []
    for i, b in enumerate(user["bets"]):
        if b["status"] == "pending":
            keyboard.append([InlineKeyboardButton(
                f"{b['match']} ({b['amount']}€ @ {b['coeff']})", callback_data=f"res_{i}"
            )])
    if not keyboard:
        await update.message.reply_text("Нет активных ставок.")
        return
    await update.message.reply_text("Выбери ставку:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    user = get_user(chat_id)

    data = query.data
    if data.startswith("res_"):
        index = int(data.split("_")[1])
        context.user_data["selected"] = index
        keyboard = [[
            InlineKeyboardButton("✅ Победа", callback_data="win"),
            InlineKeyboardButton("❌ Поражение", callback_data="lose")
        ]]
        await query.edit_message_text(f"Выбрана ставка: {user['bets'][index]['match']}",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data in ["win", "lose"]:
        index = context.user_data.get("selected")
        if index is None: return
        bet = user["bets"][index]
        if bet["status"] != "pending":
            await query.edit_message_text("Ставка уже завершена.")
            return

        if data == "win":
            profit = bet["amount"] * bet["coeff"]
            user["bank"] += profit
            bet["status"] = "win"
            msg = f"✅ Победа: {bet['match']}\n+{profit:.2f}€"
        else:
            bet["status"] = "lose"
            msg = f"❌ Поражение: {bet['match']}\n-{bet['amount']:.2f}€"

        save_data()
        await query.edit_message_text(msg + f"\n💰 Новый банк: {user['bank']:.2f}€")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    completed = [b for b in user["bets"] if b["status"] != "pending"]
    wins = [b for b in completed if b["status"] == "win"]
    losses = [b for b in completed if b["status"] == "lose"]

    total = len(completed)
    roi = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in completed)
    avg_coeff = sum(b["coeff"] for b in completed) / total if total else 0
    winrate = len(wins) / total * 100 if total else 0
    total_bets = sum(b["amount"] for b in completed)

    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"💰 Банк: {user['bank']:.2f}€\n"
        f"🎯 Ставок завершено: {total}\n"
        f"✅ Побед: {len(wins)} | ❌ Поражений: {len(losses)}\n"
        f"📈 Winrate: {winrate:.1f}%\n"
        f"📉 Средний кэф: {avg_coeff:.2f}\n"
        f"💸 Сумма ставок: {total_bets:.2f}€\n"
        f"📥 ROI: {roi:.2f}€"
    )

async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 Всего пользователей: {len(users_data)}")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    completed = [b for b in user["bets"] if b["status"] != "pending"]
    if not completed:
        await update.message.reply_text("Нет завершённых ставок.")
        return

    x, y = [], []
    value = 10.0
    for b in completed:
        dt = datetime.datetime.fromisoformat(b["time"]) if isinstance(b["time"], str) else b["time"]
        x.append(dt.strftime("%d.%m %H:%M"))
        value += (b["amount"] * b["coeff"]) if b["status"] == "win" else -b["amount"]
        y.append(value)

    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.title("📈 Рост банка")
    plt.tight_layout()
    plt.savefig("graph.png")
    plt.close()

    await update.message.reply_photo(photo=open("graph.png", "rb"))

# ——— Регистрация команд ——— #
if __name__ == '__main__':
    load_data()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users_count", users_count))
    app.add_handler(CommandHandler("graph", graph))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet_step_handler))

    app.run_polling()
