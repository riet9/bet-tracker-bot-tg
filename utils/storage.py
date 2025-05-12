import json
import os
from zoneinfo import ZoneInfo

# 📁 Файл Railway
DATA_FILE = "/mnt/data/users_data.json"
LATVIA_TZ = ZoneInfo("Europe/Riga")
users_data = {}

def load_data():
    global users_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
            print("[INFO] Загружены данные из Railway.")
    except FileNotFoundError:
        users_data = {}
        print("[INFO] Новый файл данных создан.")
    except Exception as e:
        users_data = {}
        print(f"[ERROR] Ошибка при загрузке: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"[ERROR] Ошибка при сохранении: {e}")

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

# 🔁 Создание файла, если его не было
if not os.path.exists(DATA_FILE):
    save_data()
