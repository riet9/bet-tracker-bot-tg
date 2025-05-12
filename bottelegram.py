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
    # Создаём резервную копию
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as original:
                content = original.read()
            with open("data_backup.json", "w") as backup:
                backup.write(content)
    except Exception as e:
        print(f"[WARN] Не удалось создать резервную копию: {e}")

    # Сохраняем новые данные
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
        "📘 <b>Список доступных команд:</b>\n"
        "👤 У тебя личный профиль — все ставки и банк видны только тебе\n\n"

        "🎯 <b>Ставки и результаты:</b>\n"
        "🟢 <b>/bet</b> — добавить ставку (по шагам)\n"
        "🟢 <b>/result</b> — завершить ставку (✅ победа / ❌ поражение)\n"
        "🟢 <b>/delete</b> — удалить активную ставку и вернуть деньги\n"
        "🟢 <b>/undelete</b> — восстановить удалённую ставку\n"
        "🟢 <b>/pending</b> — список текущих активных ставок\n\n"

        "📊 <b>Статистика и аналитика:</b>\n"
        "🟢 <b>/stats</b> — общая статистика (банк, winrate, ROI)\n"
        "🟢 <b>/graph</b> — график роста банка\n"
        "🟢 <b>/safe_stats</b> — аналитика по #safe ставкам\n"
        "🟢 <b>/value_stats</b> — аналитика по #value ставкам\n"
        "🟢 <b>/top_type</b> — сравнение стратегий (#safe vs #value)\n"
        "🟢 <b>/history #type</b> — история ставок по типу\n"
        "🟢 <b>/summary</b> — отчёт за сегодня\n"
        "🟢 <b>/summary 7d</b> — за 7 дней\n"
        "🟢 <b>/summary 30d</b> — за месяц\n\n"

        "📁 <b>Файл и банк:</b>\n"
        "🟢 <b>/export</b> — сохранить ставки в CSV\n"
        "🟢 <b>/bank [сумма]</b> — установить или узнать банк\n\n"

        "⚙️ <b>Служебные:</b>\n"
        "🟢 <b>/info</b> — показать это меню\n"
        "🟢 <b>/cancel</b> — отменить добавление ставки\n"
        "🟢 <b>/users_count</b> — сколько человек использует бота\n\n"

        "💾 Все данные сохраняются автоматически между перезапусками.\n"
        "💬 Просто используй команды или следуй пошаговым подсказкам.",
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

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    keyboard = []
    for i, b in enumerate(user["bets"]):
        if b["status"] == "pending":
            keyboard.append([InlineKeyboardButton(
                f"{b['match']} ({b['amount']}€ @ {b['coeff']})", callback_data=f"del_{i}"
            )])

    if not keyboard:
        await update.message.reply_text("❌ Нет активных ставок для удаления.")
        return

    await update.message.reply_text(
        "🗑️ Выбери ставку для удаления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def undelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    keyboard = []
    for i, b in enumerate(user["bets"]):
        if b["status"] == "deleted":
            keyboard.append([InlineKeyboardButton(
                f"{b['match']} ({b['amount']}€ @ {b['coeff']})", callback_data=f"undel_{i}"
            )])

    if not keyboard:
        await update.message.reply_text("📦 Нет удалённых ставок для восстановления.")
        return

    await update.message.reply_text(
        "♻️ Выбери ставку для восстановления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
    
    elif data.startswith("del_"):
        index = int(data.split("_")[1])
        if index >= len(user["bets"]) or user["bets"][index]["status"] != "pending":
            await query.edit_message_text("⚠️ Ставка не найдена или уже завершена.")
            return

        user["bank"] += user["bets"][index]["amount"]
        user["bets"][index]["status"] = "deleted"
        save_data()

        await query.edit_message_text(
            f"❌ Ставка удалена: {user['bets'][index]['match']}\n"
            f"💰 Деньги возвращены: {user['bets'][index]['amount']}€\n"
            f"Банк: {user['bank']:.2f}€"
        )

    elif data.startswith("undel_"):
        index = int(data.split("_")[1])
        if index >= len(user["bets"]) or user["bets"][index]["status"] != "deleted":
            await query.edit_message_text("⚠️ Нельзя восстановить эту ставку.")
            return

        if user["bank"] < user["bets"][index]["amount"]:
            await query.edit_message_text("⚠️ Недостаточно средств для восстановления.")
            return

        user["bank"] -= user["bets"][index]["amount"]
        user["bets"][index]["status"] = "pending"
        save_data()

        await query.edit_message_text(
            f"✅ Ставка восстановлена: {user['bets'][index]['match']}\n"
            f"💸 {user['bets'][index]['amount']}€ снято\n"
            f"Текущий банк: {user['bank']:.2f}€"
        )
    
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


async def show_type_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_type: str):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    bets = [b for b in user["bets"] if b.get("type") == bet_type and b["status"] != "pending"]
    if not bets:
        await update.message.reply_text(f"📭 Нет завершённых #{bet_type} ставок.")
        return

    wins = [b for b in bets if b["status"] == "win"]
    losses = [b for b in bets if b["status"] == "lose"]
    total = len(bets)
    roi = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in bets)
    avg_coeff = sum(b["coeff"] for b in bets) / total
    winrate = len(wins) / total * 100

    await update.message.reply_text(
        f"📊 <b>#{bet_type}</b> ставки:\n"
        f"🎯 Завершено: {total}\n"
        f"✅ Побед: {len(wins)} | ❌ Поражений: {len(losses)}\n"
        f"📈 Winrate: {winrate:.1f}%\n"
        f"📉 Средний кэф: {avg_coeff:.2f}\n"
        f"📥 ROI: {roi:.2f}€",
        parse_mode="HTML"
    )

async def safe_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_type_stats(update, context, "safe")
async def value_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_type_stats(update, context, "value")

async def top_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    def stats_for(type_):
        b = [x for x in user["bets"] if x.get("type") == type_ and x["status"] != "pending"]
        if not b:
            return None
        wins = [x for x in b if x["status"] == "win"]
        roi = sum((x["amount"] * x["coeff"] - x["amount"]) if x["status"] == "win" else -x["amount"] for x in b)
        return {
            "count": len(b),
            "wins": len(wins),
            "winrate": len(wins) / len(b) * 100,
            "avg_coeff": sum(x["coeff"] for x in b) / len(b),
            "roi": roi
        }

    s1 = stats_for("safe")
    s2 = stats_for("value")

    if not s1 and not s2:
        await update.message.reply_text("⚠️ Нет завершённых #safe или #value ставок.")
        return

    def fmt(name, d):
        return (
            f"<b>#{name}</b>\n"
            f"🎯 Завершено: {d['count']}, ✅ Побед: {d['wins']}\n"
            f"📈 Winrate: {d['winrate']:.1f}%\n"
            f"📉 Средний кэф: {d['avg_coeff']:.2f}\n"
            f"📥 ROI: {d['roi']:.2f}€\n\n"
        )

    msg = "<b>📊 Сравнение стратегий:</b>\n\n"
    if s1: msg += fmt("safe", s1)
    if s2: msg += fmt("value", s2)

    if s1 and s2:
        better = "#safe" if s1["roi"] > s2["roi"] else "#value"
        msg += f"🏆 <b>{better}</b> сейчас прибыльнее!"

    await update.message.reply_text(msg, parse_mode="HTML")


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
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("undelete", undelete))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("safe_stats", safe_stats))
    app.add_handler(CommandHandler("value_stats", value_stats))
    app.add_handler(CommandHandler("top_type", top_type))
    app.add_handler(CommandHandler("users_count", users_count))
    app.add_handler(CommandHandler("graph", graph))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet_step_handler))

    app.run_polling()
