from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from collections import Counter
from utils.storage import get_user
from utils.auth import require_auth

# /top_teams — показать топ команд по ставкам
async def top_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_chat.id))
    completed = [b for b in user["bets"] if b["status"] in ("win", "lose")]
    matches = [b["match"] for b in completed]

    teams = []
    for match in matches:
        parts = match.split(" vs ")
        if len(parts) == 2:
            teams.extend(parts)

    counter = Counter(teams)
    most_common = counter.most_common(5)

    if not most_common:
        await update.message.reply_text("📭 Нет завершённых ставок для анализа.")
        return

    msg = "📊 <b>Топ команд по ставкам:</b>\n\n"
    for i, (team, count) in enumerate(most_common, 1):
        team_wins = sum(1 for b in completed if team in b["match"] and b["status"] == "win")
        msg += f"{i}. {team} — {count} ставок ({team_wins} побед)\n"

    await update.message.reply_text(msg, parse_mode="HTML")

# /review — краткий анализ последних 10 ставок
async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_chat.id))
    last_bets = [b for b in user["bets"] if b["status"] in ("win", "lose")][-10:]


    if not last_bets:
        await update.message.reply_text("📭 Нет завершённых ставок для анализа.")
        return

    value_count = sum(1 for b in last_bets if b.get("type") == "value")
    safe_count = sum(1 for b in last_bets if b.get("type") == "safe")
    avg_coeff = sum(b["coeff"] for b in last_bets) / len(last_bets)
    winrate = sum(1 for b in last_bets if b["status"] == "win") / len(last_bets) * 100

    risky_bets = [b for b in last_bets if b["amount"] > 0.3 * user["banks"].get(b["source"], 0)]

    msg = (
        f"📊 <b>Анализ последних {len(last_bets)} ставок:</b>\n"
        f"- #value: {value_count} | #safe: {safe_count}\n"
        f"- Средний кэф: {avg_coeff:.2f}\n"
        f"- Winrate: {winrate:.1f}%\n\n"
    )

    if value_count > safe_count:
        msg += "🧠 <b>Стратегия #value выглядит прибыльнее</b>\n"
    elif safe_count > value_count:
        msg += "🧠 <b>Ты чаще используешь #safe ставки — стабильный подход</b>\n"
    else:
        msg += "🧠 <b>Баланс между #safe и #value</b>\n"

    if risky_bets:
        msg += f"⚠️ {len(risky_bets)} ставок были на 30%+ от банка — пересмотри банк-менеджмент.\n"

    await update.message.reply_text(msg, parse_mode="HTML")
