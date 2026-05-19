"""
Document Processing Engine
Handles ingestion, chunking, embedding, and vector storage
for PDFs, DOCX, TXT, and plain text content.
"""

import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# LangChain document loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_chroma import Chroma

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"
METADATA_FILE = BASE_DIR / "data" / "document_metadata.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

# ── embedding model (local, no API key needed) ─────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # fast & good quality, ~80 MB download


def get_embeddings():
    return SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)


def get_vectorstore() -> Chroma:
    return Chroma(
        persist_directory=str(VECTORSTORE_DIR),
        embedding_function=get_embeddings(),
        collection_name="enterprise_knowledge",
    )


# ── metadata store ─────────────────────────────────────────────────────────────

def load_metadata() -> Dict:
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_metadata(meta: Dict):
    with open(METADATA_FILE, "w") as f:
        json.dump(meta, f, indent=2, default=str)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── loaders ────────────────────────────────────────────────────────────────────

def load_document(path: Path) -> List:
    """Load a file into LangChain Documents based on extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(str(path))
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(str(path))
    elif ext in (".txt", ".md", ".csv"):
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()


# ── chunking ───────────────────────────────────────────────────────────────────

def split_documents(docs: List) -> List:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


# ── ingestion pipeline ─────────────────────────────────────────────────────────

def ingest_file(uploaded_file) -> Tuple[bool, str]:
    """
    Save an uploaded Streamlit file, process it, embed it.
    Returns (success: bool, message: str).
    """
    meta = load_metadata()

    # Save to disk
    save_path = UPLOAD_DIR / uploaded_file.name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    fhash = file_hash(save_path)

    # Deduplicate
    for doc_id, info in meta.items():
        if info.get("hash") == fhash:
            return False, f"'{uploaded_file.name}' is already in the knowledge base."

    try:
        raw_docs = load_document(save_path)
        chunks = split_documents(raw_docs)

        # Tag every chunk with source metadata
        for chunk in chunks:
            chunk.metadata.update({
                "source_file": uploaded_file.name,
                "file_type": save_path.suffix.lstrip(".").upper(),
                "ingested_at": datetime.now().isoformat(),
            })

        vs = get_vectorstore()
        vs.add_documents(chunks)

        # Record metadata
        doc_id = fhash[:12]
        meta[doc_id] = {
            "id": doc_id,
            "name": uploaded_file.name,
            "file_type": save_path.suffix.lstrip(".").upper(),
            "size_bytes": save_path.stat().st_size,
            "chunk_count": len(chunks),
            "page_count": len(raw_docs),
            "ingested_at": datetime.now().isoformat(),
            "hash": fhash,
            "path": str(save_path),
        }
        save_metadata(meta)

        return True, f"✅ '{uploaded_file.name}' indexed — {len(chunks)} chunks created."

    except Exception as e:
        save_path.unlink(missing_ok=True)
        return False, f"❌ Error processing '{uploaded_file.name}': {e}"


def delete_document(doc_id: str) -> Tuple[bool, str]:
    """Remove a document from vectorstore and metadata."""
    meta = load_metadata()
    if doc_id not in meta:
        return False, "Document not found."

    info = meta[doc_id]
    try:
        vs = get_vectorstore()
        # Delete by source_file metadata filter
        vs._collection.delete(
            where={"source_file": info["name"]}
        )
        Path(info["path"]).unlink(missing_ok=True)
        del meta[doc_id]
        save_metadata(meta)
        return True, f"'{info['name']}' removed from knowledge base."
    except Exception as e:
        return False, f"Error removing document: {e}"


def get_document_list() -> List[Dict]:
    meta = load_metadata()
    return sorted(meta.values(), key=lambda x: x["ingested_at"], reverse=True)


def get_stats() -> Dict:
    docs = get_document_list()
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)
    types = {}
    for d in docs:
        t = d.get("file_type", "OTHER")
        types[t] = types.get(t, 0) + 1
    return {
        "total_documents": len(docs),
        "total_chunks": total_chunks,
        "document_types": types,
    }


# ── retrieval ──────────────────────────────────────────────────────────────────

def retrieve_context(query: str, k: int = 6) -> List[Dict]:
    """Semantic search — returns top-k chunks with metadata."""
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(query, k=k)
    out = []
    for doc, score in results:
        out.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source_file", "Unknown"),
            "file_type": doc.metadata.get("file_type", ""),
            "relevance": round(1 - score, 3),   # convert distance → similarity
        })
    return out