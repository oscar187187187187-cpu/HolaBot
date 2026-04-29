import json
import os
from datetime import datetime, date

DB_FILE = "user_data_v2.json"

def load_data():
   if os.path.exists(DB_FILE):
       try:
           with open(DB_FILE, "r") as f:
               data = json.load(f)
               # Sicherstellen, dass alle Felder da sind
               defaults = {"known_words": [], "xp": 0, "streak": 0, "last_login": "", "unit": 1}
               for k, v in defaults.items():
                   if k not in data: data[k] = v
               return data
       except: pass
   return {"known_words": [], "xp": 0, "streak": 0, "last_login": "", "unit": 1}

def save_data(data):
   with open(DB_FILE, "w") as f:
       json.dump(data, f)

def add_words_bulk(text_input):
   data = load_data()
   raw_words = text_input.replace("\n", ",").split(",")
   new_entries = [w.strip().lower() for w in raw_words if w.strip()]
   before = len(data["known_words"])
   data["known_words"] = list(set(data["known_words"] + new_entries))
   save_data(data)
   return len(data["known_words"]) - before

def update_progress(xp_gain):
   data = load_data()
   data["xp"] += xp_gain

   # Unit Logik: Alle 500 XP eine neue Unit
   new_unit = (data["xp"] // 500) + 1
   data["unit"] = new_unit

   # Streak
   today = str(date.today())
   if data["last_login"] != today:
       yesterday = str(date.fromordinal(date.today().toordinal()-1))
       data["streak"] = data["streak"] + 1 if data["last_login"] == yesterday else 1
       data["last_login"] = today

   save_data(data)
   return data
