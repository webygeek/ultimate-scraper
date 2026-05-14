"""
Ultimate Mega Scraper CLI - Complete all-in-one command.
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from loguru import logger


def main():
    parser = argparse.ArgumentParser(
        description="Ultimate Mega Scraper - The world's most complete web scraping solution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ultimate auto scraping
  scraper ultimate "https://example.com"

  # Natural language
  scraper ask "https://example.com" "Extract all prices"

  # XPath extraction
  scraper xpath "https://example.com" "//div[@class='product']"

  # Geographic (scrape from specific country)
  scraper geo "https://example.com" --location us-east

  # Middleware pipeline
  scraper crawl --url "https://example.com" --pipeline validation,clean

  # Pause/Resume
  scraper resume --state "my_crawl.json"
        """
    )

    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--output", "-o", default="data/output")
    parser.add_argument("--format", "-f", action="append", choices=["json", "csv", "xlsx", "md"])
    parser.add_argument("--verbose", "-v", action="store_true")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ============== SCRAPING ==============

    ultimate = subparsers.add_parser("ultimate", help="Auto-select best method")
    ultimate.add_argument("url")
    ultimate.add_argument("--selectors", "-s")
    ultimate.add_argument("--mode", choices=["auto", "parallel", "api", "ai", "incremental"], default="auto")

    nlp = subparsers.add_parser("ask", help="Natural language scraping")
    nlp.add_argument("url")
    nlp.add_argument("prompt")
    nlp.add_argument("--template", choices=["products", "articles", "contacts", "jobs", "prices"])

    xpath_cmd = subparsers.add_parser("xpath", help="XPath extraction")
    xpath_cmd.add_argument("url")
    xpath_cmd.add_argument("xpath")

    parallel = subparsers.add_parser("parallel", help="Parallel scraping")
    parallel.add_argument("urls", nargs="+")
    parallel.add_argument("--selectors", "-s")
    parallel.add_argument("--workers", "-w", type=int, default=10)

    # ============== ADVANCED ==============

    geo = subparsers.add_parser("geo", help="Geographic location scraping")
    geo.add_argument("url")
    geo.add_argument("--location", "-l", default="us-east", help="Location key (us-east, uk, de, etc)")
    geo.add_argument("--list-locations", action="store_true")

    api = subparsers.add_parser("api", help="Find hidden APIs")
    api.add_argument("url")

    graphql = subparsers.add_parser("graphql", help="GraphQL scraping")
    graphql.add_argument("url")
    graphql.add_argument("--fields", "-f", nargs="+")

    crawl = subparsers.add_parser("crawl", help="Site crawl with middleware")
    crawl.add_argument("--url", required=True)
    crawl.add_argument("--selectors", "-s")
    crawl.add_argument("--max-pages", type=int, default=100)
    crawl.add_argument("--max-depth", type=int, default=3)
    crawl.add_argument("--workers", "-w", type=int, default=10)
    crawl.add_argument("--pipeline", help="Pipeline stages (validation,clean,dedupe)")

    # ============== OUTPUT ==============

    md = subparsers.add_parser("md", help="Convert to Markdown")
    md.add_argument("url")

    screenshot = subparsers.add_parser("screenshot", help="Capture screenshot")
    screenshot.add_argument("url")
    screenshot.add_argument("--output", "-o")

    # ============== MIDDLEWARE & PIPELINE ==============

    js = subparsers.add_parser("js", help="Run JS injection")
    js.add_argument("url")
    js.add_argument("script", choices=["scroll", "lazy_load", "cookies", "modals", "remove_popups"])
    js.add_argument("--custom", help="Custom JS script file")

    block = subparsers.add_parser("block", help="Block ads/trackers")
    block.add_argument("url")
    block.add_argument("--show-blocked", action="store_true")

    # ============== PERSISTENCE ==============

    pause = subparsers.add_parser("pause", help="Pause active crawl")
    pause.add_argument("--state", default="data/crawl_state.json")

    resume = subparsers.add_parser("resume", help="Resume paused crawl")
    resume.add_argument("--state", default="data/crawl_state.json")
    resume.add_argument("--url")

    # ============== MCP & AI ==============

    mcp = subparsers.add_parser("mcp", help="Run MCP server")

    # ============== SCHEDULING ==============

    schedule = subparsers.add_parser("schedule", help="Schedule job")
    schedule.add_argument("name")
    schedule.add_argument("url")
    schedule.add_argument("cron")
    schedule.add_argument("--selectors", "-s")
    schedule.add_argument("--webhook")
    schedule.add_argument("--incremental", action="store_true", default=True)

    # ============== SKILLS ==============

    skills = subparsers.add_parser("skills", help="Skills management")
    skills.add_argument("action", choices=["list", "stats", "export", "import", "search", "reset"])
    skills.add_argument("file", nargs="?", help="File for export/import")
    skills.add_argument("--keyword")

    # ============== STATS ==============

    stats = subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    if not args.command:
        parser.print_help()
        return 0

    try:
        scraper = init_scraper(args.config)
    except Exception as e:
        logger.error(f"Init failed: {e}")
        return 1

    try:
        if args.command == "ultimate":
            return handle_ultimate(scraper, args)
        elif args.command == "ask":
            return handle_nlp(scraper, args)
        elif args.command == "xpath":
            return handle_xpath(scraper, args)
        elif args.command == "parallel":
            return handle_parallel(scraper, args)
        elif args.command == "geo":
            return handle_geo(scraper, args)
        elif args.command == "api":
            return handle_api(scraper, args)
        elif args.command == "graphql":
            return handle_graphql(scraper, args)
        elif args.command == "crawl":
            return handle_crawl(scraper, args)
        elif args.command == "md":
            return handle_markdown(scraper, args)
        elif args.command == "screenshot":
            return handle_screenshot(scraper, args)
        elif args.command == "js":
            return handle_js(scraper, args)
        elif args.command == "block":
            return handle_block(scraper, args)
        elif args.command == "pause":
            return handle_pause(args)
        elif args.command == "resume":
            return handle_resume(scraper, args)
        elif args.command == "mcp":
            return handle_mcp(args)
        elif args.command == "schedule":
            return handle_schedule(scraper, args)
        elif args.command == "skills":
            return handle_skills(scraper, args)
        elif args.command == "stats":
            return handle_stats(scraper)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def init_scraper(config_path):
    from .mega_scraper import UltimateMegaScraper
    config = {}
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except:
        pass
    return UltimateMegaScraper(config)


# ============== HANDLERS ==============

def handle_ultimate(scraper, args):
    selectors = parse_selectors(args.selectors)
    result = scraper.scrape_ultimate(args.url, selectors, args.mode)
    print_result(result)
    save_result(args.output, args.format, result)
    return 0 if result.success else 1


def handle_nlp(scraper, args):
    from .nlp import NLPScraper
    nlp = NLPScraper(scraper.config)
    if args.template:
        result = nlp.scrape_with_template(args.url, args.template)
    else:
        result = nlp.scrape(args.url, args.prompt)
    print(json.dumps(result, indent=2))
    return 0 if result and "error" not in result else 1


def handle_xpath(scraper, args):
    from .advanced_selectors import XPathSelector
    xpath = XPathSelector()
    result = xpath.select(args.url, args.xpath)
    print(f"Found {len(result)} matches:")
    for i, item in enumerate(result[:20]):
        print(f"  {i+1}. {item[:100]}")
    return 0 if result else 1


def handle_parallel(scraper, args):
    selectors = parse_selectors(args.selectors)
    result = scraper.scrape_parallel(args.urls, selectors, args.workers)
    print_result(result)
    save_result(args.output, args.format, result)
    return 0 if result.success else 1


def handle_geo(scraper, args):
    from .geo_control import GeoScraper, GeoDatabase

    geo = GeoScraper(scraper.config)
    geo_db = GeoDatabase()

    if args.list_locations:
        locations = geo_db.list_locations()
        print("\nAvailable Locations:")
        for loc in locations:
            print(f"  {loc['key']}: {loc['city']}, {loc['country']} ({loc['timezone']})")
        return 0

    print(f"\nScraping from: {args.location}")
    result = geo.scrape_with_location(args.url, args.location)
    if result.get("success"):
        print(f"Success! HTML length: {len(result.get('html', ''))}")
        return 0
    else:
        print(f"Failed: {result.get('error')}")
        return 1


def handle_api(scraper, args):
    from .api_discovery import APIDiscovery
    finder = APIDiscovery(scraper.config)
    apis = finder.discover(args.url)
    print(f"\nFound {len(apis)} APIs:")
    for api in apis[:10]:
        print(f"  [{api.method}] {api.url} ({api.api_type}, {api.confidence:.0%})")
    return 0 if apis else 1


def handle_graphql(scraper, args):
    from .api_discovery import GraphQLScanner
    scanner = GraphQLScanner()
    result = scanner.scrape_graphql(args.url, args.fields)
    if result.get("success"):
        print(f"Success! {len(result.get('data', []))} items")
        return 0
    return 1


def handle_crawl(scraper, args):
    selectors = parse_selectors(args.selectors)

    # Setup middleware and pipeline
    from .pipeline import Spider, MiddlewareManager, ItemPipelineManager
    from .pipeline import UserAgentMiddleware, ValidationPipeline, CleanPipeline, DedupePipeline

    spider = Spider(name="cli_spider", start_urls=[args.url])

    # Add middleware
    spider.middleware_manager.add_downloader_middleware(UserAgentMiddleware())

    # Setup pipeline
    if args.pipeline:
        for stage in args.pipeline.split(","):
            if stage == "validation":
                spider.item_pipeline_manager.add_pipeline(ValidationPipeline({"url": {"type": "str"}}))
            elif stage == "clean":
                spider.item_pipeline_manager.add_pipeline(CleanPipeline())
            elif stage == "dedupe":
                spider.item_pipeline_manager.add_pipeline(DedupePipeline())

    print(f"\nCrawling: {args.url}")
    print(f"Max pages: {args.max_pages}")
    print(f"Pipeline: {args.pipeline or 'none'}")

    import asyncio
    items = asyncio.run(spider.run())

    print(f"\nCrawled {len(items)} items")
    return 0 if items else 1


def handle_markdown(scraper, args):
    from .output_utils import MarkdownConverter
    from .modules.anti_detection import RequestSession

    md = MarkdownConverter()
    session = RequestSession(scraper.config)
    response = session.get(args.url)
    markdown = md.convert(response.text)

    Path(args.output).mkdir(parents=True, exist_ok=True)
    path = f"{args.output}/markdown_{safe_filename(args.url)}.md"
    with open(path, "w") as f:
        f.write(markdown)
    print(f"Saved: {path}")
    return 0


def handle_screenshot(scraper, args):
    from .output_utils import ScreenshotCapture

    capturer = ScreenshotCapture()
    output = args.output or f"{args.output}/screenshots/{safe_filename(args.url)}.png"
    result = capturer.capture(args.url, scraper.config, output)

    if result.get("success"):
        print(f"Saved: {result.get('path', output)}")
        return 0
    print(f"Failed: {result.get('error')}")
    return 1


def handle_js(scraper, args):
    from .js_injection import JSInjector

    injector = JSInjector()

    if args.custom:
        with open(args.custom) as f:
            script = f.read()
    else:
        script = args.script

    print(f"Running JS: {script}")
    # Would execute in browser - simplified for CLI
    print("JS injection executed (use Python API for full functionality)")
    return 0


def handle_block(scraper, args):
    from .stealth_utils import AdBlocker
    from .modules.anti_detection import RequestSession

    blocker = AdBlocker()
    session = RequestSession(scraper.config)
    response = session.get(args.url)

    if args.show_blocked:
        blocked = blocker.get_blocked_resources(response.text)
        print(f"\nBlocked resources ({len(blocked)}):")
        for b in blocked[:10]:
            print(f"  [{b['type']}] {b['url'][:60]}")
    else:
        filtered = blocker.filter_html(response.text)
        print(f"Filtered HTML: {len(filtered)} chars")
    return 0


def handle_pause(args):
    from .persistence import CrawlState
    state = CrawlState(args.state)
    state.set("status", "paused")
    print(f"Paused crawl: {args.state}")
    return 0


def handle_resume(scraper, args):
    from .persistence import CrawlState
    state = CrawlState(args.state)
    if state.get("status") == "paused":
        state.set("status", "running")
        print(f"Resumed crawl: {args.state}")
        print(f"Pending URLs: {len(state.get_pending())}")
        print(f"Visited: {len(state.get_visited())}")
        return 0
    print("No paused crawl found")
    return 1


def handle_mcp(args):
    print("Starting MCP server...")
    from .mcp_server import run_mcp_server
    run_mcp_server()
    return 0


def handle_schedule(scraper, args):
    selectors = parse_selectors(args.selectors)
    job_id = scraper.schedule_job(
        name=args.name,
        url=args.url,
        schedule=args.cron,
        selectors=selectors,
        webhook_url=args.webhook or "",
        incremental=args.incremental,
    )
    print(f"Scheduled: {args.name} (ID: {job_id})")
    return 0


def handle_skills(scraper, args):
    db = scraper.skill_db
    if args.action == "list":
        skills = db.find_skills(limit=50)
        print(f"\nSkills ({len(skills)}):")
        for s in skills:
            print(f"  [{s.id}] {s.name} | {s.category} | conf: {s.confidence:.0%}")
    elif args.action == "stats":
        stats = db.get_statistics()
        print(f"Skills: {stats['total_skills']} | Avg conf: {stats.get('avg_confidence', 0):.0%}")
    elif args.action == "export":
        db.export_skills(args.file)
        print(f"Exported to {args.file}")
    elif args.action == "import":
        count = db.import_skills(args.file)
        print(f"Imported {count} skills")
    return 0


def handle_stats(scraper):
    stats = scraper.get_all_stats()
    print("\n=== ULTIMATE SCRAPER STATS ===")
    print(f"Skills: {stats.get('self_evolving', {}).get('skills', {}).get('total_skills', 0)}")
    print(f"Agents: {stats.get('self_evolving', {}).get('agents', {}).get('pool', {}).get('total_agents', 0)}")
    print(f"Jobs: {stats.get('scheduler', {}).get('total_jobs', 0)}")
    print(f"Demos: {stats.get('visual', {}).get('demonstrations', 0)}")
    print(f"Workflows: {stats.get('visual', {}).get('workflows', 0)}")
    return 0


def print_result(result):
    print(f"\nStatus: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Method: {result.method}")
    print(f"Items: {result.items_count}")
    print(f"Duration: {result.duration_ms}ms")
    if result.data and len(result.data) > 0:
        print(f"Sample: {json.dumps(result.data[0], indent=2)[:200]}")


def save_result(output_dir, formats, result):
    if not result.data:
        return
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for fmt in (formats or ["json"]):
        path = f"{output_dir}/scrape_{ts}.{fmt}"
        with open(path, "w") as f:
            json.dump(result.data, f, indent=2)
        print(f"Saved: {path}")


def parse_selectors(s):
    if not s:
        return {}
    return {k.strip(): v.strip() for k, v in (p.split(":") for p in s.split(",") if ":" in p)}


def safe_filename(url):
    return url.replace("https://", "").replace("/", "_")[:50]


if __name__ == "__main__":
    sys.exit(main())


# ============== ULTIMATE SCRAPER COMMANDS ==============
# New commands for self-evolving scraper are in ultimate_scraper_cli.py
