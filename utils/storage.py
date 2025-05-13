# ✅ Финальный utils/storage.py — мутируем словарь вместо переопределения
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
        if not os.path.exists(DATA_FILE):
            users_data.clear()
            print("📁 Файл не найден. Создана пустая структура, но НЕ сохраняем файл.")
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        users_data.clear()
        users_data.update(data)
        print("📂 load_data() вызван — загружено пользователей:", len(users_data))
    except Exception as e:
        users_data.clear()
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

    # Если пользователь с таким логином уже есть — переносим данные
    for uid, u in list(users_data.items()):
        if u.get("login") == login and uid != chat_id:
            users_data[chat_id] = u
            del users_data[uid]
            save_data()
            return users_data[chat_id]

    # Иначе создаём новый профиль
    users_data[chat_id] = {
        "banks": {"optibet": 0.0, "olybet": 0.0, "bonus": 0.0},
        "bets": [],
        "login": login,
        "timezone": "Europe/Riga",
        "authorized": True
    }
    save_data()
    return users_data[chat_id]
