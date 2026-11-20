# ============================================================
# rate_bibtex_ollama.py
# - Reads an XML prompt with decision criteria
# - Reads your BibTeX file
# - Calls a local Ollama model to rate each entry (1..5) + comment
# - Inserts results back into the SAME .bib file (in-place)
# - Includes retries + periodic checkpoints for safety
# ============================================================

import os, json, re, time, sys            # stdlib: filesystem, JSON, regex, timing, system exit
from typing import Dict, Any              # typing helpers for clarity
import requests                           # HTTP client to call Ollama's local REST API
import bibtexparser                       # parse/write BibTeX files safely
from tqdm import tqdm                     # progress bar in terminal

# ================== CONFIG (edit if needed) ==================

BIB_PATH = "output_remove_duplicates_workingcopy.bib"   # Path to your existing BibTeX file (will be modified in place)
XML_PATH = "prompt final revised.xml"                   # Path to your XML with rating criteria and instructions
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")  # Base URL for local Ollama server
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")       # Model tag name shown by `ollama list`

# Safety / performance knobs
MAX_RETRIES = 2                   # How many times to retry a single entry on error
PAUSE_BETWEEN = 0.25              # Short sleep between calls to be gentle on CPU/GPU
CHECKPOINT_EVERY = 10         # Write current progress to disk every N entries
DRY_RUN_LIMIT = None           # Set to small int (e.g., 5) for a small test; set None for full run

# ============================================================


def ping_server():
    """
    Quick health check: ensure the Ollama server is reachable before we start.
    """
    try:
        # /api/tags returns installed models; use as a ping endpoint
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()  # raise if HTTP status is not 2xx
    except Exception as e:
        # Give a clear, actionable error if server isn't running
        raise SystemExit(f"Ollama server not reachable at {OLLAMA_URL}. "
                         f"Start the Ollama app (or `ollama serve`). ({e})")


def load_inputs():
    """
    Load the XML system prompt and the BibTeX database into memory.
    Returns:
      system_prompt (str), db (bibtexparser.bibdatabase.BibDatabase)
    """
    # Read the XML prompt (your rating criteria lives here)
    with open(XML_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # Read and parse the BibTeX file into a structured object
    with open(BIB_PATH, "r", encoding="utf-8") as f:
        db = bibtexparser.load(f)

    return system_prompt, db


def payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the fields we want to show the model for rating.
    Returns a compact dict (title/abstract/keywords/venue/year/key).
    """
    return {
        "title": entry.get("title", ""),
        # some managers store abstract in 'abstractNote', so we try both
        "abstract": entry.get("abstract", entry.get("abstractNote", "")),
        # keywords might be 'keywords' or 'keyword' depending on exporter
        "keywords": entry.get("keywords", entry.get("keyword", "")),
        "bibtype": entry.get("ENTRYTYPE", ""),
        "year": entry.get("year", ""),
        # venue could be 'journal' (articles) or 'booktitle' (conferences)
        "venue": entry.get("journal", entry.get("booktitle", "")),
        "bibkey": entry.get("ID", ""),  # the BibTeX key like Smith2020
    }


def parse_json_loose(txt: str) -> dict:
    """
    Parse the model response as JSON.
    We ask Ollama to return JSON only, but we defensively strip any stray text.
    """
    try:
        return json.loads(txt)  # fast path: already clean JSON
    except Exception:
        # fallback: find the first {...} block and parse that
        m = re.search(r"\{[\s\S]*\}", txt)
        if not m:
            # nothing that looks like JSON; re-raise original error
            raise
        return json.loads(m.group(0))


def ask_ollama(system_prompt: str, pl: dict) -> Dict[str, Any]:
    """
    Call the local Ollama /api/chat endpoint with:
      - system prompt (your XML criteria)
      - user prompt requesting strict JSON with rating + comment
    Returns:
      dict with keys {"relevance_rating": int, "comment": str}
    """
    # Build user prompt: instruct the model to only return strict JSON with 2 keys
    user_prompt = (
        'Return ONLY a compact JSON object with exactly two keys:\n'
        '{"relevance_rating": <integer 1-5>, "comment": "<one-line reason>"}.\n'
        'No extra text. Entry:\n' + json.dumps(pl, ensure_ascii=False)
    )

    # Compose the chat payload; "format":"json" tells Ollama to enforce JSON output
    body = {
        "model": MODEL,  # selected local model (e.g., qwen2.5:14b-instruct)
        "messages": [
            {"role": "system", "content": system_prompt},  # XML criteria as system message
            {"role": "user",   "content": user_prompt},    # our instruction + entry payload
        ],
        "stream": False,    # one-shot response (no streaming)
        "format": "json"    # ask for pure JSON to simplify parsing
    }

    # POST to the local Ollama REST API
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
    r.raise_for_status()               # raise error if not 2xx
    txt = r.json()["message"]["content"]  # model's text output

    # Parse JSON (with a small safety net)
    data = parse_json_loose(txt)

    # Validate rating range and clean up the comment
    rating = int(data["relevance_rating"])
    if not 1 <= rating <= 5:
        raise ValueError(f"Invalid rating {rating}")
    comment = (data.get("comment", "") or "").replace("\n", " ").strip()

    # Return normalized structure
    return {"relevance_rating": rating, "comment": comment}


def main():
    """
    Orchestrate the full rating pass:
      - Check server
      - Load inputs
      - Iterate entries with retries
      - Write periodic checkpoints + final output
    """
    ping_server()                         # ensure Ollama is reachable
    system_prompt, db = load_inputs()     # XML + BibTeX
    entries = db.entries                  # list of BibTeX entries (dicts)

    # Allow small dry-run before committing to full pass
    if DRY_RUN_LIMIT:
        entries = entries[:DRY_RUN_LIMIT]
        print(f"DRY RUN: limiting to first {DRY_RUN_LIMIT} entries.")

    print(f"Loaded {len(entries)} entries from {BIB_PATH}")

    # Iterate through each entry and request a rating
    for i, entry in enumerate(tqdm(entries, desc="Rating entries", unit="paper")):
        # If the entry is already rated, skip (allows safe resume)
        if "relevance_rating" in entry and "comment" in entry:
            continue

        # Build a clean payload for the model
        pl = payload(entry)

        # Try calling the model; retry on transient errors
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Call Ollama and parse result
                res = ask_ollama(system_prompt, pl)

                # Insert results back into the BibTeX entry
                entry["relevance_rating"] = str(res["relevance_rating"])  # store as string for BibTeX
                entry["comment"] = res["comment"] or "No additional comment."
                break  # success → leave retry loop

            except Exception as e:
                # On final attempt, write a conservative default + error note
                if attempt >= MAX_RETRIES:
                    entry["relevance_rating"] = "2"
                    entry["comment"] = f"Fallback after error: {str(e)[:200]}"
                else:
                    # brief backoff before retry
                    time.sleep(0.6 * attempt)
            finally:
                # small pause to avoid overloading CPU/GPU
                time.sleep(PAUSE_BETWEEN)

        # Periodic checkpoint: write .bib so progress is saved
        if (i + 1) % CHECKPOINT_EVERY == 0:
            with open(BIB_PATH, "w", encoding="utf-8") as fw:
                bibtexparser.dump(db, fw)

    # Final write after loop completes
    with open(BIB_PATH, "w", encoding="utf-8") as fw:
        bibtexparser.dump(db, fw)

    print("Done. Ratings inserted into the SAME .bib file.")


# Standard Python entrypoint guard
if __name__ == "__main__":
    main()
