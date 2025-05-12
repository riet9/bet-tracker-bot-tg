#region Импорт библиотек и переменных
import logging
import os
import datetime
import csv
import json
import matplotlib.pyplot as plt
from telegram.constants import ParseMode

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
LATVIA_TZ = pytz.timezone("Europe/Riga")

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

DATA_FILE = "users_data.json"
users_data = {}
#endregion

#region Load and save data
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
        users_data[chat_id] = {
            "banks": {
                "optibet": 0.0,
                "olybet": 0.0,
                "bonus": 0.0
            },
            "bets": []
        }
    else:
        # Миграция старых данных (если был "bank")
        user = users_data[chat_id]
        if "banks" not in user:
            old_bank = user.get("bank", 0.0)
            user["banks"] = {
                "optibet": old_bank,
                "olybet": 0.0,
                "bonus": 0.0
            }
            user.pop("bank", None)
    return users_data[chat_id]

#endregion

#region Команды интерфейса (/start, /info, /bank, /users_count)
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

        "📆 <b>Прогнозы на день:</b>\n"
        "🟢 <b>/today</b> — вставь прогноз в сообщении или следующим сообщением\n"
        "🟢 <b>/prompt</b> — получить готовый промпт для ChatGPT\n\n"

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
    banks = user["banks"]

    if len(context.args) == 2:
        name, amount_str = context.args
        name = name.lower()
        if name not in banks:
            await update.message.reply_text("❌ Укажи банк: optibet, olybet или bonus.")
            return
        try:
            amount = float(amount_str)
            if amount < 0:
                await update.message.reply_text("⚠️ Сумма не может быть отрицательной.")
                return
            banks[name] = amount
            save_data()
            await update.message.reply_text(f"✅ Установлено: {name} = {amount:.2f}€")
        except:
            await update.message.reply_text("⚠️ Введи корректную сумму.")
    elif len(context.args) == 0:
        total = sum(banks.values())
        msg = (
            f"💰 Банки:\n"
            f"🏦 Optibet: {banks['optibet']:.2f}€\n"
            f"🏦 Olybet: {banks['olybet']:.2f}€\n"
            f"🎁 Бонусы: {banks['bonus']:.2f}€\n"
            f"📊 Всего: {total:.2f}€"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("⚠️ Используй:\n/bank optibet 20 или просто /bank")


async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👥 Всего пользователей: {len(users_data)}")
#endregion

#region Работа со ставками

#Добавление и шаги:
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bet_step"] = "match"
    await update.message.reply_text("Введи название матча (пример: NaVi vs G2)")

async def bet_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # ⬇️ Обработка отложенного прогноза после /today
    if context.user_data.get("awaiting_today_input"):
        context.user_data.pop("awaiting_today_input")
        lines = update.message.text.splitlines()
        if len(lines) < 2:
            await update.message.reply_text("⚠️ Нужно минимум 2 строки: ставка и пояснение.")
            return
        await process_today_lines(update, context, lines)
        return

    
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)
    step = context.user_data.get("bet_step")

    if context.user_data.get("awaiting_reminder_time"):
        context.user_data.pop("awaiting_reminder_time")
        match = context.user_data.pop("last_match", "неизвестный матч")
        answer = update.message.text.strip().lower()

        if answer in ["нет", "no"]:
            await update.message.reply_text("🕑 Напоминание не установлено.")
            return

        try:
            now = datetime.now(LATVIA_TZ)
            dt = LATVIA_TZ.localize(datetime.strptime(answer, "%d.%m %H:%M"))

            if dt < now:
                await update.message.reply_text("⚠️ Указанное время уже прошло. Напоминание не установлено.")
                return

            delta = dt - now
            context.application.job_queue.run_once(
                remind_result,
                when=delta,
                data={"chat_id": chat_id, "match": match}
            )
            await update.message.reply_text(f"🔔 Напоминание установлено на {dt.strftime('%d.%m %H:%M')}")
        except:
            await update.message.reply_text("⚠️ Неверный формат. Используй ДД.ММ ЧЧ:ММ, например: 12.05 18:45")
        return


    if step == "match":
        context.user_data["match"] = update.message.text.strip()
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

            match = context.user_data["match"]
            amount = context.user_data["amount"]
            platform = context.user_data["platform"]
            bet_time = datetime.datetime.now()

            if coeff <= 1.20:
                bet_type = "safe"
            elif 1.60 <= coeff <= 2.50:
                bet_type = "value"
            else:
                bet_type = "normal"

            bet = {
                "match": match,
                "amount": amount,
                "coeff": coeff,
                "status": "pending",
                "time": bet_time,
                "type": bet_type,
                "source": platform
            }

            user["bets"].append(bet)
            user["banks"][platform] -= amount
            save_data()

            # сохраняем ставку и ждём время для напоминания
            context.user_data["awaiting_reminder_time"] = True
            context.user_data["last_match"] = match

            await update.message.reply_text(
                f"✅ Ставка добавлена: {match}, {amount}€, кэф {coeff} ({'#' + bet_type})\n"
                f"💰 Банк {platform}: {user['banks'][platform]:.2f}€\n\n"
                f"🔔 Хочешь установить напоминание о проверке этой ставки?\n"
                f"Введи дату и время в формате: <b>ДД.ММ ЧЧ:ММ</b>\n"
                f"Или напиши <b>нет</b>, если не нужно.", parse_mode="HTML"
            )
        except:
            await update.message.reply_text("⚠️ Введи корректный коэффициент.")



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bet_step" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("❌ Ввод ставки отменён.")
    else:
        await update.message.reply_text("ℹ️ Сейчас ты не вводишь ставку.")


#Текущие ставки:

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

#Удаление / восстановление:
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

#endregion

#region Работа с прогнозом дня

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lines = text.splitlines()

    # Если только /today без прогноза
    if len(lines) == 1:
        context.user_data["awaiting_today_input"] = True
        await update.message.reply_text("📥 Вставь прогноз (список ставок), начиная со следующего сообщения.")
        return

    # Если прогноз сразу в том же сообщении
    lines = lines[1:]  # убираем /today

    if len(lines) < 2:
        await update.message.reply_text("⚠️ Вставь прогноз в формате:\n\nМатч – исход @кэф\nПояснение")
        return

    await process_today_lines(update, context, lines)


async def process_today_lines(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    safe, value = [], []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "@" not in line:
            i += 1
            continue

        explanation = ""
        if i + 1 < len(lines):
            explanation = lines[i+1].strip()
            if "@" not in explanation and explanation != "":
                i += 1
            else:
                explanation = ""

        try:
            coeff = float(line.split("@")[-1].strip())
        except:
            coeff = None

        if coeff:
            if coeff <= 1.20 and len(safe) < 2:
                safe.append((line, explanation))
            elif 1.60 <= coeff <= 2.50 and len(value) < 5:
                value.append((line, explanation))

        i += 1

    msg = "📅 <b>Ставки на сегодня:</b>\n\n"
    if safe:
        msg += "<b>#safe:</b>\n"
        for idx, (line, expl) in enumerate(safe, 1):
            msg += f"{idx}. {line}\n"
            if expl:
                msg += f"💬 {expl}\n"
        msg += "\n"
    if value:
        msg += "<b>#value:</b>\n"
        for idx, (line, expl) in enumerate(value, 1):
            msg += f"{idx}. {line}\n"
            if expl:
                msg += f"💬 {expl}\n"
        msg += "\n"

    total = len(safe) + len(value)
    msg += f"💰 Всего: {total} {'ставка' if total==1 else 'ставки' if total<5 else 'ставок'}"

    if not safe and not value:
        await update.message.reply_text("⚠️ Ни одна ставка не распознана. Убедись, что используешь формат:\n\nNaVi vs G2 – победа G2 @1.85\nКомментарий")
        return

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💡 Получить промпт", callback_data="send_prompt")]]
    await update.message.reply_text(
        "Нажми кнопку ниже, чтобы получить промпт для ChatGPT:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def prompt_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    user = get_user(chat_id)
    banks = user["banks"]

    prompt_text = (
        "Найди 0–2 максимально надёжные #safe ставки и 0–5 логичных #value ставок на сегодня по CS2, футболу и хоккею. "
        "Если есть действительно ценные ставки в других дисциплинах — тоже включи.\n\n"
        f"Учитывай мой текущий банк:\n"
        f"- 🏦 Optibet: €{banks['optibet']:.2f}\n"
        f"- 🏦 Olybet: €{banks['olybet']:.2f}\n\n"
        "Формат каждой ставки:\n"
        "Команда1 vs Команда2 – исход @коэффициент\n"
        "Краткое пояснение, почему ставка логична.\n"
        "Начало: [время по Риге], окончание: ~[время окончания]\n"
        "Рекомендованная сумма: €[сумма], [платформа]\n\n"
        "❗️Не добавляй вводный или завершающий текст. Только чистый список в этом формате."
    )

    await query.message.reply_text(prompt_text)


#endregion

#region Завершение и напоминания (/result, кнопки)

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

        source = bet.get("source", "optibet")  # на всякий случай default
        if data == "win":
            profit = bet["amount"] * bet["coeff"]
            user["banks"][source] += profit
            bet["status"] = "win"
            msg = f"✅ Победа: {bet['match']} ({source})\n+{profit:.2f}€"
        else:
            bet["status"] = "lose"
            msg = f"❌ Поражение: {bet['match']} ({source})\n-{bet['amount']:.2f}€"

        save_data()
        await query.edit_message_text(msg + f"\n💰 Новый банк {source}: {user['banks'][source]:.2f}€")

        
async def remind_result(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    match = data["match"]
    await context.bot.send_message(chat_id=chat_id,
        text=f"🔔 Напоминание: не забудь ввести результат ставки: {match}\nНапиши /result")
    
async def morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = "2047828228"  # Вставь сюда свой Telegram chat_id как строку, например: "123456789"
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌅 Доброе утро! Готовим прогноз 🎯\n\n"
            "Скопируй это в ChatGPT:\n\n"
            "Найди 0–2 максимально надёжные #safe ставки (1.10–1.20) и 0–5 логичных value-ставок (1.60–2.50) "
            "на сегодня по CS2, футболу и хоккею. Если есть действительно ценные ставки в других дисциплинах — тоже включи.\n\n"
            "Формат каждой ставки:\n"
            "Матч – исход @коэффициент\n"
            "Пояснение (1–2 строки)\n\n"
            "❗️Без лишнего текста. Только список."
        ),
        parse_mode="HTML"
    )


#endregion

#region Статистика и аналитика (/stats, /summary, /safe_stats, /top_type и др.)

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
        parse_mode="HTML"
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
    for b in filtered[-10:]:  # последние 10
        dt = datetime.datetime.fromisoformat(b["time"]) if isinstance(b["time"], str) else b["time"]
        status = "✅" if b["status"] == "win" else "❌"
        message += f"{status} {b['match']} — {b['amount']}€ @ {b['coeff']} ({dt.strftime('%d.%m %H:%M')})\n"

    await update.message.reply_text(message, parse_mode="HTML")
#endregion

#region Экспорт и визуализация (/graph, /export)
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
#endregion

#region Регистрация команд и запуск
if __name__ == '__main__':
    load_data()
    app = ApplicationBuilder().token(TOKEN).build()

    app.job_queue.run_daily(
        morning_reminder,
        time=datetime.time(hour=9, minute=0),  # ежедневное напоминание в 9:00
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
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("safe_stats", safe_stats))
    app.add_handler(CommandHandler("value_stats", value_stats))
    app.add_handler(CommandHandler("top_type", top_type))
    app.add_handler(CommandHandler("users_count", users_count))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("export", export))

    app.add_handler(CommandHandler("prompt", prompt))
    app.add_handler(CallbackQueryHandler(prompt_button_handler, pattern="^send_prompt$"))


    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bet_step_handler))


    app.run_polling()
#endregion