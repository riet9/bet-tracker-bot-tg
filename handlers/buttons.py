from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.storage import get_user, save_data

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    user = get_user(chat_id)
    data = query.data

    if data.startswith("res_"):
        index = int(data.split("_")[1])
        context.user_data["selected"] = index
        bet = user["bets"][index]
        keyboard = [
            [
                InlineKeyboardButton("✅ Победа", callback_data="win"),
                InlineKeyboardButton("❌ Поражение", callback_data="lose")
            ]
        ]
        await query.edit_message_text(
            f"Выбрана ставка: {bet['match']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("del_"):
        index = int(data.split("_")[1])
        bet = user["bets"][index]
        if bet["status"] != "pending":
            await query.edit_message_text("⚠️ Ставка уже завершена или неактивна.")
            return

        platform = bet.get("source", "optibet")
        user["banks"][platform] += bet["amount"]
        bet["status"] = "deleted"
        save_data()

        await query.edit_message_text(
            f"❌ Ставка удалена: {bet['match']}\n"
            f"💰 Деньги возвращены: {bet['amount']}€\n"
            f"Банк {platform}: {user['banks'][platform]:.2f}€"
        )

    elif data.startswith("undel_"):
        index = int(data.split("_")[1])
        bet = user["bets"][index]
        platform = bet.get("source", "optibet")
        if bet["status"] != "deleted":
            await query.edit_message_text("⚠️ Нельзя восстановить эту ставку.")
            return
        if user["banks"][platform] < bet["amount"]:
            await query.edit_message_text("⚠️ Недостаточно средств для восстановления.")
            return

        user["banks"][platform] -= bet["amount"]
        bet["status"] = "pending"
        save_data()

        await query.edit_message_text(
            f"✅ Ставка восстановлена: {bet['match']}\n"
            f"💸 {bet['amount']}€ снято\n"
            f"Текущий банк {platform}: {user['banks'][platform]:.2f}€"
        )

    elif data in ["win", "lose"]:
        index = context.user_data.get("selected")
        if index is None:
            return

        bet = user["bets"][index]
        if bet["status"] != "pending":
            await query.edit_message_text("Ставка уже завершена.")
            return

        source = bet.get("source", "optibet")
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