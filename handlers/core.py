from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from utils.storage import get_user, save_data, users_data

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
