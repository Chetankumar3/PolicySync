import React, { useState, useEffect } from 'react'
import '../styles/QueryHistory.css'

function QueryHistory() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [clearing, setClearing] = useState(false)

  const fetchHistory = async () => {
    try {
      setError(null)
      const response = await fetch('http://localhost:8000/history?limit=50')
      if (!response.ok) throw new Error('Failed to fetch query history')
      const data = await response.json()
      setHistory(data.history || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClearHistory = async () => {
    if (!confirm('Are you sure you want to clear all query history?')) return
    
    setClearing(true)
    try {
      const response = await fetch('http://localhost:8000/history', {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to clear history')
      setHistory([])
    } catch (err) {
      setError(err.message)
    } finally {
      setClearing(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  if (loading) return <div className="loading">Loading query history...</div>

  return (
    <div className="query-history">
      <div className="history-header">
        <h2>Query History</h2>
        {history.length > 0 && (
          <button 
            onClick={handleClearHistory}
            disabled={clearing}
            className="clear-button"
          >
            {clearing ? 'Clearing...' : 'Clear History'}
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="empty-state">
          <p>No query history yet. Start by asking a question in the Query tab!</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div key={item.id} className="history-card">
              <div className="history-card-header">
                <h4 className="question">{item.question}</h4>
                <span className="timestamp">
                  {new Date(item.timestamp).toLocaleString()}
                </span>
              </div>
              
              <div className="answer-section">
                <p className="label">Answer:</p>
                <p className="answer">{item.answer}</p>
              </div>

              <div className="metadata">
                <span className="confidence">
                  Confidence: {(item.confidence * 100).toFixed(1)}%
                </span>
                <span className="sources-count">
                  Sources: {item.sources.length}
                </span>
              </div>

              {item.sources.length > 0 && (
                <div className="sources-section">
                  <p className="label">Sources:</p>
                  <div className="sources-list">
                    {item.sources.map((source, idx) => (
                      <div key={idx} className="source-item">
                        <span className="source-name">{source.source}</span>
                        <span className="source-date">{source.date}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default QueryHistory
