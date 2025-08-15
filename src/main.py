"""
main.py

This module serves as the orchestrator for the chunky-monkey project.
It coordinates the end-to-end daily pipeline, including:

1. Fetching articles from the knowledge base API using the scraper module.
2. Cleaning and converting articles to Markdown format via the markdown_converter module.
3. Saving processed articles locally in the articles/ directory.
4. Uploading new or updated articles to the OpenAI Vector Store using the uploader module.
5. Attaching uploaded content to an OpenAI Assistant with a system prompt.
6. Logging counts of added, updated, and skipped articles.
7. Detecting deltas using hashes or timestamps to avoid redundant uploads.

This script is intended to be run as a scheduled job (e.g., via DigitalOcean App Platform).
"""
