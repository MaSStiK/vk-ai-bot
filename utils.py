import json
import os
from datetime import datetime, timezone

MEMORY_FILE = "dialog_memory.json"
ERROR_FILE = "error.json"

# Получение текущей даты
def get_time_now():
    return str(datetime.now(timezone.utc)).split(".")[0].replace(":", ".")

# Логирование времени
def log_error(e):
    try:
        error_entry = {"time": get_time_now(), "error": str(e)}
        errors = []

        if os.path.exists("error.json"):
            with open("error.json", "r", encoding="utf-8") as f:
                try:
                    errors = json.load(f)
                except json.JSONDecodeError:
                    pass # Файл может быть пустым или поврежденным

        errors.append(error_entry)

        with open("error.json", "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=4)

    except Exception as log_exc:
        print(f"Ошибка логирования: {log_exc}")

# Загрузка памяти бота
def load_memory():
    user_histories = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                user_histories.update(json.load(f))
                print(f"Загружено {len(user_histories)} пользователей из памяти.")
        except Exception as e:
            print(f"Не удалось загрузить память: {e}")
            log_error(f"Не удалось загрузить память: {e}")

    return user_histories

# Сохранение памяти бота
def save_memory(user_histories):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(user_histories, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Не удалось сохранить память: {e}")
        log_error(f"Не удалось сохранить память: {e}")
