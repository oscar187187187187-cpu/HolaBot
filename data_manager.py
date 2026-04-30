import json
import os
from datetime import date, datetime

DB_FILE = "lingo_data.json"

def load_user_data():
    """Lädt die Nutzerdaten oder erstellt ein neues Profil mit Standardwerten."""
    default_data = {
        "xp": 0,
        "gems": 500,  # Startkapital für den Shop
        "streak": 0,
        "hearts": 5,  # Standard-Herzen
        "premium": False, # Super Duolingo Status
        "last_login": "",
        "current_unit": 1,
        "current_lesson": 1,
        "completed_lessons": [],
        "known_words": ["hallo", "danke", "bitte", "tschüss"] # Basis-Wortschatz
    }
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Fehlende Schlüssel mit Defaults auffüllen
                for key, value in default_data.items():
                    if key not in data:
                        data[key] = value
                return data
        except Exception:
            pass
    return default_data

def save_user_data(data):
    """Speichert die Nutzerdaten lokal in einer JSON-Datei."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def check_daily_streak(data):
    """Prüft den Streak und setzt ihn ggf. zurück."""
    today_str = str(date.today())
    if not data["last_login"]:
        data["last_login"] = today_str
        data["streak"] = 1
        return data

    last_date = datetime.strptime(data["last_login"], "%Y-%m-%d").date()
    diff = (date.today() - last_date).days

    if diff == 1:
        data["streak"] += 1
    elif diff > 1:
        data["streak"] = 1 # Streak verloren, Neustart bei 1
    
    data["last_login"] = today_str
    save_user_data(data)
    return data

def update_progress(data, xp_gained, lesson_id):
    """Aktualisiert Fortschritt nach einer bestandenen Lektion."""
    data["xp"] += xp_gained
    data["gems"] += 15  # Belohnung für Abschluss
    if lesson_id not in data["completed_lessons"]:
        data["completed_lessons"].append(lesson_id)
        data["current_lesson"] += 1
        
        # Alle 5 Lektionen steigt man eine Unit auf
        if data["current_lesson"] > 5:
            data["current_lesson"] = 1
            data["current_unit"] += 1
            
    save_user_data(data)
    return data

def handle_wrong_answer(data):
    """Zieht ein Herz ab, sofern der Nutzer kein Premium hat."""
    if not data["premium"] and data["hearts"] > 0:
        data["hearts"] -= 1
    save_user_data(data)
    return data

def refill_hearts(data, cost=350):
    """Kauft Herzen mit Gems im Shop."""
    if data["gems"] >= cost and data["hearts"] < 5:
        data["gems"] -= cost
        data["hearts"] = 5
        save_user_data(data)
        return True
    return False

def buy_premium(data, cost=1000):
    """Aktiviert Super-Modus (unendliche Herzen)."""
    if data["gems"] >= cost and not data["premium"]:
        data["gems"] -= cost
        data["premium"] = True
        save_user_data(data)
        return True
    return False
