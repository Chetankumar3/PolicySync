# Deployment and Running Instructions

## For GitHub Reviewers

This document provides step-by-step instructions to run PolicySync on your local machine.

## System Requirements

- **Python**: 3.9 or higher
- **Node.js**: 18.0 or higher
- **npm**: 8.0 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: 2GB for dependencies and data

## Step 1: Get Groq API Key

1. Visit https://console.groq.com/keys
2. Sign up or log in
3. Copy your API key

## Step 2: Clone Repository

```bash
git clone https://github.com/yourusername/policysync.git
cd policysync
```

## Step 3: Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

If you get any dependency conflicts, try:
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

## Step 4: Start Backend

**Windows PowerShell**:
```powershell
$env:GROQ_API_KEY = "your_groq_api_key_here"
python main.py
```

**macOS/Linux**:
```bash
export GROQ_API_KEY="your_groq_api_key_here"
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting up PolicySync...
INFO:     LanceDB initialized
INFO:     Starting background scheduler
INFO:     Fetching initial RBI data...
```

**Wait 10-20 seconds** for initial data fetch to complete.

## Step 5: Frontend Setup (New Terminal)

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
  VITE v5.0.0  ready in XXX ms

  ➜  Local:   http://localhost:5173/
```

## Step 6: Open Application

Visit: http://localhost:5173/

## Testing the System

### 1. Check Status
- Click "Ingestion Status" panel
- Should show documents from RBI sources
- Click "Fetch New Data Now" to manually trigger update

### 2. Run Query
- Click "Query" panel
- Try: "What is the minimum capital adequacy ratio?"
- System will return answer with sources

### 3. View Retention Tests
- Click "Retention Tests" panel
- Shows benchmark question results
- All should show PASS (initial baseline)

### 4. Monitor Drift
- Click "Drift Monitor" panel
- Shows confidence scores over time
- Will have minimal data on first run

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'lancedb'`

**Solution**:
```bash
pip install lancedb
```

### Issue: GROQ_API_KEY not recognized

**Solution**: Make sure to set it BEFORE running python:

```bash
# Windows
set GROQ_API_KEY=sk-xxxx

# macOS/Linux
export GROQ_API_KEY=sk-xxxx
```

### Issue: Port 8000 already in use

**Solution**:
```bash
# Find process using port 8000
# Windows
netstat -ano | findstr :8000

# macOS/Linux
lsof -i :8000

# Kill the process or use different port
python main.py --port 8001
```

### Issue: npm install fails with permission error

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Try install again
npm install
```

### Issue: `LanceDB` database is locked

**Solution**:
```bash
# Delete the database and restart
rm -rf backend/lancedb_store/

# Restart backend
python main.py
```

### Issue: Groq API returns errors

**Verify**:
1. API key is valid and not expired
2. You have credits on Groq account
3. API key is set as environment variable
4. Try test query at https://console.groq.com

## API Testing with curl

### Health Check
```bash
curl http://localhost:8000/health
```

### Status
```bash
curl http://localhost:8000/status
```

### Query Endpoint
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the repo rate?",
    "include_archive": true
  }'
```

### Fetch Now
```bash
curl -X POST http://localhost:8000/fetch-now
```

## Docker Deployment (Optional)

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Backend setup
COPY backend/requirements.txt ./backend/
RUN pip install -r backend/requirements.txt

# Copy code
COPY backend ./backend
COPY frontend ./frontend

# Frontend setup
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Expose ports
EXPOSE 8000 3000

# Start both services
WORKDIR /app
CMD ["python", "backend/main.py"]
```

### Build and Run
```bash
docker build -t policysync .
docker run -e GROQ_API_KEY=your_key -p 8000:8000 -p 3000:3000 policysync
```

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 backend.main:app
```

### Using Heroku
```bash
heroku create your-app-name
git push heroku main
heroku config:set GROQ_API_KEY=your_key
```

### Using AWS Lambda
```bash
pip install zappa
zappa init
zappa deploy production
```

## Performance Monitoring

### Logs Location
- Backend logs: stdout/stderr
- LanceDB logs: `./backend/lancedb_store/`
- Fetch logs: Check console output

### Check LanceDB Size
```bash
du -sh backend/lancedb_store/
```

## Resetting the System

### Clear All Data
```bash
rm -rf backend/lancedb_store/
rm backend/fetched_urls.json
```

### Restart Everything
```bash
# Terminal 1: Stop backend (Ctrl+C)
# Terminal 2: Stop frontend (Ctrl+C)

rm -rf backend/lancedb_store/
python backend/main.py
```

```bash
# New Terminal
npm run dev
```

## Support

For issues:
1. Check troubleshooting section above
2. Review logs in console output
3. Open GitHub issue with:
   - OS and Python version
   - Full error message
   - Steps to reproduce
