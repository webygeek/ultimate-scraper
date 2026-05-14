"""
Results page - View and manage scrape results.
"""
import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function Results() {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  useEffect(() => {
    loadResults()
  }, [page])

  async function loadResults() {
    setLoading(true)
    try {
      const data = await api.listResults(page)
      setResults(data.results || [])
    } catch (error) {
      console.error('Failed to load results:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id) {
    try {
      await api.deleteResult(id)
      loadResults()
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  return (
    <div className="results-page">
      <h1>Results</h1>

      {loading ? (
        <div className="loading">Loading...</div>
      ) : results.length === 0 ? (
        <div className="empty-state">
          <p>No results yet. Run a scrape first!</p>
        </div>
      ) : (
        <>
          <table className="results-table">
            <thead>
              <tr>
                <th>URL</th>
                <th>Items</th>
                <th>Format</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.id}>
                  <td className="url-cell">{result.url}</td>
                  <td>{result.item_count}</td>
                  <td>{result.format}</td>
                  <td>{new Date(result.created_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      className="btn small"
                      onClick={() => window.open(`/results/${result.id}`)}
                    >
                      View
                    </button>
                    <button
                      className="btn small"
                      onClick={() => handleDelete(result.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
