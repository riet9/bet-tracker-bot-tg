from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from datetime import datetime
from utils.storage import get_user
from utils.timezone import LATVIA_TZ

# /today — вставка прогнозов в формате ChatGPT
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ''
    lines = text.splitlines()

    if context.user_data.get('awaiting_today_input'):
        context.user_data.pop('awaiting_today_input', None)
        start_idx = next((i for i, l in enumerate(lines) if '@' in l), 0)
        await process_today_lines(update, context, lines[start_idx:])
        return

    if len(lines) == 1:
        context.user_data['awaiting_today_input'] = True
        await update.message.reply_text('📥 Вставь прогноз (список ставок), начиная со следующего сообщения.')
        return

    lines = lines[1:]
    if len(lines) < 2:
        await update.message.reply_text('⚠️ Вставь прогноз в формате:\n\nМатч – исход @коэф\nПояснение')
        return

    await process_today_lines(update, context, lines)

# Вспомогательная функция для форматирования
def format_entries(lines: list[str]) -> str:
    safe, value = [], []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '@' not in line:
            i += 1
            continue
        explanation = start_time = end_time = deadline = stake = ''
        if i+1 < len(lines) and '@' not in lines[i+1]:
            explanation = lines[i+1].strip(); i += 1
        for _ in range(4):
            if i+1 >= len(lines): break
            nl = lines[i+1].strip(); ll = nl.lower()
            if ll.startswith('начало:'): start_time = nl
            elif ll.startswith('окончание:') or ll.startswith('оконч:'): end_time = nl
            elif ll.startswith('ставить до:') or ll.startswith('до:'): deadline = nl
            elif ll.startswith('рекомендованная сумма:'): stake = nl
            else: break
            i += 1
        try: coeff = float(line.split('@')[-1].strip())
        except: coeff = None
        entry = line
        if explanation: entry += f"\n💬 {explanation}"
        if start_time: entry += f"\n⏰ {start_time}"
        if end_time: entry += f"\n⏳ {end_time}"
        if deadline: entry += f"\n🕓 {deadline}"
        if stake: entry += f"\n💵 {stake}"
        if coeff:
            if coeff <= 1.20 and len(safe) < 2: safe.append(entry)
            elif 1.60 <= coeff <= 2.50 and len(value) < 5: value.append(entry)
        i += 1

    msg = '📅 <b>Ставки на сегодня:</b>\n\n'
    if safe:
        msg += '<b>#safe:</b>\n' + ''.join(f"{idx}. {e}\n\n" for idx,e in enumerate(safe,1))
    if value:
        msg += '<b>#value:</b>\n' + ''.join(f"{idx}. {e}\n\n" for idx,e in enumerate(value,1))
    total = len(safe) + len(value)
    forms = ('ставка','ставки','ставок')
    suffix = forms[0] if total%10==1 and total%100!=11 else forms[1] if 2<=total%10<=4 and not 12<=total%100<=14 else forms[2]
    msg += f"💰 Всего: {total} {suffix}"
    if not safe and not value:
        return '⚠️ Ни одна ставка не распознана. Убедись, что используешь формат из промпта.'
    return msg

# /process_today_lines — отправка отформатированных ставок
async def process_today_lines(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    response = format_entries(lines)
    await update.message.reply_text(
        response,
        parse_mode=ParseMode.HTML if response.startswith('📅') else None
    )

# /prompt — выбор утреннего или вечернего промпта
async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('🌅 Утренний промпт', callback_data='prompt_morning')],
        [InlineKeyboardButton('🌙 Вечерний промпт', callback_data='prompt_evening')]
    ]
    await update.message.reply_text(
        'Выбери промпт для ChatGPT:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик кнопок промптов
async def prompt_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    chat_id = str(query.message.chat.id)
    user = get_user(chat_id); banks = user.get('banks', {})
    today = datetime.now(LATVIA_TZ).strftime('%d.%m.%Y')

    if query.data == 'prompt_morning':
        text = (
            "Я разбираюсь только в футболе, хоккее и CS2.\n\n"
            f"Найди на сегодня ({today}):\n"
            " • 1–2 максимально надёжные #safe (коэффициенты 1.10–1.25),\n"
            " • до 5 логичных #value (1.60–2.80),\n"
            " • максимум 2 обоснованные #sharp (2.80–3.50) или #wildcard (3.50+).\n\n"
            "Начинай с матчей, которые стартуют с 06:00 по Риге и позже.\n\n"
            "Ищи по всем видам спорта и лигам: CS2, футбол, хоккей, теннис, настольный теннис, волейбол, баскетбол, гандбол, Dota, LoL, Valorant, Rocket League и другим. Не ограничивайся топ-турнирами и популярными лигами.\n\n"
            "Я доверяю системе. Готов ставить даже на дисциплины, в которых не разбираюсь, если ставка обоснована и имеет value.\n\n"
            "Цель: вырастить банк до €800.\n"
            "Готов ставить до 70% банка в день, если value явно оправдано.\n\n"
            "Банк:\n"
            f" • Optibet: €{banks.get('optibet',0):.2f}\n"
            f" • Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент  \n"
            "Краткое пояснение, почему ставка логична.  \n"
            "Начало: [время по Риге], окончание: ~[время окончания]  \n"
            "⏳ До какого времени желательно поставить  \n"
            "Рекомендованная сумма: €[сумма], [платформа]  \n"
            "Тег: #[safe]/#[value]/#[sharp]/#[wildcard]\n\n"
            "❗️Только реальные события и линии. Без вводного или завершающего текста — только чистый список в указанном формате."
        )
    else:
        text = (
            "Я разбираюсь только в футболе, хоккее и CS2.\n\n"
            f"Найди 1–3 логичных ставок (#value, #sharp или #wildcard) на:\n"
            f" • вечер сегодня ({today}),\n"
            " • и утро следующего дня (до 09:00 по Риге).\n\n"
            "Ищи по всем дисциплинам: CS2, футбол, хоккей, теннис, баскетбол, настольный теннис, волейбол, гандбол, Dota, LoL, Valorant и другим. Не ограничивайся популярными лигами — ищи value везде.\n\n"
            "Я доверяю системе. Готов ставить даже на дисциплины, в которых не разбираюсь, если ставка обоснована и имеет value.\n\n"
            "Цель: вырастить банк до €800.\n"
            "Могу использовать до 70% оставшегося банка, если ставки логичны.\n\n"
            "Банк:\n"
            f" • Optibet: €{banks.get('optibet',0):.2f}\n"
            f" • Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент  \n"
            "Краткое пояснение, почему ставка логична.  \n"
            "Начало: [время по Риге], окончание: ~[время окончания]  \n"
            "⏳ До какого времени желательно поставить  \n"
            "Рекомендованная сумма: €[сумма], [платформа]  \n"
            "Тег: #[value]/#[sharp]/#[wildcard]\n\n"
            "❗️Только реальные события и линии. Без вводного или завершающего текста — только чистый список в указанном формате."
        )
    await query.message.reply_text(text)
