# PolicySync - Banking Credit Analysis

A real-time Retrieval-Augmented Generation system for banking credit analysis with continual learning capabilities. This system addresses six critical failure modes in production RAG systems through incremental indexing, dual-path retrieval, intelligent re-ranking, retention testing, and drift monitoring.

## 🎯 Core Features

1. **Incremental Indexing** - Documents are indexed incrementally without rebuilding entire index
   - Solves: Computational explosion on index updates
   - Implementation: [ingestion.py](backend/ingestion.py)

2. **Dual-Path Retriever** - Queries both active and archive indexes
   - Solves: Loss of historical context
   - Implementation: [retriever.py](backend/retriever.py)

3. **Context Re-ranker** - Intelligent ranking using similarity + recency + conflict penalties
   - Solves: Outdated documents ranking above current ones
   - Formula: `score = similarity × recency_weight × collection_penalty`

4. **LLM Reasoning Engine** - Groq-powered analysis with cited sources
   - Solves: Hallucination and lack of attribution
   - Implementation: [main.py](backend/main.py) - `/query` endpoint

5. **Retention Tester** - Benchmark questions to detect catastrophic forgetting
   - Solves: Silent knowledge loss from new ingestion
   - Implementation: [evaluator.py](backend/evaluator.py)

6. **Drift Monitor** - Tracks confidence scores over time
   - Solves: Undetected system degradation
   - Implementation: [evaluator.py](backend/evaluator.py)

## 📁 Project Structure

```
policysync/
├── backend/
│   ├── main.py              ← FastAPI app with 7 endpoints
│   ├── ingestion.py         ← Chunking, embedding, indexing
│   ├── retriever.py         ← Dual-path retriever + re-ranker
│   ├── evaluator.py         ← Retention tester + drift monitor
│   ├── cron_fetcher.py      ← Scheduled RBI data fetcher
│   ├── conflict.py          ← Conflict detection (day 2+)
│   ├── requirements.txt     ← Python dependencies
│   ├── test_pipeline.py     ← Integration test
│   └── lancedb_store/        ← Persistent LanceDB storage
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── QueryPanel.jsx
│   │   │   ├── IngestionStatus.jsx
│   │   │   ├── EvalDashboard.jsx
│   │   │   └── DriftMonitor.jsx
│   │   └── styles/
│   │       ├── QueryPanel.css
│   │       ├── IngestionStatus.css
│   │       ├── EvalDashboard.css
│   │       └── DriftMonitor.css
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── README.md
├── .gitignore
├── .env.example
├── setup.bat                ← Windows setup script
└── run.sh                   ← Unix/Mac setup script
```

## 🛠️ Tech Stack

- **Backend**: FastAPI 0.104 + LanceDB + APScheduler 3.10.4
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) - runs locally
- **Vector DB**: LanceDB with persistent storage (active_index + archive_index)
- **LLM**: Groq API (llama-3.3-70b-versatile)
- **Frontend**: React 18 + Vite + Recharts
- **Data Sources**: RBI website (real-time scraping)

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Groq API key (get free at https://console.groq.com)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/policysync.git
cd policysync
```

2. **Set up Groq API key**
```bash
# Windows
set GROQ_API_KEY=your_groq_api_key_here

# macOS/Linux
export GROQ_API_KEY=your_groq_api_key_here
```

3. **Backend Setup**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend will start on `http://localhost:8000` and:
- Initialize LanceDB with two tables (active_index, archive_index)
- Start APScheduler to fetch RBI data every 8 hours
- Fetch initial RBI data immediately on startup

4. **Frontend Setup (in a new terminal)**
```bash
cd frontend
npm install
npm run dev
```

The frontend will start on `http://localhost:5173`

### One-Command Setup (Windows)
```bash
setup.bat
```

### One-Command Setup (macOS/Linux)
```bash
bash run.sh
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check and connection status |
| `POST` | `/query` | Query the system with a question |
| `POST` | `/ingest` | Manually ingest a document |
| `GET` | `/status` | Get ingestion stats (active/archive counts) |
| `GET` | `/retention` | Get retention test results |
| `GET` | `/drift` | Get drift monitor logs |
| `POST` | `/fetch-now` | Trigger immediate RBI data fetch |

### Example Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the minimum capital adequacy ratio?",
    "include_archive": true
  }'
```

Response includes:
- Cited answer from LLM
- Source documents with dates and collections
- Confidence scores
- Retrieved from both active and archive indexes

## 🎓 How Each Feature Works

### Incremental Indexing
- New documents are chunked (512 chars, 50 char overlap)
- Each chunk gets a unique ID based on content hash
- Before insertion, system checks if chunk already exists
- Skips duplicates, only inserts new content
- **Result**: Scales to millions of updates without rebuilding

### Dual-Path Retriever
```
Query Input
    ↓
├─→ Query Active Index (current regulations)
│      ↓
│      (Returns: current rules, recent circulars)
│
└─→ Query Archive Index (historical rules)
       ↓
       (Returns: superseded rules, old versions)
    ↓
Combined Results with source tags
    ↓
Re-ranker (sorts by relevance + recency)
    ↓
Top 5 to LLM for reasoning
```

### Context Re-Ranker
Re-ranks all retrieved documents using:
```
final_score = semantic_similarity × recency_weight × collection_penalty

Where:
- semantic_similarity = cosine distance normalized
- recency_weight = 1.0 for today, decays to 0.3 for 730+ days
- collection_penalty = 1.0 for active, 0.5 for archive
```

### Retention Tester
1. **Setup Phase**: Defines 5-8 benchmark questions (e.g., "What is minimum CAR?")
2. **Baseline**: Stores baseline answer for each question
3. **Every Fetch**: Re-runs all benchmarks after new data ingestion
4. **Comparison**: Sends baseline + current answer to LLM to judge consistency
5. **Log**: Stores results with timestamp
6. **UI**: Shows pass/fail over time

**Why It Matters**: Without retention testing, new data can silently break old answers.

### Drift Monitor
1. **Probe Queries**: Fixed set of 5 standard questions
2. **Every Fetch**: Records top result's confidence score for each probe
3. **Logging**: Stores scores with timestamps to drift_log.json
4. **Visualization**: UI shows confidence as line chart over time
5. **Alert**: Significant drops indicate system degradation

## 📊 Data Pipeline

```
┌─────────────────────────────────────┐
│   RBI Websites (Every 8 Hours)      │
│  - Notifications                    │
│  - Master Directions                │
│  - Press Releases                   │
└──────────────────┬──────────────────┘
                   ↓
        ┌──────────────────────┐
        │  Fetch & Scrape      │
        │  (BeautifulSoup)     │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │ Compare with         │
        │ fetched_urls.json    │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │ New Docs Only        │
        │ ✗ Skip duplicates    │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │ Chunking & Embedding │
        │ (all-MiniLM-L6-v2)   │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │ Upsert to            │
        │ active_index         │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │ Run Retention Tests  │
        │ & Record Drift       │
        └──────────────────────┘
```

## 🎯 Use Case: Banking Analyst Assistant

1. **Analyst asks**: "What's the current repo rate and how does it compare historically?"
2. **System**:
   - Queries active_index → finds "Repo rate: 6.5% (May 2026)"
   - Queries archive_index → finds "Repo rate: 4.0% (May 2024)"
   - Re-ranks by recency → current floats to top
   - Sends to Groq with system prompt emphasizing dates and sources
3. **Groq returns**: "Current repo rate is 6.5% as of May 2026 (RBI Notification XYZ). Historically in May 2024 it was 4.0% (RBI Notification ABC). The 2.5% increase reflects RBI's tightening cycle."
4. **Analyst sees**:
   - Answer with proper citations
   - Both current and historical documents listed
   - Confidence score (0.87)
   - Sources with dates and relevance scores

## 📈 Retention Dashboard Example

| Question | Status | Last Tested | Consistency |
|----------|--------|-------------|-------------|
| What is minimum CAR? | ✅ PASS | 2026-05-16 | 92% |
| What is repo rate? | ✅ PASS | 2026-05-16 | 88% |
| PSL guidelines? | ✅ PASS | 2026-05-16 | 85% |
| FDI limits? | ⚠️ FAIL | 2026-05-16 | 42% |
| KYC requirements? | ✅ PASS | 2026-05-16 | 90% |

A FAIL means the system gave a contradictory answer for the same question after new data was ingested.

## 🔮 What Happens Day 2-4 (Polish Phase)

### Day 2: Conflict Detection
- When new chunk is added, check active_index for contradictions
- If conflict found (>0.8 similarity), call Groq to judge
- If confirmed contradiction, move old chunk to archive
- Add "Conflict Log" UI showing recent conflicts side-by-side

### Day 3: UI Polish
- Add sidebar navigation between panels
- Style as professional banking tool
- Add live ingestion feed
- Recharts line graph for drift monitor
- Color-coded retention results

### Day 4: Demo & Edge Cases
- Handle network timeouts gracefully
- Retry logic for Groq API
- Better error messages in UI
- Demo script for professors

