import json
import os
from datetime import datetime, date

DB_FILE = "user_data.json"

def load_data():
   if os.path.exists(DB_FILE):
       try:
           with open(DB_FILE, "r") as f:
               return json.load(f)
       except: pass
   return {"known_words": [], "xp": 0, "streak": 0, "last_login": ""}

def save_data(data):
   with open(DB_FILE, "w") as f:
       json.dump(data, f)

def update_xp(amount):
   data = load_data()
   data["xp"] += amount

   # Streak Logik
   today = str(date.today())
   if data["last_login"] != today:
       if data["last_login"] == str(date.fromordinal(date.today().toordinal()-1)):
           data["streak"] += 1
       else:
           data["streak"] = 1
       data["last_login"] = today

   save_data(data)
   return data

def add_words_bulk(text_input):
   data = load_data()
   raw_words = text_input.replace("\n", ",").split(",")
   new_entries = [w.strip().lower() for w in raw_words if w.strip()]
   data["known_words"] = list(set(data["known_words"] + new_entries))
   save_data(data)
   return len(new_entries)
