"""
Phase 2.4 — Scrape Tolkien Gateway for Hobbit-related lore pages.

Usage:
    python scripts/scrape.py

Outputs raw HTML-stripped text files into data/raw/.
"""

import os
import time
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("TOLKIEN_GATEWAY_BASE", "https://www.tolkiengateway.net/wiki/")
DELAY = float(os.getenv("SCRAPE_DELAY_SECONDS", 1.5))
OUTPUT_DIR = Path("data/raw/tolkiengateway")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Seed pages — expand this list as needed
SEED_PAGES = [
    "The_Hobbit",
    "Bilbo_Baggins",
    "Gandalf",
    "Thorin_Oakenshield",
    "Smaug",
    "The_Shire",
    "Bag_End",
    "Gollum",
    "The_One_Ring",
    "Rivendell",
    "Mirkwood",
    "Erebor",
    "Lake-town",
    "Battle_of_Five_Armies",
    "Arkenstone",
    "Dwarves",
    "Elves",
    "Trolls",
    "Goblins",
    "Beorn",
    "Eagles",
    "Wargs",
    "Necromancer",
    "Dol_Guldur",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TolkienLoreBot/1.0; educational project)"
}


def fetch_page(slug: str) -> dict | None:
    url = BASE_URL + slug
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] {slug}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove nav, footer, edit links, references section
    for tag in soup.select(
        "#toc, .navbox, .references, .reflist, #catlinks, "
        ".mw-editsection, script, style"
    ):
        tag.decompose()

    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        print(f"  [WARN] No content div for {slug}")
        return None

    text = content_div.get_text(separator="\n", strip=True)

    return {
        "slug": slug,
        "url": url,
        "title": slug.replace("_", " "),
        "text": text,
        "source": "tolkiengateway",
    }


def scrape_all():
    print(f"Scraping {len(SEED_PAGES)} pages from Tolkien Gateway...")
    results = []

    for slug in SEED_PAGES:
        print(f"  Fetching: {slug}")
        page = fetch_page(slug)
        if page:
            out_path = OUTPUT_DIR / f"{slug}.json"
            out_path.write_text(json.dumps(page, indent=2, ensure_ascii=False))
            results.append(slug)
        time.sleep(DELAY)

    print(f"\nDone. Saved {len(results)}/{len(SEED_PAGES)} pages to {OUTPUT_DIR}")


if __name__ == "__main__":
    scrape_all()
