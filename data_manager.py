import json
import os

DB_FILE = "vocab_db.json"

def load_vocab():
   if os.path.exists(DB_FILE):
       try:
           with open(DB_FILE, "r") as f:
               return json.load(f)
       except Exception:
           return {"known_words": []}
   return {"known_words": []}

def save_vocab(words_dict):
   with open(DB_FILE, "w") as f:
       json.dump(words_dict, f)

def add_duolingo_words(new_words_list):
   data = load_vocab()
   # Bestehende Wörter laden und neue hinzufügen (verhindert doppelte Wörter)
   current_words = set(data.get("known_words", []))
   current_words.update(new_words_list)

   data["known_words"] = list(current_words)
   save_vocab(data)
