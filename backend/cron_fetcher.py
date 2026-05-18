"""
Scheduled data fetcher for PolicySync.

Strategy:
- On startup (DB empty): seed from local saved HTML files in backend/sources/
- Cron / fetch-now: try live fetch of RBI pages; only ingest if quality content found.
  If live fetch fails (JS-rendered), silently skip — baseline is already in DB.
"""
import requests
import hashlib
import json
import os
from datetime import datetime
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FETCHED_HASHES_FILE = "./lancedb_store/fetched_hashes.json"

# Local saved HTML files (Ctrl+S from browser)
SOURCES_DIR = "./sources"

LOCAL_HTML_SOURCES = [
    {
        "filename": "Notifications - Reserve Bank of India.html",
        "source": "RBI Notifications",
        "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx"
    },
    {
        "filename": "Press Releases - Reserve Bank of India.html",
        "source": "RBI Press Releases",
        "url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
    },
    {
        "filename": "Reserve Bank of India - Master Directions.html",
        "source": "RBI Master Directions",
        "url": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"
    },
]

# Live URLs for cron updates (only ingested if real content comes back)
RBI_LIVE_URLS = [
    {
        "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        "source": "RBI Notifications"
    },
    {
        "url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "source": "RBI Press Releases"
    },
    {
        "url": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
        "source": "RBI Master Directions"
    },
]


def load_fetched_hashes() -> set:
    if os.path.exists(FETCHED_HASHES_FILE):
        try:
            with open(FETCHED_HASHES_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_fetched_hashes(hashes: set):
    try:
        os.makedirs(os.path.dirname(FETCHED_HASHES_FILE) or ".", exist_ok=True)
        with open(FETCHED_HASHES_FILE, 'w') as f:
            json.dump(list(hashes), f, indent=2)
    except Exception as e:
        logger.error(f"Error saving fetched hashes: {e}")


def extract_text_from_html(html_content: str) -> str:
    """
    Parse HTML and extract clean readable text.
    Removes nav, header, footer, scripts, styles.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove noise tags
    for tag in soup(["nav", "header", "footer", "script", "style", "noscript"]):
        tag.decompose()

    # Try to find main content area
    content = (
        soup.find("div", class_="main-content") or
        soup.find("div", id="content") or
        soup.find("div", class_="content") or
        soup.find("article") or
        soup.find("main") or
        soup.find("body")
    )

    if not content:
        return ""

    text = content.get_text(separator="\n")
    # Clean up blank lines and whitespace
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def chunk_html_text(text: str, chunk_size: int = 2000, overlap: int = 100) -> List[str]:
    """
    Split large HTML text into overlapping chunks for ingestion.
    """
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def load_local_html_sources() -> List[Dict[str, Any]]:
    """
    Read saved HTML files from backend/sources/ and extract text.
    Returns one document per meaningful chunk of each file.
    """
    documents = []

    for source_config in LOCAL_HTML_SOURCES:
        filepath = os.path.join(SOURCES_DIR, source_config["filename"])

        if not os.path.exists(filepath):
            logger.warning(f"Local HTML file not found: {filepath}")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            text = extract_text_from_html(html_content)

            if not text or len(text) < 200:
                logger.warning(f"No usable text extracted from {filepath}")
                continue

            # Split into chunks so we don't ingest one massive blob
            chunks = chunk_html_text(text, chunk_size=2000, overlap=100)

            for i, chunk in enumerate(chunks):
                documents.append({
                    "text": chunk,
                    "source": f"{source_config['source']} (part {i+1})",
                    "url": source_config["url"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "_from_local": True
                })

            logger.info(f"Loaded '{source_config['source']}' → {len(chunks)} chunks from local HTML")

        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")

    return documents


def try_live_fetch(url: str) -> str:
    """
    Try to fetch live content from a URL.
    Returns empty string if unreachable or only nav/junk content.
    """
    try:
        response = requests.get(url, timeout=12)
        response.encoding = 'utf-8'
        text = extract_text_from_html(response.text)

        if not text or len(text) < 500:
            return ""

        lines = [l for l in text.splitlines() if l.strip()]
        avg_line_len = sum(len(l) for l in lines) / max(len(lines), 1)

        if avg_line_len < 50:
            logger.debug(f"Live fetch quality too low (avg line {avg_line_len:.0f}): {url}")
            return ""

        return text[:4000]

    except Exception as e:
        logger.debug(f"Live fetch failed for {url}: {e}")
        return ""


def identify_new_documents(fetched_hashes: set, documents: List[Dict]) -> List[Dict]:
    """Identify new documents by content hash"""
    new_docs = []
    for doc in documents:
        content_hash = hashlib.md5(doc.get("text", "").encode()).hexdigest()
        if content_hash not in fetched_hashes:
            doc["_hash"] = content_hash
            new_docs.append(doc)
        else:
            logger.debug(f"Already ingested: {doc.get('source', '')[:60]}")
    return new_docs


def seed_baseline_documents(db):
    """
    Called once on startup when DB is empty.
    Ingests all local HTML files from backend/sources/.
    """
    from ingestion import ingest_document

    logger.info("Seeding DB from local HTML files in backend/sources/...")
    documents = load_local_html_sources()

    if not documents:
        logger.error(
            "No local HTML files found in backend/sources/. "
            "Please save the RBI pages (Ctrl+S in browser) into backend/sources/."
        )
        return

    fetched_hashes = load_fetched_hashes()
    seeded = 0

    for doc in documents:
        try:
            ingest_document(
                text=doc["text"],
                source_name=doc["source"],
                source_url=doc["url"],
                db=db,
                document_date=doc["date"]
            )
            fetched_hashes.add(doc.get("_hash") or hashlib.md5(doc["text"].encode()).hexdigest())
            seeded += 1
        except Exception as e:
            logger.error(f"Error seeding {doc.get('source')}: {e}")

    save_fetched_hashes(fetched_hashes)
    logger.info(f"Seeding complete. Ingested {seeded} chunks from local HTML files.")


def fetch_and_ingest_new_documents():
    """
    Cron job / fetch-now: try live RBI pages and ingest only genuinely new content.
    If live fetch fails (JS-rendered), silently skips — baseline is already in DB.
    """
    try:
        logger.info("Starting fetch and ingest job...")

        from ingestion import ingest_document, initialize_db
        db = initialize_db()
        fetched_hashes = load_fetched_hashes()

        new_documents = []

        for live_config in RBI_LIVE_URLS:
            url = live_config["url"]
            source = live_config["source"]

            logger.info(f"Trying live fetch: {source}")
            text = try_live_fetch(url)

            if not text:
                logger.info(f"  No quality content from live fetch, skipping: {source}")
                continue

            chunks = chunk_html_text(text, chunk_size=2000, overlap=100)
            for i, chunk in enumerate(chunks):
                new_documents.append({
                    "text": chunk,
                    "source": f"{source} (live, part {i+1})",
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })

        truly_new = identify_new_documents(fetched_hashes, new_documents)
        logger.info(f"Found {len(truly_new)} new chunks from live fetch")

        ingest_count = 0
        for doc in truly_new:
            try:
                ingest_document(
                    text=doc["text"],
                    source_name=doc["source"],
                    source_url=doc["url"],
                    db=db,
                    document_date=doc["date"]
                )
                fetched_hashes.add(doc["_hash"])
                ingest_count += 1
            except Exception as e:
                logger.error(f"Error ingesting {doc.get('source')}: {e}")

        save_fetched_hashes(fetched_hashes)
        logger.info(f"Fetch job complete. Ingested {ingest_count} new chunks.")

        return {
            "timestamp": datetime.now().isoformat(),
            "live_chunks_found": len(new_documents),
            "new_chunks_ingested": ingest_count
        }

    except Exception as e:
        logger.error(f"Error in fetch_and_ingest_new_documents: {e}")
        raise


# Keep fetch_all_documents for test_pipeline.py compatibility
def fetch_all_documents() -> List[Dict[str, str]]:
    return load_local_html_sources()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_and_ingest_new_documents()