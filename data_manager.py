import json
import os
from datetime import date

DB_FILE = "holalingo_ultra.json"

def load_all_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            # Migration/Defaults
            defaults = {"vocab": [], "path_xp": 0, "streak": 0, "last_login": "", "completed_lessons": 0}
            for k, v in defaults.items():
                if k not in data: data[k] = v
            return data
    return {"vocab": [], "path_xp": 0, "streak": 0, "last_login": "", "completed_lessons": 0}

def save_all_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def delete_word(word_to_remove):
    data = load_all_data()
    data["vocab"] = [w for w in data["vocab"] if w.lower() != word_to_remove.lower()]
    save_all_data(data)

def get_units():
    data = load_all_data()
    words = data["vocab"]
    # Eine Unit pro 5 Wörter
    units = []
    for i in range(0, len(words), 5):
        unit_words = words[i:i+5]
        units.append({"id": (i//5)+1, "words": unit_words})
    return units
