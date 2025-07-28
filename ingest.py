import os
import requests
import json
import chromadb
import uuid
import datetime
import time
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib
from urllib.parse import urlparse

LOCAL_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMADB_HOST = "server_url"
CHROMADB_PORT = 0000
CHROMADB_COLLECTION_NAME = "collection_name"

PROJECT_ROOT_DIRECTORIES = [
    "/Path/To/Files"
]

INCLUDE_EXTENSIONS = {
    '.php', '.js', '.jsx', '.ts', '.tsx', '.html', '.htm', '.css', '.scss', '.json',
    '.py', '.md', '.txt', '.xml', '.yml', '.yaml', '.sql', '.c', '.cpp', '.h', '.hpp'
}

EXCLUDE_DIRS = {
    'node_modules', '.git', 'vendor', 'dist', 'build', 'cache', '__pycache__',
    'wp-admin', 'wp-includes'
}

PROCESSED_FILES_STATE_FILE = "processed_files_state.json"

local_embedding_model = None
chroma_collection = None
processed_files_state = {}

def initialize_components():
    global local_embedding_model, chroma_collection, processed_files_state

    try:
        print(f"Loading local embedding model: {LOCAL_EMBEDDING_MODEL_NAME}...")
        local_embedding_model = SentenceTransformer(LOCAL_EMBEDDING_MODEL_NAME)
        print("Local embedding model loaded successfully.")
    except Exception as e:
        print(f"Error loading local embedding model: {e}")
        local_embedding_model = None
        return False

    try:
        print(f"Connecting to ChromaDB at {CHROMADB_HOST}...")

        parsed_url = urlparse(CHROMADB_HOST)
        chroma_host_to_connect = parsed_url.hostname
        chroma_port_to_connect = parsed_url.port if parsed_url.port else CHROMADB_PORT

        chroma_client = chromadb.HttpClient(
            host=chroma_host_to_connect,
            port=chroma_port_to_connect,
            ssl=True
        )

        heartbeat = chroma_client.heartbeat()
        print(f"ChromaDB Heartbeat: {heartbeat}")

        chroma_collection = chroma_client.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
        print(f"Connected to ChromaDB collection: '{chroma_collection.name}'")
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}. Please check CHROMADB_HOST/PORT and firewall rules.")
        chroma_collection = None
        return False

    try:
        if os.path.exists(PROCESSED_FILES_STATE_FILE):
            with open(PROCESSED_FILES_STATE_FILE, 'r') as f:
                processed_files_state = json.load(f)
            print(f"Loaded {len(processed_files_state)} entries from processed files state.")
    except Exception as e:
        print(f"Error loading processed files state: {e}. Starting with empty state.")
        processed_files_state = {}

    return True

def save_processed_files_state():
    """Saves the current state of processed files to a JSON file."""
    try:
        with open(PROCESSED_FILES_STATE_FILE, 'w') as f:
            json.dump(processed_files_state, f, indent=4)
        print("Processed files state saved.")
    except Exception as e:
        print(f"Error saving processed files state: {e}")

def get_embedding(text_chunk: str) -> List[float] | None:
    if local_embedding_model is None:
        print("Local embedding model not loaded. Cannot generate embeddings.")
        return None
    try:
        embedding = local_embedding_model.encode(text_chunk).tolist()
        return embedding
    except Exception as e:
        print(f"Error generating local embedding for chunk: {text_chunk[:50]}... Error: {e}")
        return None

def get_file_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.js', '.jsx', '.ts', '.tsx']: return 'javascript'
    elif ext == '.php': return 'php'
    elif ext == '.py': return 'python'
    elif ext in ['.html', '.htm']: return 'html'
    elif ext in ['.css', '.scss']: return 'css'
    elif ext in ['.md', '.txt']: return 'markdown'
    elif ext == '.json': return 'json'
    elif ext == '.xml': return 'xml'
    elif ext in ['.yml', '.yaml']: return 'yaml'
    elif ext == '.sql': return 'sql'
    elif ext in ['.c', '.cpp', '.h', '.hpp']: return 'c_cpp'
    else: return 'unknown'

def get_project_name(file_path: str, root_dirs: List[str]) -> str:
    if not root_dirs:
        return "unknown_project"

    base_root = root_dirs[0]
    if not base_root.endswith(os.sep):
        base_root = base_root + os.sep

    if file_path.startswith(base_root):
        relative_path = os.path.relpath(file_path, base_root)
        if os.sep in relative_path:
            return relative_path.split(os.sep)[0]
        else:
            return "root_level_project"
    return "unknown_project"

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    chunks = []
    if not text: return chunks
    words = text.split()
    start_idx = 0
    while start_idx < len(words):
        end_idx = min(start_idx + chunk_size, len(words))
        chunk = " ".join(words[start_idx:end_idx])
        chunks.append(chunk)
        if end_idx == len(words): break
        start_idx += (chunk_size - chunk_overlap)
        if start_idx >= len(words): break
    return chunks

def get_file_content(file_path: str) -> str | None:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f: return f.read()
        except Exception as e:
            print(f"Could not read file {file_path} due to encoding error: {e}")
            return None
    except Exception as e:
        print(f"Could not read file {file_path}: {e}")
        return None

def calculate_file_hash(file_path: str) -> str:
    """Calculates the MD5 hash of a file's content."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {file_path}: {e}")
        return ""

def process_file(file_path: str):
    """Processes a single file: chunks, embeds, and adds to ChromaDB."""
    if chroma_collection is None or local_embedding_model is None:
        print("ChromaDB or embedding model not initialized. Skipping file processing.")
        return

    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in INCLUDE_EXTENSIONS:
        return

    for excluded_dir in EXCLUDE_DIRS:
        if excluded_dir in os.path.normpath(file_path).split(os.sep):
            return

    try:
        current_mtime = os.path.getmtime(file_path)
        current_hash = calculate_file_hash(file_path)

        if file_path in processed_files_state:
            old_state = processed_files_state[file_path]
            if old_state.get("mtime") == current_mtime and old_state.get("hash") == current_hash:
                return
            else:
                print(f"Detected change in {file_path}. Re-processing...")
                chroma_collection.delete(where={"file_path": file_path})
                print(f"  -> Removed old embeddings for {file_path}.")
        else:
            print(f"New file detected: {file_path}. Processing...")

        content = get_file_content(file_path)
        if content is None:
            return

        chunks = chunk_text(content)
        if not chunks:
            print(f"No chunks generated for {file_path}. Skipping.")
            return

        project_name = get_project_name(file_path, PROJECT_ROOT_DIRECTORIES)
        language = get_file_language(file_path)

        embeddings_to_add = []
        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []

        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                metadata = {
                    "file_path": file_path,
                    "project_name": project_name,
                    "language": language,
                    "chunk_id": f"{i}",
                    "last_accessed_timestamp": datetime.datetime.now().isoformat()
                }
                embeddings_to_add.append(embedding)
                documents_to_add.append(chunk)
                metadatas_to_add.append(metadata)
                ids_to_add.append(f"{file_path}_{i}_{uuid.uuid4()}")

        if embeddings_to_add:
            chroma_collection.add(
                documents=documents_to_add,
                embeddings=embeddings_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            processed_files_state[file_path] = {"mtime": current_mtime, "hash": current_hash}
            print(f"  -> Added {len(embeddings_to_add)} chunks for {file_path} to ChromaDB.")
        else:
            print(f"  -> No embeddings generated for {file_path}.")

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

def remove_deleted_file_from_chroma(file_path: str):
    if chroma_collection is None:
        print("ChromaDB not initialized. Cannot remove deleted file.")
        return

    if file_path in processed_files_state:
        print(f"File deleted: {file_path}. Removing associated embeddings from ChromaDB...")
        try:
            chroma_collection.delete(where={"file_path": file_path})
            del processed_files_state[file_path]
            print(f"  -> Removed embeddings for {file_path} from ChromaDB.")
        except Exception as e:
            print(f"Error removing embeddings for {file_path}: {e}")

class CodeChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            process_file(event.src_path)
            save_processed_files_state()

    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path)
            save_processed_files_state()

    def on_deleted(self, event):
        if not event.is_directory:
            remove_deleted_file_from_chroma(event.src_path)
            save_processed_files_state()

    def on_moved(self, event):
        if not event.is_directory:
            remove_deleted_file_from_chroma(event.src_path)
            process_file(event.dest_path)
            save_processed_files_state()

def initial_ingestion_and_start_watching():
    if not initialize_components():
        print("Initialization failed. Exiting.")
        return

    print("\n--- Performing Initial Full Ingestion ---")
    initial_processed_count = 0
    files_to_scan = []
    for root_dir in PROJECT_ROOT_DIRECTORIES:
        if not os.path.isdir(root_dir):
            print(f"Warning: Project root directory not found: {root_dir}. Skipping initial scan.")
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                files_to_scan.append(file_path)

    for file_path in files_to_scan:
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in INCLUDE_EXTENSIONS:
            is_excluded = False
            for excluded_dir in EXCLUDE_DIRS:
                if excluded_dir in os.path.normpath(file_path).split(os.sep):
                    is_excluded = True
                    break
            if is_excluded:
                continue

            needs_processing = True
            if file_path in processed_files_state:
                try:
                    current_mtime = os.path.getmtime(file_path)
                    current_hash = calculate_file_hash(file_path)
                    old_state = processed_files_state[file_path]
                    if old_state.get("mtime") == current_mtime and old_state.get("hash") == current_hash:
                        needs_processing = False
                except FileNotFoundError:
                    remove_deleted_file_from_chroma(file_path)
                    needs_processing = False

            if needs_processing:
                process_file(file_path)
                initial_processed_count += 1
    save_processed_files_state()
    print(f"--- Initial Ingestion Complete. Processed {initial_processed_count} files. ---")

    print("\n--- Starting File System Watcher ---")
    event_handler = CodeChangeHandler()
    observer = Observer()
    for path in PROJECT_ROOT_DIRECTORIES:
        if os.path.isdir(path):
            observer.schedule(event_handler, path, recursive=True)
            print(f"Watching directory: {path}")
        else:
            print(f"Warning: Cannot watch non-existent directory: {path}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("\nFile system watcher stopped.")
    save_processed_files_state()

if __name__ == "__main__":
    initial_ingestion_and_start_watching()
