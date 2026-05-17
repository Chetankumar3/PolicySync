"""
Scheduled data fetcher: scrapes RBI website for new regulatory documents
Runs every 8 hours and only ingests new documents
"""
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# RBI data sources
RBI_URLS = {
    "notifications": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
    "master_directions": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
    "press_releases": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
}

FETCHED_URLS_FILE = "./lancedb_store/fetched_urls.json"

def load_fetched_urls() -> Dict[str, set]:
    """Load set of already-fetched URLs from JSON file"""
    if os.path.exists(FETCHED_URLS_FILE):
        try:
            with open(FETCHED_URLS_FILE, 'r') as f:
                data = json.load(f)
                return {k: set(v) for k, v in data.items()}
        except:
            return {source: set() for source in RBI_URLS.keys()}
    return {source: set() for source in RBI_URLS.keys()}

def save_fetched_urls(fetched_urls: Dict[str, set]):
    """Save set of fetched URLs to JSON file"""
    try:
        os.makedirs(os.path.dirname(FETCHED_URLS_FILE) or ".", exist_ok=True)
        with open(FETCHED_URLS_FILE, 'w') as f:
            data = {k: list(v) for k, v in fetched_urls.items()}
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving fetched URLs: {e}")

def fetch_rbi_notifications() -> List[Dict[str, str]]:
    """Fetch RBI notifications"""
    documents = []
    try:
        logger.info("Fetching RBI Notifications...")
        response = requests.get(RBI_URLS["notifications"], timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content from the page
        main_content = soup.find("div", class_="main-content") or soup.find("div", id="content")
        if main_content:
            text = main_content.get_text(separator="\n")
            if text.strip():
                documents.append({
                    "title": "RBI Notifications",
                    "text": text[:2000],  # Take first 2000 chars
                    "url": RBI_URLS["notifications"],
                    "source": "RBI Notifications",
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
        
        logger.info(f"Extracted RBI Notifications content")
    except Exception as e:
        logger.error(f"Error fetching RBI Notifications: {e}")
    
    return documents

def fetch_rbi_master_directions() -> List[Dict[str, str]]:
    """Fetch RBI Master Directions"""
    documents = []
    try:
        logger.info("Fetching RBI Master Directions...")
        response = requests.get(RBI_URLS["master_directions"], timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        main_content = soup.find("div", class_="main-content") or soup.find("div", id="content")
        if main_content:
            text = main_content.get_text(separator="\n")
            if text.strip():
                documents.append({
                    "title": "RBI Master Directions",
                    "text": text[:2000],
                    "url": RBI_URLS["master_directions"],
                    "source": "RBI Master Directions",
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
        
        logger.info(f"Extracted RBI Master Directions content")
    except Exception as e:
        logger.error(f"Error fetching RBI Master Directions: {e}")
    
    return documents

def fetch_rbi_press_releases() -> List[Dict[str, str]]:
    """Fetch RBI Press Releases"""
    documents = []
    try:
        logger.info("Fetching RBI Press Releases...")
        response = requests.get(RBI_URLS["press_releases"], timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        main_content = soup.find("div", class_="main-content") or soup.find("div", id="content")
        if main_content:
            text = main_content.get_text(separator="\n")
            if text.strip():
                documents.append({
                    "title": "RBI Press Releases",
                    "text": text[:2000],
                    "url": RBI_URLS["press_releases"],
                    "source": "RBI Press Releases",
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
        
        logger.info(f"Extracted RBI Press Releases content")
    except Exception as e:
        logger.error(f"Error fetching RBI Press Releases: {e}")
    
    return documents

def fetch_all_documents() -> List[Dict[str, str]]:
    """Fetch documents from all RBI sources"""
    all_docs = []
    all_docs.extend(fetch_rbi_notifications())
    all_docs.extend(fetch_rbi_master_directions())
    all_docs.extend(fetch_rbi_press_releases())
    return all_docs

def identify_new_documents(
    fetched_urls: Dict[str, set],
    documents: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Identify new documents by comparing against previously fetched URLs"""
    new_documents = []
    
    for doc in documents:
        url = doc.get("url", "")
        source = doc.get("source", "unknown")
        
        # Check if URL was already fetched
        if url not in fetched_urls.get(source, set()):
            new_documents.append(doc)
            fetched_urls[source].add(url)
        else:
            logger.debug(f"Document already fetched: {source} - {url}")
    
    return new_documents

def fetch_and_ingest_new_documents():
    """
    Main cron job: fetch new documents, identify new ones, and ingest them
    """
    try:
        logger.info("Starting fetch and ingest job...")
        
        # Import here to avoid circular imports
        from ingestion import ingest_document, initialize_db
        
        # Initialize DB
        db = initialize_db()
        
        # Load previously fetched URLs
        fetched_urls = load_fetched_urls()
        
        # Fetch documents from all sources
        all_documents = fetch_all_documents()
        logger.info(f"Fetched {len(all_documents)} documents from RBI sources")
        
        # Identify new documents
        new_documents = identify_new_documents(fetched_urls, all_documents)
        logger.info(f"Found {len(new_documents)} new documents to ingest")
        
        # Ingest new documents
        ingest_count = 0
        for doc in new_documents:
            try:
                ingest_document(
                    text=doc.get("text", ""),
                    source_name=doc.get("source", "Unknown"),
                    source_url=doc.get("url", ""),
                    db=db,
                    document_date=doc.get("date", datetime.now().strftime("%Y-%m-%d"))
                )
                ingest_count += 1
            except Exception as e:
                logger.error(f"Error ingesting {doc.get('source')}: {e}")
        
        # Save updated fetched URLs
        save_fetched_urls(fetched_urls)
        
        logger.info(f"Fetch and ingest job completed. Ingested {ingest_count} documents")
        
        # Store fetch metadata
        fetch_log = {
            "timestamp": datetime.now().isoformat(),
            "documents_fetched": len(all_documents),
            "new_documents": len(new_documents),
            "documents_ingested": ingest_count
        }
        
        return fetch_log
    
    except Exception as e:
        logger.error(f"Error in fetch_and_ingest_new_documents: {e}")
        raise

if __name__ == "__main__":
    # Test the fetcher
    logging.basicConfig(level=logging.INFO)
    fetch_and_ingest_new_documents()
