import chromadb
from urllib.parse import urlparse

CHROMADB_URL = "server_url" # Your ChromaDB URL
CHROMADB_COLLECTION_NAME = "collection_name" # The collection to delete

def clear_collection():
    try:
        print(f"Attempting to connect to ChromaDB at {CHROMADB_URL}...")
        parsed_url = urlparse(CHROMADB_URL)
        chroma_host_to_connect = parsed_url.hostname
        chroma_port_to_connect = parsed_url.port if parsed_url.port else 443 # Default HTTPS port

        chroma_client = chromadb.HttpClient(
            host=chroma_host_to_connect,
            port=chroma_port_to_connect,
            ssl=True
        )

        heartbeat = chroma_client.heartbeat()
        print(f"ChromaDB Heartbeat: {heartbeat}")

        # Delete the collection
        print(f"Deleting collection: '{CHROMADB_COLLECTION_NAME}'...")
        chroma_client.delete_collection(name=CHROMADB_COLLECTION_NAME)
        print(f"Collection '{CHROMADB_COLLECTION_NAME}' deleted successfully.")

        # Verify it's gone (optional)
        try:
            chroma_client.get_collection(name=CHROMADB_COLLECTION_NAME)
            print("Verification failed: Collection still exists (unexpected).")
        except Exception as e:
            print(f"Verification successful: Collection no longer found (expected).")

    except Exception as e:
        print(f"Error clearing ChromaDB collection: {e}")

if __name__ == "__main__":
    clear_collection()