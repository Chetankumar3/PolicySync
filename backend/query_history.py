"""
Query history tracking using SQLite
Stores user queries, answers, confidence scores, and sources
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

DB_PATH = "./lancedb_store/query_history.db"


def init_query_history_db():
    """
    Initialize the SQLite database for query history.
    Creates the query_history table if it doesn't exist.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT,
                confidence REAL,
                sources_json TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Query history database initialized")
        
    except Exception as e:
        logger.error(f"Error initializing query history database: {e}")
        raise


def save_query(question: str, answer: str, confidence: float, sources: List[Dict[str, Any]]):
    """
    Save a query to the history database.
    
    Args:
        question: The user's question
        answer: The generated answer
        confidence: The confidence score of the retrieval
        sources: List of source dictionaries (will be JSON-serialized)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Serialize sources to JSON
        sources_json = json.dumps(sources)
        
        cursor.execute(
            """
            INSERT INTO query_history (question, answer, confidence, sources_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (question, answer, confidence, sources_json, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Saved query to history: {question[:50]}...")
        
    except Exception as e:
        logger.error(f"Error saving query to history: {e}")


def get_query_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve the last N queries from the history.
    
    Args:
        limit: Maximum number of queries to return (default: 50)
    
    Returns:
        List of query dictionaries, ordered by most recent first
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, question, answer, confidence, sources_json, timestamp
            FROM query_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to dictionaries
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "confidence": row[3],
                "sources": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            })
        
        logger.info(f"Retrieved {len(history)} queries from history")
        return history
        
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        return []


def clear_query_history():
    """
    Delete all rows from the query history table.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM query_history")
        
        conn.commit()
        conn.close()
        logger.info("Cleared query history")
        
    except Exception as e:
        logger.error(f"Error clearing query history: {e}")
        raise
