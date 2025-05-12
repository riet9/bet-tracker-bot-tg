from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import get_user, save_data

# /goal [цель] — установка или показ цели
async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user = get_user(chat_id)

    # Если передана новая цель
    if context.args:
        try:
            target = float(context.args[0])
            if target <= 0:
                raise ValueError
            user["goal"] = target
            save_data()
            await update.message.reply_text(f"🎯 Цель установлена: {target:.2f}€")
        except:
            await update.message.reply_text("⚠️ Укажи корректную сумму. Пример: /goal 800")
        return

    # Если просто /goal — показать прогресс
    goal_value = user.get("goal")
    if not goal_value:
        await update.message.reply_text("🎯 У тебя пока не задана цель. Напиши /goal 800, например.")
        return

    total_bank = sum(user["banks"].values())
    progress = min(100.0, total_bank / goal_value * 100)

    bar = progress_bar(progress)

    await update.message.reply_text(
        f"🎯 Цель: {goal_value:.2f}€\n"
        f"💰 Текущий банк: {total_bank:.2f}€\n"
        f"📈 Прогресс: {progress:.1f}%\n"
        f"{bar}"
    )

def progress_bar(percentage: float) -> str:
    filled = int(percentage // 5)
    empty = 20 - filled
    return "▓" * filled + "░" * empty + f" {percentage:.1f}%"
