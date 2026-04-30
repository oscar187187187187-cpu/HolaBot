import json
import os
from datetime import date, datetime, timedelta

DB_FILE = "habitpeak_storage.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validierung der Felder für Robustheit
                fields = ["vocab", "xp", "streak", "last_login", "completed_lessons", "stats"]
                for field in fields:
                    if field not in data:
                        if field == "vocab": data[field] = []
                        elif field == "stats": data[field] = {"total_errors": 0}
                        else: data[field] = 0
                return data
        except Exception:
            pass
    return {
        "vocab": [], 
        "xp": 0, 
        "streak": 0, 
        "last_login": "", 
        "completed_lessons": 0,
        "stats": {"total_errors": 0}
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def add_words_bulk(text_input, category="Allgemein"):
    data = load_data()
    raw_list = text_input.replace("\n", ",").split(",")
    added_count = 0
    existing_words = [v["word"].lower() for v in data["vocab"]]
    
    for word in raw_list:
        clean_word = word.strip().lower()
        if clean_word and clean_word not in existing_words:
            data["vocab"].append({
                "word": clean_word,
                "cat": category,
                "errors": 0,
                "success": 0,
                "added_at": str(date.today())
            })
            added_count += 1
    save_data(data)
    return added_count

def delete_word(word_to_del):
    data = load_data()
    data["vocab"] = [v for v in data["vocab"] if v["word"] != word_to_del]
    save_data(data)

def check_streak():
    data = load_data()
    today = date.today()
    if not data["last_login"]:
        return data

    last_date = datetime.strptime(data["last_login"], "%Y-%m-%d").date()
    diff = (today - last_date).days

    if diff == 1:
        # Streak gehalten - wird beim ersten XP-Gewinn erhöht
        pass 
    elif diff > 1:
        # Streak verloren
        data["streak"] = 0
    
    save_data(data)
    return data

def get_smart_words(limit=5):
    data = load_data()
    # Sortiert nach Fehlern (absteigend) und Erfolg (aufsteigend)
    sorted_vocab = sorted(data["vocab"], key=lambda x: (x["errors"], -x["success"]), reverse=True)
    return [v["word"] for v in sorted_vocab[:limit]]

def get_unit_structure():
    data = load_data()
    all_words = [v["word"] for v in data["vocab"]]
    units = []
    # 5 Wörter bilden eine Lerneinheit
    for i in range(0, len(all_words), 5):
        units.append({
            "id": (i // 5) + 1,
            "words": all_words[i:i+5]
        })
    return units
