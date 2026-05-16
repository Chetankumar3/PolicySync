import React, { useState } from 'react'
import '../styles/QueryPanel.css'

function QueryPanel() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          include_archive: true
        })
      })

      if (!response.ok) {
        throw new Error('Failed to query the system')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="query-panel">
      <h2>Query the RAG System</h2>
      
      <form onSubmit={handleSubmit} className="query-form">
        <div className="form-group">
          <label htmlFor="question">Ask a banking regulatory question:</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., What is the minimum capital adequacy ratio for banks?"
            rows={4}
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading} className="submit-button">
          {loading ? 'Processing...' : 'Ask'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="result">
          <div className="answer-section">
            <h3>Answer</h3>
            <p className="answer-text">{result.answer}</p>
            <div className="metadata">
              <span>Confidence: {(result.confidence * 100).toFixed(1)}%</span>
              <span>Timestamp: {new Date(result.timestamp).toLocaleString()}</span>
            </div>
          </div>

          <div className="sources-section">
            <h3>Sources ({result.sources.length})</h3>
            <div className="sources-list">
              {result.sources.map((source, idx) => (
                <div key={idx} className={`source-card ${source.collection}`}>
                  <div className="source-header">
                    <h4>{source.source}</h4>
                    <span className={`collection-badge ${source.collection}`}>
                      {source.collection === 'active_index' ? 'Current' : 'Archive'}
                    </span>
                  </div>
                  <p className="source-date">{source.date}</p>
                  <p className="source-text">{source.text}</p>
                  <div className="source-score">
                    Score: {(source.score * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default QueryPanel
