import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from markdown_converter import article_to_markdown

import pytest
import json

# Example JSON input (shortened for brevity, use your full sample in real test)
EXAMPLE_JSON = {
    "meta": {
        "has_more": True,
        "after_cursor": "aT0AAAAAAAAAZI/Ya18AAAAAaWEJAdVTAAAA",
        "before_cursor": "aTMAAAAAAAAAZHAUFGAAAAAAaaUeGD9dAQAA"
    },
    "links": {
        "first": "https://support.optisigns.com/api/v2/help_center/en-us/articles?page%5Bsize%5D=10",
        "last": "https://support.optisigns.com/api/v2/help_center/en-us/articles?page%5Bbefore%5D=bGFzdF9wYWdl&page%5Bsize%5D=10",
        "prev": "https://support.optisigns.com/api/v2/help_center/en-us/articles?page%5Bbefore%5D=aTMAAAAAAAAAZHAUFGAAAAAAaaUeGD9dAQAA&page%5Bsize%5D=10",
        "next": "https://support.optisigns.com/api/v2/help_center/en-us/articles?page%5Bafter%5D=aT0AAAAAAAAAZI%2FYa18AAAAAaWEJAdVTAAAA&page%5Bsize%5D=10"
    },
    "articles": [
        {
            "id": 1500002131621,
            "url": "https://optisignshelp.zendesk.com/api/v2/help_center/en-us/articles/1500002131621.json",
            "html_url": "https://support.optisigns.com/hc/en-us/articles/1500002131621-How-to-use-YouTube-Live-with-OptiSigns",
            "author_id": 373132830174,
            "comments_disabled": True,
            "draft": False,
            "promoted": False,
            "position": 51,
            "vote_sum": -1,
            "vote_count": 1,
            "section_id": 26324076807315,
            "created_at": "2021-01-29T13:58:08Z",
            "updated_at": "2025-08-05T15:17:00Z",
            "name": "How to use YouTube Live with OptiSigns",
            "title": "How to use YouTube Live with OptiSigns",
            "source_locale": "en-us",
            "locale": "en-us",
            "outdated": False,
            "outdated_locales": [],
            "edited_at": "2024-02-18T15:03:33Z",
            "user_segment_id": None,
            "permission_group_id": 787493,
            "content_tag_ids": [],
            "label_names": [],
            "body": "<p>There are 2 ways to use YouTube Live with OptiSigns.</p>"
        }
    ]
}

from markdown_converter import html_to_markdown

def check_all_fields(d, md, parent_key=None):
    """
    Recursively check that every key and value from the JSON dict d
    appears in the Markdown string md.
    Special-case: for 'body' fields, check for Markdown-converted content.
    """
    if isinstance(d, dict):
        for k, v in d.items():
            assert str(k) in md, f"Missing key: {k}"
            check_all_fields(v, md, parent_key=k)
    elif isinstance(d, list):
        for item in d:
            check_all_fields(item, md, parent_key=parent_key)
    else:
        if d is None:
            assert "None" in md or "null" in md, "Missing value: None/null"
        elif isinstance(d, bool):
            assert str(d) in md or str(d).lower() in md, f"Missing value: {d}"
        else:
            if d != "":
                if parent_key == "body":
                    # For HTML body, check for Markdown-converted content
                    md_body = html_to_markdown(d)
                    for line in md_body.splitlines():
                        if line.strip():
                            assert line.strip() in md, f"Missing body content: {line.strip()}"
                else:
                    assert str(d) in md, f"Missing value: {d}"

def test_article_to_markdown_lossless():
    """
    Test that article_to_markdown outputs all keys and values from the input JSON.
    """
    # Test the top-level structure
    markdown = article_to_markdown(EXAMPLE_JSON)
    check_all_fields(EXAMPLE_JSON, markdown)

    # Test for each article individually (simulate real usage)
    for article in EXAMPLE_JSON.get("articles", []):
        md_article = article_to_markdown(article)
        check_all_fields(article, md_article)
