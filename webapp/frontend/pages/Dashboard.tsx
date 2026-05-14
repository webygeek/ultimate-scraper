"""
Dashboard page - Overview statistics.
"""
import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function Dashboard() {
  const [stats, setStats] = useState({
    totalScrapes: 0,
    successfulScrapes: 0,
    failedScrapes: 0,
    activeJobs: 0,
  })
  const [recentActivity, setRecentActivity] = useState([])

  useEffect(() => {
    loadDashboard()
  }, [])

  async function loadDashboard() {
    try {
      const data = await api.getStats()
      setStats(data)
      setRecentActivity(data.recent || [])
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    }
  }

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-icon">🔍</span>
          <div className="stat-content">
            <span className="stat-value">{stats.totalScrapes}</span>
            <span className="stat-label">Total Scrapes</span>
          </div>
        </div>

        <div className="stat-card success">
          <span className="stat-icon">✅</span>
          <div className="stat-content">
            <span className="stat-value">{stats.successfulScrapes}</span>
            <span className="stat-label">Successful</span>
          </div>
        </div>

        <div className="stat-card error">
          <span className="stat-icon">❌</span>
          <div className="stat-content">
            <span className="stat-value">{stats.failedScrapes}</span>
            <span className="stat-label">Failed</span>
          </div>
        </div>

        <div className="stat-card">
          <span className="stat-icon">⏳</span>
          <div className="stat-content">
            <span className="stat-value">{stats.activeJobs}</span>
            <span className="stat-label">Active Jobs</span>
          </div>
        </div>
      </div>

      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="actions-grid">
          <button className="action-btn primary">
            <span>🔍</span>
            <span>New Scrape</span>
          </button>
          <button className="action-btn">
            <span>📋</span>
            <span>Import URLs</span>
          </button>
          <button className="action-btn">
            <span>📊</span>
            <span>Export Data</span>
          </button>
          <button className="action-btn">
            <span>⏰</span>
            <span>Schedule Job</span>
          </button>
        </div>
      </div>

      <div className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          {recentActivity.length === 0 ? (
            <p className="empty-state">No recent activity</p>
          ) : (
            recentActivity.map((item, index) => (
              <div key={index} className="activity-item">
                <span className="activity-icon">
                  {item.success ? '✅' : '❌'}
                </span>
                <div className="activity-content">
                  <span className="activity-title">{item.url}</span>
                  <span className="activity-time">{item.time}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
