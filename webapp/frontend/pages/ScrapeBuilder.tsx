"""
ScrapeBuilder page - Visual scraper builder.
"""
import { useState } from 'react'
import { api } from '../services/api'

export function ScrapeBuilder() {
  const [url, setUrl] = useState('')
  const [mode, setMode] = useState('auto')
  const [selectors, setSelectors] = useState('')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [results, setResults] = useState(null)

  async function handleScrape() {
    if (!url) return

    try {
      const data = await api.createScrapeJob(
        url,
        selectors ? JSON.parse(selectors) : undefined,
        mode
      )
      setJobId(data.job_id)
      pollStatus(data.job_id)
    } catch (error) {
      console.error('Scrape failed:', error)
    }
  }

  async function pollStatus(jobId) {
    const interval = setInterval(async () => {
      try {
        const status = await api.getScrapeStatus(jobId)
        setStatus(status)

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval)
          if (status.status === 'completed') {
            const result = await api.getScrapeResult(jobId)
            setResults(result)
          }
        }
      } catch (error) {
        clearInterval(interval)
      }
    }, 1000)
  }

  return (
    <div className="scrape-builder">
      <h1>Scrape Builder</h1>

      <div className="builder-form">
        <div className="form-group">
          <label>URL to Scrape</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
          />
        </div>

        <div className="form-group">
          <label>Scrape Mode</label>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="auto">Auto (Best)</option>
            <option value="parallel">Parallel</option>
            <option value="api">API Discovery</option>
            <option value="ai">AI Assist</option>
            <option value="incremental">Incremental</option>
          </select>
        </div>

        <div className="form-group">
          <label>Selectors (JSON)</label>
          <textarea
            value={selectors}
            onChange={(e) => setSelectors(e.target.value)}
            placeholder='{"title": "h1", "price": ".price"}'
            rows={4}
          />
        </div>

        <button className="btn primary" onClick={handleScrape}>
          🔍 Start Scrape
        </button>
      </div>

      {status && (
        <div className="status-panel">
          <h3>Status: {status.status}</h3>
          <div className="progress-bar">
            <div className="progress" style={{ width: `${status.progress * 100}%` }} />
          </div>
          {status.error && <p className="error">{status.error}</p>}
        </div>
      )}

      {results && (
        <div className="results-panel">
          <h3>Results ({results.data?.length || 0} items)</h3>
          <pre>{JSON.stringify(results.data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
