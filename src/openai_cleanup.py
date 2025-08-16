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

def main():
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY must be set in the .env file.")
        return

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

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
            vector_store_ns = getattr(client.beta, ns)
            vector_stores = vector_store_ns.list()
            if not vector_stores.data:
                print(f"No vector stores found in {ns}.")
            for vs in vector_stores.data:
                name = getattr(vs, "name", "no name")
                print(f"Deleting vector store: {vs.id} ({name})")
                vector_store_ns.delete(vs.id)
                deleted_any = True
        except AttributeError:
            continue
        except Exception as e:
            print(f"Error listing or deleting vector stores in {ns}: {e}")
    if not deleted_any:
        print("No vector store namespace found or nothing to delete.")

if __name__ == "__main__":
    main()
