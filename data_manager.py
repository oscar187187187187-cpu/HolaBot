import json
import os

DB_FILE = "vocab_db.json"

def load_vocab():
   if os.path.exists(DB_FILE):
       try:
           with open(DB_FILE, "r") as f:
               data = json.load(f)
               return data if isinstance(data, dict) else {"known_words": []}
       except Exception:
           return {"known_words": []}
   return {"known_words": []}

def save_vocab(words_dict):
   with open(DB_FILE, "w") as f:
       json.dump(words_dict, f)

def add_words_bulk(text_input):
   if not text_input: return 0
   # Ersetzt Zeilenumbrüche durch Kommas, teilt alles auf und säubert die Wörter
   raw_words = text_input.replace("\n", ",").split(",")
   clean_words = [w.strip().lower() for w in raw_words if w.strip()]

   data = load_vocab()
   current_words = set(data.get("known_words", []))
   before_count = len(current_words)
   current_words.update(clean_words)

   data["known_words"] = list(current_words)
   save_vocab(data)
   # Gibt zurück, wie viele NEUE Wörter wirklich gespeichert wurden
   return len(current_words) - before_count

def get_user_level():
   data = load_vocab()
   count = len(data.get("known_words", []))
   # Simples Level-System: Alle 50 Vokabeln = 1 Level Up!
   level = (count // 50) + 1
   return level, count
