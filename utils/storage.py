# ✅ Обновлённый utils/storage.py
import json
import os
from zoneinfo import ZoneInfo

# Railway persistent storage
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
        save_data()
    except Exception as e:
        users_data = {}
        print(f"[ERROR] Ошибка при загрузке: {e}")

def save_data():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"[ERROR] Ошибка при сохранении: {e}")

def get_user(chat_id: str):
    chat_id = str(chat_id)

    # Не создаём нового пользователя сразу, только если он авторизовался
    return users_data.get(chat_id, {})


def create_user(chat_id: str, login: str):
    global users_data
    chat_id = str(chat_id)

    # Если кто-то уже был с таким логином — перенеси данные
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
