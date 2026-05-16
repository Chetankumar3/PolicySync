import React, { useState, useEffect } from 'react'
import '../styles/EvalDashboard.css'

function EvalDashboard() {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchResults = async () => {
    try {
      setError(null)
      const response = await fetch('http://localhost:8000/retention')
      if (!response.ok) throw new Error('Failed to fetch retention results')
      const data = await response.json()
      setResults(data.results || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchResults()
    const interval = setInterval(fetchResults, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="loading">Loading retention tests...</div>

  const passCount = results.filter(r => r.status === 'pass').length
  const failCount = results.filter(r => r.status === 'fail').length
  const errorCount = results.filter(r => r.status === 'error').length

  return (
    <div className="eval-dashboard">
      <h2>Retention Test Dashboard</h2>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="summary">
        <div className="summary-card pass">
          <p className="label">Passed</p>
          <p className="count">{passCount}</p>
        </div>
        <div className="summary-card fail">
          <p className="label">Failed</p>
          <p className="count">{failCount}</p>
        </div>
        <div className="summary-card error">
          <p className="label">Errors</p>
          <p className="count">{errorCount}</p>
        </div>
      </div>

      <div className="info-box">
        <h4>What is the Retention Tester?</h4>
        <p>
          The retention tester runs benchmark questions after each data fetch to ensure the system
          hasn't forgotten important regulatory concepts. This detects "catastrophic forgetting" -
          the silent failure mode where adding new knowledge causes the system to lose old answers.
        </p>
      </div>

      <div className="results-list">
        <h3>Benchmark Questions</h3>
        {results.map((result, idx) => (
          <div key={idx} className={`result-card ${result.status}`}>
            <div className="result-header">
              <h4>{result.question}</h4>
              <span className={`status-badge ${result.status}`}>
                {result.status.toUpperCase()}
              </span>
            </div>

            {result.timestamp && (
              <p className="timestamp">
                Tested: {new Date(result.timestamp).toLocaleString()}
              </p>
            )}

            {result.baseline_answer && (
              <div className="answer-comparison">
                <div className="answer-part">
                  <p className="label">Baseline Answer:</p>
                  <p className="answer">{result.baseline_answer}</p>
                </div>
                {result.current_answer && (
                  <div className="answer-part">
                    <p className="label">Current Answer:</p>
                    <p className="answer">{result.current_answer}</p>
                  </div>
                )}
              </div>
            )}

            {result.error && (
              <p className="error-text">{result.error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default EvalDashboard
