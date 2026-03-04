"""
Phase 2.6 — Clean and normalize scraped/sourced text.

Usage:
    python scripts/clean.py

Reads JSON files from data/raw/, writes cleaned JSON to data/cleaned/.
"""

import json
import re
from pathlib import Path

RAW_DIRS = [
    Path("data/raw/tolkiengateway"),
    Path("data/raw/gutenberg"),  # Phase 2.5 — add Hobbit text here
]
OUTPUT_DIR = Path("data/cleaned")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    # Collapse excessive whitespace / blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Remove wiki-style edit markers and citations [1], [edit], etc.
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[edit\]", "", text, flags=re.IGNORECASE)

    # Fix common encoding artifacts
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " — ").replace("\u2013", "–")

    # Strip lines that are just punctuation or very short (nav remnants)
    lines = [ln for ln in text.splitlines() if len(ln.strip()) > 3]

    return "\n".join(lines).strip()


def process_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["text"] = clean_text(data["text"])
    data["char_count"] = len(data["text"])
    return data


def clean_all():
    total = 0
    for raw_dir in RAW_DIRS:
        if not raw_dir.exists():
            continue
        for json_file in raw_dir.glob("*.json"):
            print(f"  Cleaning: {json_file.name}")
            cleaned = process_file(json_file)
            out_path = OUTPUT_DIR / json_file.name
            out_path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False))
            total += 1

    print(f"\nDone. Cleaned {total} files → {OUTPUT_DIR}")


if __name__ == "__main__":
    clean_all()
