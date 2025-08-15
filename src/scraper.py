"""
scraper.py

This module is responsible for fetching articles from the specified knowledge base API (e.g., Zendesk).
It provides functions to authenticate with the API, retrieve articles in JSON format, and handle pagination if necessary.

Responsibilities:
- Connect to the knowledge base API using credentials from environment variables.
- Fetch at least 30 articles per run, supporting pagination as needed.
- Return article data in a structured JSON format for downstream processing.
- Handle API errors and logging.

This module is designed to be imported and used by the main orchestrator script.
"""
