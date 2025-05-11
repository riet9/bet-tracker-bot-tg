import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import datetime, csv

# Загрузка токена из .env
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Хранилище ставок и банка
bank = 10.0
bets = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой бот для ставок. Напиши /bet чтобы добавить ставку.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Список команд:\n"
        "/start — приветствие и запуск бота\n"
        "/bet — добавить новую ставку (после команды напиши: Матч, Сумма, Кэф)\n"
        "/result — выбрать ставку и ввести её результат (победа или поражение)\n"
        "/stats — посмотреть статистику: банк, winrate, ROI\n"
        "/export — экспортировать все ставки в файл CSV\n"
        "/info — показать это меню помощи"
    )

async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши ставку в формате:\nМатч: NaVi vs BIG\nСумма: 2\nКэф: 1.7")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i, b in enumerate(bets):
        if b["status"] == "pending":
            keyboard.append([InlineKeyboardButton(f"{b['match']} ({b['amount']}€, кэф {b['coeff']})", callback_data=f"select_{i}")])
    if not keyboard:
        await update.message.reply_text("Нет активных ставок для завершения.")
        return
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери ставку, чтобы ввести результат:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bank
    query = update.callback_query
    await query.answer()

    if query.data.startswith("select_"):
        index = int(query.data.split("_")[1])
        context.user_data["selected_bet"] = index
        keyboard = [
            [
                InlineKeyboardButton("✅ Победа", callback_data='result_win'),
                InlineKeyboardButton("❌ Поражение", callback_data='result_lose')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Выбрана ставка: {bets[index]['match']}\nВыбери результат:", reply_markup=reply_markup)

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
            await query.edit_message_text(f"✅ Победа по ставке: {bet['match']}\n+{profit:.2f}€\n💰 Новый банк: {bank:.2f}€")
        else:
            bet["status"] = "lose"
            await query.edit_message_text(f"❌ Поражение по ставке: {bet['match']}\n-{bet['amount']:.2f}€\n💰 Новый банк: {bank:.2f}€")

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
            bets.append({"match": match, "amount": amount, "coeff": coeff, "status": "pending", "time": bet_time})
            bank -= amount
            await update.message.reply_text(f"✅ Ставка добавлена: {match}, {amount}€, кэф {coeff}\n💰 Банк: {bank:.2f}€")
        except:
            await update.message.reply_text("⚠️ Формат неверный. Используй:\nМатч: ...\nСумма: ...\nКэф: ...")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Удалён вечерний отчёт временно, чтобы сосредоточиться на переносе

    app.run_polling()
