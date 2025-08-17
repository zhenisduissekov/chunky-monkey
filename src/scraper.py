"""
Scraper for OptiSigns Help Center with robust cursor pagination and deduplication.

- Uses cursor pagination via links.next from the API response.
- Handles HTTP 429 (rate limit) and 5xx errors with backoff and logs.
- Deduplicates articles by id across pages.
- Detects and logs pagination loops (if links.next repeats).
- Logs page-by-page progress, backoff events, and final totals.
- Keeps the public API and Markdown flow unchanged.
- Honors .env for config.

To confirm paging: Run with a large min_articles and check logs for:
  "Page 1 ... Page 2 ...", running totals, deduplication, and final count.
"""

import os
import time
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("KNOWLEDGE_BASE_API_URL")
PAGE_SIZE = int(os.getenv("KNOWLEDGE_BASE_PAGE_SIZE", "10"))

from markdown_converter import clean_html, html_to_markdown, slugify, article_to_markdown
import os

def save_articles_as_markdown(articles, output_dir="articles"):
    os.makedirs(output_dir, exist_ok=True)
    for i, article in enumerate(articles):
        title = article.get("title", f"article_{i}")
        slug = slugify(title)
        markdown = article_to_markdown(article)
        md_filename = f"{output_dir}/{slug or f'article_{i}'}.md"
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(markdown)

def _get_with_retries(session: requests.Session, url: str, logger=None) -> requests.Response:
    max_429_retries = 5
    max_5xx_retries = 5
    attempt = 0
    while True:
        print(f"[scraper] Sending GET request to: {url}")  # LOG REQUEST
        resp = session.get(url, timeout=10)
        print(f"[scraper] Response status: {resp.status_code}")  # LOG STATUS
        print(f"[scraper] Response body (first 200 chars): {resp.text[:200]}")  # LOG BODY
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            if logger:
                logger.warning(f"HTTP 429 Too Many Requests. Sleeping for {retry_after}s before retrying (attempt {attempt+1}/{max_429_retries})")
            else:
                print(f"[scraper] HTTP 429 Too Many Requests. Sleeping for {retry_after}s before retrying (attempt {attempt+1}/{max_429_retries})")
            attempt += 1
            if attempt >= max_429_retries:
                raise RuntimeError(f"Too many HTTP 429s from {url}")
            time.sleep(retry_after)
            continue
        elif 500 <= resp.status_code < 600:
            delay = 2 ** attempt if attempt < max_5xx_retries else 16
            if logger:
                logger.warning(f"HTTP {resp.status_code} Server Error. Sleeping for {delay}s before retrying (attempt {attempt+1}/{max_5xx_retries})")
            else:
                print(f"[scraper] HTTP {resp.status_code} Server Error. Sleeping for {delay}s before retrying (attempt {attempt+1}/{max_5xx_retries})")
            attempt += 1
            if attempt >= max_5xx_retries:
                raise RuntimeError(f"Too many HTTP 5xxs from {url}: {resp.text}")
            time.sleep(delay)
            continue
        elif not resp.ok:
            raise RuntimeError(f"HTTP error {resp.status_code} for {url}: {resp.text}")
        return resp

def fetch_articles(logger=None) -> List[Dict[str, Any]]:
    session = requests.Session()
    url = f"{API_URL}?page[size]={PAGE_SIZE}"
    results = []
    seen_ids = set()
    page_idx = 1
    prev_url = None
    repeated_next_count = 0

    while True:
        resp = _get_with_retries(session, url, logger)
        try:
            data = resp.json()
        except Exception as e:
            print(f"[scraper] Failed to parse JSON from {url}: {e}")
            raise RuntimeError(f"Failed to parse JSON from {url}: {e}")

        if not isinstance(data, dict):
            print(f"[scraper] API response is not a dict at {url}: {data}")
            raise RuntimeError(f"API response is not a dict at {url}: {data}")

        articles = data.get("articles")
        print(f"[scraper] Articles found in response: {len(articles) if isinstance(articles, list) else 'None'}")
        if not isinstance(articles, list):
            raise RuntimeError(f"No 'articles' list in response at {url}: {data}")

        added_this_page = 0
        for article in articles:
            aid = article.get("id")
            if aid is not None and aid not in seen_ids:
                results.append(article)
                seen_ids.add(aid)
                added_this_page += 1

        running_total = len(results)
        has_more = data.get("meta", {}).get("has_more", False)
        links = data.get("links", {})
        next_url = links.get("next")

        logmsg = f"[scraper] Page {page_idx}: added {added_this_page}, running total {running_total}, has_more={has_more}"
        if logger:
            logger.info(logmsg)
        else:
            print(logmsg)

        # Loop detection: if next_url repeats, break with warning
        if next_url and next_url == url:
            repeated_next_count += 1
            warnmsg = f"[scraper] Detected repeated links.next (loop) at page {page_idx} ({next_url}). Breaking pagination."
            if logger:
                logger.warning(warnmsg)
            else:
                print(warnmsg)
            break
        else:
            repeated_next_count = 0

        if has_more and next_url:
            prev_url = url
            url = next_url
            page_idx += 1
            continue
        else:
            break

    # Final dedupe
    unique_results = []
    unique_ids = set()
    for article in results:
        aid = article.get("id")
        if aid is not None and aid not in unique_ids:
            unique_results.append(article)
            unique_ids.add(aid)

    finalmsg = f"[scraper] Finished. Total unique articles: {len(unique_results)} (IDs: {len(unique_ids)})"
    if logger:
        logger.info(finalmsg)
    else:
        print(finalmsg)

    return unique_results

# Existing Markdown flow and save_articles_as_markdown remain unchanged.

if __name__ == "__main__":
    print("[scraper] Starting main block")
    print(f"[scraper] API_URL: {API_URL}")
    print(f"[scraper] PAGE_SIZE: {PAGE_SIZE}")
    articles = fetch_articles()
    print(f"[scraper] fetch_articles returned {len(articles)} articles")
    if articles:
        save_articles_as_markdown(articles, output_dir="articles")
        print(f"Saved {len(articles)} articles to the articles/ folder as Markdown (.md) files.")
    else:
        print("No articles fetched.")
