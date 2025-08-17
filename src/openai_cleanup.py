"""
openai_cleanup.py

This script deletes all uploaded files and vector stores from your OpenAI account.
Use this for development resets to avoid accumulating unused resources.

WARNING: This will permanently delete all files and vector stores accessible by your API key.

Usage:
    python src/openai_cleanup.py
"""

import os
from dotenv import load_dotenv
import openai
import requests

def main():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY must be set in the .env file.")
        return

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Debug: print available namespaces under client.beta
    print("DEBUG: Available namespaces in client.beta:", dir(client.beta))
    # Debug: print available attributes in client.beta.assistants
    print("DEBUG: Available attributes in client.beta.assistants:", dir(client.beta.assistants))

    # Delete all files
    print("Listing and deleting all OpenAI files...")
    try:
        files = client.files.list()
        if not files.data:
            print("No files found.")
        for file in files.data:
            print(f"Deleting file: {file.id} ({file.filename})")
            client.files.delete(file.id)
    except Exception as e:
        print(f"Error listing or deleting files: {e}")

    # Delete all vector stores (try both possible namespaces)
    deleted_any = False
    for ns in ["vector_stores", "vectorStores"]:
        try:
            print(f"DEBUG: Trying namespace '{ns}'...")
            vector_store_ns = getattr(client.beta, ns)
            vector_stores = vector_store_ns.list()
            print(f"DEBUG: vector_stores.list() in '{ns}' returned: {vector_stores}")
            if not vector_stores.data:
                print(f"No vector stores found in {ns}.")
            for vs in vector_stores.data:
                name = getattr(vs, "name", "no name")
                print(f"Deleting vector store: {vs.id} ({name})")
                vector_store_ns.delete(vs.id)
                deleted_any = True
        except AttributeError:
            print(f"DEBUG: Namespace '{ns}' not found in client.beta.")
            continue
        except Exception as e:
            print(f"Error listing or deleting vector stores in {ns}: {e}")

    # Fallback: Try direct REST API for vector stores if SDK did not find any
    if not deleted_any:
        print("No vector store namespace found or nothing to delete via SDK. Trying REST API for vector stores...")
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2"
        }
        try:
            resp = requests.get("https://api.openai.com/v1/vector_stores", headers=headers)
            if resp.status_code != 200:
                print(f"REST API: Failed to list vector stores. Status: {resp.status_code}, Response: {resp.text}")
            else:
                stores = resp.json().get("data", [])
                print(f"REST API: Found {len(stores)} vector stores.")
                for store in stores:
                    store_id = store["id"]
                    name = store.get("name", "")
                    print(f"REST API: Deleting vector store: {store_id} ({name})")
                    del_resp = requests.delete(f"https://api.openai.com/v1/vector_stores/{store_id}", headers=headers)
                    print("REST API: Status:", del_resp.status_code, "Response:", del_resp.text)
                if not stores:
                    print("REST API: No vector stores found.")
        except Exception as e:
            print(f"REST API: Error listing or deleting vector stores: {e}")

if __name__ == "__main__":
    main()
