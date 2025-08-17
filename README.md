# chunky-monkey

## Overview

**chunky-monkey** is an automated, containerized pipeline for scraping knowledge base articles, converting them to Markdown, and uploading them to an OpenAI Vector Store for use with an AI Assistant. The service is designed to run as a scheduled daily job (e.g., on DigitalOcean App Platform), efficiently detecting and uploading only new or updated articles.

---

## Architecture

1. **Scraper** (`src/scraper.py`): Fetches articles from a knowledge base API (e.g., Zendesk), cleans and converts them to Markdown, and saves them in the `articles/` directory.
2. **Delta Detection** (`src/main.py`): Computes SHA256 hashes for each Markdown file and compares them to a stored record (`article_hashes.json`) to detect new or updated articles.
3. **Uploader** (`src/uploader.py`): Uploads Markdown files to OpenAI, creates a Vector Store, batch-attaches files, and updates the Assistant to use the new Vector Store.
4. **Orchestrator** (`src/main.py`): Runs the scraper, delta detection, and uploader in sequence as a single job.
5. **Containerization** (`Dockerfile`): The entire workflow is packaged in a Docker image for reproducible, portable deployment.

---

## Features

- **Automated scraping and conversion** of knowledge base articles to Markdown.
- **Delta detection**: Only new or changed articles are uploaded, minimizing API usage and cost.
- **OpenAI integration**: Files are uploaded to a Vector Store and attached to an Assistant for retrieval-augmented AI.
- **Daily scheduling**: Designed to run as a daily job on DigitalOcean App Platform or any container scheduler.
- **Robust logging and error reporting** for easy monitoring and debugging.

---

## Setup & Usage

### 1. Clone the Repository

```sh
git clone https://github.com/your-org/chunky-monkey.git
cd chunky-monkey
```

### 2. Configure Environment Variables

Copy `.env.sample` to `.env` and fill in your secrets:

```
cp .env.sample .env
```

**Required variables:**
- `OPENAI_API_KEY` — Your OpenAI API key.
- `ASSISTANT_ID` — The Assistant ID from the OpenAI platform.
- `KNOWLEDGE_BASE_API_URL` — The API endpoint for your knowledge base.
- `KNOWLEDGE_BASE_PAGE_SIZE` — (e.g., `10`)
- Any other variables required by your scraper.

**Important:**  
- Do **not** use quotes or comments in `.env` values.
- Example:
  ```
  OPENAI_API_KEY=sk-...
  ASSISTANT_ID=asst_...
  KNOWLEDGE_BASE_API_URL=https://support.optisigns.com/api/v2/help_center/en-us/articles.json
  KNOWLEDGE_BASE_PAGE_SIZE=10
  ```

### 3. Build and Run with Docker

```sh
make docker-build
make docker-run
```

---

### 🐳 Run with Docker (All Environment Variables)

You can run this service in a single command using Docker.  
Just replace the environment variable values as needed:

```sh
docker run \
  -e OPENAI_API_KEY=your-openai-api-key \
  -e ASSISTANT_ID=your-assistant-id \
  -e KNOWLEDGE_BASE_API_URL=https://support.optisigns.com/api/v2/help_center/en-us/articles.json \
  -e KNOWLEDGE_BASE_PAGE_SIZE=1 \
  -e KNOWLEDGE_BASE_FILE_NUMBER=14 \
  -e LOG_LEVEL=INFO \
  -e SCRAPE_PERIOD="* * * * *" \
  your-dockerhub-username/your-image-name:latest
```

**Replace:**
- `your-openai-api-key` with your actual OpenAI API key.
- `your-assistant-id` with your OpenAI Assistant ID.
- Adjust `KNOWLEDGE_BASE_API_URL`, `KNOWLEDGE_BASE_PAGE_SIZE`, `KNOWLEDGE_BASE_FILE_NUMBER`, `LOG_LEVEL`, and `SCRAPE_PERIOD` as needed for your deployment.
- `your-dockerhub-username/your-image-name:latest` with your actual Docker image name and tag.

#### Example (run every hour):

```sh
docker run \
  -e OPENAI_API_KEY=sk-... \
  -e ASSISTANT_ID=asst_... \
  -e KNOWLEDGE_BASE_API_URL=https://support.optisigns.com/api/v2/help_center/en-us/articles.json \
  -e KNOWLEDGE_BASE_PAGE_SIZE=1 \
  -e KNOWLEDGE_BASE_FILE_NUMBER=14 \
  -e LOG_LEVEL=INFO \
  -e SCRAPE_PERIOD="0 * * * *" \
  johndoe/chunky-monkey:latest
```

#### Required Environment Variables

| Variable                   | Description                                                        |
|----------------------------|--------------------------------------------------------------------|
| `OPENAI_API_KEY`           | Your OpenAI API key (required for uploading to Vector Store)        |
| `ASSISTANT_ID`             | The ID of your OpenAI Assistant                                    |
| `KNOWLEDGE_BASE_API_URL`   | Knowledge base API endpoint (e.g., Zendesk articles endpoint)       |
| `KNOWLEDGE_BASE_PAGE_SIZE` | Number of articles per page to fetch from the knowledge base        |
| `KNOWLEDGE_BASE_FILE_NUMBER` | Number of files to process per run                                |
| `LOG_LEVEL`                | Log level (e.g., INFO, DEBUG)                                      |
| `SCRAPE_PERIOD`            | Cron schedule for running the scraper (e.g., `0 0 * * *` for daily) |

---

- **Important:** If you are deploying to a cloud platform (like DigitalOcean), you must build your Docker image for the correct architecture (linux/amd64). On Apple Silicon (M1/M2) or ARM machines, use:
  ```sh
  make docker-build-linux
  ```
  or
  ```sh
  docker build --platform linux/amd64 -t chunky-monkey .
  ```
  This ensures your image will run on cloud servers (which are amd64/x86_64).

- All logs and errors will be printed to your terminal.
- To reset the Docker image and containers:
  ```sh
  make docker-reset
  ```

### 4. Deploy & Schedule on DigitalOcean App Platform

1. **Push your Docker image** to a registry (Docker Hub or DigitalOcean Container Registry).
2. **Create a new App** in DigitalOcean App Platform:
   - Choose "Worker" or "Job" type.
   - Set the image to your pushed Docker image.
   - Set the command to `python src/main.py` (default).
   - Add your `.env` variables in the App Platform UI.
   - Set the schedule to run once per day.
3. **Monitor logs** in the DigitalOcean dashboard for each run.

---

## Delta Detection

- The service uses SHA256 hashes to detect new or updated articles.
- Hashes are stored in `article_hashes.json`.
- On each run:
  - The scraper fetches and saves articles as Markdown.
  - The orchestrator computes hashes for all `.md` files.
  - Only files with new or changed hashes are uploaded.
  - The hash record is updated after a successful upload.

---

## Chunking Strategy

**Note:** Chunking is currently **not applied** in this service for three reasons:
- To keep the implementation simple and robust.
- To ensure that article URLs remain relatable and visible in every file.
- Because the files being uploaded are not large enough to require chunking at this stage.

If chunking becomes necessary in the future (for larger files or more advanced retrieval), this strategy can be revisited.

---

## Troubleshooting

- **Docker fails to run with Error 125:**  
  - Check your `.env` file for spaces or quotes around variable names/values.
  - Example: `KNOWLEDGE_BASE_API_URL=https://...` (no quotes, no spaces).
- **ValueError for int() conversion:**  
  - Remove comments or extra text from environment variable values.
  - Example: `KNOWLEDGE_BASE_PAGE_SIZE=10`
- **No connection adapters were found:**  
  - Remove quotes from URL values in `.env`.
- **OpenAI API errors:**  
  - Check that your API key and Assistant ID are correct and valid for your organization/project.
  - Review the error message printed in the logs for details.
- **No new or updated articles detected:**  
  - Ensure your scraper is fetching fresh content and saving `.md` files in the `articles/` directory.

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

## Playground Sanity Check

Below is a screenshot showing the Assistant correctly answering a sample question with citations:

![Playground Answer](assets/Screenshot%202025-08-16%20at%2022.39.48.png)

**Sample Q&A:**

> **User:** How do I add a YouTube video?  
> **OptiBot:**  
> To add a YouTube video in OptiSigns:  
> 1. Go to the Files/Assets page.  
> 2. Click Add Asset and select YouTube App from the app list.  
> 3. Enter the YouTube video URL.  
> 4. Set optional configurations like video title and duration.  
> 5. Click Save to add the YouTube video as an asset.  
> You can then use this asset in your playlists or assign it to your screens.  
> **Article URL:** https://www.optisigns.com/support/how-to-display-youtube-video-on-your-digital-signage

All screenshots and demo images are stored in the `assets/` folder.
---

## Tests

Basic unit and integration tests are included to demonstrate how testing can be implemented for this project. These tests cover core utilities (such as hash computation and delta detection), as well as basic mocking for the scraper and uploader modules. The current tests are not exhaustive, but serve as a foundation for further test development and show that the codebase is testable and can be extended with more comprehensive tests as needed.

Run all tests with:
```
make test
```

---

## Makefile Commands

- `make install` — Set up Python virtual environment and install dependencies.
- `make run` — Run the pipeline locally (venv).
- `make test-utils` — Test the utils module.
- `make test-scraper` — Test the scraper module.
- `make test-upload` — Run the uploader script.
- `make clean` — Remove venv, cache, and generated files.
- `make reset` — Clean and reinstall everything.
- `make reset-openai` — Remove all uploaded files and vector stores from OpenAI.
- `make reset-all` — Full local and OpenAI cleanup.
- `make docker-build` — Build the Docker image.
- `make docker-run` — Run the app in Docker (requires `.env`).
- `make docker-reset` — Remove Docker image and stopped containers.

---

## Improvements & Notes

- Modular, extensible codebase.
- No hard-coded secrets; all config via `.env`.
- Designed for easy deployment and scheduling.
- Logs counts of added, updated, and skipped articles.
- Robust error handling and logging for easy debugging.

---

## License

MIT License

---