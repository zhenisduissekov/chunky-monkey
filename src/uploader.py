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
        raise requests.HTTPError(msg, response=resp) from None

def find_markdown_files(articles_dir: pathlib.Path):
    return sorted([p for p in articles_dir.iterdir() if p.suffix.lower() == ".md"])

# ----------------------------
# File Uploads → /files
# ----------------------------

def upload_file(filepath: pathlib.Path, api_key: str) -> str:
    url = f"{OPENAI_API_BASE}/files"
    headers = {"Authorization": f"Bearer {api_key}"}
    headers.update(BETA_HEADER)  # not strictly required for /files, but harmless and consistent
    with open(filepath, "rb") as f:
        files = {"file": (filepath.name, f)}
        data = {"purpose": "assistants"}
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    _raise_with_body(resp)
    return resp.json()["id"]

# ----------------------------
# Vector Store creation + batch attach
# ----------------------------

def create_vector_store(api_key: str, name: str = "kb-store") -> str:
    url = f"{OPENAI_API_BASE}/vector_stores"
    headers = _auth_headers(api_key, json_body=True)
    payload = {"name": name}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    _raise_with_body(resp)
    return resp.json()["id"]

def batch_attach_files_to_vector_store(vector_store_id: str, file_ids: list[str], api_key: str):
    """
    Uses file_batches endpoint to attach multiple files in one request.
    """
    url = f"{OPENAI_API_BASE}/vector_stores/{vector_store_id}/file_batches"
    headers = _auth_headers(api_key, json_body=True)
    payload = {"file_ids": file_ids}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    _raise_with_body(resp)
    return resp.json()

# ----------------------------
# Assistant update (v2)
# ----------------------------

def ensure_file_search_tool_and_attach_store(assistant_id: str, vector_store_id: str, api_key: str):
    """
    In Assistants v2, you update with POST and only the fields you want to change.
    Ensure tools include {"type":"file_search"} and set tool_resources pointing at the vector store.
    """
    url = f"{OPENAI_API_BASE}/assistants/{assistant_id}"

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

# ----------------------------
# Main
# ----------------------------

def main():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    ASSISTANT_ID = os.getenv("ASSISTANT_ID", "").strip()

    if not OPENAI_API_KEY or not ASSISTANT_ID:
        print("Error: OPENAI_API_KEY and ASSISTANT_ID must be set in the .env file.")
        raise SystemExit(1)

    articles_dir = (pathlib.Path(__file__).parent / ".." / "articles").resolve()
    md_files = find_markdown_files(articles_dir)

    if not md_files:
        print(f"No Markdown files found in {articles_dir}. Nothing to upload.")
        return

    print(f"Found {len(md_files)} Markdown files. Uploading to /files ...")
    file_ids = []
    for p in md_files:
        fid = upload_file(p, OPENAI_API_KEY)
        file_ids.append(fid)
        print(f"  - {p.name} → file_id={fid}")

    print("Creating vector store ...")
    vs_id = create_vector_store(OPENAI_API_KEY, name="knowledge-base")
    print(f"Vector store created: {vs_id}")

    print("Batch-attaching files to vector store ...")
    batch_info = batch_attach_files_to_vector_store(vs_id, file_ids, OPENAI_API_KEY)
    print(f"File batch status: {batch_info.get('status', 'submitted')} (vector_store_id={vs_id})")

    print("Updating assistant to enable file_search and attach vector store ...")
    updated = ensure_file_search_tool_and_attach_store(ASSISTANT_ID, vs_id, OPENAI_API_KEY)
    print(f"Assistant updated. Attached vector_store_ids: {updated.get('tool_resources', {}).get('file_search', {}).get('vector_store_ids')}")

    print(f"Done. {len(md_files)} files uploaded. Vector Store ID: {vs_id}")

if __name__ == "__main__":
    main()
