import React, { useState, useEffect } from 'react'
import './App.css'
import QueryPanel from './components/QueryPanel'
import IngestionStatus from './components/IngestionStatus'
import EvalDashboard from './components/EvalDashboard'
import DriftMonitor from './components/DriftMonitor'

function App() {
  const [activeTab, setActiveTab] = useState('query')
  const [systemStatus, setSystemStatus] = useState({
    status: 'initializing',
    message: 'Loading...'
  })

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/health')
        if (response.ok) {
          setSystemStatus({
            status: 'healthy',
            message: 'Connected'
          })
        }
      } catch (error) {
        setSystemStatus({
          status: 'error',
          message: 'Backend not available'
        })
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>PolicySync</h1>
          <p>Banking Credit Analysis System</p>
          <div className={`status-indicator ${systemStatus.status}`}>
            {systemStatus.message}
          </div>
        </div>
      </header>

      <div className="container">
        <nav className="sidebar">
          <ul className="nav-menu">
            <li>
              <button
                className={`nav-button ${activeTab === 'query' ? 'active' : ''}`}
                onClick={() => setActiveTab('query')}
              >
                Query
              </button>
            </li>
            <li>
              <button
                className={`nav-button ${activeTab === 'status' ? 'active' : ''}`}
                onClick={() => setActiveTab('status')}
              >
                Ingestion Status
              </button>
            </li>
            <li>
              <button
                className={`nav-button ${activeTab === 'eval' ? 'active' : ''}`}
                onClick={() => setActiveTab('eval')}
              >
                Retention Tests
              </button>
            </li>
            <li>
              <button
                className={`nav-button ${activeTab === 'drift' ? 'active' : ''}`}
                onClick={() => setActiveTab('drift')}
              >
                Drift Monitor
              </button>
            </li>
          </ul>
        </nav>

        <main className="main-content">
          {activeTab === 'query' && <QueryPanel />}
          {activeTab === 'status' && <IngestionStatus />}
          {activeTab === 'eval' && <EvalDashboard />}
          {activeTab === 'drift' && <DriftMonitor />}
        </main>
      </div>
    </div>
  )
}

export default App
