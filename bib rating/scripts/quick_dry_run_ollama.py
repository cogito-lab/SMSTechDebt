import os, json, re, requests, bibtexparser

# --- Config ---
BIB_PATH   = "output_remove_duplicates_workingcopy.bib"
XML_PATH   = "prompt final revised.xml"
OLLAMA_URL = "http://localhost:11434"
MODEL      = "qwen2.5:14b-instruct"   # you have this installed
N          = 5  # how many entries to test
# --------------

def load():
    with open(XML_PATH, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    with open(BIB_PATH, "r", encoding="utf-8") as f:
        db = bibtexparser.load(f)
    return sys_prompt, db

def payload(e):
    return {
        "title": e.get("title",""),
        "abstract": e.get("abstract", e.get("abstractNote","")),
        "keywords": e.get("keywords", e.get("keyword","")),
        "bibtype": e.get("ENTRYTYPE",""),
        "year": e.get("year",""),
        "venue": e.get("journal", e.get("booktitle","")),
        "bibkey": e.get("ID",""),
    }

def parse_json_loose(txt: str) -> dict:
    # Ollama usually obeys format=json, but be defensive:
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", txt)  # grab first JSON-ish block
        if not m: raise
        return json.loads(m.group(0))

def ask_ollama(sys_prompt: str, pl: dict) -> dict:
    user_prompt = (
        'Return ONLY a compact JSON object with exactly two keys:\n'
        '{"relevance_rating": <integer 1-5>, "comment": "<one-line reason>"}.\n'
        'No extra text. Entry:\n' + json.dumps(pl, ensure_ascii=False)
    )
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
        "format": "json"  # enforce JSON
    }, timeout=600)
    r.raise_for_status()
    txt = r.json()["message"]["content"]
    data = parse_json_loose(txt)
    rating = int(data["relevance_rating"])
    if not 1 <= rating <= 5:
        raise ValueError(f"rating out of range: {rating}")
    comment = (data.get("comment","") or "").replace("\n"," ").strip()
    return {"relevance_rating": rating, "comment": comment}

def main():
    # ping server
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
    except Exception as e:
        raise SystemExit(f"Ollama server not reachable at {OLLAMA_URL}: {e}")

    sys_prompt, db = load()
    entries = db.entries[:N]
    print(f"Dry-run on {len(entries)} entries (no file will be modified).\n")

    for e in entries:
        pl = payload(e)
        bibkey = pl["bibkey"] or "<no-key>"
        try:
            res = ask_ollama(sys_prompt, pl)
            print(f"[{bibkey}] rating={res['relevance_rating']} | {res['comment'][:140]}")
        except Exception as ex:
            print(f"[{bibkey}] ERROR: {ex}")

if __name__ == "__main__":
    main()
