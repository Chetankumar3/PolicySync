import React, { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import '../styles/DriftMonitor.css'

function DriftMonitor() {
  const [driftLogs, setDriftLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedQuery, setSelectedQuery] = useState(0)

  const fetchDriftLogs = async () => {
    try {
      setError(null)
      const response = await fetch('http://localhost:8000/drift')
      if (!response.ok) throw new Error('Failed to fetch drift logs')
      const data = await response.json()
      setDriftLogs(data.drift_logs || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDriftLogs()
    const interval = setInterval(fetchDriftLogs, 15000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="loading">Loading drift monitor...</div>

  // Extract unique queries
  const uniqueQueries = []
  const queryMap = {}
  driftLogs.forEach(log => {
    if (log.queries) {
      log.queries.forEach((q, idx) => {
        if (!queryMap[idx]) {
          queryMap[idx] = q.query
          uniqueQueries.push({ id: idx, query: q.query })
        }
      })
    }
  })

  // Prepare data for the selected query
  const chartData = driftLogs
    .filter(log => log.queries && log.queries[selectedQuery])
    .map(log => ({
      timestamp: new Date(log.timestamp).toLocaleTimeString(),
      confidence: (log.queries[selectedQuery].confidence * 100).toFixed(1),
      fullTimestamp: log.timestamp
    }))

  const currentQuery = uniqueQueries[selectedQuery]?.query || "No query selected"

  return (
    <div className="drift-monitor">
      <h2>Drift Monitor</h2>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="info-box">
        <h4>What is the Drift Monitor?</h4>
        <p>
          The drift monitor tracks confidence scores for probe queries over time. If confidence
          drops significantly, the system may be drifting - losing its ability to answer standard
          questions correctly. This represents KL divergence and distribution shift in production systems.
        </p>
      </div>

      {driftLogs.length === 0 ? (
        <div className="no-data">
          <p>No drift data yet. Run a few queries to start tracking drift.</p>
        </div>
      ) : (
        <>
          <div className="query-selector">
            <label>Select a probe query to monitor:</label>
            <select
              value={selectedQuery}
              onChange={(e) => setSelectedQuery(parseInt(e.target.value))}
            >
              {uniqueQueries.map(q => (
                <option key={q.id} value={q.id}>
                  {q.query}
                </option>
              ))}
            </select>
          </div>

          <div className="chart-container">
            <h3>Confidence Score Over Time</h3>
            <p className="current-query">Query: {currentQuery}</p>

            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="confidence"
                    stroke="#8884d8"
                    name="Confidence %"
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p>No data for this query yet.</p>
            )}
          </div>

          <div className="stats">
            <div className="stat-card">
              <p className="label">Latest Confidence</p>
              <p className="value">
                {chartData.length > 0
                  ? `${chartData[chartData.length - 1].confidence}%`
                  : 'N/A'}
              </p>
            </div>
            <div className="stat-card">
              <p className="label">Highest Confidence</p>
              <p className="value">
                {chartData.length > 0
                  ? `${Math.max(...chartData.map(d => parseFloat(d.confidence)))}%`
                  : 'N/A'}
              </p>
            </div>
            <div className="stat-card">
              <p className="label">Lowest Confidence</p>
              <p className="value">
                {chartData.length > 0
                  ? `${Math.min(...chartData.map(d => parseFloat(d.confidence)))}%`
                  : 'N/A'}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default DriftMonitor
