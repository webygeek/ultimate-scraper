# Ultimate Scraper

A comprehensive, AI-powered web scraping solution with built-in Cloudflare bypass using Firecrawl.

## Features

- **Firecrawl Integration** - Bypass Cloudflare protection, render JavaScript, extract clean data
- **Multi-Agent System** - Coordinator, SERP, Browser, and CAPTCHA agents
- **Self-Learning** - Skills database that learns from successful scrapes
- **Parallel Scraping** - Distributed scraping with proxy rotation
- **AI Selectors** - Auto-generate CSS selectors using AI
- **Cloudflare Bypass** - Multiple strategies (Firecrawl, cloudscraper, paid services)
- **Browser Automation** - Playwright with stealth mode
- **Third-Party Reference** - Database of 18+ external scraping services for comparison

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Start Firecrawl (for Cloudflare bypass)

```bash
# Windows
cd docker && docker-compose up -d

# Or use the script
docker/start.sh
```

### 3. Use the Scraper

```bash
# CLI
python main.py firecrawl "https://example.com"

# Python
python -c "
from scraper.integrations import FirecrawlClient
client = FirecrawlClient()
result = client.scrape('https://example.com')
print(result['markdown'])
"
```

---

## Firecrawl Integration

Firecrawl handles Cloudflare-protected sites by:
- Bypassing Cloudflare challenges
- Rendering JavaScript
- Extracting clean markdown/HTML

### Usage

```python
from scraper.integrations import FirecrawlClient

# Create client (auto-connects to local Docker)
client = FirecrawlClient()

# Check if available
if client.is_available():
    # Scrape a URL
    result = client.scrape("https://example.com")

    if result["success"]:
        print(result["markdown"])  # or result["html"]
```

### Methods

| Method | Description |
|--------|-------------|
| `client.scrape(url)` | Scrape with HTML + Markdown |
| `client.scrape_markdown(url)` | Get markdown only |
| `client.scrape_html(url)` | Get HTML only |
| `client.crawl(url, max_depth=2)` | Crawl site recursively |
| `client.map(url)` | Discover all URLs on domain |
| `client.batch_scrape(urls)` | Scrape multiple URLs |

### Firecrawl Options

**Local Docker** (default, no API key needed):
```bash
cd docker && docker-compose up -d
```

**Cloud API** (requires API key from firecrawl.dev):
```python
client = FirecrawlClient({"firecrawl": {"api_key": "fc-xxx"}})
```

**Self-hosted**:
```python
client = FirecrawlClient({"firecrawl": {"base_url": "http://your-server:3002"}})
```

---

## CLI Commands

```bash
# Firecrawl scrape
python main.py firecrawl "https://example.com"
python main.py fc "https://example.com"

# Natural language scraping
python main.py ask "https://example.com" "Extract all prices"

# XPath extraction
python main.py xpath "https://example.com" "//div[@class='product']"

# Geographic scraping
python main.py geo "https://example.com" --location us-east

# Screenshot
python main.py screenshot "https://example.com"

# Web server
python main.py server
```

---

## Project Structure

```
ultimate-scraper/
├── main.py                  # CLI entry point
├── config.yaml              # Configuration
├── requirements.txt         # Python dependencies
├── docker/
│   ├── docker-compose.yaml # Firecrawl Docker setup
│   ├── .env               # Environment variables
│   ├── start.sh            # Start script
│   └── stop.sh             # Stop script
├── scraper/
│   ├── integrations/       # Third-party integrations
│   │   ├── firecrawl_client.py
│   │   └── cloudflare_bypass.py
│   ├── sources/            # Website-specific scrapers
│   │   └── clutch_scraper.py
│   ├── agents/             # Multi-agent system
│   ├── modules/            # Core modules
│   └── skills/             # Self learning system
└── data/                    # Scraped data output
```

---

## Configuration

Edit `config.yaml`:

```yaml
# Firecrawl Settings
firecrawl:
  base_url: "http://localhost:3002"
  timeout: 120

# Anti-detection
anti_detection:
  enabled: true
  rotate_user_agent: true
  stealth_mode: true

# Cloudflare Bypass
cloudflare_bypass:
  enabled: true
  strategy: "cloudscraper"  # cloudscraper, undetected, scraperapi, brightdata

# Rate Limiting
requests:
  rate_limit:
    requests_per_minute: 20
```

---

## Third-Party Services Reference

The project includes a comprehensive database of 18+ external scraping services:

```python
from scraper.third_party import SCRAPING_SERVICES, get_free_services, get_recommendation

# All services
print(f"Total services: {len(SCRAPING_SERVICES)}")

# Free services
for s in get_free_services():
    print(f"FREE: {s['name']}")

# Get recommendations
recs = get_recommendation(budget='medium', features_needed=['js_rendering'])
for s in recs:
    print(f"{s['name']}: {s['pricing']['starting_price']}")
```

### Quick Comparison

| Service | Tier | Success Rate | Price |
|---------|------|-------------|-------|
| Bright Data | Enterprise | ~99% | $300+/mo |
| ScraperAPI | Mid-tier | ~99% | $25+/mo |
| ScrapingBee | Mid-tier | 99.9% | $49+/mo |
| **Firecrawl** | Open Source | ~95% | **FREE** |
| Crawlee | Open Source | Varies | **FREE** |

---

## Using on Different Machines/Projects

### Clone and Run

```bash
# Clone the repository
git clone https://github.com/yourusername/ultimate-scraper.git
cd ultimate-scraper

# Install dependencies
pip install -r requirements.txt

# Start Firecrawl
cd docker && docker-compose up -d

# Use the scraper
python main.py firecrawl "https://example.com"
```

### Copy Firecrawl Docker Files

If you only need Firecrawl in another project:

```bash
# Copy docker folder to your project
cp -r ultimate-scraper/docker your-project/

# Start Firecrawl
cd your-project/docker && docker-compose up -d
```

### Quick Firecrawl Module

For minimal setup, copy just the Firecrawl client:

```python
# firecrawl.py - single file, works anywhere with Docker
from firecrawl import FirecrawlClient

client = FirecrawlClient()
result = client.scrape("https://example.com")
```

---

## Cloudflare Bypass Comparison

| Method | Success Rate | Cost | Setup |
|--------|-------------|------|-------|
| **Firecrawl** | ~95% | Free (self-hosted) | Docker required |
| **cloudscraper** | ~30-50% | Free | pip install |
| **ScraperAPI** | ~99% | ~$25/month | API key |
| **Bright Data** | ~99% | ~$300/month | API key |

---

## Examples

### Scrape a Website

```python
from scraper.integrations import FirecrawlClient

client = FirecrawlClient()
result = client.scrape("https://news.ycombinator.com")

if result["success"]:
    print(result["markdown"])
```

### Crawl a Site

```python
client = FirecrawlClient()
pages = client.crawl("https://example.com", max_depth=2, max_pages=50)

for page in pages:
    print(page["markdown"])
```

### Scrape Clutch.co

```python
from scraper.sources import ClutchScraper

scraper = ClutchScraper()
agencies = scraper.scrape("seo", "new_york")
```

### Batch Scrape

```python
client = FirecrawlClient()
urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
results = client.batch_scrape(urls)
```

---

## Troubleshooting

### Firecrawl not running

```bash
cd docker && docker-compose up -d
docker ps | grep firecrawl
```

### Connection refused

```bash
# Check if Docker is running
docker ps

# Restart Firecrawl
cd docker && docker-compose restart
```

### Still blocked

Try cloudscraper as fallback:
```python
import cloudscraper
scraper = cloudscraper.create_scraper()
response = scraper.get("https://example.com")
```

---

## License

MIT License
