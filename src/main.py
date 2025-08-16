"""
main.py

Orchestrates the daily job:
- Runs the scraper to fetch articles.
- Detects new or updated articles using SHA256 hashes.
- Uploads only new/changed articles to OpenAI Vector Store via the uploader.
- Updates the hash record after successful upload.
- Can run the entire process N times per execution, controlled by the RUNS_PER_JOB environment variable.
- Can run periodically within the same process, controlled by the SCRAPE_PERIOD_SECONDS environment variable.

Intended for use in a Dockerized scheduled job (e.g., DigitalOcean App Platform).

Assumes:
- Scraper saves Markdown files to articles/
- Uploader script can accept a list of files to upload (if not, it uploads all .md files in articles/)
"""

import os
import hashlib
import json
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

from croniter import croniter
from datetime import datetime

ARTICLES_DIR = Path(__file__).parent.parent / "articles"
HASH_RECORD = Path(__file__).parent.parent / "article_hashes.json"

def compute_hash(filepath):
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def detect_article_deltas():
    """Detect new, updated, and skipped Markdown files in articles/."""
    prev_hashes = {}
    if HASH_RECORD.exists():
        with open(HASH_RECORD, "r") as f:
            prev_hashes = json.load(f)
    added = []
    updated = []
    skipped = []
    new_hashes = prev_hashes.copy()
    for md_file in ARTICLES_DIR.glob("*.md"):
        h = compute_hash(md_file)
        if md_file.name not in prev_hashes:
            added.append(md_file)
        elif prev_hashes[md_file.name] != h:
            updated.append(md_file)
        else:
            skipped.append(md_file)
        new_hashes[md_file.name] = h
    return added, updated, skipped, new_hashes

def run_scraper():
    """Run the scraper script to fetch articles."""
    print("Running scraper...")
    result = subprocess.run(
        ["python", "src/scraper.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Scraper failed:", result.stderr)
        raise RuntimeError("Scraper failed")

def run_uploader():
    """Run the uploader script to upload articles."""
    print("Running uploader...")
    result = subprocess.run(
        ["python", "src/uploader.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Uploader failed:", result.stderr)
        raise RuntimeError("Uploader failed")

def main():
    # 1. Scrape articles
    run_scraper()

    # 2. Detect new/updated/skipped articles
    added, updated, skipped, new_hashes = detect_article_deltas()
    total = len(list(ARTICLES_DIR.glob("*.md")))
    print(f"Added: {len(added)}, Updated: {len(updated)}, Skipped: {len(skipped)}")
    if not (added or updated):
        print("No new or updated articles to upload.")
        return

    print(f"Found {len(added) + len(updated)} new or updated articles:")
    for f in added + updated:
        print(f"  - {f.name}")

    # 3. Upload (calls uploader, which uploads all .md files in articles/)
    run_uploader()

    # 4. Update hash record
    with open(HASH_RECORD, "w") as f:
        json.dump(new_hashes, f, indent=2)
    print("Hash record updated.")

    # 5. Cleanup articles directory
    cleanup_articles_dir()

def cleanup_articles_dir():
    """Delete all Markdown files in the articles directory."""
    print("Cleaning up articles directory...")
    for md_file in ARTICLES_DIR.glob("*.md"):
        try:
            md_file.unlink()
            print(f"Deleted {md_file.name}")
        except Exception as e:
            print(f"Failed to delete {md_file.name}: {e}")

import time

if __name__ == "__main__":
    cron_expr = os.getenv("SCRAPE_PERIOD", "0 0 * * *")
    print(f"Using cron schedule: {cron_expr}")
    while True:
        main()
        now = datetime.now()
        cron = croniter(cron_expr, now)
        next_run = cron.get_next(datetime)
        sleep_seconds = (next_run - now).total_seconds()
        print(f"Sleeping for {int(sleep_seconds)} seconds until next scheduled run at {next_run}...")
        time.sleep(sleep_seconds)
