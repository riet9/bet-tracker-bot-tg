import logging
import os
import datetime
import csv
import json
import matplotlib.pyplot as plt

DATA_FILE = "data.json"

def load_data():
    global bank, bets
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            bank = data.get("bank", 10.0)
            bets = data.get("bets", [])
    except FileNotFoundError:
        bank = 10.0
        bets = []

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
    with open(DATA_FILE, "w") as file:
        json.dump({"bank": bank, "bets": bets}, file, indent=2, default=str)


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
    await update.message.reply_text("Привет! Я твой бот для ставок. Напиши /bet чтобы добавить ставку. \n /info - что бы узнать список доступных команд")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 <b>Список доступных команд:</b>\n\n"
        "🟢 <b>/start</b> — запустить бота\n"
        "🟢 <b>/bet</b> — добавить ставку по шагам (матч, сумма, кэф)\n"
        "🟢 <b>/result</b> — выбрать активную ставку и указать результат (✅ или ❌)\n"
        "🟢 <b>/stats</b> — статистика: winrate, ROI, средний кэф и банк\n"
        "🟢 <b>/export</b> — выгрузить историю ставок в CSV\n"
        "🟢 <b>/graph</b> — график роста банка по завершённым ставкам\n"
        "🟢 <b>/bank [сумма]</b> — вручную установить текущий банк\n"
        "🟢 <b>/info</b> — показать это меню\n"
        "🟢 <b>/cancel</b> — отменить добавление ставки на любом этапе\n"
        "🟢 <b>/delete</b> — удалить активную ставку и вернуть деньги в банк\n"
        "🟢 <b>/undelete</b> — восстановить удалённую ставку (если удалил случайно)\n"
        "🟢 <b>/pending</b> — список активных ставок (ещё не завершённых)\n"
        "🟢 /safe_stats — статистика по #safe ставкам (низкие кэфы)\n"
        "🟢 /value_stats — статистика по #value ставкам (кэфы 1.60–2.50)\n"
        "🟢 /top_type — сравнение эффективности #safe и #value ставок\n"
        "🟢 /history #type — история ставок по типу (#safe, #value, #normal)\n"

        "\n📁 Все данные сохраняются между перезапусками\n"
        "💬 Просто используй команды или следуй подсказкам"
    , parse_mode="HTML")

    
async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bank
    if context.args:
        try:
            new_bank = float(context.args[0])
            if new_bank < 0:
                await update.message.reply_text("⚠️ Банк не может быть отрицательным.")
                return
            bank = new_bank
            save_data()
            await update.message.reply_text(f"✅ Новый банк установлен: {bank:.2f}€")
        except:
            await update.message.reply_text("⚠️ Введи число. Пример:\n/bank 15")
    else:
        await update.message.reply_text(f"💰 Текущий банк: {bank:.2f}€\nЧтобы изменить, введи:\n/bank 20")

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    completed_bets = [b for b in bets if b["status"] != "pending"]
    if not completed_bets:
        await update.message.reply_text("Нет завершённых ставок для графика.")
        return

    x = []
    y = []
    current = 10.0  # начнем с фиксированного старта

    for b in completed_bets:
        x.append(b["time"].strftime("%Y-%m-%d %H:%M"))
        if b["status"] == "win":
            current += b["amount"] * b["coeff"]
        else:
            current -= b["amount"]
        y.append(current)

    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o")
    plt.xticks(rotation=45, ha='right')
    plt.title("📈 Рост банка по завершённым ставкам")
    plt.xlabel("Дата и время")
    plt.ylabel("Банк (€)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("bank_graph.png")
    plt.close()

    await update.message.reply_photo(photo=open("bank_graph.png", "rb"))


# Первая команда /bet
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bet_step"] = "match"
    await update.message.reply_text("Введи название матча (пример: NaVi vs G2)")

# Обработка каждого шага
async def bet_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bets, bank
    step = context.user_data.get("bet_step")

    if step == "match":
        context.user_data["match"] = update.message.text.strip()
        context.user_data["bet_step"] = "amount"
        await update.message.reply_text("Введи сумму ставки в € (например: 2.5)")

    elif step == "amount":
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                await update.message.reply_text("⚠️ Сумма должна быть больше 0. Попробуй ещё раз.")
                return
            if amount > bank:
                await update.message.reply_text(f"⚠️ У тебя только {bank:.2f}€. Введи меньшую сумму.")
                return
            context.user_data["amount"] = amount
            context.user_data["bet_step"] = "coeff"
            await update.message.reply_text("Введи коэффициент (например: 1.85)")
        except:
            await update.message.reply_text("⚠️ Введи корректное число. Пример: 2.5")

    elif step == "coeff":
        try:
            coeff = float(update.message.text.strip())
            if coeff < 1:
                await update.message.reply_text("⚠️ Коэффициент должен быть не меньше 1.00")
                return

            match = context.user_data["match"]
            amount = context.user_data["amount"]
            bet_time = datetime.datetime.now()

            # Определение типа ставки
            if coeff <= 1.20:
                bet_type = "safe"
            elif 1.60 <= coeff <= 2.50:
                bet_type = "value"
            else:
                bet_type = "normal"

            bets.append({
                "match": match,
                "amount": amount,
                "coeff": coeff,
                "status": "pending",
                "time": bet_time,
                "type": bet_type
            })

            bank -= amount
            context.user_data.clear()
            save_data()
            
            # Запланировать напоминание через 24 часа
            job_queue.run_once(
                remind_result,
                when=datetime.timedelta(hours=24),
                data={"chat_id": update.effective_chat.id, "match": match}
            )
            
            await update.message.reply_text(f"✅ Ставка добавлена: {match}, {amount}€, кэф {coeff} ({'#' + bet_type})\n💰 Банк: {bank:.2f}€")

        except:
            await update.message.reply_text("⚠️ Введи корректный коэффициент. Пример: 1.75")
        


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_bets = [b for b in bets if b["status"] == "pending"]

    if not pending_bets:
        await update.message.reply_text("✅ Все ставки завершены!")
        return

    message = "📋 <b>Активные ставки:</b>\n\n"
    for i, b in enumerate(pending_bets, 1):
        date_str = b['time'].strftime("%d.%m %H:%M")
        message += f"{i}. {b['match']} — {b['amount']}€ @ {b['coeff']} ({date_str})\n"

    await update.message.reply_text(message, parse_mode="HTML")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i, b in enumerate(bets):
        if b["status"] == "pending":
            keyboard.append([
                InlineKeyboardButton(
                    f"{b['match']} ({b['amount']}€, @ {b['coeff']})",
                    callback_data=f"del_{i}"
                )
            ])
    if not keyboard:
        await update.message.reply_text("❌ Нет активных ставок для удаления.")
        return

    await update.message.reply_text(
        "🗑️ Выбери ставку для удаления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def undelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i, b in enumerate(bets):
        if b["status"] == "deleted":
            keyboard.append([
                InlineKeyboardButton(
                    f"{b['match']} ({b['amount']}€, @ {b['coeff']})",
                    callback_data=f"undel_{i}"
                )
            ])
    if not keyboard:
        await update.message.reply_text("📦 Нет удалённых ставок для восстановления.")
        return

    await update.message.reply_text(
        "♻️ Выбери ставку для восстановления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bet_step" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("❌ Добавление ставки отменено.")
    else:
        await update.message.reply_text("ℹ️ Сейчас нет активного ввода ставки.")


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
        
    elif query.data.startswith("del_"):
        index = int(query.data.split("_")[1])
        if index >= len(bets) or bets[index]["status"] != "pending":
            await query.edit_message_text("⚠️ Ставка не найдена или уже завершена.")
            return

        # Возврат в банк
        bank += bets[index]["amount"]
        bets[index]["status"] = "deleted"
        save_data()

        await query.edit_message_text(
            f"❌ Ставка удалена: {bets[index]['match']}\n💰 Банк возвращён: {bets[index]['amount']}€\nТекущий банк: {bank:.2f}€"
        )
    
    elif query.data.startswith("undel_"):
        
        index = int(query.data.split("_")[1])
        if index >= len(bets) or bets[index]["status"] != "deleted":
            await query.edit_message_text("⚠️ Ставка не найдена или уже восстановлена.")
            return

        if bank < bets[index]["amount"]:
            await query.edit_message_text("⚠️ Недостаточно средств в банке для восстановления.")
            return

        bank -= bets[index]["amount"]
        bets[index]["status"] = "pending"
        save_data()

        await query.edit_message_text(
            f"✅ Ставка восстановлена: {bets[index]['match']}\n💸 {bets[index]['amount']}€ вычтено из банка\nТекущий банк: {bank:.2f}€"
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
            save_data()
        else:
            bet["status"] = "lose"
            await query.edit_message_text(f"❌ Поражение: {bet['match']}\n-{bet['amount']:.2f}€\n💰 Банк: {bank:.2f}€")
            save_data()
            
async def remind_result(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    match = job_data["match"]
    await context.bot.send_message(chat_id=chat_id, text=f"🔔 Напоминание: не забудь ввести результат ставки: {match}\nНапиши /result")



async def show_type_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_type: str):
    filtered = [b for b in bets if b.get("type") == bet_type and b["status"] != "pending"]
    if not filtered:
        await update.message.reply_text(f"📭 Нет завершённых ставок с типом #{bet_type}.")
        return

    wins = [b for b in filtered if b["status"] == "win"]
    losses = [b for b in filtered if b["status"] == "lose"]
    total = len(filtered)
    total_wagered = sum(b["amount"] for b in filtered)
    profit = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in filtered)
    avg_coeff = sum(b["coeff"] for b in filtered) / total
    winrate = len(wins) / total * 100

    await update.message.reply_text(
        f"📊 Статистика по #{bet_type} ставкам:\n"
        f"🎯 Завершено: {total}\n"
        f"✅ Побед: {len(wins)} | ❌ Поражений: {len(losses)}\n"
        f"📈 Winrate: {winrate:.1f}%\n"
        f"📉 Средний кэф: {avg_coeff:.2f}\n"
        f"📥 ROI: {profit:.2f}€"
    )

async def safe_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_type_stats(update, context, "safe")

async def value_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_type_stats(update, context, "value")

async def top_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def get_stats(bet_type):
        filtered = [b for b in bets if b.get("type") == bet_type and b["status"] != "pending"]
        if not filtered:
            return None
        wins = [b for b in filtered if b["status"] == "win"]
        total = len(filtered)
        profit = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"] for b in filtered)
        winrate = len(wins) / total * 100
        avg_coeff = sum(b["coeff"] for b in filtered) / total
        return {
            "count": total,
            "wins": len(wins),
            "winrate": winrate,
            "profit": profit,
            "avg_coeff": avg_coeff
        }

    safe = get_stats("safe")
    value = get_stats("value")

    if not safe and not value:
        await update.message.reply_text("❌ Нет завершённых #safe или #value ставок.")
        return

    msg = "📊 <b>Сравнение #safe и #value ставок:</b>\n\n"

    def fmt(title, s):
        return (
            f"<b>{title}:</b>\n"
            f"🎯 Завершено: {s['count']} | ✅ Побед: {s['wins']}\n"
            f"📈 Winrate: {s['winrate']:.1f}%\n"
            f"📉 Средний кэф: {s['avg_coeff']:.2f}\n"
            f"📥 ROI: {s['profit']:.2f}€\n\n"
        )

    if safe:
        msg += fmt("#safe", safe)
    if value:
        msg += fmt("#value", value)

    if safe and value:
        better = "#safe" if safe["profit"] > value["profit"] else "#value"
        msg += f"🏆 Сейчас <b>{better}</b> стратегия приносит больше прибыли!"

    await update.message.reply_text(msg, parse_mode="HTML")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("ℹ️ Используй: /history #safe или /history #value")
        return

    arg = context.args[0].lstrip("#").lower()
    if arg not in ["safe", "value", "normal"]:
        await update.message.reply_text("❌ Неверный тип. Доступны: #safe, #value, #normal")
        return

    filtered = [b for b in bets if b.get("type") == arg and b["status"] != "pending"]
    if not filtered:
        await update.message.reply_text(f"📭 Нет завершённых #{arg} ставок.")
        return

    message = f"📖 История #{arg} ставок:\n\n"
    for b in filtered[-10:]:  # Показываем только последние 10
        date = b['time'].strftime("%d.%m %H:%M")
        status = "✅" if b["status"] == "win" else "❌"
        message += f"{status} {b['match']} — {b['amount']}€ @ {b['coeff']} ({date})\n"

    await update.message.reply_text(message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    completed_bets = [b for b in bets if b["status"] != "pending"]
    wins = [b for b in completed_bets if b["status"] == "win"]
    losses = [b for b in completed_bets if b["status"] == "lose"]

    total = len(completed_bets)
    total_wagered = sum(b["amount"] for b in completed_bets)
    total_profit = sum((b["amount"] * b["coeff"] - b["amount"]) if b["status"] == "win" else -b["amount"]
                       for b in completed_bets)
    avg_coeff = sum(b["coeff"] for b in completed_bets) / total if total else 0
    winrate = (len(wins) / total * 100) if total else 0

    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"💰 Банк: {bank:.2f}€\n"
        f"🎯 Ставок завершено: {total}\n"
        f"✅ Побед: {len(wins)} | ❌ Поражений: {len(losses)}\n"
        f"📈 Winrate: {winrate:.1f}%\n"
        f"📉 Средний кэф: {avg_coeff:.2f}\n"
        f"💸 Сумма ставок: {total_wagered:.2f}€\n"
        f"📥 Прибыль (ROI): {total_profit:.2f}€"
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
    load_data()
    app = ApplicationBuilder().token(TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    bet_step_handler
))
    app.add_handler(CommandHandler("safe_stats", safe_stats))
    app.add_handler(CommandHandler("value_stats", value_stats))
    app.add_handler(CommandHandler("top_type", top_type))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("undelete", undelete))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("cancel", cancel))




    app.run_polling()
