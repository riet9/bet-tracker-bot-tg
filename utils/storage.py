# ✅ Финальный utils/storage.py — с безопасным load_data
import json
import os
from zoneinfo import ZoneInfo

# Railway persistent path
DATA_FILE = "/mnt/data/users_data.json"
LATVIA_TZ = ZoneInfo("Europe/Riga")
users_data = {}

def load_data():
    global users_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
            print("📂 load_data() вызван — загружено пользователей:", len(users_data))
    except FileNotFoundError:
        users_data = {}
        print("📁 Файл не найден. Создана пустая структура, но НЕ сохраняем файл.")
    except Exception as e:
        users_data = {}
        print(f"[ERROR] Ошибка при загрузке: {e}")

def save_data():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False, default=str)
        print("💾 save_data() вызван — пользователей:", len(users_data))
    except Exception as e:
        print(f"[ERROR] Ошибка при сохранении: {e}")

def get_user(chat_id: str):
    chat_id = str(chat_id)
    return users_data.get(chat_id, {})

def create_user(chat_id: str, login: str):
    global users_data
    chat_id = str(chat_id)

    for uid, u in list(users_data.items()):
        if u.get("login") == login and uid != chat_id:
            users_data[chat_id] = u
            del users_data[uid]
            save_data()
            return users_data[chat_id]

    users_data[chat_id] = {
        "banks": {"optibet": 0.0, "olybet": 0.0, "bonus": 0.0},
        "bets": [],
        "login": login,
        "timezone": "Europe/Riga",
        "authorized": True
    }
    save_data()
    return users_data[chat_id]
