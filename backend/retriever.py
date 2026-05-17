"""
Dual-path retriever and re-ranker: retrieve from active and archive indexes,
then rank results by semantic similarity, recency, and conflict penalties
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
from ingestion import get_or_create_table

logger = logging.getLogger(__name__)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def dual_path_retrieve(
    query: str,
    db,
    collection_name: str = "active_index",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve documents from a specific collection (active or archive)
    Returns results with source collection metadata
    """
    try:
        table = get_or_create_table(db, collection_name)
        
        # Embed the query
        query_embedding = embedding_model.encode(query, convert_to_numpy=False)
        query_embedding = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding)
        
        # Query LanceDB
        results = table.search(query_embedding).limit(top_k).to_list()
        
        # Format results
        formatted_results = []
        if results:
            for item in results:
                metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
                formatted_results.append({
                    "id": item.get("id", "") if isinstance(item, dict) else "",
                    "text": item.get("text", "") if isinstance(item, dict) else "",
                    "source": metadata.get("source", "Unknown"),
                    "url": metadata.get("url", ""),
                    "date": metadata.get("date", ""),
                    "collection": collection_name,
                    "score": float(item.get("score", 0.0)) if isinstance(item, dict) else 0.0,
                    "metadata": metadata
                })
        
        logger.info(f"Retrieved {len(formatted_results)} results from {collection_name}")
        return formatted_results
    
    except Exception as e:
        logger.error(f"Error retrieving from {collection_name}: {e}")
        return []

def calculate_recency_weight(date_str: str) -> float:
    """
    Calculate recency weight: more recent documents get higher weight (0.5-1.0)
    """
    try:
        if not date_str or date_str == "Unknown":
            return 0.5
        
        doc_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_old = (datetime.now() - doc_date).days
        
        # Decay: 0 days old = 1.0, 365 days old = 0.5, 730+ days old = 0.3
        if days_old <= 365:
            weight = 1.0 - (days_old / 365) * 0.5
        elif days_old <= 730:
            weight = 0.5 - ((days_old - 365) / 365) * 0.2
        else:
            weight = 0.3
        
        return max(0.3, min(1.0, weight))
    except:
        return 0.5

def rerank_results(
    results: List[Dict[str, Any]],
    query: str,
    active_penalty: float = 1.0,
    archive_penalty: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Re-rank retrieved results using:
    - Semantic similarity score
    - Recency weight
    - Collection penalty (active = 1.0, archive = 0.5)
    
    Formula: final_score = similarity * recency_weight * collection_penalty
    """
    try:
        if not results:
            return []
        
        # Calculate final scores
        for result in results:
            similarity = float(result.get("score", 0.5))
            recency = calculate_recency_weight(result.get("date", ""))
            
            # Apply collection penalty
            if result.get("collection") == "active_index":
                penalty = active_penalty
            else:
                penalty = archive_penalty
            
            # Final score
            final_score = similarity * recency * penalty
            result["final_score"] = final_score
        
        # Sort by final score descending
        ranked = sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)
        
        logger.info(f"Re-ranked {len(ranked)} results")
        return ranked
    
    except Exception as e:
        logger.error(f"Error re-ranking results: {e}")
        return results

def retrieve_and_rank(
    query: str,
    db,
    top_k_per_collection: int = 10,
    include_archive: bool = True
) -> List[Dict[str, Any]]:
    """
    Main retrieval function: query both indexes and return ranked results
    """
    try:
        # Retrieve from active index
        active_results = dual_path_retrieve(
            query,
            db,
            collection_name="active_index",
            top_k=top_k_per_collection
        )
        
        # Retrieve from archive index
        archive_results = []
        if include_archive:
            archive_results = dual_path_retrieve(
                query,
                db,
                collection_name="archive_index",
                top_k=top_k_per_collection // 2  # Take fewer from archive
            )
        
        # Combine and re-rank
        all_results = active_results + archive_results
        ranked_results = rerank_results(all_results, query)
        
        return ranked_results
    
    except Exception as e:
        logger.error(f"Error in retrieve_and_rank: {e}")
        return []
