"""
Settings page - Configure scraper settings.
"""
import { useState, useEffect } from 'react'
import { api } from '../services/api'

export function Settings() {
  const [config, setConfig] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  async function loadConfig() {
    try {
      const data = await api.getConfig()
      setConfig(data)
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.updateConfig(config)
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <section className="settings-section">
        <h2>Scraping</h2>
        <div className="form-group">
          <label>Rate Limit (per minute)</label>
          <input
            type="number"
            value={config.rate_limit_per_minute || 60}
            onChange={(e) =>
              setConfig({ ...config, rate_limit_per_minute: Number(e.target.value) })
            }
          />
        </div>
        <div className="form-group">
          <label>Timeout (seconds)</label>
          <input
            type="number"
            value={config.scrape_timeout || 60}
            onChange={(e) =>
              setConfig({ ...config, scrape_timeout: Number(e.target.value) })
            }
          />
        </div>
        <div className="form-group">
          <label>Max Concurrent Jobs</label>
          <input
            type="number"
            value={config.max_concurrent_jobs || 10}
            onChange={(e) =>
              setConfig({ ...config, max_concurrent_jobs: Number(e.target.value) })
            }
          />
        </div>
      </section>

      <section className="settings-section">
        <h2>Browser</h2>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={config.browser?.headless ?? true}
              onChange={(e) =>
                setConfig({
                  ...config,
                  browser: { ...config.browser, headless: e.target.checked },
                })
              }
            />
            Headless Mode
          </label>
        </div>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={config.browser?.stealth ?? true}
              onChange={(e) =>
                setConfig({
                  ...config,
                  browser: { ...config.browser, stealth: e.target.checked },
                })
              }
            />
            Stealth Mode
          </label>
        </div>
      </section>

      <section className="settings-section">
        <h2>Proxy</h2>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={config.proxy?.enabled ?? false}
              onChange={(e) =>
                setConfig({
                  ...config,
                  proxy: { ...config.proxy, enabled: e.target.checked },
                })
              }
            />
            Enable Proxy
          </label>
        </div>
      </section>

      <button className="btn primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}
