"""
markdown_converter.py

This module provides functionality to clean and convert HTML articles into Markdown format.
It is responsible for:
- Removing unwanted elements such as navigation bars, advertisements, and footers from the HTML.
- Preserving important content structure, including headings, code blocks, and links.
- Converting the cleaned HTML into well-formatted Markdown suitable for downstream processing and storage.

Functions in this module are intended to be used by the main orchestrator to process raw article content before saving or uploading.
"""
