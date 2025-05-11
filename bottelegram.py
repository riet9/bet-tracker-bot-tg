import logging
import os
import datetime
import csv

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

bank = 10.0
bets = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой бот для ставок. Напиши /bet чтобы добавить ставку.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Команды:\n"
        "/start — начать\n"
        "/bet — добавить ставку\n"
        "/result — выбрать ставку и ввести результат\n"
        "/stats — посмотреть банк, winrate, ROI\n"
        "/export — экспортировать в CSV\n"
        "/info — это меню"
    )

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши ставку в формате:\nМатч: NaVi vs G2\nСумма: 2\nКэф: 1.75")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bets, bank
    text = update.message.text
    if text.lower().startswith("матч"):
        try:
            lines = text.split('\n')
            match = lines[0].split(":")[1].strip()
            amount = float(lines[1].split(":")[1].strip())
            coeff = float(lines[2].split(":")[1].strip())
            bet_time = datetime.datetime.now()
            bets.append({
                "match": match,
                "amount": amount,
                "coeff": coeff,
                "status": "pending",
                "time": bet_time
            })
            bank -= amount
            await update.message.reply_text(f"✅ Ставка добавлена: {match}, {amount}€, кэф {coeff}\n💰 Банк: {bank:.2f}€")
        except:
            await update.message.reply_text("⚠️ Неверный формат. Пример:\nМатч: NaVi vs G2\nСумма: 2\nКэф: 1.75")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i, b in enumerate(bets):
        if b["status"] == "pending":
            keyboard.append([
                InlineKeyboardButton(f"{b['match']} ({b['amount']}€, кэф {b['coeff']})", callback_data=f"select_{i}")
            ])
    if not keyboard:
        await update.message.reply_text("Нет активных ставок.")
        return
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери ставку:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bank
    query = update.callback_query
    await query.answer()

    if query.data.startswith("select_"):
        index = int(query.data.split("_")[1])
        context.user_data["selected_bet"] = index
        keyboard = [
            [InlineKeyboardButton("✅ Победа", callback_data='result_win'),
             InlineKeyboardButton("❌ Поражение", callback_data='result_lose')]
        ]
        await query.edit_message_text(
            f"Выбрана ставка: {bets[index]['match']}\nВыбери результат:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in ["result_win", "result_lose"]:
        index = context.user_data.get("selected_bet")
        if index is None or index >= len(bets):
            await query.edit_message_text("Ошибка: ставка не найдена.")
            return
        bet = bets[index]
        if bet["status"] != "pending":
            await query.edit_message_text("Эта ставка уже завершена.")
            return
        if query.data == "result_win":
            profit = bet["amount"] * bet["coeff"]
            bank += profit
            bet["status"] = "win"
            await query.edit_message_text(f"✅ Победа: {bet['match']}\n+{profit:.2f}€\n💰 Банк: {bank:.2f}€")
        else:
            bet["status"] = "lose"
            await query.edit_message_text(f"❌ Поражение: {bet['match']}\n-{bet['amount']:.2f}€\n💰 Банк: {bank:.2f}€")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wins = sum(1 for b in bets if b["status"] == "win")
    total = sum(1 for b in bets if b["status"] != "pending")
    roi = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"]
              for b in bets if b["status"] != "pending")
    winrate = (wins / total * 100) if total > 0 else 0
    await update.message.reply_text(
        f"📊 Статистика:\nБанк: {bank:.2f}€\nСтавок: {total}\nВыиграно: {wins}\nWinrate: {winrate:.1f}%\nROI: {roi:.2f}€"
    )

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("bets_export.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Дата", "Матч", "Сумма", "Кэф", "Статус"])
        for b in bets:
            writer.writerow([
                b['time'].strftime("%Y-%m-%d %H:%M"),
                b['match'], b['amount'], b['coeff'], b['status']
            ])
    await update.message.reply_document(document=open("bets_export.csv", "rb"), filename="bets_export.csv")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()
