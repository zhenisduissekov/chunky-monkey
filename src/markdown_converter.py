"""
markdown_converter.py

This module provides functions to clean HTML content and convert it to Markdown,
preserving important structure (headings, code blocks, links) and removing unwanted
elements (navigation, ads, etc.).

Usage:
    - clean_html(html_content): Remove nav/ads/unwanted elements from HTML.
    - html_to_markdown(html_content): Convert cleaned HTML to Markdown.

Dependencies:
    - beautifulsoup4
    - markdownify

Author: chunky-monkey team
"""

from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re

def clean_html(html_content: str) -> str:
    """
    Cleans the HTML content by removing navigation bars, ads, and other unwanted elements.
    Returns cleaned HTML as a string.

    This function is intentionally conservative: it removes common nav/footer/aside elements
    and elements with classes/ids that often indicate ads or navigation.

    Args:
        html_content (str): Raw HTML string.

    Returns:
        str: Cleaned HTML string.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove <nav>, <footer>, <aside>, and elements with common ad/nav classes/ids
    for tag in soup.find_all(['nav', 'footer', 'aside']):
        tag.decompose()

    # Remove elements with ad/nav-related class or id
    for selector in [
        '[class*="nav"]', '[id*="nav"]',
        '[class*="footer"]', '[id*="footer"]',
        '[class*="ad"]', '[id*="ad"]',
        '[class*="banner"]', '[id*="banner"]',
        '[class*="sidebar"]', '[id*="sidebar"]'
    ]:
        for tag in soup.select(selector):
            tag.decompose()

    # Optionally, remove empty elements
    for tag in soup.find_all():
        if not tag.text.strip() and tag.name not in ['img', 'br', 'hr']:
            tag.decompose()

    # Return cleaned HTML as string
    return str(soup)

def html_to_markdown(html_content: str) -> str:
    """
    Converts cleaned HTML content to Markdown format.
    Preserves headings, code blocks, and links.

    Args:
        html_content (str): Cleaned HTML string.

    Returns:
        str: Markdown string.
    """
    # markdownify options:
    # - heading_style: 'ATX' for #, ##, etc.
    # - code_language: None (don't force language)
    # - strip: False (don't strip whitespace)
    # - bullets: '*' for unordered lists
    markdown = md(
        html_content,
        heading_style="ATX",
        bullets="*",
        strip=["style", "script"]
    )

    # Optionally, clean up excessive blank lines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown).strip()
    return markdown

def slugify(title: str) -> str:
    """
    Converts a title to a filesystem-friendly slug for filenames.

    Args:
        title (str): The article title.

    Returns:
        str: Slugified string.
    """
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:50]  # Limit length for filesystem safety

# Example usage for testing
if __name__ == "__main__":
    example_html = """
    <html>
      <body>
        <nav>This is nav</nav>
        <h1>Title</h1>
        <p>Some <a href="/relative/link">relative link</a> and <a href="https://example.com">absolute link</a>.</p>
        <pre><code>print("Hello, world!")</code></pre>
        <footer>This is footer</footer>
      </body>
    </html>
    """
    cleaned = clean_html(example_html)
    print("CLEANED HTML:\n", cleaned)
    md_out = html_to_markdown(cleaned)
    print("\nMARKDOWN:\n", md_out)
