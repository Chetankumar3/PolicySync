"""
Ingestion pipeline: chunking, embedding, and indexing to ChromaDB
"""
import chromadb
from chromadb.config import Settings
import json
import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
import hashlib

logger = logging.getLogger(__name__)

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def initialize_db():
    """Initialize ChromaDB with two collections: active_index and archive_index"""
    try:
        # Create persistent ChromaDB directory
        os.makedirs("./chroma_store", exist_ok=True)
        
        # Initialize ChromaDB with persistence
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_store",
            anonymized_telemetry=False,
        )
        
        client = chromadb.Client(settings)
        
        # Create or get collections
        active_collection = client.get_or_create_collection(
            name="active_index",
            metadata={"description": "Current active regulatory documents"}
        )
        
        archive_collection = client.get_or_create_collection(
            name="archive_index",
            metadata={"description": "Historical or superseded documents"}
        )
        
        logger.info(f"ChromaDB initialized with collections:")
        logger.info(f"  - active_index: {active_collection.count()} documents")
        logger.info(f"  - archive_index: {archive_collection.count()} documents")
        
        return client
    
    except Exception as e:
        logger.error(f"Error initializing ChromaDB: {e}")
        raise

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Chunk text into overlapping segments
    """
    chunks = []
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def embed_text(text: str) -> List[float]:
    """
    Embed text using sentence-transformers
    """
    try:
        embedding = embedding_model.encode(text, convert_to_numpy=False)
        return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        raise

def generate_chunk_id(text: str, source: str, index: int) -> str:
    """
    Generate unique ID for a chunk using hash
    """
    combined = f"{source}_{index}_{text[:100]}"
    return hashlib.md5(combined.encode()).hexdigest()

def ingest_document(
    text: str,
    source_name: str,
    source_url: str = "",
    db=None,
    document_date: str = None
) -> Dict[str, Any]:
    """
    Ingest a document: chunk, embed, and upsert to ChromaDB
    """
    if not db:
        raise ValueError("Database not initialized")
    
    if document_date is None:
        document_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        logger.info(f"Ingesting document: {source_name}")
        
        # Get active collection
        active_collection = db.get_or_create_collection("active_index")
        
        # Chunk the document
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from {source_name}")
        
        ingested_count = 0
        
        # Process each chunk
        for idx, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(chunk, source_name, idx)
            
            # Check if chunk already exists
            try:
                existing = active_collection.get(ids=[chunk_id])
                if existing and existing['ids']:
                    logger.debug(f"Chunk {chunk_id} already exists, skipping")
                    continue
            except:
                pass
            
            # Embed the chunk
            embedding = embed_text(chunk)
            
            # Upsert to active index
            active_collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": source_name,
                    "url": source_url,
                    "date": document_date,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "ingestion_time": datetime.now().isoformat()
                }]
            )
            
            ingested_count += 1
        
        logger.info(f"Successfully ingested {ingested_count} new chunks from {source_name}")
        
        return {
            "status": "success",
            "source": source_name,
            "chunks_created": len(chunks),
            "chunks_ingested": ingested_count,
            "date": document_date
        }
    
    except Exception as e:
        logger.error(f"Error ingesting document {source_name}: {e}")
        raise

def get_collection_stats(db):
    """Get statistics for both collections"""
    try:
        active = db.get_or_create_collection("active_index")
        archive = db.get_or_create_collection("archive_index")
        
        return {
            "active_index": {
                "count": active.count(),
                "metadata": active.metadata
            },
            "archive_index": {
                "count": archive.count(),
                "metadata": archive.metadata
            }
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return None
