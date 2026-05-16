# Continual RAG Agent - Technical Architecture

## System Overview

The Continual RAG Agent is a production-ready system that addresses critical failure modes in traditional RAG systems through a multi-layered architecture combining incremental indexing, dual-path retrieval, intelligent re-ranking, and continuous monitoring.

## Architectural Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE (React/Vite)                │
│  ┌─────────────────┬──────────────────┬──────────┬──────────────┐
│  │ Query Panel     │ Ingestion Status │ Eval     │ Drift        │
│  │                 │                  │ Dashboard│ Monitor      │
│  └────────┬────────┴────────┬─────────┴─────┬────┴────────┬─────┘
└───────────┼──────────────────┼────────────────┼─────────────┼─────┐
            │ HTTP/JSON        │                │             │
┌───────────▼──────────────────▼────────────────▼─────────────▼─────┐
│                      FastAPI Backend (main.py)                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 7 Endpoints: /query, /ingest, /status, /retention, /drift   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────┬──────────────────┬────────────────┬──────────────────┐
            │                  │                │
    ┌───────▼────────┐ ┌──────▼──────┐ ┌──────▼──────────┐
    │   Retriever    │ │  Ingestion  │ │   Evaluator    │
    │ (retriever.py) │ │(ingestion.py)│ │(evaluator.py)  │
    └───────┬────────┘ └──────┬──────┘ └──────┬──────────┘
            │                 │                │
            │ ┌───────────────┼────────────────┤
            │ │               │                │
    ┌───────▼─────────────────▼────────────────▼─────┐
    │    ChromaDB Vector Database                    │
    │  ┌──────────────────┬──────────────────────┐   │
    │  │  active_index    │   archive_index      │   │
    │  │  (current docs)  │   (historical docs)  │   │
    │  └──────────────────┴──────────────────────┘   │
    │  Persistent Storage: ./chroma_store/          │
    └────────────────────────────────────────────────┘
            │                 │
            │                 └─ Chunked documents with metadata
            │
    ┌───────▼──────────────────────────┐
    │  Scheduled Data Fetcher          │
    │  (cron_fetcher.py, APScheduler)  │
    └───────┬──────────────────────────┘
            │ Every 8 hours
            │
    ┌───────▼──────────────────────────┐
    │  RBI Websites (Real Data)         │
    │  - Notifications                  │
    │  - Master Directions              │
    │  - Press Releases                 │
    └────────────────────────────────────┘
```

## Core Components

### 1. Data Ingestion Pipeline (`ingestion.py`)

**Responsibility**: Transform raw documents into indexed chunks

**Process**:
```python
Raw Document (text)
    ↓
Chunking (512 chars, 50-char overlap)
    ↓
Embedding (all-MiniLM-L6-v2)
    ↓
Duplicate Check (hash-based ID)
    ↓
Upsert to ChromaDB active_index
    ↓
Store Metadata (source, date, URL)
```

**Key Functions**:
- `chunk_text()`: Overlapping sliding window chunking
- `embed_text()`: Local embedding using sentence-transformers
- `ingest_document()`: Main ingestion orchestration
- `generate_chunk_id()`: MD5 hash of (source, index, text_prefix)

**Why It's Better**:
- Avoid re-indexing: Chunk IDs are deterministic, duplicate checks prevent redundant embeddings
- Metadata tracking: Every chunk knows its source, date, and ingestion time
- Batch optimization: Could be extended to batch embedding/indexing

### 2. Dual-Path Retriever (`retriever.py`)

**Responsibility**: Search both active and archive indexes in parallel

**Architecture**:
```
Query Input
    ↓
Embed Query (same model as indexing)
    ↓
Parallel Search:
    ├─ Active Index:   Find top-K current documents
    └─ Archive Index:  Find top-K/2 historical documents
    ↓
Format Results with collection tags
    ↓
Pass to Re-ranker
```

**Key Functions**:
- `dual_path_retrieve()`: Query single collection
- `calculate_recency_weight()`: Exponential decay based on document age
- `rerank_results()`: Apply scoring formula

**Recency Weight Formula**:
```
Days Old  | Weight
----------|--------
0         | 1.0 (today)
1-365     | 1.0 - (days/365)*0.5
366-730   | 0.5 - ((days-365)/365)*0.2
730+      | 0.3 (minimum)
```

**Re-ranking Score**:
```
final_score = similarity_score × recency_weight × collection_penalty

Where:
- similarity_score: 1 - (distance/2), normalized to [0,1]
- recency_weight: decaying function of document age
- collection_penalty: 1.0 for active, 0.5 for archive
```

### 3. Scheduled Data Fetcher (`cron_fetcher.py`)

**Responsibility**: Continuously pull new RBI documents

**Data Sources**:
1. RBI Notifications: `https://www.rbi.org.in/Scripts/NotificationUser.aspx`
2. Master Directions: `https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx`
3. Press Releases: `https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx`

**Process**:
```
Fetch (requests)
    ↓
Parse (BeautifulSoup)
    ↓
Extract Titles, Dates, Text
    ↓
Compare against fetched_urls.json
    ↓
Identify New Documents Only
    ↓
Send to Ingestion Pipeline
    ↓
Update fetched_urls.json
```

**Key Innovation**:
- `fetched_urls.json` prevents duplicate ingestion
- Only new documents are processed
- Scales from dozens to thousands of daily documents

**APScheduler Integration**:
```python
scheduler = BackgroundScheduler()
scheduler.add_job(
    fetch_and_ingest_new_documents,
    "interval",
    hours=8,
    id="rbi_fetcher"
)
```

### 4. Evaluator - Retention Testing (`evaluator.py`)

**Problem It Solves**: Catastrophic Forgetting

Catastrophic forgetting occurs when a neural system (or RAG system) loses previous knowledge after learning new information. Without detection, this fails silently.

**Solution**:
```
Define Benchmark Questions (e.g., "What is minimum CAR?")
    ↓
Store Baseline Answers (known correct answers)
    ↓
After Each Fetch:
    ├─ Re-run all benchmarks
    ├─ Get new answers
    ├─ Send to Groq: "Are these consistent?"
    └─ Groq returns: YES or NO
    ↓
Store Results: {question, status, timestamp, answers}
    ↓
UI Dashboard shows PASS/FAIL over time
```

**Benchmark Questions** (5-8 for banking):
- "What is the minimum capital adequacy ratio for scheduled commercial banks?"
- "What are the main regulatory guidelines for KYC?"
- "What is the RBI's policy on foreign direct investment?"
- "What are the guidelines for priority sector lending?"
- "What is the repo rate and how does it affect the economy?"

**Consistency Scoring**:
Currently uses keyword overlap (Jaccard similarity > 0.5). Can be upgraded to full Groq LLM comparison for production.

### 5. Drift Monitor (`evaluator.py`)

**Problem It Solves**: System Degradation Goes Unnoticed

Production ML systems degrade silently. Confidence scores dropping indicates that the retriever is finding less relevant documents.

**Solution**:
```
Define Probe Queries (5 fixed, stable questions)
    ↓
After Each Fetch:
    ├─ Re-run each probe query
    ├─ Record top result's similarity score
    └─ Log: {timestamp, query, confidence}
    ↓
Visualize as Line Chart Over Time
    ↓
Significant drops trigger alerts
```

**Probe Queries**:
- "What is the current repo rate?"
- "What is the CRR for banks?"
- "What are the guidelines for priority sector lending?"
- "What is the minimum capital adequacy ratio?"
- "What are the RBI guidelines for digital banking?"

**Drift Detection Logic**:
- If max confidence in last 10 samples drops >30%, system is drifting
- Indicates distribution shift or relevance degradation
- Aligns with KL divergence concept in production ML

### 6. FastAPI Backend (`main.py`)

**Endpoints**:

```python
GET /health
├─ Status: 200 if system ready
└─ Returns: {status, timestamp, database}

POST /query
├─ Input: {question, include_archive}
├─ Process: Retrieve → Rerank → Format
└─ Returns: {answer, sources, confidence, timestamp}

POST /ingest
├─ Input: {document_text, document_name, document_url}
├─ Process: Chunk → Embed → Upsert
└─ Returns: {status, chunks_created, chunks_ingested}

GET /status
├─ Query: Both collections
└─ Returns: {active_docs, archive_docs, total_chunks, status}

GET /retention
├─ Process: Run all benchmarks or return log
└─ Returns: [{question, status, consistency_score}]

GET /drift
├─ Query: drift_log.json
└─ Returns: [{timestamp, queries: [{query, confidence}]}]

POST /fetch-now
├─ Trigger: Immediate RBI fetch (for demo/testing)
└─ Returns: {status, documents_fetched, timestamp}
```

**CORS Configuration**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Data Structures

### ChromaDB Collections

**active_index**:
```json
{
  "ids": ["md5_hash_1", "md5_hash_2"],
  "documents": ["chunk text", "chunk text"],
  "embeddings": [[0.1, 0.2, ...], [...]],
  "metadatas": [
    {
      "source": "RBI Notifications",
      "date": "2026-05-16",
      "url": "https://rbi.org.in/...",
      "chunk_index": 0,
      "total_chunks": 5,
      "ingestion_time": "2026-05-16T10:30:00Z"
    }
  ]
}
```

**archive_index**:
Same structure, but contains superseded or historical documents.

### Logs

**fetched_urls.json** (tracks ingested URLs):
```json
{
  "notifications": ["url1", "url2"],
  "master_directions": ["url3"],
  "press_releases": ["url4"]
}
```

**retention_log.json** (benchmark results):
```json
[
  {
    "question": "What is minimum CAR?",
    "status": "pass",
    "timestamp": "2026-05-16T10:30:00Z",
    "baseline_answer": "...",
    "current_answer": "...",
    "consistency_score": 0.92
  }
]
```

**drift_log.json** (confidence tracking):
```json
[
  {
    "timestamp": "2026-05-16T10:30:00Z",
    "queries": [
      {
        "query": "What is repo rate?",
        "top_source": "RBI Notification",
        "confidence": 0.87
      }
    ]
  }
]
```

## Scaling Considerations

### For 1M Documents
- Batch embedding: Process chunks in batches of 32-64
- Parallel ingestion: Thread pool for concurrent upserts
- Archive strategy: Move docs >1 year old to archive

### For 100 Concurrent Users
- Connection pooling for ChromaDB
- Query caching for retention/drift endpoints
- Load balance multiple backend instances

### For Real-Time Ingestion
- Message queue (Kafka/RabbitMQ) for document jobs
- Async upserts to ChromaDB
- Webhook notifications when conflicts detected

## Security Considerations

- **Groq API Key**: Store as environment variable, never in code
- **Data Privacy**: Documents contain regulatory (public) information
- **Input Validation**: Sanitize user questions to prevent injection
- **Rate Limiting**: Add to FastAPI for production

## Error Handling

**Graceful Degradation**:
```python
try:
    results = dual_path_retrieve(query, db)
except Exception as e:
    logger.error(f"Retrieval failed: {e}")
    results = []  # Empty results better than error
    # Return degraded response to UI
```

**Network Resilience**:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_rbi_data():
    response = requests.get(url, timeout=10)
    return response.text
```

## Future Enhancements

### Phase 2: Conflict Resolution
- Real-time conflict detection during ingestion
- LLM-powered contradiction detection
- Automatic archival of contradicted chunks
- Conflict log visualization

### Phase 3: Advanced Re-ranking
- Learning-to-rank model trained on click-through data
- BM25 hybrid search combining lexical + semantic
- Domain-specific similarity weights

### Phase 4: Multi-Turn Conversation
- Store conversation context
- Progressive refinement of queries
- Cross-reference resolution ("it" → "capital adequacy ratio")

## References & Concepts

- **Catastrophic Forgetting**: Rusu et al., "Continual Learning Through Synaptic Intelligence"
- **Retrieval-Augmented Generation**: Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- **Distribution Shift**: Moreno-Torres et al., "A unifying view on dataset shift in classification"
- **ChromaDB Architecture**: Open-source vector database with persistence
- **Sentence Transformers**: Sentence-BERT for semantic search
