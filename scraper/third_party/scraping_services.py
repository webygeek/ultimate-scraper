"""
Third-Party Web Scraping Services Database

Comprehensive reference of external scraping services.
Use this for comparison and integration planning.

Quick Reference:
    from scraper.third_party import SCRAPING_SERVICES

    # Get all services
    for service in SCRAPING_SERVICES:
        print(f"{service['name']}: {service['website']}")

    # Filter by features
    free_services = [s for s in SCRAPING_SERVICES if s['pricing'].get('free_tier')]
    enterprise_services = [s for s in SCRAPING_SERVICES if s['tier'] == 'enterprise']
"""

SCRAPING_SERVICES = [
    # =========================================================================
    # ENTERPRISE GRADE
    # =========================================================================

    {
        "name": "Bright Data",
        "website": "https://brightdata.com",
        "description": "Most comprehensive enterprise scraping solution with 400M+ IPs",
        "tier": "enterprise",
        "products": [
            "Web Scraper IDE",
            "Scraper APIs (pre-built & custom)",
            "AI Scraper Studio",
            "Unlocker API",
            "SERP API",
            "Browser API",
            "Crawl API",
            "Dataset Marketplace",
            "Data Feeds",
            "Residential/Datacenter/ISP Proxies",
        ],
        "features": {
            "ip_pool": "400M+ IPs",
            "countries": "195 countries",
            "success_rate": "~99%",
            "js_rendering": True,
            "ai_extraction": True,
            "geotargeting": True,
            "captcha_solving": True,
            "unlimited_scale": True,
        },
        "pricing": {
            "starting_price": "$300+/month",
            "free_tier": False,
            "model": "Usage-based",
            "notes": "Enterprise pricing, contact sales",
        },
        "integrations": ["LangChain", "ChatGPT", "Zapier", "Airbyte"],
        "compliance": ["SOC2", "GDPR", "CCPA"],
        "uptime": "99.9%",
        "use_cases": [
            "Enterprise data collection",
            "Market research",
            "Competitor analysis",
            "Brand monitoring",
        ],
        "pros": [
            "Largest proxy network",
            "Most comprehensive features",
            "AI-powered extraction",
            "Legal compliance",
        ],
        "cons": [
            "Expensive",
            "Complex setup",
            "Enterprise focus",
        ],
    },

    {
        "name": "Zyte (formerly Crawlera)",
        "website": "https://www.zyte.com",
        "description": "AI-powered ban avoidance with smart proxy rotation",
        "tier": "enterprise",
        "products": [
            "Smart Proxy Manager",
            "Zyte Cloud",
            "Automatic Ban Detection",
            "Headless Browser",
        ],
        "features": {
            "ip_pool": "Large residential pool",
            "countries": "200+ countries",
            "success_rate": "~99%",
            "js_rendering": True,
            "ai_extraction": True,
            "geotargeting": True,
            "captcha_solving": "Automatic",
            "smart_rotation": True,
        },
        "pricing": {
            "starting_price": "Usage-based",
            "free_tier": False,
            "model": "Pay-as-you-go",
            "notes": "Cost estimator available",
        },
        "integrations": ["Python", "Scrapy", "Selenium", "Playwright"],
        "use_cases": [
            "E-commerce scraping",
            "Price monitoring",
            "Anti-bot testing",
        ],
        "pros": [
            "AI ban avoidance",
            "Smart rotation",
            "Headless browser",
        ],
        "cons": [
            "Higher cost",
            "Learning curve",
        ],
    },

    {
        "name": "Oxylabs",
        "website": "https://www.oxylabs.io",
        "description": "Full-stack data extraction with AI Studio",
        "tier": "enterprise",
        "products": [
            "Web Scraper API",
            "Web Unblocker",
            "AI Studio",
            "Fast Search API",
            "Residential/Mobile/Datacenter/ISP Proxies",
            "Custom Datasets",
        ],
        "features": {
            "ip_pool": "Large pool",
            "countries": "Global coverage",
            "success_rate": "99%+",
            "js_rendering": True,
            "ai_extraction": "AI Scraper, AI Crawler, AI Search",
            "response_time": "<1 second",
            "geotargeting": True,
            "captcha_solving": True,
        },
        "pricing": {
            "starting_price": "Enterprise pricing",
            "free_tier": False,
            "model": "Subscription",
            "notes": "Contact sales for pricing",
        },
        "integrations": ["ChatGPT", "LangChain", "Zapier", "30+ tools"],
        "use_cases": [
            "AI workflows",
            "Enterprise scraping",
            "SERP data",
        ],
        "pros": [
            "AI Studio for natural language",
            "<1s response time",
            "99%+ success rate",
        ],
        "cons": [
            "Enterprise focus",
            "No transparent pricing",
        ],
    },

    {
        "name": "Apify",
        "website": "https://apify.com",
        "description": "Largest marketplace of ready-made scrapers (29,000+ Actors)",
        "tier": "enterprise",
        "products": [
            "Actor Marketplace (29,000+)",
            "Crawlee SDK",
            "Proxy Manager",
            "Data Storage",
            "Scheduler",
        ],
        "features": {
            "marketplace": "29,000+ Actors",
            "success_rate": "99.95% uptime",
            "js_rendering": True,
            "ai_extraction": "Via Actors",
            "geotargeting": True,
            "captcha_solving": "Via Actors",
            "auto_scaling": True,
        },
        "pricing": {
            "starting_price": "$500 free credits",
            "free_tier": True,
            "model": "Pay-as-you-go",
            "notes": "$500 free for new creators",
        },
        "integrations": ["Zapier", "GitHub", "Google Sheets", "Slack", "MCP"],
        "compliance": ["SOC2", "GDPR", "CCPA"],
        "use_cases": [
            "Social media scraping",
            "E-commerce",
            "Maps data",
            "Quick start projects",
        ],
        "pros": [
            "Massive marketplace",
            "No coding needed",
            "Many ready-made solutions",
        ],
        "cons": [
            "Variable Actor quality",
            "Can get expensive",
        ],
    },

    # =========================================================================
    # MID-TIER APIs
    # =========================================================================

    {
        "name": "ScraperAPI",
        "website": "https://www.scraperapi.com",
        "description": "Simple API with structured data outputs and async scraping",
        "tier": "mid-tier",
        "products": [
            "Scraping API",
            "Async Scraper",
            "Structured Data",
            "DataPipeline (no-code)",
            "LangChain Integration",
        ],
        "features": {
            "success_rate": "~99%",
            "js_rendering": True,
            "ai_extraction": True,
            "geotargeting": True,
            "captcha_solving": True,
            "async_scraping": True,
            "structured_output": True,
        },
        "pricing": {
            "starting_price": "~$25/month",
            "free_tier": True,
            "model": "Credits-based",
            "notes": "Recently acquired Traject Data for enterprise",
        },
        "integrations": ["cURL", "Python", "NodeJS", "PHP", "Ruby", "Java", "LangChain"],
        "use_cases": [
            "E-commerce data",
            "SERP collection",
            "Market research",
            "AI applications",
        ],
        "pros": [
            "Simple API",
            "Structured data outputs",
            "LangChain ready",
        ],
        "cons": [
            "Credit system complexity",
            "Rate limits on lower tiers",
        ],
    },

    {
        "name": "ScrapingBee",
        "website": "https://www.scrapingbee.com",
        "description": "JavaScript rendering with AI-powered natural language extraction",
        "tier": "mid-tier",
        "products": [
            "Web Scraping API",
            "Google Search API",
            "Amazon/Walmart/YouTube APIs",
            "AI Extraction",
            "MCP Server",
        ],
        "features": {
            "success_rate": "99.9% (Google Search)",
            "js_rendering": True,
            "ai_extraction": True,  # Natural language queries
            "geotargeting": True,
            "captcha_solving": True,
            "screenshot": True,
        },
        "pricing": {
            "starting_price": "$49/month",
            "free_tier": True,
            "model": "Credits-based",
            "credits": "250,000/month (Freelance)",
            "plans": {
                "Freelance": "$49 (250k credits)",
                "Startup": "$99 (1M credits)",
                "Business": "$249 (3M credits)",
                "Business+": "$599 (8M credits)",
            },
        },
        "integrations": ["CLI", "MCP Server", "Make", "n8n", "Zapier"],
        "use_cases": [
            "Dynamic content",
            "Google searches",
            "AI applications",
        ],
        "pros": [
            "AI natural language extraction",
            "MCP server",
            "High success rate",
        ],
        "cons": [
            "Pricier than competitors",
        ],
    },

    {
        "name": "SerpAPI",
        "website": "https://www.serpapi.com",
        "description": "Best for SERP data - 100+ search engines and e-commerce sites",
        "tier": "mid-tier",
        "products": [
            "Search Engine APIs (100+)",
            "E-commerce APIs (50+)",
            "X-Ray",
            "ZeroTrace Mode",
            "Ludicrous Speed",
        ],
        "features": {
            "search_engines": "100+ including Google, Bing, DuckDuckGo, Baidu, Yandex",
            "ecommerce": "Amazon, Walmart, eBay, Home Depot, etc.",
            "success_rate": "High",
            "structured_output": True,
            "js_rendering": False,
        },
        "pricing": {
            "starting_price": "$25/month",
            "free_tier": True,
            "model": "Search-based",
            "plans": {
                "Free": "250 searches/month",
                "Starter": "$25 (1,000 searches)",
                "Developer": "$75 (5,000 searches)",
                "Production": "$150 (15,000 searches)",
                "Big Data": "$275 (30,000 searches)",
            },
            "notes": "U.S. Legal Shield included",
        },
        "integrations": ["Python", "Ruby", "JavaScript", "Go", "PHP", "Java", "Rust", ".Net", "MCP"],
        "use_cases": [
            "SERP tracking",
            "SEO monitoring",
            "Price comparison",
            "Rank tracking",
        ],
        "pros": [
            "Best for search engines",
            "50+ e-commerce sites",
            "Legal protection",
        ],
        "cons": [
            "Limited to supported sites",
            "No JS rendering",
        ],
    },

    {
        "name": "Scrapingdog",
        "website": "https://www.scrapingdog.com",
        "description": "40M+ rotating proxies with built-in CAPTCHA solving",
        "tier": "mid-tier",
        "products": [
            "Web Scraping API",
            "Google/Amazon/Walmart/LinkedIn APIs",
            "40M+ Rotating Proxies",
        ],
        "features": {
            "ip_pool": "40M+ proxies",
            "success_rate": "~99%",
            "js_rendering": True,
            "ai_extraction": True,  # LLM-ready JSON
            "geotargeting": True,
            "captcha_solving": "Built-in",
            "concurrency": "Up to 100 requests",
        },
        "pricing": {
            "starting_price": "$40/month",
            "free_tier": True,
            "model": "Credits-based",
            "credits": "200,000 requests (Starter)",
            "plans": {
                "Starter": "$40 (200k requests)",
                "Pro": "$100+ (various)",
                "Custom": "$30,000 (1B+ requests)",
            },
            "notes": "Annual plans discounted",
        },
        "integrations": ["Python", "NodeJS", "Ruby", "PHP", "Go"],
        "use_cases": [
            "High-volume scraping",
            "Social media",
            "LinkedIn scraping",
        ],
        "pros": [
            "Built-in CAPTCHA solving",
            "40M+ proxies",
            "LLM-ready JSON",
        ],
        "cons": [
            "LinkedIn API requires login",
        ],
    },

    {
        "name": "PhantomBuster",
        "website": "https://phantombuster.com",
        "description": "Social media scraping and automation specialist",
        "tier": "mid-tier",
        "products": [
            "LinkedIn Scraper",
            "Instagram Scraper",
            "Twitter/X Scraper",
            "Facebook Scraper",
            "Outreach Automation",
        ],
        "features": {
            "social_media": True,
            "automated_outreach": True,
            "prospecting": True,
            "email_finding": True,
        },
        "pricing": {
            "starting_price": "$99/month",
            "free_tier": False,
            "model": "Subscription",
            "notes": "Per-seat pricing",
        },
        "integrations": ["HubSpot", "Salesforce", "Airtable", "Google Sheets"],
        "use_cases": [
            "LinkedIn prospecting",
            "Social media automation",
            "Lead generation",
        ],
        "pros": [
            "Best for social media",
            "Outreach automation",
            "Email finding",
        ],
        "cons": [
            "Social media focus only",
            "Account risk",
            "Expensive",
        ],
    },

    # =========================================================================
    # BUDGET / STARTUP
    # =========================================================================

    {
        "name": "DataImpulse",
        "website": "https://www.dataimpulse.com",
        "description": "Affordable residential proxies with free geotargeting",
        "tier": "budget",
        "products": [
            "Residential Proxies",
            "Datacenter Proxies",
            "Mobile Proxies",
            "Premium Residential",
        ],
        "features": {
            "ip_pool": "90M+ IPs",
            "countries": "195+ countries",
            "success_rate": "99.9%",
            "geotargeting": "Free (state/city/ZIP/ASN)",
            "sticky_sessions": True,
        },
        "pricing": {
            "starting_price": "$5 (5GB)",
            "free_tier": False,
            "model": "Pay-per-traffic",
            "notes": "Traffic never expires",
            "plans": {
                "Intro": "$5 (5GB, ~$1/GB)",
                "Basic": "$50 (50GB, ~$1/GB)",
                "Advanced": "$800 (1TB, ~$0.8/GB)",
            },
        },
        "integrations": ["API", "HTTP(S)", "SOCKS5"],
        "use_cases": [
            "Budget scraping",
            "High-volume proxies",
            "Geotargeted requests",
        ],
        "pros": [
            "Cheapest residential proxies",
            "Free geotargeting",
            "No traffic expiration",
        ],
        "cons": [
            "Proxy only (no API)",
            "No JS rendering",
        ],
    },

    {
        "name": "Crawlera",
        "website": "https://www.zyte.com/smart-proxy-manager/",
        "description": "Now part of Zyte - smart rotating proxy with ban avoidance",
        "tier": "budget",
        "products": [
            "Smart Proxy Rotation",
            "Ban Detection",
            "Automatic Retries",
        ],
        "features": {
            "success_rate": "~98%",
            "js_rendering": False,
            "geotargeting": True,
            "captcha_solving": "Automatic",
            "smart_rotation": True,
        },
        "pricing": {
            "starting_price": "$29/month",
            "free_tier": False,
            "model": "Usage-based",
        },
        "integrations": ["Scrapy", "Selenium", "Playwright", "Requests"],
        "use_cases": [
            "Budget-friendly scraping",
            "Scrapy integration",
        ],
        "pros": [
            "Scrapy native support",
            "Automatic ban avoidance",
        ],
        "cons": [
            "No JS rendering",
            "Merged with Zyte",
        ],
    },

    # =========================================================================
    # OPEN SOURCE / SELF-HOSTED
    # =========================================================================

    {
        "name": "Firecrawl",
        "website": "https://firecrawl.dev",
        "description": "Open-source Cloudflare bypass and site crawler",
        "tier": "opensource",
        "products": [
            "Self-hosted Docker",
            "Cloud API",
            "SDK (Python, JS, Go, etc.)",
        ],
        "features": {
            "cloudflare_bypass": True,
            "js_rendering": True,
            "markdown_extraction": True,
            "crawling": True,
            "map_discovery": True,
            "batch_scrape": True,
        },
        "pricing": {
            "starting_price": "Free (self-hosted)",
            "free_tier": True,
            "cloud_tier": "500 credits/month free",
            "model": "Self-hosted or subscription",
        },
        "integrations": ["Python", "NodeJS", "Go", "Ruby", "PHP", "LangChain"],
        "github": "https://github.com/mendableai/firecrawl",
        "docker": "c:/tmp/firecrawl or project docker/ folder",
        "use_cases": [
            "Cloudflare-protected sites",
            "Static site crawling",
            "Budget scraping",
            "Self-hosted solutions",
        ],
        "pros": [
            "Free self-hosted",
            "Great Cloudflare bypass",
            "Markdown output",
            "Easy Docker setup",
        ],
        "cons": [
            "~95% success rate (vs 99%)",
            "Self-maintenance",
        ],
    },

    {
        "name": "Crawlab",
        "website": "https://crawlab.io",
        "description": "Open-source spider management and distributed crawling",
        "tier": "opensource",
        "products": [
            "Spider Management",
            "Task Scheduler",
            "Distributed Nodes",
            "Results Storage",
        ],
        "features": {
            "spider_management": True,
            "distributed_crawling": True,
            "scheduled_tasks": True,
            "multi_language": ["Python", "Node.js", "Go", "Java"],
            "scrapy_support": True,
        },
        "pricing": {
            "starting_price": "Free (Community)",
            "free_tier": True,
            "model": "Self-hosted",
            "plans": {
                "Community": "Free",
                "Enterprise": "$140/year",
                "Permanent": "$400 one-time",
            },
        },
        "integrations": ["Scrapy", "Selenium", "Playwright", "Custom spiders"],
        "github": "https://github.com/crawlab-team/crawlab",
        "use_cases": [
            "Spider orchestration",
            "Distributed crawling",
            "Team collaboration",
        ],
        "pros": [
            "Free self-hosted",
            "Spider management",
            "Distributed crawling",
        ],
        "cons": [
            "No built-in proxy rotation",
            "Requires spiders",
        ],
    },

    {
        "name": "Crawlee (Apify SDK)",
        "website": "https://crawlee.dev",
        "description": "Open-source web scraping and browser automation library",
        "tier": "opensource",
        "products": [
            "Crawlee (Python)",
            "Crawlee (Node.js)",
            "Playwright/Puppeteer integration",
        ],
        "features": {
            "auto_scaling": True,
            "proxy_rotation": True,
            "request_queue": True,
            "storage": True,
            "js_rendering": True,
        },
        "pricing": {
            "starting_price": "Free",
            "free_tier": True,
            "model": "Open source",
        },
        "github": "https://github.com/apify/crawlee",
        "integrations": ["Playwright", "Puppeteer", "Cheerio", "BeautifulSoup"],
        "use_cases": [
            "Building custom scrapers",
            "Headless browsing",
            "Large-scale crawling",
        ],
        "pros": [
            "Free and open source",
            "Well-maintained",
            "Apify integration",
        ],
        "cons": [
            "Requires coding",
            "No proxy pool included",
        ],
    },

    {
        "name": "Nitter",
        "website": "https://github.com/zedeus/nitter",
        "description": "Open-source Twitter/X alternative (no API needed)",
        "tier": "opensource",
        "products": [
            "Self-hosted Twitter frontend",
            "RSS feeds",
            "API access",
        ],
        "features": {
            "no_auth_required": True,
            "rss_feeds": True,
            "json_api": True,
        },
        "pricing": {
            "starting_price": "Free",
            "free_tier": True,
            "model": "Self-hosted",
        },
        "github": "https://github.com/zedeus/nitter",
        "use_cases": [
            "Twitter scraping without API",
            "Archive tweets",
            "Research",
        ],
        "pros": [
            "No Twitter API needed",
            "Free",
        ],
        "cons": [
            "Twitter actively blocks",
            "Instance reliability varies",
        ],
    },

    # =========================================================================
    # SPECIALIZED SERVICES
    # =========================================================================

    {
        "name": "SerpAPI (Specialized)",
        "website": "https://www.serpapi.com",
        "description": "Specialized in search engine and e-commerce scraping",
        "tier": "specialized",
        "products": [
            "Google Search API",
            "Google Maps API",
            "Amazon Product API",
            "Walmart API",
            "eBay API",
        ],
        "features": {
            "search_engines": 100,
            "ecommerce_sites": 50,
            "structured_data": True,
            "historical_data": "Some sites",
        },
        "pricing": {
            "starting_price": "$25/month",
            "free_tier": True,
            "model": "Credits per search",
        },
        "use_cases": [
            "SEO tracking",
            "Price monitoring",
            "Competitor analysis",
            "Local SEO",
        ],
        "pros": [
            "Best for search/e-commerce",
            "Reliable structured data",
        ],
        "cons": [
            "Limited to supported sites",
        ],
    },

    {
        "name": "Diffbot",
        "website": "https://www.diffbot.com",
        "description": "AI-powered article and product extraction",
        "tier": "specialized",
        "products": [
            "Article API",
            "Product API",
            "Image API",
            "Video API",
            "Forum API",
        ],
        "features": {
            "ai_extraction": True,
            "structured_data": True,
            "no_selectors": True,  # Automatic extraction
        },
        "pricing": {
            "starting_price": "$300/month",
            "free_tier": True,
            "model": "Credits-based",
            "notes": "1,000 free credits/month",
        },
        "use_cases": [
            "News aggregation",
            "E-commerce data",
            "Article scraping",
        ],
        "pros": [
            "AI automatic extraction",
            "No CSS selectors needed",
        ],
        "cons": [
            "Expensive",
            "AI can miss details",
        ],
    },

    {
        "name": "Glera",
        "website": "https://www.glera.com",
        "description": "Real-time web scraping with change detection",
        "tier": "specialized",
        "products": [
            "Real-time Scraping",
            "Change Detection",
            "Monitoring API",
        ],
        "features": {
            "real_time": True,
            "change_detection": True,
            "monitoring": True,
        },
        "pricing": {
            "starting_price": "Contact sales",
            "free_tier": False,
            "model": "Subscription",
        },
        "use_cases": [
            "Price monitoring",
            "Competitor tracking",
            "Change alerts",
        ],
        "pros": [
            "Real-time updates",
            "Change detection",
        ],
        "cons": [
            "Niche use case",
            "Limited info",
        ],
    },
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_services_by_tier(tier: str) -> list:
    """Get all services in a specific tier."""
    return [s for s in SCRAPING_SERVICES if s.get("tier") == tier]


def get_services_by_feature(feature: str) -> list:
    """Get services that have a specific feature."""
    return [
        s for s in SCRAPING_SERVICES
        if s.get("features", {}).get(feature)
    ]


def get_free_services() -> list:
    """Get all services with free tiers."""
    return [s for s in SCRAPING_SERVICES if s.get("pricing", {}).get("free_tier")]


def get_services_by_use_case(use_case: str) -> list:
    """Get services suitable for a specific use case."""
    return [
        s for s in SCRAPING_SERVICES
        if use_case.lower() in [uc.lower() for uc in s.get("use_cases", [])]
    ]


def compare_services(service_names: list) -> dict:
    """Compare specific services side by side."""
    services = [
        s for s in SCRAPING_SERVICES
        if s["name"] in service_names
    ]

    comparison = {
        "services": services,
        "features": {},
        "pricing": {},
    }

    for service in services:
        comparison["features"][service["name"]] = service.get("features", {})
        comparison["pricing"][service["name"]] = service.get("pricing", {})

    return comparison


def get_recommendation(
    budget: str = "medium",
    features_needed: list = None,
    use_case: str = None,
) -> list:
    """
    Get service recommendations based on requirements.

    Args:
        budget: "free", "low", "medium", "high", "enterprise"
        features_needed: List of required features
        use_case: Primary use case

    Returns:
        List of recommended services
    """
    recommendations = []

    # Filter by budget
    if budget == "free":
        recommendations = get_free_services()
    elif budget == "low":
        recommendations = [s for s in SCRAPING_SERVICES if "free" in str(s.get("pricing", {}).get("starting_price", ""))]
    elif budget == "medium":
        recommendations = [s for s in SCRAPING_SERVICES if s.get("tier") in ["mid-tier", "budget"]]
    elif budget == "high":
        recommendations = [s for s in SCRAPING_SERVICES if s.get("tier") in ["mid-tier", "enterprise"]]
    elif budget == "enterprise":
        recommendations = [s for s in SCRAPING_SERVICES if s.get("tier") == "enterprise"]

    # Filter by features
    if features_needed:
        recommendations = [
            s for s in recommendations
            if all(s.get("features", {}).get(f) for f in features_needed)
        ]

    # Filter by use case
    if use_case:
        recommendations = get_services_by_use_case(use_case)

    return recommendations


# =============================================================================
# QUICK REFERENCE TABLE
# =============================================================================

QUICK_REFERENCE = """
╔═══════════════════════════╦═══════════════╦═══════════════╦═══════════╗
║ Service                   ║ Tier          ║ Success Rate  ║ Price      ║
╠═══════════════════════════╬═══════════════╬═══════════════╬═══════════╣
║ Bright Data              ║ Enterprise    ║ ~99%          ║ $300+/mo   ║
║ Zyte                     ║ Enterprise    ║ ~99%          ║ Usage-based║
║ Oxylabs                 ║ Enterprise    ║ 99%+          ║ Enterprise ║
║ Apify                    ║ Enterprise    ║ 99.95%        ║ Free tier ║
╠═══════════════════════════╬═══════════════╬═══════════════╬═══════════╣
║ ScraperAPI              ║ Mid-tier     ║ ~99%          ║ $25+/mo    ║
║ ScrapingBee             ║ Mid-tier     ║ 99.9%         ║ $49+/mo    ║
║ SerpAPI                 ║ Mid-tier     ║ High          ║ $25+/mo    ║
║ Scrapingdog             ║ Mid-tier     ║ ~99%          ║ $40+/mo    ║
╠═══════════════════════════╬═══════════════╬═══════════════╬═══════════╣
║ DataImpulse              ║ Budget        ║ 99.9%         ║ $5+        ║
║ Crawlera                 ║ Budget        ║ ~98%          ║ $29+/mo    ║
╠═══════════════════════════╬═══════════════╬═══════════════╬═══════════╣
║ Firecrawl                ║ Open Source  ║ ~95%          ║ FREE       ║
║ Crawlab                   ║ Open Source  ║ Varies        ║ FREE       ║
║ Crawlee                   ║ Open Source  ║ Varies        ║ FREE       ║
╚═══════════════════════════╝═══════════════╝═══════════════╝═══════════╝
"""

if __name__ == "__main__":
    print("Third-Party Web Scraping Services")
    print("=" * 60)
    print()
    print(QUICK_REFERENCE)
    print()
    print(f"Total services: {len(SCRAPING_SERVICES)}")
    print()
    print("Usage in Python:")
    print("  from scraper.third_party import SCRAPING_SERVICES")
    print("  from scraper.third_party import get_free_services, get_recommendation")
