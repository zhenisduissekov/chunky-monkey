"""
uploader.py

This module is responsible for handling the chunking and uploading of Markdown articles
to the OpenAI Vector Store using the OpenAI API. It reads processed Markdown files from
the articles/ directory, splits them into manageable chunks suitable for embedding,
uploads them programmatically to the vector store, and attaches them to a specified
Assistant with a provided system prompt.

Key responsibilities:
- Read and chunk Markdown files for optimal vector storage.
- Upload new or updated articles to the OpenAI Vector Store.
- Associate uploaded content with an Assistant.
- Log upload statistics (added, updated, skipped).

All API keys and configuration are loaded securely from environment variables.
"""
