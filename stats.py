import chromadb
from urllib.parse import urlparse
from collections import defaultdict # For easily counting project entries

# --- Configuration (Match your ingest.py and Flask app config) ---
CHROMADB_URL = "server_url" 
CHROMADB_PORT = 0000
CHROMADB_COLLECTION_NAME = "collection_name"

def get_chromadb_stats():
    try:
        print(f"Connecting to ChromaDB at {CHROMADB_URL}...")
        
        # Parse the CHROMADB_URL to get hostname and port
        parsed_url = urlparse(CHROMADB_URL)
        chroma_host_to_connect = parsed_url.hostname
        chroma_port_to_connect = parsed_url.port if parsed_url.port else CHROMADB_PORT

        # Initialize the ChromaDB client with SSL for HTTPS
        client = chromadb.HttpClient(
            host=chroma_host_to_connect,
            port=chroma_port_to_connect,
            ssl=True # Important for HTTPS
        )
        
        # Test connection
        heartbeat = client.heartbeat()
        print(f"ChromaDB Heartbeat: {heartbeat}")

        # Get the specific collection
        try:
            collection = client.get_collection(name=CHROMADB_COLLECTION_NAME)
            print(f"\nSuccessfully accessed collection: '{collection.name}'")
        except Exception as e:
            print(f"Error accessing collection '{CHROMADB_COLLECTION_NAME}': {e}")
            print("Please ensure the collection exists and is correctly named.")
            return

        # Fetch all metadata from the collection
        # We fetch only metadatas to minimize data transfer if documents/embeddings are large
        print(f"Fetching all metadata from '{collection.name}' to calculate statistics...")
        all_items = collection.get(
            ids=collection.get()['ids'], # Get all IDs to fetch all items
            include=['metadatas']
        )
        
        if not all_items or not all_items['metadatas']:
            print(f"No items found in collection '{collection.name}'.")
            return

        # Process the metadata to get unique projects and counts
        project_counts = defaultdict(int)
        for metadata in all_items['metadatas']:
            project_name = metadata.get('project_name', 'unknown_project_name')
            project_counts[project_name] += 1

        # Print the statistics
        print(f"\n--- Statistics for ChromaDB Collection: '{collection.name}' ---")
        print(f"Total items in collection: {len(all_items['metadatas'])}")
        print(f"Total unique projects: {len(project_counts)}")
        print("\nProjects:")
        
        # Sort projects alphabetically for consistent output
        sorted_projects = sorted(project_counts.items())
        for project, count in sorted_projects:
            print(f"- '{project}': {count} entries")

        print("\n--- End of Statistics ---")

    except Exception as e:
        print(f"An error occurred while getting ChromaDB statistics: {e}")

if __name__ == "__main__":
    get_chromadb_stats()
