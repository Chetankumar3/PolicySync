# Continual RAG Agent - Banking Credit Analysis

A real-time Retrieval-Augmented Generation system for banking credit analysis with continual learning capabilities.

## Features

1. **Incremental Indexing** - Documents are indexed incrementally without rebuilding the entire index
2. **Dual-Path Retriever** - Queries both active and archive indexes for comprehensive context
3. **Context Re-ranker** - Ranks results by semantic similarity, recency, and conflict penalties
4. **LLM Reasoning Engine** - Groq-powered analysis with cited sources
5. **Retention Tester** - Detects catastrophic forgetting through benchmark question tracking
6. **Drift Monitor** - Tracks system confidence scores over time for degradation detection

## Project Structure

```
continual-rag-agent/
  backend/
    main.py          ← FastAPI app, all endpoints
    ingestion.py     ← chunking, embedding, indexing
    conflict.py      ← conflict detection logic
    retriever.py     ← dual-path retriever + re-ranker
    evaluator.py     ← retention tester + drift monitor
    cron_fetcher.py  ← scheduled data fetcher
    chroma_store/    ← ChromaDB persisted here
  frontend/
    src/
      App.jsx
      components/
        QueryPanel.jsx
        IngestionStatus.jsx
        EvalDashboard.jsx
        DriftMonitor.jsx
  README.md
```

## Tech Stack

- **Backend**: FastAPI + ChromaDB + LangChain + Groq API
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: Groq (llama-3.3-70b-versatile)
- **Scheduler**: APScheduler
- **Frontend**: React + Vite + Recharts
- **Data Sources**: RBI website (Notifications, Master Directions, Press Releases)

## Setup and Running

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here
python main.py
```

The backend will start on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on `http://localhost:5173`

## API Endpoints

- `GET /health` - Health check
- `POST /query` - Execute a query and retrieve cited answers
- `POST /ingest` - Manually ingest a document
- `GET /status` - Get system status
- `GET /retention` - Get retention test results
- `GET /drift` - Get drift monitor data
- `POST /fetch-now` - Manually trigger RBI data fetch

## Data Pipeline

Every 8 hours, the system:
1. Fetches the latest documents from RBI websites
2. Identifies new documents by comparing against previously indexed ones
3. Ingests new documents into the active index
4. Runs retention tests to detect catastrophic forgetting
5. Records drift samples for confidence monitoring

## Features in Detail

### Incremental Indexing
Documents are chunked, embedded, and indexed. Before ingestion, the system checks if a chunk already exists to avoid re-indexing.

### Dual-Path Retriever
- **Active Index**: Current, valid regulatory documents
- **Archive Index**: Historical or superseded documents
Both are queried for every analyst question, enabling historical context.

### Re-ranker
Scores results using: `score = semantic_similarity × recency_weight × collection_penalty`
- Active documents: 1.0 penalty
- Archive documents: 0.5 penalty
- More recent documents: higher recency weight

### Retention Tester
Runs benchmark questions periodically to ensure the system hasn't forgotten important concepts through catastrophic forgetting.

### Drift Monitor
Tracks the confidence scores of probe queries over time. Significant drops indicate system degradation.

## Future Enhancements (Days 2-4)

- Real conflict detection and automatic archival
- Conflict log visualization
- Comprehensive React UI with proper styling
- Live ingestion feed
- Detailed drift charts with Recharts
- Demo script and edge case handling

## Demo Flow

1. Show live ingestion status with real RBI data
2. Ask a regulatory question and display cited answer
3. Open conflict log showing how newer circulars override older ones
4. Show retention dashboard with benchmark test results
5. Display drift monitor showing stable confidence scores

