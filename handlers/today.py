from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from datetime import datetime
from utils.storage import get_user
from utils.timezone import LATVIA_TZ

# /today — вставка прогнозов из ChatGPT, форматирование и отправка
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ''
    lines = text.splitlines()

    if context.user_data.get('awaiting_today_input'):
        context.user_data.pop('awaiting_today_input', None)
        # отбрасываем всё до первой линии со «@»
        start_idx = next((i for i, l in enumerate(lines) if '@' in l), 0)
        await process_today_lines(update, context, lines[start_idx:])
        return

    if len(lines) == 1:
        context.user_data['awaiting_today_input'] = True
        await update.message.reply_text('📥 Вставь прогноз (список ставок), начиная со следующего сообщения.')
        return

    # если текст на той же строке с /today
    lines = lines[1:]
    if not any('@' in l for l in lines):
        await update.message.reply_text('⚠️ Вставь прогноз в формате: Матч – исход @коэффициент')
        return

    await process_today_lines(update, context, lines)

# Группируем строки в записи, форматируем и распределяем по категориям
def format_entries(lines: list[str]) -> str:
    # группировка по запускам строки с @
    entries = []
    current = []
    for line in lines:
        if '@' in line and current:
            entries.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append(current)

    cats = {'safe': [], 'value': [], 'sharp': [], 'wildcard': [], 'other': []}
    for group in entries:
        text = '\n'.join(g.strip() for g in group if g.strip())
        # определяем категорию по тегу
        tag = None
        for t in ['#safe', '#value', '#sharp', '#wildcard']:
            if t in text:
                tag = t.lstrip('#')
                break
        if not tag:
            # fallback по коэффициенту
            try:
                coeff = float(text.split('@')[-1].split()[0])
            except:
                tag = 'other'
            else:
                if coeff <= 1.20:
                    tag = 'safe'
                elif coeff <= 2.50:
                    tag = 'value'
                elif coeff <= 3.50:
                    tag = 'sharp'
                else:
                    tag = 'wildcard'
        cats.setdefault(tag, []).append(text)

    # строим сообщение
    msg = '📅 <b>Ставки на сегодня:</b>\n\n'
    total = 0
    for cat in ['safe', 'value', 'sharp', 'wildcard']:
        items = cats.get(cat, [])
        if items:
            msg += f'<b>#{cat}:</b>\n'
            for i, e in enumerate(items, 1):
                msg += f'{i}. {e}\n\n'
            total += len(items)
    form = 'ставка' if total == 1 else 'ставки' if total < 5 else 'ставок'
    msg += f'💰 Всего: {total} {form}'
    if total == 0:
        return '⚠️ Ни одна ставка не распознана. Убедись, что используешь формат из промпта.'
    return msg

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
            " • 1–2 максимально надёжные #safe (1.10–1.25),\n"
            " • до 5 логичных #value (1.60–2.80),\n"
            " • максимум 2 обоснованные #sharp (2.80–3.50) или #wildcard (3.50+).\n"
            "Начинай с матчей с 06:00 по Риге.\n\n"
            "Ищи по всем видам спорта: CS2, футбол, хоккей, теннис, настольный теннис, волейбол, баскетбол, гандбол, Dota, LoL, Valorant, Rocket League.\n\n"
            "Цель: вырастить банк до €800. Готов ставить до 70% банка в день.\n\n"
            "Банк:\n"
            f" • Optibet: €{banks.get('optibet',0):.2f}\n"
            f" • Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент  \n"
            "Краткое пояснение, почему ставка логична.  \n"
            "⏰ Начало / окончание.  \n"
            "⏳ До какого времени желательно поставить.  \n"
            "💵 Рекомендованная сумма: €[сумма], [платформа]  \n"
            "Тег: #[safe]/#[value]/#[sharp]/#[wildcard]"
        )
    else:
        text = (
            "Я разбираюсь только в футболе, хоккее и CS2.\n\n"
            f"Найди 1–3 логичных ставок (#value, #sharp, #wildcard) на вечер сегодня ({today}) и утро следующего дня до 09:00.\n\n"
            "Ищи по всем дисциплинам: CS2, футбол, хоккей, теннис, баскетбол, настольный теннис, волейбол, гандбол, Dota, LoL, Valorant.\n\n"
            "Цель: вырастить банк до €800. Могу использовать до 70% оставшегося банка.\n\n"
            "Банк:\n"
            f" • Optibet: €{banks.get('optibet',0):.2f}\n"
            f" • Olybet:  €{banks.get('olybet',0):.2f}\n\n"
            "Формат каждой ставки:\n"
            "Команда1 vs Команда2 – исход @коэффициент  \n"
            "Краткое пояснение, почему ставка логична.  \n"
            "⏰ Начало / окончание.  \n"
            "⏳ До какого времени желательно поставить.  \n"
            "💵 Рекомендованная сумма: €[сумма], [платформа]  \n"
            "Тег: #[value]/#[sharp]/#[wildcard]"
        )
    await query.message.reply_text(text)
