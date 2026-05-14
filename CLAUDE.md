# Project Instructions

## Project Overview
**Ultimate Scraper** - A comprehensive, AI-powered web scraping solution with built-in Cloudflare bypass using Firecrawl.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| CLI Framework | argparse |
| HTTP | requests, httpx |
| HTML Parsing | BeautifulSoup4, lxml |
| Browser Automation | Playwright |
| Cloudflare Bypass | Firecrawl (local Docker) |
| AI Integration | LangChain, OpenAI, Anthropic |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start Firecrawl (required for Cloudflare bypass)
cd docker && docker-compose up -d

# Use the scraper
python main.py firecrawl "https://example.com"
```

## Using on Other Machines or Projects

### Option 1: Clone and Run
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

### Option 2: Copy Docker Folder Only
```bash
# Copy docker folder to your project
cp -r ultimate-scraper/docker your-project/

# Start Firecrawl
cd your-project/docker && docker-compose up -d

# Use Firecrawl client in Python
from scraper.integrations import FirecrawlClient
client = FirecrawlClient()
result = client.scrape("https://example.com")
```

### Option 3: Copy Firecrawl Client Only
```python
# Copy scraper/integrations/firecrawl_client.py to your project
# Then use directly
from firecrawl_client import FirecrawlClient
client = FirecrawlClient()
```

## Firecrawl Integration

Firecrawl handles Cloudflare-protected sites by:
- Bypassing Cloudflare challenges
- Rendering JavaScript
- Extracting clean markdown/HTML

### Firecrawl Setup

**Local Docker (default - no API key needed):**
```bash
cd docker && docker-compose up -d
```

**Cloud API (requires API key from firecrawl.dev):**
```python
client = FirecrawlClient({"firecrawl": {"api_key": "fc-xxx"}})
```

**Self-hosted:**
```python
client = FirecrawlClient({"firecrawl": {"base_url": "http://your-server:3002"}})
```

### Firecrawl Methods

| Method | Description |
|--------|-------------|
| `client.scrape(url)` | Scrape with HTML + Markdown |
| `client.scrape_markdown(url)` | Get markdown only |
| `client.scrape_html(url)` | Get HTML only |
| `client.crawl(url, max_depth=2)` | Crawl site recursively |
| `client.map(url)` | Discover all URLs on domain |
| `client.batch_scrape(urls)` | Scrape multiple URLs |

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py firecrawl <url>` | Scrape using Firecrawl |
| `python main.py fc <url>` | Shortcut for firecrawl |
| `python main.py ask <url> "<prompt>"` | Natural language scraping |
| `python main.py xpath <url> "<selector>"` | XPath extraction |
| `python main.py geo <url> --location us` | Geographic scraping |
| `python main.py server` | Start FastAPI web server |
| `python main.py mcp` | Start MCP server |

## Project Structure

```
ultimate-scraper/
├── main.py                    # CLI entry point
├── config.yaml               # Configuration
├── requirements.txt          # Python dependencies
├── docker/                   # Firecrawl Docker (copy to any project)
│   ├── docker-compose.yaml
│   ├── .env
│   ├── start.sh
│   └── stop.sh
├── scraper/
│   ├── integrations/         # Third-party integrations
│   │   ├── firecrawl_client.py    # Firecrawl integration
│   │   └── cloudflare_bypass.py  # Cloudflare strategies
│   ├── sources/              # Website-specific scrapers
│   │   └── clutch_scraper.py
│   ├── third_party/          # Third-party services reference
│   │   └── scraping_services.py    # 18+ services with details
│   └── modules/              # Core modules
└── data/                    # Scraped data output
```

## Third-Party Services Reference

The `scraper/third_party/` module contains information about 18+ external scraping services.

```python
from scraper.third_party import SCRAPING_SERVICES, get_free_services

# Get all services
for service in SCRAPING_SERVICES:
    print(f"{service['name']}: {service['website']}")

# Get free services only
for service in get_free_services():
    print(f"FREE: {service['name']}")

# Filter by tier
from scraper.third_party import get_services_by_tier
enterprise = get_services_by_tier('enterprise')

# Filter by feature
from scraper.third_party import get_services_by_feature
with_js = get_services_by_feature('js_rendering')

# Get recommendations
from scraper.third_party import get_recommendation
recommendations = get_recommendation(budget='medium', features_needed=['js_rendering'])
```

## Code Style

- **File naming**: snake_case for Python files
- **Class naming**: PascalCase (e.g., `FirecrawlClient`)
- **Module structure**: Each feature has its own directory with `__init__.py`
- **Error handling**: Uses `loguru` for logging

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
  strategy: "cloudscraper"
```

## Troubleshooting

### Firecrawl not running
```bash
cd docker && docker-compose up -d
docker ps | grep firecrawl
```

### Connection refused
```bash
# Check Docker is running
docker ps

# Restart Firecrawl
cd docker && docker-compose restart
```
