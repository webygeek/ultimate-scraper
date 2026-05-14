/**
 * Ultimate Scraper - Options Page Script
 */

document.addEventListener('DOMContentLoaded', () => {
  loadSettings()
  setupEventListeners()
})

async function loadSettings() {
  const result = await chrome.storage.local.get(['settings'])
  const settings = result.settings || {}

  // API Configuration
  document.getElementById('apiEndpoint').value = settings.apiEndpoint || ''
  document.getElementById('apiKey').value = settings.apiKey || ''

  // Default Settings
  document.getElementById('defaultMode').value = settings.defaultMode || 'auto'
  document.getElementById('autoSave').checked = settings.autoSave || false
  document.getElementById('showNotifications').checked = settings.showNotifications !== false

  // Default Selectors
  document.getElementById('titleSelector').value = settings.titleSelector || 'h1'
  document.getElementById('priceSelector').value = settings.priceSelector || '[class*="price"]'
  document.getElementById('descSelector').value = settings.descSelector || '[class*="desc"]'
}

function setupEventListeners() {
  document.getElementById('saveBtn').addEventListener('click', saveSettings)
  document.getElementById('testConnectionBtn').addEventListener('click', testConnection)
  document.getElementById('resetSelectorsBtn').addEventListener('click', resetSelectors)
}

async function saveSettings() {
  const settings = {
    apiEndpoint: document.getElementById('apiEndpoint').value,
    apiKey: document.getElementById('apiKey').value,
    defaultMode: document.getElementById('defaultMode').value,
    autoSave: document.getElementById('autoSave').checked,
    showNotifications: document.getElementById('showNotifications').checked,
    titleSelector: document.getElementById('titleSelector').value,
    priceSelector: document.getElementById('priceSelector').value,
    descSelector: document.getElementById('descSelector').value,
  }

  await chrome.storage.local.set({ settings })

  showNotification('Settings saved!')
}

async function testConnection() {
  const endpoint = document.getElementById('apiEndpoint').value
  const btn = document.getElementById('testConnectionBtn')
  btn.disabled = true
  btn.textContent = 'Testing...'

  try {
    const response = await fetch(`${endpoint}/api/v1/health`)
    if (response.ok) {
      showNotification('✅ Connection successful!')
    } else {
      showError('Connection failed')
    }
  } catch (error) {
    showError('Connection failed: ' + error.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Test Connection'
  }
}

function resetSelectors() {
  document.getElementById('titleSelector').value = 'h1'
  document.getElementById('priceSelector').value = '[class*="price"]'
  document.getElementById('descSelector').value = '[class*="desc"]'
  showNotification('Selectors reset to defaults')
}

function showNotification(message) {
  const notification = document.createElement('div')
  notification.className = 'notification success'
  notification.textContent = message
  document.body.appendChild(notification)
  setTimeout(() => notification.remove(), 3000)
}

function showError(message) {
  const notification = document.createElement('div')
  notification.className = 'notification error'
  notification.textContent = message
  document.body.appendChild(notification)
  setTimeout(() => notification.remove(), 5000)
}
