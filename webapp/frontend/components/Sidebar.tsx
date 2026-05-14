"""
Sidebar navigation component.
"""
import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/scrape', label: 'Scraper', icon: '🔍' },
  { path: '/results', label: 'Results', icon: '📋' },
  { path: '/scheduler', label: 'Scheduler', icon: '⏰' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      <div className="logo">
        <span className="logo-icon">🕷️</span>
        <span className="logo-text">UltimateScraper</span>
      </div>

      <nav className="nav">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="storage-info">
          <span className="storage-label">Storage</span>
          <div className="storage-bar">
            <div className="storage-used" style={{ width: '45%' }} />
          </div>
          <span className="storage-text">4.5 GB / 10 GB</span>
        </div>
      </div>
    </aside>
  )
}
