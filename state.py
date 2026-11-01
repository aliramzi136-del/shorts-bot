import json, os

PATH = os.path.join(os.path.dirname(__file__), "state.json")

def load():
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"used_source_ids": [], "published": []}

def save(st):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
