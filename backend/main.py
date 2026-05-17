"""
FastAPI backend for Continual RAG Agent - Banking Credit Analysis
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from datetime import datetime
import logging
from ingestion import initialize_db, ingest_document, get_or_create_table
from retriever import dual_path_retrieve, rerank_results
from evaluator import run_retention_tests, get_drift_logs
from cron_fetcher import fetch_and_ingest_new_documents
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
db = None
scheduler = None
last_fetch_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    global db, scheduler, last_fetch_time
    
    # --- STARTUP LOGIC ---
    logger.info("Starting up PolicySync...")
    
    # Initialize LanceDB
    db = initialize_db()
    logger.info("LanceDB initialized")
    
    # Initialize scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Schedule data fetcher to run every 8 hours
    scheduler.add_job(
        fetch_and_ingest_new_documents,
        "interval",
        hours=8,
        id="rbi_fetcher"
    )
    
    # Fetch initial data on startup
    logger.info("Fetching initial RBI data...")
    try:
        fetch_and_ingest_new_documents()
        last_fetch_time = datetime.now().isoformat()
        logger.info("Initial data fetched successfully")
    except Exception as e:
        logger.error(f"Error fetching initial data: {e}")
    
    logger.info("Startup complete")
    
    yield  # Application runs during this yield
    
    # --- SHUTDOWN LOGIC ---
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")


# Initialize FastAPI app with the new lifespan manager
app = FastAPI(
    title="Continual RAG Agent API",
    description="Banking credit analysis with continual learning",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    include_archive: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    timestamp: str

class IngestionRequest(BaseModel):
    document_text: str
    document_name: str
    document_url: str = ""

class StatusResponse(BaseModel):
    active_docs: int
    archive_docs: int
    last_fetch_time: str
    total_chunks: int
    status: str

class RetentionResult(BaseModel):
    question: str
    status: str
    timestamp: str
    baseline_answer: str
    current_answer: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db else "disconnected"
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Main query endpoint - retrieve and rank documents, then query LLM"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        logger.info(f"Processing query: {request.question}")
        
        # Retrieve from both indexes
        active_results = dual_path_retrieve(
            request.question,
            db,
            collection_name="active_index",
            top_k=10
        )
        
        archive_results = []
        if request.include_archive:
            archive_results = dual_path_retrieve(
                request.question,
                db,
                collection_name="archive_index",
                top_k=5
            )
        
        # Combine and rerank
        all_results = active_results + archive_results
        ranked_results = rerank_results(all_results, request.question)
        
        # Format response
        sources = [
            {
                "text": result.get("text", ""),
                "source": result.get("source", "Unknown"),
                "date": result.get("date", "Unknown"),
                "collection": result.get("collection", "unknown"),
                "score": float(result.get("score", 0.0))
            }
            for result in ranked_results[:5]
        ]
        
        # Build LLM response (placeholder for now)
        confidence = float(ranked_results[0].get("score", 0.5)) if ranked_results else 0.0
        answer = f"Based on the retrieved documents, here's the answer to your question:\n\n"
        answer += "".join([f"• {src['source']}: {src['text'][:200]}...\n" for src in sources[:3]])
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_endpoint(request: IngestionRequest):
    """Manual document ingestion endpoint"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        logger.info(f"Ingesting document: {request.document_name}")
        
        ingest_document(
            text=request.document_text,
            source_name=request.document_name,
            source_url=request.document_url,
            db=db
        )
        
        return {
            "status": "success",
            "message": f"Document '{request.document_name}' ingested successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def status_endpoint():
    """Get system status including document counts"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        active_count = get_or_create_table(db, "active_index").count_rows()
        archive_count = get_or_create_table(db, "archive_index").count_rows()
        
        return StatusResponse(
            active_docs=active_count,
            archive_docs=archive_count,
            last_fetch_time=last_fetch_time or "Never",
            total_chunks=active_count + archive_count,
            status="ready"
        )
    
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/retention")
async def retention_endpoint():
    """Get retention test results"""
    try:
        results = run_retention_tests(db)
        return {
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Retention endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drift")
async def drift_endpoint():
    """Get drift monitor data"""
    try:
        drift_data = get_drift_logs()
        return {
            "drift_logs": drift_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Drift endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fetch-now")
async def fetch_now_endpoint():
    """Manually trigger data fetching"""
    try:
        global last_fetch_time
        logger.info("Manual fetch triggered")
        fetch_and_ingest_new_documents()
        last_fetch_time = datetime.now().isoformat()
        return {
            "status": "success",
            "message": "Data fetch completed",
            "timestamp": last_fetch_time
        }
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)