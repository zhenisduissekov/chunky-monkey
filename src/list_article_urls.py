```python
"""
list_article_urls.py

Scans all Markdown files in the articles/ directory and prints every line that starts with 'Article URL:'.
This is useful for debugging retrieval/citation issues and ensuring all expected URLs are present in your knowledge base.

Usage:
    python src/list_article_urls.py
"""

import os
import pathlib

def list_article_urls(articles_dir):
    articles_path = pathlib.Path(articles_dir)
    if not articles_path.exists() or not articles_path.is_dir():
        print(f"Directory not found: {articles_dir}")
        return

    md_files = sorted([p for p in articles_path.iterdir() if p.suffix.lower() == ".md"])
    if not md_files:
        print(f"No Markdown files found in {articles_dir}")
        return

    found_any = False
    for md_file in md_files:
        with md_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        urls = [line.strip() for line in lines if line.strip().startswith("Article URL:")]
        if urls:
            found_any = True
            print(f"\n{md_file.name}:")
            for url in urls:
                print(f"  {url}")
    if not found_any:
        print("No 'Article URL:' lines found in any Markdown file.")

if __name__ == "__main__":
    # Default articles directory is ../articles relative to this script
    script_dir = pathlib.Path(__file__).parent
    articles_dir = (script_dir.parent / "articles").resolve()
    list_article_urls(articles_dir)
