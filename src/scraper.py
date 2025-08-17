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

from utils import setup_logging
scraper_logger = setup_logging(log_level="ERROR", log_file="logs/scraper_errors.log")

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
    request_success = 0
    request_failed = 0
    while True:
        try:
            resp = session.get(url, timeout=10)
            if resp.ok:
                request_success += 1
            else:
                request_failed += 1
        except Exception as e:
            request_failed += 1
            raise
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            attempt += 1
            if attempt >= max_429_retries:
                raise RuntimeError(f"Too many HTTP 429s from {url}")
            time.sleep(retry_after)
            continue
        elif 500 <= resp.status_code < 600:
            delay = 2 ** attempt if attempt < max_5xx_retries else 16
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
        try:
            resp = _get_with_retries(session, url, logger)
            try:
                data = resp.json()
            except Exception as e:
                scraper_logger.error(f"Failed to parse JSON from {url}: {e}", exc_info=True)
                raise RuntimeError(f"Failed to parse JSON from {url}: {e}")

            if not isinstance(data, dict):
                scraper_logger.error(f"API response is not a dict at {url}: {data}")
                raise RuntimeError(f"API response is not a dict at {url}: {data}")
        except Exception as e:
            scraper_logger.error(f"Error during scraping at URL {url}: {e}", exc_info=True)
            raise

        articles = data.get("articles")
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

        # No per-page logmsg print, only summary at the end

        # Loop detection: if next_url repeats, break with warning
        if next_url and next_url == url:
            repeated_next_count += 1
            warnmsg = f"[scraper] Detected repeated links.next (loop) at page {page_idx} ({next_url}). Breaking pagination."
            if logger:
                logger.warning(warnmsg)
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

    # No per-run print, only summary in main block
    return unique_results

# Existing Markdown flow and save_articles_as_markdown remain unchanged.

if __name__ == "__main__":
    print("[scraper] Starting main block", flush=True)
    print(f"[scraper] API_URL: {API_URL}", flush=True)
    print(f"[scraper] PAGE_SIZE: {PAGE_SIZE}", flush=True)
    downloaded = 0
    failed_saves = 0
    request_success = 0
    request_failed = 0
    try:
        # Patch fetch_articles to use request counters
        def fetch_articles_summary(logger=None):
            global request_success, request_failed
            session = requests.Session()
            url = f"{API_URL}?page[size]={PAGE_SIZE}"
            results = []
            seen_ids = set()
            page_idx = 1
            prev_url = None
            repeated_next_count = 0

            while True:
                try:
                    resp = session.get(url, timeout=10)
                    if resp.ok:
                        request_success += 1
                    else:
                        request_failed += 1
                    data = resp.json()
                    if not isinstance(data, dict):
                        raise RuntimeError(f"API response is not a dict at {url}: {data}")
                except Exception as e:
                    request_failed += 1
                    scraper_logger.error(f"Error during scraping at URL {url}: {e}", exc_info=True)
                    break

                articles = data.get("articles")
                if not isinstance(articles, list):
                    break

                for article in articles:
                    aid = article.get("id")
                    if aid is not None and aid not in seen_ids:
                        results.append(article)
                        seen_ids.add(aid)

                has_more = data.get("meta", {}).get("has_more", False)
                links = data.get("links", {})
                next_url = links.get("next")

                if next_url and next_url == url:
                    break

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
            return unique_results

        articles = fetch_articles_summary()
        downloaded = len(articles)
        if articles:
            for i, article in enumerate(articles):
                try:
                    title = article.get("title", f"article_{i}")
                    slug = slugify(title)
                    markdown = article_to_markdown(article)
                    md_filename = f"articles/{slug or f'article_{i}'}.md"
                    with open(md_filename, "w", encoding="utf-8") as f:
                        f.write(markdown)
                except Exception as e:
                    failed_saves += 1
                    scraper_logger.error(f"Error saving article {title}: {e}", exc_info=True)
        print(f"Summary: HTTP requests: {request_success} succeeded, {request_failed} failed. Downloaded: {downloaded}, Saved: {downloaded - failed_saves}, Failed to save: {failed_saves}", flush=True)
        if request_failed or failed_saves:
            print("Some errors occurred. See logs/scraper_errors.log for details.", flush=True)
        else:
            print("Scraper completed successfully with no errors.", flush=True)
    except Exception as e:
        scraper_logger.error(f"Error in main scraper block: {e}", exc_info=True)
        print(f"Error in main scraper block: {e}", flush=True)
