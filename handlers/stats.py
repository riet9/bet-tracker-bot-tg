import datetime
import csv
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import get_user

# /stats — общая статистика
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    banks = user["banks"]
    completed = [b for b in user["bets"] if b["status"] != "pending"]
    wins = [b for b in completed if b["status"] == "win"]
    losses = [b for b in completed if b["status"] == "lose"]

    total = len(completed)
    roi = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in completed)
    avg_coeff = sum(b["coeff"] for b in completed) / total if total else 0
    winrate = len(wins) / total * 100 if total else 0
    total_bets = sum(b["amount"] for b in completed)
    total_bank = sum(banks.values())

    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"🏦 Optibet: {banks['optibet']:.2f}€\n"
        f"🏦 Olybet: {banks['olybet']:.2f}€\n"
        f"🎁 Бонусы: {banks['bonus']:.2f}€\n"
        f"📊 Всего банк: {total_bank:.2f}€\n\n"
        f"🎯 Ставок завершено: {total}\n"
        f"✅ Побед: {len(wins)} | ❌ Поражений: {len(losses)}\n"
        f"📈 Winrate: {winrate:.1f}%\n"
        f"📉 Средний кэф: {avg_coeff:.2f}\n"
        f"💸 Сумма ставок: {total_bets:.2f}€\n"
        f"📥 ROI: {roi:.2f}€"
    )

# /summary — отчёт по периоду
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    banks = user["banks"]
    now = datetime.datetime.now()
    period = context.args[0] if context.args else "today"

    if period == "today":
        filtered = [b for b in user["bets"] if datetime.datetime.fromisoformat(b["time"]).date() == now.date()]
        label = "Сегодня"
    elif period == "7d":
        cutoff = now - datetime.timedelta(days=7)
        filtered = [b for b in user["bets"] if datetime.datetime.fromisoformat(b["time"]) >= cutoff]
        label = "За 7 дней"
    elif period == "30d":
        cutoff = now - datetime.timedelta(days=30)
        filtered = [b for b in user["bets"] if datetime.datetime.fromisoformat(b["time"]) >= cutoff]
        label = "За 30 дней"
    else:
        await update.message.reply_text("❌ Используй:\n/summary, /summary 7d, /summary 30d")
        return

    completed = [b for b in filtered if b["status"] != "pending"]
    wins = [b for b in completed if b["status"] == "win"]
    losses = [b for b in completed if b["status"] == "lose"]
    profit = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in completed)
    total_bank = sum(banks.values())

    await update.message.reply_text(
        f"📆 <b>{label}:</b>\n"
        f"📋 Ставок: {len(filtered)} (завершено: {len(completed)})\n"
        f"✅ Победы: {len(wins)} | ❌ Поражения: {len(losses)}\n"
        f"💸 Прибыль: {profit:.2f}€\n\n"
        f"🏦 Optibet: {banks['optibet']:.2f}€\n"
        f"🏦 Olybet: {banks['olybet']:.2f}€\n"
        f"🎁 Бонусы: {banks['bonus']:.2f}€\n"
        f"📊 Всего банк: {total_bank:.2f}€",
        parse_mode=ParseMode.HTML
    )

# /history — история ставок по типу
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    if not context.args:
        await update.message.reply_text("ℹ️ Пример использования:\n/history #safe или /history #value")
        return

    bet_type = context.args[0].lstrip("#").lower()
    if bet_type not in ["safe", "value", "normal"]:
        await update.message.reply_text("❌ Неверный тип. Доступны: #safe, #value, #normal")
        return

    filtered = [b for b in user["bets"] if b.get("type") == bet_type and b["status"] != "pending"]
    if not filtered:
        await update.message.reply_text(f"📭 Нет завершённых #{bet_type} ставок.")
        return

    message = f"📖 <b>История #{bet_type} ставок:</b>\n\n"
    for b in filtered[-10:]:
        dt = datetime.datetime.fromisoformat(b["time"]) if isinstance(b["time"], str) else b["time"]
        status = "✅" if b["status"] == "win" else "❌"
        message += f"{status} {b['match']} — {b['amount']}€ @ {b['coeff']} ({dt.strftime('%d.%m %H:%M')})\n"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# /export — экспорт в CSV
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    if not user["bets"]:
        await update.message.reply_text("📭 У тебя нет ставок для экспорта.")
        return

    filename = f"bets_export_{chat_id}.csv"
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Дата", "Матч", "Сумма (€)", "Коэф", "Статус", "Тип"])
        for b in user["bets"]:
            dt = datetime.datetime.fromisoformat(b["time"]) if isinstance(b["time"], str) else b["time"]
            writer.writerow([
                dt.strftime("%Y-%m-%d %H:%M"),
                b["match"], b["amount"], b["coeff"],
                b["status"], b.get("type", "—")
            ])

    await update.message.reply_document(document=open(filename, "rb"), filename=filename)

# /graph — визуализация роста банка
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
