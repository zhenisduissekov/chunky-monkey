"""
uploader.py

Uploads Markdown files from the articles/ directory to OpenAI's Vector Store via REST API,
attaches the files to a Vector Store, and links that store to an Assistant.

Fixes vs prior version:
- Adds required "OpenAI-Beta: assistants=v2" header to all relevant calls.
- Uses POST to update the Assistant (v2 update semantics) instead of PUT-ing the whole object.
- Ensures the Assistant has the file_search tool enabled and sets tool_resources correctly.
- Uses vector store file batch endpoint for attaching multiple files.
- Prints server error bodies on HTTP errors to aid debugging.

Environment variables (from .env):
- OPENAI_API_KEY
- ASSISTANT_ID

Usage:
    python src/uploader.py
"""

import os
import json
import pathlib
import requests
from dotenv import load_dotenv
from utils import setup_logging

uploader_logger = setup_logging(log_level="ERROR", log_file="logs/uploader_errors.log")

# ----------------------------
# Config & constants
# ----------------------------
OPENAI_API_BASE = "https://api.openai.com/v1"
BETA_HEADER = {"OpenAI-Beta": "assistants=v2"}

# ----------------------------
# Helpers
# ----------------------------

def _auth_headers(api_key: str, json_body: bool = True) -> dict:
    h = {
        "Authorization": f"Bearer {api_key}",
    }
    h.update(BETA_HEADER)
    if json_body:
        h["Content-Type"] = "application/json"
    return h

def _raise_with_body(resp: requests.Response):
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        body = resp.text
        msg = f"{str(e)}\n--- Response body ---\n{body}\n----------------------"
        uploader_logger.error(msg, exc_info=True)
        raise requests.HTTPError(msg, response=resp) from None

def find_markdown_files(articles_dir: pathlib.Path):
    return sorted([p for p in articles_dir.iterdir() if p.suffix.lower() == ".md"])

def get_file_status(file_id: str, api_key: str) -> dict:
    url = f"{OPENAI_API_BASE}/files/{file_id}"
    headers = _auth_headers(api_key, json_body=False)
    resp = requests.get(url, headers=headers, timeout=30)
    _raise_with_body(resp)
    return resp.json()

# ----------------------------
# File Uploads → /files
# ----------------------------

def upload_file(filepath: pathlib.Path, api_key: str) -> str:
    url = f"{OPENAI_API_BASE}/files"
    headers = {"Authorization": f"Bearer {api_key}"}
    headers.update(BETA_HEADER)  # not strictly required for /files, but harmless and consistent
    try:
        with open(filepath, "rb") as f:
            files = {"file": (filepath.name, f)}
            data = {"purpose": "assistants"}
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        _raise_with_body(resp)
        return resp.json()["id"]
    except Exception as e:
        uploader_logger.error(f"Error uploading file {filepath}: {e}", exc_info=True)
        raise

# ----------------------------
# Vector Store creation + batch attach
# ----------------------------

def create_vector_store(api_key: str, name: str = "kb-store") -> str:
    url = f"{OPENAI_API_BASE}/vector_stores"
    headers = _auth_headers(api_key, json_body=True)
    payload = {"name": name}
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        _raise_with_body(resp)
        return resp.json()["id"]
    except Exception as e:
        uploader_logger.error(f"Error creating vector store: {e}", exc_info=True)
        raise

def batch_attach_files_to_vector_store(vector_store_id: str, file_ids: list[str], api_key: str):
    """
    Uses file_batches endpoint to attach multiple files in one request.
    """
    url = f"{OPENAI_API_BASE}/vector_stores/{vector_store_id}/file_batches"
    headers = _auth_headers(api_key, json_body=True)
    payload = {"file_ids": file_ids}
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        _raise_with_body(resp)
        return resp.json()
    except Exception as e:
        uploader_logger.error(f"Error batch attaching files to vector store {vector_store_id}: {e}", exc_info=True)
        raise

# ----------------------------
# Assistant update (v2)
# ----------------------------

def ensure_file_search_tool_and_attach_store(assistant_id: str, vector_store_id: str, api_key: str):
    """
    In Assistants v2, you update with POST and only the fields you want to change.
    Ensure tools include {"type":"file_search"} and set tool_resources pointing at the vector store.
    """
    url = f"{OPENAI_API_BASE}/assistants/{assistant_id}"

    try:
        # First, GET to see current tools (include beta header!)
        get_headers = _auth_headers(api_key, json_body=False)
        resp_get = requests.get(url, headers=get_headers, timeout=30)
        _raise_with_body(resp_get)
        asst = resp_get.json()

        tools = asst.get("tools") or []
        has_file_search = any(t.get("type") == "file_search" for t in tools)
        if not has_file_search:
            tools.append({"type": "file_search"})

        payload = {
            "tools": tools,
            "tool_resources": {
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        }

        # v2 update is POST to the same URL with only changed fields
        post_headers = _auth_headers(api_key, json_body=True)
        resp_post = requests.post(url, headers=post_headers, data=json.dumps(payload), timeout=60)
        _raise_with_body(resp_post)
        return resp_post.json()
    except Exception as e:
        uploader_logger.error(f"Error updating assistant {assistant_id} to attach vector store {vector_store_id}: {e}", exc_info=True)
        raise

# ----------------------------
# Main
# ----------------------------

def main():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    ASSISTANT_ID = os.getenv("ASSISTANT_ID", "").strip()

    try:
        if not OPENAI_API_KEY or not ASSISTANT_ID:
            print("Error: OPENAI_API_KEY and ASSISTANT_ID must be set in the .env file.")
            raise SystemExit(1)

        articles_dir = (pathlib.Path(__file__).parent / ".." / "articles").resolve()
        md_files = find_markdown_files(articles_dir)

        if not md_files:
            print(f"No Markdown files found in {articles_dir}. Nothing to upload.")
            return

        print(f"Found {len(md_files)} Markdown files. Uploading to /files ...", flush=True)
        total_files = 0
        succeeded = 0
        failed = 0
        assigned = 0
        assign_failed = 0
        MAX_RETRIES = 3
        BACKOFF_FACTOR = 2  # seconds

        print("Creating vector store ...", flush=True)
        vs_id = create_vector_store(OPENAI_API_KEY, name="knowledge-base")
        print(f"Vector store created: {vs_id}", flush=True)

        import time

        for p in md_files:
            total_files += 1
            file_uploaded = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    fid = upload_file(p, OPENAI_API_KEY)
                    status_info = get_file_status(fid, OPENAI_API_KEY)
                    status = status_info.get("status")
                    if status != "processed":
                        uploader_logger.error(f"File {p.name} (id={fid}) failed in OpenAI storage: status={status}, error={status_info.get('error', 'No error message')}")
                        print(f"  - {p.name} → file_id={fid} [FAILED: {status}]", flush=True)
                        failed += 1
                        break
                    else:
                        succeeded += 1
                        file_uploaded = True
                        break  # Success, exit retry loop
                except Exception as e:
                    uploader_logger.error(f"Attempt {attempt} failed for {p}: {e}", exc_info=True)
                    if attempt == MAX_RETRIES:
                        print(f"  - {p.name} [UPLOAD ERROR after {MAX_RETRIES} attempts]", flush=True)
                        failed += 1
                    else:
                        time.sleep(BACKOFF_FACTOR ** (attempt - 1))  # Exponential backoff

            if file_uploaded:
                # Wait before assigning to vector store
                time.sleep(5)
                try:
                    # Assign file to vector store one by one
                    batch_info = batch_attach_files_to_vector_store(vs_id, [fid], OPENAI_API_KEY)
                    batch_status = batch_info.get('status', 'unknown')
                    if batch_status == "completed":
                        assigned += 1
                    else:
                        assign_failed += 1
                        uploader_logger.error(f"File {p.name} (id={fid}) failed to assign to vector store: batch status={batch_status}, batch_info={batch_info}")
                        print(f"  - {p.name} → file_id={fid} [ASSIGN FAILED: {batch_status}]", flush=True)
                except Exception as e:
                    assign_failed += 1
                    uploader_logger.error(f"Error assigning file {p.name} (id={fid}) to vector store: {e}", exc_info=True)
                    print(f"  - {p.name} → file_id={fid} [ASSIGN ERROR]", flush=True)

        print(f"Upload summary: Tried {total_files} files. Uploaded: {succeeded}. Upload failed: {failed}. Assigned to vector store: {assigned}. Assign failed: {assign_failed}.", flush=True)

        print("Updating assistant to enable file_search and attach vector store ...", flush=True)
        updated = ensure_file_search_tool_and_attach_store(ASSISTANT_ID, vs_id, OPENAI_API_KEY)
        print(f"Assistant updated. Attached vector_store_ids: {updated.get('tool_resources', {}).get('file_search', {}).get('vector_store_ids')}", flush=True)

        print(f"Done. {total_files} files processed. Vector Store ID: {vs_id}", flush=True)
    except Exception as e:
        uploader_logger.error(f"Error in uploader main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
