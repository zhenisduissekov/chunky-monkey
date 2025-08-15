# chunky-monkey

**End-to-End Automated Knowledge Base Article Pipeline**

This project implements a daily job that:
1. Scrapes ≥ 30 articles from a knowledge base API (e.g., Zendesk).
2. Cleans and converts them into Markdown, preserving structure and code, while removing navigation/ads.
3. Saves them locally in the `articles/` folder.
4. Uploads them programmatically to an OpenAI Vector Store (using the OpenAI API).
5. Attaches them to an Assistant with a provided system prompt.
6. Detects deltas (new/updated articles) using hashes or timestamps.
7. Runs daily via a scheduled job (e.g., DigitalOcean App Platform).

---

## Setup

1. **Clone the repo**  
   `git clone https://github.com/your-org/chunky-monkey.git`

2. **Configure environment variables**  
   Copy `.env.sample` to `.env` and fill in your secrets:
   ```
   cp .env.sample .env
   ```

3. **Build and run with Docker**  
   ```
   docker build -t chunky-monkey .
   docker run --env-file .env -v $(pwd)/articles:/app/articles chunky-monkey
   ```

4. **Logs**  
   Output logs are written to the `logs/` directory.

---

## Project Structure

```
chunky-monkey/
├── assets/           # Demo screenshots and visual assets
├── articles/         # Markdown files (output)
├── logs/             # Log files
├── src/              # All Python modules
│   ├── scraper.py
│   ├── markdown_converter.py
│   ├── uploader.py
│   ├── utils.py
│   ├── main.py
│   └── __init__.py
├── Dockerfile
├── requirements.txt
├── .env.sample
├── README.md
```

---

## Example: Successful Query Screenshot

All screenshots and demo images are stored in the `assets/` folder.

![Assistant Query Example](assets/screenshot.png)

---

## Improvements & Notes

- Modular, extensible codebase.
- No hard-coded secrets; all config via `.env`.
- Designed for easy deployment and scheduling.
- Logs counts of added, updated, and skipped articles.

---