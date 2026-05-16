import React, { useState, useEffect } from 'react'
import '../styles/IngestionStatus.css'

function IngestionStatus() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [fetchingNow, setFetchingNow] = useState(false)

  const fetchStatus = async () => {
    try {
      setError(null)
      const response = await fetch('http://localhost:8000/status')
      if (!response.ok) throw new Error('Failed to fetch status')
      const data = await response.json()
      setStatus(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleManualFetch = async () => {
    setFetchingNow(true)
    try {
      const response = await fetch('http://localhost:8000/fetch-now', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Fetch failed')
      await fetchStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setFetchingNow(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="loading">Loading status...</div>

  return (
    <div className="ingestion-status">
      <h2>Ingestion Status</h2>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {status && (
        <div className="status-container">
          <div className="status-grid">
            <div className="status-card">
              <h3>Active Index</h3>
              <p className="big-number">{status.active_docs}</p>
              <p className="card-label">Documents</p>
            </div>

            <div className="status-card">
              <h3>Archive Index</h3>
              <p className="big-number">{status.archive_docs}</p>
              <p className="card-label">Documents</p>
            </div>

            <div className="status-card">
              <h3>Total Chunks</h3>
              <p className="big-number">{status.total_chunks}</p>
              <p className="card-label">Indexed Chunks</p>
            </div>

            <div className="status-card">
              <h3>System Status</h3>
              <p className={`status-value ${status.status}`}>
                {status.status.toUpperCase()}
              </p>
              <p className="card-label">Ready to query</p>
            </div>
          </div>

          <div className="last-fetch">
            <p><strong>Last Fetch:</strong> {status.last_fetch_time}</p>
            <p className="hint">Data fetched from: RBI Notifications, Master Directions, Press Releases</p>
          </div>

          <button
            onClick={handleManualFetch}
            disabled={fetchingNow}
            className="fetch-button"
          >
            {fetchingNow ? 'Fetching...' : 'Fetch New Data Now'}
          </button>

          <div className="info-box">
            <h4>How It Works</h4>
            <p>
              The system automatically fetches new regulatory documents from RBI every 8 hours.
              Only new documents are ingested - the system tracks previously fetched URLs to avoid
              re-indexing the same content. Click the button above to trigger an immediate fetch.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default IngestionStatus
