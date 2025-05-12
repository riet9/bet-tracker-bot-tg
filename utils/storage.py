import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_FILE = "data/users_data.json"
LATVIA_TZ = ZoneInfo("Europe/Riga")
users_data = {}

def load_data():
    global users_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
    except FileNotFoundError:
        users_data = {}

def save_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as original:
                content = original.read()
            with open("data/data_backup.json", "w", encoding="utf-8") as backup:
                backup.write(content)
    except Exception as e:
        print(f"[WARN] Не удалось создать резервную копию: {e}")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False, default=str)

def get_user(chat_id: str):
    chat_id = str(chat_id)
    if chat_id not in users_data:
        users_data[chat_id] = {
            "banks": {
                "optibet": 0.0,
                "olybet": 0.0,
                "bonus": 0.0
            },
            "bets": [],
            "timezone": "Europe/Riga"
        }
    else:
        # Миграция со старой структуры
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
