"""
Header component.
*/
import { Link } from 'react-router-dom'

export function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <span className="page-title">Dashboard</span>
      </div>
      <div className="header-right">
        <Link to="/settings" className="icon-btn" title="Settings">
          ⚙️
        </Link>
        <div className="user-menu">
          <span className="user-avatar">👤</span>
        </div>
      </div>
    </header>
  )
}
