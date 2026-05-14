/**
 * Ultimate Scraper - Content Script
 * Runs on every page
 */

let isSelectionMode = false
let highlightedElements = []

// Listen for messages from background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'SCRAPE_WITH_SELECTORS':
      const data = scrapeWithSelectors(message.data)
      sendResponse({ success: true, data })
      break

    case 'GET_ELEMENT_INFO':
      const info = getElementInfo(message.data)
      sendResponse({ success: true, data: info })
      break

    case 'TOGGLE_SELECTION_MODE':
      toggleSelectionMode(message.data)
      sendResponse({ success: true, enabled: isSelectionMode })
      break

    case 'GET_PAGE_DATA':
      const pageData = getPageData()
      sendResponse({ success: true, data: pageData })
      break

    case 'HIGHLIGHT_ELEMENT':
      highlightElement(message.data)
      sendResponse({ success: true })
      break

    case 'CLEAR_HIGHLIGHTS':
      clearHighlights()
      sendResponse({ success: true })
      break

    default:
      sendResponse({ success: false, error: 'Unknown message type' })
  }
})

// Scrape with provided selectors
function scrapeWithSelectors(selectors) {
  const results = []

  if (!selectors || Object.keys(selectors).length === 0) {
    // Auto-detect
    results.push(...scrapeAuto())
  } else {
    // Use provided selectors
    for (const [field, selector] of Object.entries(selectors)) {
      const elements = document.querySelectorAll(selector)
      elements.forEach((el, index) => {
        if (!results[index]) results[index] = {}
        results[index][field] = getFieldValue(el, field)
      })
    }
  }

  return results
}

// Auto-detect content
function scrapeAuto() {
  const results = []

  // Find product listings
  const products = document.querySelectorAll(
    '[class*="product"], [class*="item"], [class*="card"], article, .result'
  )

  if (products.length > 1) {
    products.forEach(product => {
      const item = {}
      item.title = product.querySelector('h1, h2, h3, h4, a')?.textContent?.trim() || ''
      item.price = product.querySelector('[class*="price"], [class*="cost"]')?.textContent?.trim() || ''
      item.link = product.querySelector('a')?.href || ''
      item.image = product.querySelector('img')?.src || ''
      if (item.title) results.push(item)
    })
  } else {
    // Single item page
    const item = {}
    item.title = document.querySelector('h1')?.textContent?.trim() || ''
    item.price = document.querySelector('[class*="price"]')?.textContent?.trim() || ''
    item.description = document.querySelector('[class*="desc"], p')?.textContent?.trim() || ''
    item.image = document.querySelector('img')?.src || ''
    if (item.title) results.push(item)
  }

  return results
}

// Get field value based on type
function getFieldValue(element, field) {
  switch (field) {
    case 'url':
      return element.href || element.getAttribute('data-url') || ''
    case 'image':
      return element.src || element.getAttribute('data-src') || ''
    case 'price':
      return element.textContent?.trim().replace(/[^\d.,]/g, '') || ''
    default:
      return element.textContent?.trim() || ''
  }
}

// Get element info
function getElementInfo(data) {
  const { selector, tag, index } = data

  if (selector) {
    const elements = document.querySelectorAll(selector)
    if (index !== undefined && elements[index]) {
      return getElementDetails(elements[index])
    }
    return Array.from(elements).map(el => getElementDetails(el))
  }

  return null
}

// Get detailed element info
function getElementDetails(element) {
  return {
    tag: element.tagName.toLowerCase(),
    text: element.textContent?.trim().substring(0, 100),
    html: element.outerHTML.substring(0, 200),
    cssSelector: generateSelector(element),
    xpath: generateXPath(element),
    attributes: {
      id: element.id,
      class: element.className,
      href: element.getAttribute('href'),
      src: element.getAttribute('src'),
    }
  }
}

// Generate CSS selector
function generateSelector(element) {
  if (element.id) return `#${element.id}`

  const path = []
  while (element && element.nodeType === Node.ELEMENT_NODE) {
    let selector = element.tagName.toLowerCase()
    if (element.className) {
      const classes = element.className.split(' ')
        .filter(c => c && !c.match(/^active|hover|selected/))
        .slice(0, 2)
      if (classes.length) {
        selector += '.' + classes.join('.')
      }
    }
    path.unshift(selector)
    element = element.parentElement
  }
  return path.join(' > ')
}

// Generate XPath
function generateXPath(element) {
  if (element.id) return `//*[@id="${element.id}"]`

  const path = []
  while (element && element.nodeType === Node.ELEMENT_NODE) {
    let index = 1
    let sibling = element.previousSibling
    while (sibling) {
      if (sibling.nodeType === Node.ELEMENT_NODE &&
          sibling.tagName === element.tagName) {
        index++
      }
      sibling = sibling.previousSibling
    }
    path.unshift(`${element.tagName.toLowerCase()}[${index}]`)
    element = element.parentElement
  }
  return '/' + path.join('/')
}

// Get basic page data
function getPageData() {
  return {
    url: window.location.href,
    title: document.title,
    description: document.querySelector('meta[name="description"]')?.content || '',
    ogTitle: document.querySelector('meta[property="og:title"]')?.content || '',
    ogImage: document.querySelector('meta[property="og:image"]')?.content || '',
    links: Array.from(document.querySelectorAll('a[href]'))
      .slice(0, 20)
      .map(a => ({ text: a.textContent?.trim(), href: a.href })),
    images: Array.from(document.querySelectorAll('img[src]'))
      .slice(0, 10)
      .map(img => img.src),
  }
}

// Toggle selection mode
function toggleSelectionMode(enabled) {
  isSelectionMode = enabled

  if (enabled) {
    document.body.style.cursor = 'crosshair'
    document.addEventListener('mouseover', handleMouseOver)
    document.addEventListener('click', handleClick, true)
  } else {
    document.body.style.cursor = ''
    document.removeEventListener('mouseover', handleMouseOver)
    document.removeEventListener('click', handleClick, true)
    clearHighlights()
  }
}

// Handle mouse over during selection
function handleMouseOver(event) {
  if (!isSelectionMode) return

  // Remove previous highlight
  clearHighlights()

  // Highlight current element
  const element = event.target
  if (element && element !== document.body) {
    element.style.outline = '2px solid #3b82f6'
    element.style.outlineOffset = '2px'
    highlightedElements.push(element)
  }
}

// Handle click during selection
function handleClick(event) {
  if (!isSelectionMode) return

  event.preventDefault()
  event.stopPropagation()

  const element = event.target

  // Notify extension
  chrome.runtime.sendMessage({
    type: 'ELEMENT_SELECTED',
    data: {
      selector: generateSelector(element),
      xpath: generateXPath(element),
      tag: element.tagName.toLowerCase(),
      text: element.textContent?.trim().substring(0, 50),
    }
  })

  // Exit selection mode
  toggleSelectionMode(false)
}

// Highlight specific element
function highlightElement(data) {
  const { selector } = data
  if (!selector) return

  clearHighlights()

  const elements = document.querySelectorAll(selector)
  elements.forEach(el => {
    el.style.outline = '2px solid #10b981'
    el.style.outlineOffset = '2px'
    highlightedElements.push(el)
  })
}

// Clear all highlights
function clearHighlights() {
  highlightedElements.forEach(el => {
    el.style.outline = ''
    el.style.outlineOffset = ''
  })
  highlightedElements = []
}
