import os
import requests

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")  # Set this to your vector store ID

OPENAI_API_BASE = "https://api.openai.com/v1"
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2"
}

def list_vector_store_files(vector_store_id):
    url = f"{OPENAI_API_BASE}/vector_stores/{vector_store_id}/files"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])

def get_file_status(vector_store_id, file_id):
    url = f"{OPENAI_API_BASE}/vector_stores/{vector_store_id}/files/{file_id}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    if not OPENAI_API_KEY or not VECTOR_STORE_ID:
        print("Please set OPENAI_API_KEY and VECTOR_STORE_ID in your environment.", flush=True)
        exit(1)

    files = list_vector_store_files(VECTOR_STORE_ID)
    print(f"Found {len(files)} files in vector store {VECTOR_STORE_ID}.\n", flush=True)
    failed = 0
    for f in files:
        file_id = f["id"]
        status_info = get_file_status(VECTOR_STORE_ID, file_id)
        status = status_info.get("status")
        if status != "processed":
            failed += 1
            print(f"File {file_id} failed: {status_info.get('error', {}).get('message', 'No error message')}", flush=True)
    if failed == 0:
        print("All files processed successfully.", flush=True)
    else:
        print(f"\n{failed} files failed. See above for details.", flush=True)
