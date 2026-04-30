import json
import os
from datetime import date

DB_FILE = "holalingo_ultimate.json"

def load_data():
    """Lädt alle Nutzerdaten und setzt Standardwerte, falls leer."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                defaults = {"vocab": [], "path_xp": 0, "streak": 0, "last_login": "", "completed_lessons": 0}
                for k, v in defaults.items():
                    if k not in data: data[k] = v
                return data
        except Exception:
            pass
    return {"vocab": [], "path_xp": 0, "streak": 0, "last_login": "", "completed_lessons": 0}

def save_data(data):
    """Speichert die Daten sicher in der JSON."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def add_words_bulk(text_input):
    """Fügt viele neue Wörter hinzu und filtert Duplikate."""
    data = load_data()
    raw_words = text_input.replace("\n", ",").split(",")
    new_entries = [w.strip() for w in raw_words if w.strip()]
    before = len(data["vocab"])
    data["vocab"] = list(set(data["vocab"] + new_entries))
    save_data(data)
    return len(data["vocab"]) - before

def delete_word(word_to_remove):
    """Löscht ein spezifisches Wort aus dem Wortschatz."""
    data = load_data()
    data["vocab"] = [w for w in data["vocab"] if w != word_to_remove]
    save_data(data)

def get_units():
    """Generiert den Lernpfad dynamisch basierend auf dem Wortschatz (5 Wörter = 1 Unit)."""
    data = load_data()
    words = data["vocab"]
    units = []
    for i in range(0, len(words), 5):
        unit_words = words[i:i+5]
        units.append({"id": (i//5)+1, "words": unit_words})
    return units

def update_xp_and_streak(xp_amount):
    """Verwaltet den Streak und fügt XP hinzu."""
    data = load_data()
    data["path_xp"] += xp_amount
    
    today = str(date.today())
    if data["last_login"] != today:
        yesterday = str(date.fromordinal(date.today().toordinal()-1))
        if data["last_login"] == yesterday:
            data["streak"] += 1
        else:
            data["streak"] = 1
        data["last_login"] = today
        
    save_data(data)
    return data
