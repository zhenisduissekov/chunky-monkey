"""
scraper.py

Fetches articles from the OptiSigns public knowledge base API.

- Handles pagination using 'links.next' and 'meta.has_more'.
- Stops when enough articles are collected or no more pages.
- Robust to minor API structure changes.
- Logs progress and errors.

Designed for use in the main pipeline and for standalone testing.
"""

import os
import requests
from typing import List, Dict, Any
from src.utils import setup_logging
from src.markdown_converter import clean_html, html_to_markdown, slugify
from dotenv import load_dotenv

# Always load .env from the project root, regardless of where the script is run from
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

API_URL = os.getenv("KNOWLEDGE_BASE_API_URL")
PAGE_SIZE = int(os.getenv("KNOWLEDGE_BASE_PAGE_SIZE", "10"))

def fetch_articles(min_articles: int = None, logger=None) -> List[Dict[str, Any]]:
    """
    Fetch at least `min_articles` articles from the OptiSigns API.
    Handles pagination and basic error checking.
    """
    if min_articles is None:
        min_articles = int(os.getenv("KNOWLEDGE_BASE_FILE_NUMBER", "30"))
    if logger is None:
        logger = setup_logging()
    articles: List[Dict[str, Any]] = []
    url = f"{API_URL}?page[size]={PAGE_SIZE}"
    session = requests.Session()

    while url and len(articles) < min_articles:
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch articles from {url}: {e}")
            break

        # Defensive: check for expected keys, log and break if missing
        if not isinstance(data, dict):
            logger.error(f"Unexpected response format: {data}")
            break

        page_articles = data.get("articles")
        if not isinstance(page_articles, list):
            logger.error(f"Missing or invalid 'articles' key in response: {data}")
            break

        articles.extend(page_articles)
        logger.info(f"Fetched {len(page_articles)} articles (total: {len(articles)})")

        # Pagination: use 'links.next' if present, else stop
        url = data.get("links", {}).get("next")
        if not data.get("meta", {}).get("has_more", False):
            break

    if len(articles) < min_articles:
        logger.error(f"Fetched only {len(articles)} articles, but {min_articles} were requested. Exiting with error.")
        raise RuntimeError(f"Not enough articles fetched: needed {min_articles}, got {len(articles)}")
    elif len(articles) > min_articles:
        articles = articles[:min_articles]

    return articles

def save_articles_as_markdown(articles, output_dir="articles"):
    os.makedirs(output_dir, exist_ok=True)
    for i, article in enumerate(articles):
        title = article.get("title", f"article_{i}")
        slug = slugify(title)
        html_body = article.get("body", "")
        cleaned_html = clean_html(html_body)
        markdown = html_to_markdown(cleaned_html)
        md_filename = f"{output_dir}/{slug or f'article_{i}'}.md"
        with open(md_filename, "w", encoding="utf-8") as f:
            # Always include the title as a Markdown header at the top
            f.write(f"# {title}\n\n{markdown}")

if __name__ == "__main__":
    logger = setup_logging()
    articles = fetch_articles(logger=logger)
    if articles:
        save_articles_as_markdown(articles, output_dir="articles")
        logger.info(f"Saved {len(articles)} articles to the articles/ folder as Markdown (.md) files.")
    else:
        logger.warning("No articles fetched.")
