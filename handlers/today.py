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

    # Ждём, когда пользователь вставит прогноз во втором сообщении
    if len(lines) == 1:
        context.user_data['awaiting_today_input'] = True
        await update.message.reply_text(
            '📥 Вставь прогноз (список ставок), начиная со следующего сообщения.'
        )
        return

    # Если это продолжение /today
    lines = lines[1:]
    if len(lines) < 2:
        await update.message.reply_text(
            '⚠️ Вставь прогноз в формате:\n\nМатч – исход @кэф\nПояснение'
        )
        return

    await process_today_lines(update, context, lines)

# Обработка строк прогноза из ChatGPT
async def process_today_lines(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    safe, value = [], []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '@' not in line:
            i += 1
            continue

        # Собираем пояснения и метаданные
        explanation = start_time = end_time = deadline = stake = ''
        # Пояснение на следующей строке
        if i+1 < len(lines) and '@' not in lines[i+1]:
            explanation = lines[i+1].strip()
            i += 1
        # До 4 строк дополнительных данных
        for _ in range(4):
            if i+1 >= len(lines):
                break
            nl = lines[i+1].strip()
            ll = nl.lower()
            if ll.startswith('начало:'):
                start_time = nl
            elif ll.startswith('окончание:') or ll.startswith('оконч:'):
                end_time = nl
            elif ll.startswith('ставить до:') or ll.startswith('до:'):
                deadline = nl
            elif ll.startswith('рекомендованная сумма:'):
                stake = nl
            else:
                break
            i += 1

        # Коэффициент
        try:
            coeff = float(line.split('@')[-1].strip())
        except:
            coeff = None

        # Собираем полную запись
        entry = line
        if explanation:
            entry += f"\n💬 {explanation}"
        if start_time:
            entry += f"\n⏰ {start_time}"
        if end_time:
            entry += f"\n⏳ {end_time}"
        if deadline:
            entry += f"\n🕓 {deadline}"
        if stake:
            entry += f"\n💵 {stake}"

        # Классификация
        if coeff:
            if coeff <= 1.20 and len(safe) < 2:
                safe.append(entry)
            elif 1.60 <= coeff <= 2.50 and len(value) < 5:
                value.append(entry)
        i += 1

    # Формируем сообщение
    msg = '📅 <b>Ставки на сегодня:</b>\n\n'
    if safe:
        msg += '<b>#safe:</b>\n' + ''.join(f"{idx}. {e}\n\n" for idx, e in enumerate(safe, 1))
    if value:
        msg += '<b>#value:</b>\n' + ''.join(f"{idx}. {e}\n\n" for idx, e in enumerate(value, 1))

    total = len(safe) + len(value)
    forms = ('ставка', 'ставки', 'ставок')
    form = forms[0] if total%10==1 and total%100!=11 else forms[1] if 2<=total%10<=4 and not 12<=total%100<=14 else forms[2]
    msg += f"💰 Всего: {total} {form}"

    if not safe and not value:
        await update.message.reply_text(
            '⚠️ Ни одна ставка не распознана. Убедись, что используешь формат из промпта.'
        )
        return

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

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

# Обработчик кнопок /prompt
async def prompt_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    user = get_user(chat_id)
    banks = user.get('banks', {})
    today = datetime.now(LATVIA_TZ).strftime('%d.%m.%Y')

    if query.data == 'prompt_morning':
        text = (
            f"Найди 1–2 максимально надёжные #safe (1.10–1.25), до 5 логичных #value (1.60–2.80) и "
            f"максимум 2 обоснованные #sharp (2.80–3.50) или #wildcard (3.50+) ставки на сегодня ({today}).\n"
            "Приоритет: CS2, футбол, хоккей. Если есть оправданные варианты в теннисе, баскетболе и других дисциплинах — тоже включи.\n\n"
            "Моя цель: с текущего банка дойти до €800.\n"
            "Готов поставить до 70% банка в день, если ставки обоснованы.\n\n"
            "Банк:\n"
            f"- Optibet: €{banks.get('optibet',0):.2f}\n"
            f"- Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент\n"
            "Краткое пояснение, почему ставка логична.\n"
            "Начало: [время по Риге], окончание: ~[время окончания]\n"
            "⏳ До какого времени желательно поставить\n"
            "Рекомендованная сумма: €[сумма], [платформа]\n"
            "Тег: #[safe]/#[value]/#[sharp]/#[wildcard]\n\n"
            "❗️Только реальные матчи и линии. Не добавляй текст до или после — только чистый список."
        )
    else:
        text = (
            f"Есть ли ещё 1–3 логичных ставки (#value, #sharp или #wildcard) на вечер/ночь сегодня ({today})?\n"
            "Проверь, появились ли актуальные матчи по CS2, хоккею, NBA, футболу или другим дисциплинам с вечерними событиями.\n\n"
            "Учитывай остаток моего банка:\n"
            f"- Optibet: €{banks.get('optibet',0):.2f}\n"
            f"- Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент\n"
            "Краткое пояснение, почему ставка логична.\n"
            "Начало: [время по Риге], окончание: ~[время окончания]\n"
            "⏳ До какого времени желательно поставить\n"
            "Рекомендованная сумма: €[сумма], [платформа]\n"
            "Тег: #[value]/#[sharp]/#[wildcard]\n\n"
            "❗️Ищи глубоко и выбирай только действительно стоящие варианты.\n"
            "❗️Без воды — только список в формате выше."
        )

    await query.message.reply_text(text)
