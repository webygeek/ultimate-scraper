# Project Instructions

## Project Overview

**Ultimate Scraper** - A comprehensive, AI-powered web scraping solution with built-in Cloudflare bypass using Firecrawl.

**GitHub:** https://github.com/webygeek/ultimate-scraper

---

## Setup (First Time)

When this repo is cloned, run these commands:

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Start Firecrawl Docker (handles Cloudflare bypass)
cd docker && docker-compose up -d

# 3. Verify Firecrawl is running
curl http://localhost:3002/
# Should return: {"status":"ok"}
```

---

## Quick Start

```bash
# Scrape a website
python main.py firecrawl "https://example.com"

# Or in Python
python -c "
from scraper.integrations import FirecrawlClient
client = FirecrawlClient()
result = client.scrape('https://example.com')
print(result['markdown'])
"
```

---

## Project Structure

```
ultimate-scraper/
├── main.py              # CLI entry point
├── config.yaml          # Configuration
├── requirements.txt     # Python dependencies
├── docker/              # Firecrawl Docker (pre-built image)
│   ├── docker-compose.yaml
│   ├── .env
│   ├── start.sh         # ./start.sh to launch
│   └── stop.sh          # ./stop.sh to stop
├── scraper/
│   ├── integrations/
│   │   ├── firecrawl_client.py    # Main scraping client
│   │   ├── cloudflare_bypass.py    # Cloudflare strategies
│   │   └── langchain_integration.py
│   ├── sources/
│   │   ├── clutch_scraper.py
│   │   ├── google_serp.py
│   │   └── generic.py
│   ├── agents/           # Multi-agent system
│   ├── modules/         # Browser, captcha, rate limiting
│   ├── skills/          # Self-learning
│   └── third_party/      # Services database
│       ├── scraping_services.py      # 18+ scraping services
│       └── feature_gap_analysis.py   # Gap analysis
└── webapp/             # FastAPI web app
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py firecrawl <url>` | Scrape using Firecrawl |
| `python main.py fc <url>` | Shortcut for firecrawl |
| `python main.py ask <url> "<prompt>"` | Natural language scraping |
| `python main.py xpath <url> "<selector>"` | XPath extraction |
| `python main.py geo <url> --location us` | Geographic scraping |
| `python main.py screenshot <url>` | Take screenshot |
| `python main.py server` | Start web server |
| `python main.py mcp` | Start MCP server |

---

## Firecrawl Client

```python
from scraper.integrations import FirecrawlClient

client = FirecrawlClient()

# Check if running
client.is_available()

# Scrape a URL
result = client.scrape("https://example.com")
if result["success"]:
    print(result["markdown"])  # or result["html"]

# Crawl site
pages = client.crawl("https://example.com", max_depth=2)

# Batch scrape
results = client.batch_scrape(["url1", "url2"])
```

---

## Third-Party Services Reference

```python
from scraper.third_party import SCRAPING_SERVICES, get_free_services

# All services
for service in SCRAPING_SERVICES:
    print(f"{service['name']}: {service['website']}")

# Free services only
for service in get_free_services():
    print(f"FREE: {service['name']}")
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| HTTP | requests, httpx |
| HTML Parsing | BeautifulSoup4, lxml |
| Browser | Playwright |
| Cloudflare Bypass | Firecrawl (Docker) |
| AI | LangChain, OpenAI, Anthropic |

---

## Troubleshooting

### Firecrawl not running
```bash
cd docker && docker-compose up -d
docker ps | grep firecrawl
```

### Connection refused
```bash
# Restart Firecrawl
cd docker && docker-compose restart
```

### Import errors
```bash
pip install -r requirements.txt
```

---

## Features (29 planned)

See TODO_FEATURES.md for full roadmap:
- Webhook Notifications
- Job Status API
- Scheduled Scraping
- Batch Processing
- AI/NL Extraction
- Pre-built Site Templates (20+)
- Anti-Bot Bypass Suite
- Workflow Integrations (make.com, n8n, Zapier)
- RAG Pipeline
- And more...
