/**
 * Ultimate Scraper - Background Service Worker
 */

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'SCRAPE_PAGE':
      scrapePage(message.data, sender.tab)
        .then(result => sendResponse({ success: true, data: result }))
        .catch(error => sendResponse({ success: false, error: error.message }))
      return true // Keep channel open for async response

    case 'GET_SELECTION':
      getElementSelection(message.data)
        .then(result => sendResponse({ success: true, data: result }))
        .catch(error => sendResponse({ success: false, error: error.message }))
      return true

    case 'SAVE_TO_CLOUD':
      saveToCloud(message.data)
        .then(result => sendResponse({ success: true, data: result }))
        .catch(error => sendResponse({ success: false, error: error.message }))
      return true

    case 'GET_HISTORY':
      getHistory()
        .then(result => sendResponse({ success: true, data: result }))
        .catch(error => sendResponse({ success: false, error: error.message }))
      return true

    case 'ADD_TO_HISTORY':
      addToHistory(message.data)
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }))
      return true

    default:
      sendResponse({ success: false, error: 'Unknown message type' })
  }
})

// Scrape the current page
async function scrapePage(data, tab) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tab.id, {
      type: 'SCRAPE_WITH_SELECTORS',
      data: data
    }, response => {
      if (response && response.success) {
        resolve(response.data)
      } else {
        reject(new Error(response?.error || 'Scraping failed'))
      }
    })
  })
}

// Get element selection from page
async function getElementSelection(data) {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      chrome.tabs.sendMessage(tabs[0].id, {
        type: 'GET_ELEMENT_INFO',
        data: data
      }, response => {
        if (response && response.success) {
          resolve(response.data)
        } else {
          reject(new Error(response?.error || 'Failed to get selection'))
        }
      })
    })
  })
}

// Save data to cloud
async function saveToCloud(data) {
  // Get API endpoint from storage
  const config = await chrome.storage.local.get(['apiEndpoint', 'apiKey'])

  if (!config.apiEndpoint) {
    throw new Error('API endpoint not configured')
  }

  const response = await fetch(`${config.apiEndpoint}/scrape`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.apiKey && { Authorization: `Bearer ${config.apiKey}` })
    },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error('Failed to save to cloud')
  }

  return response.json()
}

// History management
async function getHistory() {
  const result = await chrome.storage.local.get(['scrapeHistory'])
  return result.scrapeHistory || []
}

async function addToHistory(data) {
  const history = await getHistory()
  history.unshift({
    ...data,
    timestamp: Date.now()
  })
  // Keep only last 100 items
  history.splice(100)
  await chrome.storage.local.set({ scrapeHistory: history })
}

// Initialize storage
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    scrapeHistory: [],
    settings: {
      apiEndpoint: '',
      apiKey: '',
      defaultSelectors: {},
      autoSave: false,
      theme: 'light'
    }
  })
})
