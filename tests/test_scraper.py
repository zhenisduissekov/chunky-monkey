from unittest.mock import patch
from src.markdown_converter import clean_html, html_to_markdown, slugify

@patch("src.scraper.requests.Session.get")
def test_fetch_and_save_articles(mock_get, tmp_path):
    """
    Test that fetch_articles returns articles and save_articles_as_markdown saves them as Markdown files.
    This test mocks the network call to avoid real HTTP requests.
    """
    # Mock API response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "articles": [
            {"id": 1, "title": "Test Article", "body": "Hello, world!"},
            {"id": 2, "title": "Another Article", "body": "More content."}
        ],
        "links": {},
        "meta": {"has_more": False}
    }

    # Fetch articles (should use the mocked response)
    articles = fetch_articles()
    assert len(articles) == 2
    assert articles[0]["title"] == "Test Article"
    assert articles[1]["title"] == "Another Article"

    # Save articles as Markdown files in tmp_path
    save_articles_as_markdown(articles, output_dir=tmp_path)
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 2
    contents = [f.read_text() for f in files]
    # Check that the title is present as a Markdown header in each file
    assert any("# Test Article" in c for c in contents)
    assert any("# Another Article" in c for c in contents)
