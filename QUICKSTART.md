# Quick Start (5 minutes)

## 1. Get API Key
Visit https://console.groq.com/keys and copy your API key

## 2. Backend (Terminal 1)
```bash
cd backend
pip install -r requirements.txt
set GROQ_API_KEY=your_api_key_here
python main.py
```

Wait for: `INFO:     Uvicorn running on http://0.0.0.0:8000`

## 3. Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

Wait for: `Local:   http://localhost:5173/`

## 4. Open Browser
Visit: **http://localhost:5173**

## Try It
1. Click "Query" panel
2. Ask: "What is the minimum capital adequacy ratio?"
3. See results with source documents from RBI

## What to Explore
- **Ingestion Status**: See active/archive document counts
- **Retention Tests**: Benchmark test results
- **Drift Monitor**: Confidence scores over time

---

For detailed documentation, see:
- `README.md` - Features and API
- `ARCHITECTURE.md` - Technical deep-dive
- `DEPLOYMENT.md` - Complete setup guide
