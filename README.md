
# CodeVectorSync

> 🚧 Active-hobby code—expect the occasional bug.
> Found one? Open an issue or PR!

This project helps you keep your local code and documentation synchronized with a ChromaDB vector store. Making it possible to easily ask AI questions about your codebase, find related functions across projects, or even get context-aware suggestions directly from your own files.

CodeVectorSync monitors your specified project directories, processes files (like .py, .js, .md, etc.), chunks their content, generates embeddings using a local SentenceTransformer model (all-MiniLM-L6-v2), and then stores these embeddings and their metadata in ChromaDB. It automatically detects new files, changes to existing files, and deletions, keeping your vector database up-to-date.

---

## Features
- ✔️ Recursive indexing of any local directory  
- ✔️ Fast semantic search over functions, classes, comments and docs  
- ✔️ Q&A via retrieval-augmented generation (RAG) with OpenAI GPT  
- ✔️ Zero-config defaults, but fully customizable with `.env`  
- ✔️ Easy to extend: switch embedding models, chunking strategies, etc.

## Getting Started
Prerequisites
Python 3.8+
A running ChromaDB instance (local or remote).

### Clone the repository
```bash
git clone https://github.com/moseland/CodeVectorSync.git
cd CodeVectorSync

### Install dependencies
```bash
pip install -r requirements.txt

### Update Configuration
Open ingest.py and modify the following variables to match your setup:

CHROMADB_HOST: Your ChromaDB server URL.

CHROMADB_COLLECTION_NAME: The name of the collection where your code embeddings will be stored.

PROJECT_ROOT_DIRECTORIES: A list of the root directories where your code projects are located.

INCLUDE_EXTENSIONS: File extensions to include in the ingestion process.

EXCLUDE_DIRS: Directories to ignore (like node_modules, .git, etc.).

### Usage
Start the ingestion and watcher script:
This will perform an initial scan of your configured directories and then start monitoring them for changes.

```bash
python ingest.py

Keep this script running in the background.

Check ChromaDB Statistics (Optional):
To see what's currently in your ChromaDB collection and get counts per project:

```bash
python stats.py

Clear the ChromaDB Collection (Use with Caution!):
If you want to completely wipe your code_knowledge_base collection (e.g., to start fresh), run:

```bash
python clear.py

WARNING: This action is irreversible and will delete all embeddings in the specified collection.

## License
MIT License (You should create a LICENSE file if you don't have one).