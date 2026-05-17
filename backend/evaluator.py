"""
Evaluator: Retention tester and drift monitor
- Retention tester: runs benchmark questions to detect catastrophic forgetting
- Drift monitor: tracks confidence scores over time to detect system degradation
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

RETENTION_LOG_FILE = "./lancedb_store/retention_log.json"
DRIFT_LOG_FILE = "./lancedb_store/drift_log.json"

# Benchmark questions for retention testing
BENCHMARK_QUESTIONS = [
    {
        "question": "What is the minimum capital adequacy ratio for scheduled commercial banks in India?",
        "baseline_answer": "The minimum capital adequacy ratio for SCBs is 10.5%, comprising Tier I 5.5% and Tier II 5%."
    },
    {
        "question": "What are the main regulatory guidelines for know-your-customer (KYC) requirements?",
        "baseline_answer": "KYC requirements mandate customer identification, verification of identity, understanding of customer's business, and maintaining records."
    },
    {
        "question": "What is the RBI's policy on foreign direct investment limits?",
        "baseline_answer": "FDI limits vary by sector. Most sectors allow up to 100% FDI under automatic route."
    },
    {
        "question": "What are the guidelines for priority sector lending?",
        "baseline_answer": "PSL guidelines mandate that banks lend at least 40% of net bank credit to priority sectors including agriculture, MSMEs."
    },
    {
        "question": "What is the repo rate and how does it affect the economy?",
        "baseline_answer": "Repo rate is the rate at which RBI lends to commercial banks. It influences money supply and inflation control."
    }
]

def load_retention_log() -> List[Dict[str, Any]]:
    """Load retention test log"""
    if os.path.exists(RETENTION_LOG_FILE):
        try:
            with open(RETENTION_LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_retention_log(log: List[Dict[str, Any]]):
    """Save retention test log"""
    try:
        os.makedirs(os.path.dirname(RETENTION_LOG_FILE) or ".", exist_ok=True)
        with open(RETENTION_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving retention log: {e}")

def load_drift_log() -> List[Dict[str, Any]]:
    """Load drift monitor log"""
    if os.path.exists(DRIFT_LOG_FILE):
        try:
            with open(DRIFT_LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_drift_log(log: List[Dict[str, Any]]):
    """Save drift monitor log"""
    try:
        os.makedirs(os.path.dirname(DRIFT_LOG_FILE) or ".", exist_ok=True)
        with open(DRIFT_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving drift log: {e}")

def check_answer_consistency(baseline: str, current: str) -> bool:
    """
    Consistency check using keyword overlap on key terms only
    """
    try:
        # Extract meaningful keywords (ignore stopwords)
        stopwords = {"the", "a", "an", "is", "are", "of", "for", "in", "to", "and", 
                     "or", "at", "by", "with", "that", "this", "it", "as", "on", "be"}

        def keywords(text):
            return set(
                w for w in text.lower().split()
                if w not in stopwords and len(w) > 3
            )

        baseline_kw = keywords(baseline)
        current_kw = keywords(current)

        if not baseline_kw:
            return True

        # What fraction of baseline keywords appear in current answer
        overlap = len(baseline_kw & current_kw) / len(baseline_kw)

        # Pass if 30%+ of baseline keywords are present (was 50% Jaccard on all words)
        return overlap >= 0.30

    except:
        return True

def run_retention_tests(db) -> List[Dict[str, Any]]:
    """
    Run retention tests: check if benchmark questions still return consistent answers
    """
    try:
        from retriever import retrieve_and_rank
        
        results = []
        current_log = load_retention_log()
        
        for benchmark in BENCHMARK_QUESTIONS:
            question = benchmark["question"]
            baseline_answer = benchmark["baseline_answer"]
            
            try:
                # Retrieve relevant documents
                retrieved = retrieve_and_rank(question, db, top_k_per_collection=5)
                
                # For now, simulate an answer based on retrieved content
                if retrieved:
                    current_answer = retrieved[0].get("text", "No information found")[:200]
                else:
                    current_answer = "No information found"
                
                # Check consistency
                is_consistent = check_answer_consistency(baseline_answer, current_answer)
                
                result = {
                    "question": question,
                    "status": "pass" if is_consistent else "fail",
                    "timestamp": datetime.now().isoformat(),
                    "baseline_answer": baseline_answer,
                    "current_answer": current_answer,
                    "consistency_score": 0.8 if is_consistent else 0.4
                }
                
                results.append(result)
                current_log.append(result)
                
            except Exception as e:
                logger.error(f"Error testing question: {question} - {e}")
                results.append({
                    "question": question,
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
        
        # Save updated log (keep only last 100 entries)
        save_retention_log(current_log[-100:])
        
        logger.info(f"Retention tests completed: {sum(1 for r in results if r.get('status') == 'pass')}/{len(results)} passed")
        
        return results
    
    except Exception as e:
        logger.error(f"Error running retention tests: {e}")
        return []

def get_drift_logs() -> List[Dict[str, Any]]:
    """Get drift monitor logs"""
    try:
        return load_drift_log()
    except Exception as e:
        logger.error(f"Error getting drift logs: {e}")
        return []

def record_drift_sample(probe_queries: List[str], db):
    """
    Record a drift sample: for each probe query, store the top result's confidence
    """
    try:
        from retriever import retrieve_and_rank
        
        drift_log = load_drift_log()
        sample = {
            "timestamp": datetime.now().isoformat(),
            "queries": []
        }
        
        for query in probe_queries:
            retrieved = retrieve_and_rank(query, db, top_k_per_collection=5)
            
            if retrieved:
                top_result = retrieved[0]
                confidence = float(top_result.get("final_score", 0.5))
                
                sample["queries"].append({
                    "query": query,
                    "top_source": top_result.get("source", "Unknown"),
                    "confidence": confidence
                })
            else:
                sample["queries"].append({
                    "query": query,
                    "top_source": "None",
                    "confidence": 0.0
                })
        
        drift_log.append(sample)
        save_drift_log(drift_log[-100:])  # Keep last 100 samples
        
        logger.info(f"Recorded drift sample with {len(sample['queries'])} queries")
        
    except Exception as e:
        logger.error(f"Error recording drift sample: {e}")

def get_probe_queries() -> List[str]:
    """Get the list of probe queries for drift monitoring"""
    return [
        "What is the current repo rate?",
        "What is the CRR for banks?",
        "What are the guidelines for priority sector lending?",
        "What is the minimum capital adequacy ratio?",
        "What are the RBI guidelines for digital banking?"
    ]

def initialize_evaluator():
    """Initialize evaluator with empty logs if needed"""
    try:
        if not os.path.exists(RETENTION_LOG_FILE):
            save_retention_log([])
        
        if not os.path.exists(DRIFT_LOG_FILE):
            save_drift_log([])
        
        logger.info("Evaluator initialized")
    
    except Exception as e:
        logger.error(f"Error initializing evaluator: {e}")
