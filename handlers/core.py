from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from auth_config import ALLOWED_USERS
from utils.storage import get_user, save_data, users_data
import json
import os
import subprocess

# Замените на свой Telegram ID
ADMIN_ID = 2047828228  # ← поставь сюда свой chat_id

"""
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if "authorized" in context.user_data and context.user_data["authorized"]:
        await update.message.reply_text("✅ Ты уже авторизован.")
        return

    if "auth_step" not in context.user_data:
        context.user_data["auth_step"] = "login"
        await update.message.reply_text("👤 Введи свой логин:")
        return

    step = context.user_data["auth_step"]
    if step == "login":
        context.user_data["login_attempt"] = update.message.text.strip()
        context.user_data["auth_step"] = "password"
        await update.message.reply_text("🔑 Введи пароль:")
        return

    if step == "password":
        login = context.user_data["login_attempt"]
        password = update.message.text.strip()

        if login in ALLOWED_USERS and ALLOWED_USERS[login] == password:
            context.user_data["authorized"] = True
            context.user_data["login"] = login
            user = get_user(chat_id)
            user["login"] = login
            await update.message.reply_text(f"✅ Добро пожаловать, {login}!")
            get_user(chat_id)
            save_data()
            await update.message.reply_text(
                "👋 Привет! Я бот для отслеживания твоих ставок.\n"
                "Напиши /bet чтобы добавить ставку.\n"
                "Напиши /info, чтобы узнать, что я умею."
            )           
        else:
            await update.message.reply_text("❌ Неверный логин или пароль. Попробуй ещё раз.")
            context.user_data.clear()
    """

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # Уже авторизован
    if context.user_data.get("authorized"):
        await update.message.reply_text("✅ Ты уже авторизован.")
        return

    # Если не начат процесс авторизации — спрашиваем логин
    if "auth_step" not in context.user_data:
        context.user_data["auth_step"] = "login"
        await update.message.reply_text("👤 Введи свой логин:")
        return

    step = context.user_data["auth_step"]

    if step == "login":
        context.user_data["login_attempt"] = update.message.text.strip()
        context.user_data["auth_step"] = "password"
        await update.message.reply_text("🔑 Введи пароль:")
        return

    if step == "password":
        login = context.user_data.get("login_attempt", "")
        password = update.message.text.strip()

        if login in ALLOWED_USERS and ALLOWED_USERS[login] == password:
            context.user_data["authorized"] = True
            context.user_data["login"] = login

            user = get_user(chat_id)
            user["login"] = login
            save_data()

            context.user_data.pop("auth_step", None)
            context.user_data.pop("login_attempt", None)

            await update.message.reply_text(f"✅ Привет, {login}!\nТы успешно авторизован.")
            await update.message.reply_text(
                "Напиши /bet чтобы добавить ставку.\n"
                "Или /info, чтобы узнать, что я умею."
            )
        else:
            await update.message.reply_text("❌ Неверный логин или пароль. Попробуй снова.")
            context.user_data.clear()



async def admin_backup_push(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ У тебя нет доступа.")
        return

    try:
        subprocess.run(["git", "add", "backups/users_data.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Auto backup"], check=True)
        subprocess.run(["git", "push"], check=True)
        await update.message.reply_text("✅ Бэкап запушен в GitHub.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при push: {e}")

"""
# /admin_backup — экспорт users_data.json вручную
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ У тебя нет доступа к этой команде.")
        return

    filename = "users_data_backup.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False, default=str)

    await update.message.reply_document(
        document=open(filename, "rb"),
        filename=filename,
        caption="📄 Резервная копия users_data"
    )
"""

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
        "🟢 <b>/summary 30d</b> — за месяц\n"
        "🟢 <b>/goal</b> — прогресс к цели (€800)\n"
        "🟢 <b>/top_teams</b> — лучшие команды по ROI\n"
        "🟢 <b>/review</b> — обзор последних ставок\n"
        "\n📁 <b>Файл и банк:</b>\n"
        "🟢 <b>/export</b> — сохранить ставки в CSV\n"
        "🟢 <b>/bank [сумма]</b> — установить или узнать банк\n\n"
        "⚙️ <b>Служебные:</b>\n"
        "🟢 <b>/info</b> — показать это меню\n"
        "🟢 <b>/cancel</b> — отменить добавление ставки\n"
        "🟢 <b>/users_count</b> — сколько человек использует бота\n\n"
        "💾 Все данные сохраняются автоматически между перезапусками.\n"
        "💬 Просто используй команды или следуй пошаговым подсказкам.",
        parse_mode=ParseMode.HTML
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
