from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from utils.storage import get_user

# /today — вставка прогнозов в формате ChatGPT
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lines = text.splitlines()

    if len(lines) == 1:
        context.user_data["awaiting_today_input"] = True
        await update.message.reply_text("📥 Вставь прогноз (список ставок), начиная со следующего сообщения.")
        return

    lines = lines[1:]  # убираем /today
    if len(lines) < 2:
        await update.message.reply_text("⚠️ Вставь прогноз в формате:\n\nМатч – исход @кэф\nПояснение")
        return

    await process_today_lines(update, context, lines)

# Обработка строк прогноза из ChatGPT
async def process_today_lines(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    safe, value = [], []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "@" not in line:
            i += 1
            continue

        explanation = ""
        start_time = ""
        end_time = ""
        stake_line = ""

        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and "@" not in next_line:
                explanation = next_line
                i += 1

        for _ in range(3):
            if i + 1 >= len(lines):
                break
            next_line = lines[i + 1].strip().lower()
            if next_line.startswith("начало:"):
                start_time = lines[i + 1].strip()
            elif next_line.startswith("окончание:") or next_line.startswith("оконч:"):
                end_time = lines[i + 1].strip()
            elif next_line.startswith("рекомендованная сумма:"):
                stake_line = lines[i + 1].strip()
            else:
                break
            i += 1

        try:
            coeff = float(line.split("@")[-1].strip())
        except:
            coeff = None

        full_entry = f"{line}"
        if explanation: full_entry += f"\n💬 {explanation}"
        if start_time:  full_entry += f"\n⏰ {start_time}"
        if end_time:    full_entry += f"\n⏳ {end_time}"
        if stake_line:  full_entry += f"\n💵 {stake_line}"

        if coeff:
            if coeff <= 1.20 and len(safe) < 2:
                safe.append(full_entry)
            elif 1.60 <= coeff <= 2.50 and len(value) < 5:
                value.append(full_entry)

        i += 1

    msg = "📅 <b>Ставки на сегодня:</b>\n\n"
    if safe:
        msg += "<b>#safe:</b>\n"
        for idx, entry in enumerate(safe, 1):
            msg += f"{idx}. {entry}\n\n"
    if value:
        msg += "<b>#value:</b>\n"
        for idx, entry in enumerate(value, 1):
            msg += f"{idx}. {entry}\n\n"

    total = len(safe) + len(value)
    msg += f"💰 Всего: {total} {'ставка' if total == 1 else 'ставки' if total < 5 else 'ставок'}"

    if not safe and not value:
        await update.message.reply_text("⚠️ Ни одна ставка не распознана. Убедись, что используешь формат из промпта.")
        return

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# /prompt — генерация ChatGPT-промпта
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
        "Найди 0–2 максимально надёжные #safe ставки и 0–5 логичных #value ставок на сегодня по CS2, футболу и хоккею.\n"
        "Если есть действительно ценные ставки в других дисциплинах — тоже включи.\n\n"
        "Учитывай мой текущий банк:\n"
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
