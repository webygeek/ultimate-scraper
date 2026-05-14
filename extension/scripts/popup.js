/**
 * Ultimate Scraper - Popup Script
 */

document.addEventListener('DOMContentLoaded', () => {
  init()
})

async function init() {
  // Get current tab URL
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
  const currentTab = tabs[0]

  document.getElementById('url').value = currentTab?.url || ''

  // Setup tab switching
  setupTabs()

  // Setup event listeners
  setupEventListeners()

  // Load history
  loadHistory()
}

function setupTabs() {
  const tabs = document.querySelectorAll('.tab')
  const contents = document.querySelectorAll('.tab-content')

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab

      // Update tab buttons
      tabs.forEach(t => t.classList.remove('active'))
      tab.classList.add('active')

      // Update content
      contents.forEach(c => c.classList.remove('active'))
      document.getElementById(target).classList.add('active')
    })
  })
}

function setupEventListeners() {
  // Scrape button
  document.getElementById('scrapeBtn').addEventListener('click', scrapeCurrentPage)

  // Select mode button
  document.getElementById('selectModeBtn').addEventListener('click', toggleSelectionMode)

  // History clear
  document.getElementById('clearHistoryBtn').addEventListener('click', clearHistory)

  // Copy button
  document.getElementById('copyBtn').addEventListener('click', copyResults)

  // Download button
  document.getElementById('downloadBtn').addEventListener('click', downloadResults)

  // Cloud save button
  document.getElementById('cloudBtn').addEventListener('click', saveToCloud)
}

async function scrapeCurrentPage() {
  const btn = document.getElementById('scrapeBtn')
  btn.disabled = true
  btn.textContent = '⏳ Scraping...'

  const mode = document.getElementById('mode').value
  const selectorsStr = document.getElementById('selectors').value
  const selectors = selectorsStr ? JSON.parse(selectorsStr) : {}

  try {
    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
    const tabId = tabs[0].id

    // Send scrape message to background
    const response = await chrome.runtime.sendMessage({
      type: 'SCRAPE_PAGE',
      data: { mode, selectors }
    })

    if (response.success) {
      displayResults(response.data)
    } else {
      showError(response.error)
    }
  } catch (error) {
    showError(error.message)
  } finally {
    btn.disabled = false
    btn.textContent = '🔍 Scrape Page'
  }
}

function displayResults(data) {
  const resultsDiv = document.getElementById('results')
  const previewDiv = resultsDiv.querySelector('.results-preview')
  const countDiv = resultsDiv.querySelector('.results-count')

  resultsDiv.style.display = 'block'
  countDiv.textContent = `${data.length} items found`

  // Show preview (first 3 items)
  previewDiv.innerHTML = data.slice(0, 3).map(item => `
    <div class="result-item">
      <pre>${JSON.stringify(item, null, 2)}</pre>
    </div>
  `).join('')

  // Store data for later use
  window.scrapeResults = data
}

function toggleSelectionMode() {
  const btn = document.getElementById('selectModeBtn')

  chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
    chrome.tabs.sendMessage(tabs[0].id, {
      type: 'TOGGLE_SELECTION_MODE',
      data: true
    }, response => {
      if (response.success) {
        if (response.enabled) {
          btn.textContent = '👆 Exit Selection'
          btn.classList.add('active')
        } else {
          btn.textContent = '👆 Start Selection'
          btn.classList.remove('active')
        }
      }
    })
  })
}

async function loadHistory() {
  const history = await chrome.runtime.sendMessage({
    type: 'GET_HISTORY'
  })

  const list = document.getElementById('historyList')

  if (history.data && history.data.length > 0) {
    list.innerHTML = history.data.slice(0, 10).map(item => `
      <div class="history-item" data-id="${item.id}">
        <div class="history-url">${item.url}</div>
        <div class="history-meta">
          <span>${item.count} items</span>
          <span>${formatTime(item.timestamp)}</span>
        </div>
      </div>
    `).join('')

    // Add click handlers
    list.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        const item = history.data.find(h => h.id === el.dataset.id)
        if (item) displayResults(item.data)
      })
    })
  }
}

function clearHistory() {
  chrome.storage.local.set({ scrapeHistory: [] })
  document.getElementById('historyList').innerHTML = '<p class="empty-state">No recent scrapes</p>'
}

function copyResults() {
  if (window.scrapeResults) {
    navigator.clipboard.writeText(JSON.stringify(window.scrapeResults, null, 2))
    showNotification('Copied to clipboard!')
  }
}

function downloadResults() {
  if (window.scrapeResults) {
    const blob = new Blob([JSON.stringify(window.scrapeResults, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `scrape-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }
}

async function saveToCloud() {
  if (window.scrapeResults) {
    try {
      const result = await chrome.runtime.sendMessage({
        type: 'SAVE_TO_CLOUD',
        data: {
          url: document.getElementById('url').value,
          data: window.scrapeResults
        }
      })

      if (result.success) {
        showNotification('Saved to cloud!')
      } else {
        showError(result.error)
      }
    } catch (error) {
      showError(error.message)
    }
  }
}

function showError(message) {
  const resultsDiv = document.getElementById('results')
  resultsDiv.style.display = 'block'
  resultsDiv.querySelector('.results-preview').innerHTML = `
    <div class="error-message">❌ ${message}</div>
  `
}

function showNotification(message) {
  // Simple notification
  const notification = document.createElement('div')
  notification.className = 'notification'
  notification.textContent = message
  document.body.appendChild(notification)
  setTimeout(() => notification.remove(), 2000)
}

function formatTime(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return date.toLocaleDateString()
}
