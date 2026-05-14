"""
Scheduler page - Manage scheduled jobs.
"""
import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function Scheduler() {
  const [schedules, setSchedules] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [newSchedule, setNewSchedule] = useState({
    name: '',
    url: '',
    cron_expression: '0 */6 * * *',
  })

  useEffect(() => {
    loadSchedules()
  }, [])

  async function loadSchedules() {
    try {
      const data = await api.listSchedules()
      setSchedules(data)
    } catch (error) {
      console.error('Failed to load schedules:', error)
    }
  }

  async function handleCreate() {
    try {
      await api.createSchedule(newSchedule)
      setShowModal(false)
      setNewSchedule({ name: '', url: '', cron_expression: '0 */6 * * *' })
      loadSchedules()
    } catch (error) {
      console.error('Create failed:', error)
    }
  }

  async function handleToggle(id, enabled) {
    try {
      await api.toggleSchedule(id, !enabled)
      loadSchedules()
    } catch (error) {
      console.error('Toggle failed:', error)
    }
  }

  return (
    <div className="scheduler-page">
      <div className="page-header">
        <h1>Scheduled Jobs</h1>
        <button className="btn primary" onClick={() => setShowModal(true)}>
          + New Schedule
        </button>
      </div>

      {schedules.length === 0 ? (
        <div className="empty-state">
          <p>No scheduled jobs. Create one to get started!</p>
        </div>
      ) : (
        <div className="schedule-list">
          {schedules.map((schedule) => (
            <div key={schedule.id} className="schedule-card">
              <div className="schedule-info">
                <h3>{schedule.name}</h3>
                <p className="url">{schedule.url}</p>
                <p className="cron">{schedule.cron_expression}</p>
              </div>
              <div className="schedule-stats">
                <span>{schedule.run_count} runs</span>
                <span>{schedule.success_count} successful</span>
              </div>
              <div className="schedule-actions">
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={schedule.enabled}
                    onChange={() => handleToggle(schedule.id, schedule.enabled)}
                  />
                  <span>Enabled</span>
                </label>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>New Scheduled Job</h2>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={newSchedule.name}
                onChange={(e) =>
                  setNewSchedule({ ...newSchedule, name: e.target.value })
                }
              />
            </div>
            <div className="form-group">
              <label>URL</label>
              <input
                type="text"
                value={newSchedule.url}
                onChange={(e) =>
                  setNewSchedule({ ...newSchedule, url: e.target.value })
                }
              />
            </div>
            <div className="form-group">
              <label>Cron Expression</label>
              <input
                type="text"
                value={newSchedule.cron_expression}
                onChange={(e) =>
                  setNewSchedule({ ...newSchedule, cron_expression: e.target.value })
                }
              />
              <span className="hint">e.g., 0 */6 * * * (every 6 hours)</span>
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setShowModal(false)}>
                Cancel
              </button>
              <button className="btn primary" onClick={handleCreate}>
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
