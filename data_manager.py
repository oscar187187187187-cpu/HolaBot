import json
import os

DB_FILE = "vocab_db.json"

def load_vocab():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"known_words": []}

def save_vocab(words):
    with open(DB_FILE, "w") as f:
        json.dump({"known_words": words}, f)

def add_duolingo_words(new_words_list):
    data = load_vocab()
    # Füge nur neue Wörter hinzu (keine Duplikate)
    combined = list(set(data["known_words"] + new_words_list))
    save_vocab(combined)