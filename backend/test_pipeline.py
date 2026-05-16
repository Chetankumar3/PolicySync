#!/usr/bin/env python
"""Quick test of the fetcher and ingestion pipeline"""
import sys
import logging
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from cron_fetcher import fetch_all_documents
    from ingestion import initialize_db, ingest_document
    
    logger.info("Testing RBI data fetcher...")
    docs = fetch_all_documents()
    logger.info(f"Fetched {len(docs)} documents from RBI")
    
    for doc in docs:
        logger.info(f"  - {doc.get('source')}: {doc.get('title', 'N/A')[:60]}")
    
    if docs:
        logger.info("\nInitializing ChromaDB...")
        db = initialize_db()
        
        logger.info("Ingesting first document...")
        result = ingest_document(
            text=docs[0].get('text', ''),
            source_name=docs[0].get('source', 'Unknown'),
            source_url=docs[0].get('url', ''),
            db=db,
            document_date=docs[0].get('date', None)
        )
        logger.info(f"Ingestion result: {result}")
        
        from ingestion import get_collection_stats
        stats = get_collection_stats(db)
        logger.info(f"Collection stats: {stats}")
    
    logger.info("\nTest completed successfully!")
    
except Exception as e:
    logger.error(f"Test failed: {e}", exc_info=True)
