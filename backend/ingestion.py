"""
Ingestion pipeline: chunking, embedding, and indexing to LanceDB
"""
import lancedb
import json
import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
import hashlib
from lancedb.pydantic import LanceModel, Vector

logger = logging.getLogger(__name__)

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- DEFINED STRICT SCHEMA FOR LANCEDB ---
class MetadataSchema(LanceModel):
    source: str
    url: str
    date: str
    chunk_index: int
    total_chunks: int
    ingestion_time: str

class DocumentSchema(LanceModel):
    id: str
    vector: Vector(384) # 384 matches 'all-MiniLM-L6-v2' output dimension
    text: str
    metadata: MetadataSchema
# -----------------------------------------

def initialize_db():
    """Initialize LanceDB with two tables: active_index and archive_index"""
    try:
        # Create persistent LanceDB directory
        os.makedirs("./lancedb_store", exist_ok=True)

        # Initialize LanceDB
        db = lancedb.connect("./lancedb_store")

        # Create or open tables
        active_collection = get_or_create_table(db, "active_index")
        archive_collection = get_or_create_table(db, "archive_index")
        
        logger.info(f"LanceDB initialized with tables:")
        logger.info(f"  - active_index: {active_collection.count_rows()} documents")
        logger.info(f"  - archive_index: {archive_collection.count_rows()} documents")
        
        return db
    
    except Exception as e:
        logger.error(f"Error initializing LanceDB: {e}")
        raise

def get_or_create_table(db, table_name: str):
    """Open an existing LanceDB table or create it if missing."""
    try:
        return db.open_table(table_name)
    except Exception:
        # Passed the schema to allow creating an empty table
        return db.create_table(table_name, schema=DocumentSchema)

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
    Ingest a document: chunk, embed, and insert to LanceDB
    """
    if not db:
        raise ValueError("Database not initialized")
    
    if document_date is None:
        document_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        logger.info(f"Ingesting document: {source_name}")
        
        # Get active table
        active_table = get_or_create_table(db, "active_index")

        # Chunk the document
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from {source_name}")

        records = []
        for idx, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(chunk, source_name, idx)
            embedding = embed_text(chunk)
            records.append({
                "id": chunk_id,
                "vector": embedding,
                "text": chunk,
                "metadata": {
                    "source": source_name,
                    "url": source_url,
                    "date": document_date,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "ingestion_time": datetime.now().isoformat()
                }
            })

        if records:
            # Upsert requires passing a specific key in LanceDB if updating. 
            # Sticking to append/add functionality for typical LanceDB insertions.
            active_table.add(records)

        ingested_count = len(records)
        
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
        active = get_or_create_table(db, "active_index")
        archive = get_or_create_table(db, "archive_index")
        
        return {
            "active_index": {
                "count": active.count_rows()
            },
            "archive_index": {
                "count": archive.count_rows()
            }
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return None