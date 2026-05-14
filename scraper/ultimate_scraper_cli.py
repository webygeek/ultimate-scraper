"""
Ultimate Scraper CLI - Self-evolution commands.
"""
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger


def add_ultimate_commands(subparsers):
    """Add ultimate scraper commands to parser."""
    # Evolve command
    evolve = subparsers.add_parser("evolve", help="Self-learning scraper commands")
    evolve.add_argument("action", choices=["stats", "suggest", "check-proxies", "export"])
    evolve.add_argument("--url", help="Website URL")
    evolve.set_defaults(func=handle_evolve)

    # Pool command
    pool = subparsers.add_parser("pool", help="Manage proxy/browser pools")
    pool.add_argument("action", choices=["proxy", "browser", "check"])
    pool.add_argument("--file", help="Proxy file path")
    pool.add_argument("--size", type=int, help="Browser pool size")
    pool.set_defaults(func=handle_pool)

    # Ultimate scrape
    ultimate = subparsers.add_parser("scrape-ultimate", help="Scrape with self-evolution")
    ultimate.add_argument("url", help="URL to scrape")
    ultimate.add_argument("--retries", type=int, default=3)
    ultimate.add_argument("--proxy", action="store_true")
    ultimate.add_argument("--technique", help="Force technique")
    ultimate.add_argument("--output", "-o", help="Output file")
    ultimate.add_argument("--proxies", help="Proxy file")
    ultimate.set_defaults(func=handle_scrape_ultimate)

    # Analyze
    analyze = subparsers.add_parser("analyze", help="Analyze website for scraping challenges")
    analyze.add_argument("url", help="URL to analyze")
    analyze.set_defaults(func=handle_analyze)


def handle_evolve(args):
    """Handle evolve command."""
    from .ultimate_scraper import UltimateScraper

    ultimate = UltimateScraper()

    if args.action == "stats":
        stats = ultimate.get_stats()
        print("\n=== Self-Evolution Stats ===")
        print(f"Proxies: {stats.get('technique_selector', {}).get('proxy_pool', {}).get('total', 0)}")
        print(f"Browsers: {stats.get('technique_selector', {}).get('browser_pool', {}).get('total', 0)}")
        print(f"Domains tracked: {len(stats.get('technique_selector', {}).get('rate_limiter', {}).get('delays', {}))}")

    elif args.action == "check-proxies":
        ultimate.proxy_pool.check_all()
        print("Proxy health check complete")
        print(f"Working: {ultimate.proxy_pool.get_stats()['working']}/{ultimate.proxy_pool.get_stats()['total']}")

    elif args.action == "suggest" and args.url:
        domain = urlparse(args.url).netloc
        suggestions = ultimate.selector.get_suggestions(domain)
        print(f"\nSuggestions for {domain}:")
        for s in suggestions or ["No specific suggestions"]:
            print(f"  - {s}")

    elif args.action == "export":
        print("Exporting all scraper data...")
        # Export skills
        from .skills.scraper_skills import ScraperSkillsDB
        db = ScraperSkillsDB()
        count = db.export_skills("data/scraper_skills_export.json")
        print(f"Exported {count} techniques")
        print("Done!")
        return 0

    return 0


def handle_pool(args):
    """Handle pool commands."""
    if args.action == "proxy" or args.action == "check":
        from .ultimate_scraper import ProxyPool

        pool = ProxyPool(args.file or "data/proxies.txt")
        stats = pool.get_stats()

        print("\n=== Proxy Pool ===")
        print(f"Total: {stats['total']}")
        print(f"Working: {stats['working']}")
        print(f"Failed: {stats['failed']}")
        print(f"Rotation Index: {stats['rotation_index']}")

        if args.action == "check" or args.action == "check-proxies":
            print("\nChecking proxy health...")
            pool.check_all()
            print("Health check complete")

    elif args.action == "browser":
        from .ultimate_scraper import BrowserPool

        pool = BrowserPool(pool_size=args.size or 3)
        stats = pool.get_stats()

        print("\n=== Browser Pool ===")
        print(f"Total: {stats['total']}")
        print(f"Available: {stats['available']}")
        print(f"In Use: {stats['in_use']}")

    return 0


def handle_scrape_ultimate(args):
    """Handle ultimate scrape command."""
    from .ultimate_scraper import UltimateScraper

    ultimate = UltimateScraper()

    print(f"\n{'='*60}")
    print(f"SELF-EVOLVING SCRAPE: {args.url}")
    print(f"{'='*60}")

    # Scrape
    result = ultimate.scrape(
        url=args.url,
        max_retries=args.retries or 3,
        use_browser=True,
        use_proxy=args.proxy,
        custom_technique=args.technique,
    )

    # Report
    print(f"\n{'='*60}")
    print("RESULT")
    print(f"{'='*60}")
    print(f"Success: {result['success']}")
    print(f"Technique: {result['technique']}")
    print(f"Items Extracted: {result['items_extracted']}")

    print(f"\nChallenges Detected:")
    for challenge, detected in result['challenges'].items():
        status = "YES" if detected else "no"
        print(f"  {challenge}: {status}")

    if result.get('error'):
        print(f"\nError: {result['error']}")

    # Save
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result.get('data') or {}, f, indent=2)
        print(f"\nSaved to: {args.output}")

    return 0 if result['success'] else 1


def handle_analyze(args):
    """Handle analyze command."""
    from .ultimate_scraper import AutomaticTechniqueSelector

    selector = AutomaticTechniqueSelector()
    domain = urlparse(args.url).netloc

    print(f"\n{'='*60}")
    print(f"ANALYZING: {domain}")
    print(f"{'='*60}")

    # Get suggestions
    suggestions = selector.get_suggestions(domain)
    print("\nSuggestions:")
    for s in suggestions or ["No specific suggestions - try standard scraping"]:
        print(f"  - {s}")

    # Get technique history
    conn = sqlite3.connect("data/scraper_profiles.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT method, success, items_extracted, timestamp
        FROM technique_website
        WHERE domain = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """, (domain,))

    rows = c.fetchall()
    conn.close()

    if rows:
        print("\nRecent Attempts:")
        for row in rows:
            status = "SUCCESS" if row['success'] else "FAILED"
            print(f"  [{status}] {row['method']} - {row['items_extracted']} items")

    # Get website stats
    conn = sqlite3.connect("data/scraper_profiles.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM website_stats WHERE domain = ?", (domain,))
    row = c.fetchone()
    conn.close()

    if row:
        print("\nWebsite Profile:")
        print(f"  Cloudflare: {'Yes' if row['has_cloudflare'] else 'No'}")
        print(f"  Anti-bot: {'Yes' if row['has_antibot'] else 'No'}")
        print(f"  Lazy Load: {'Yes' if row['uses_lazy_load'] else 'No'}")
        print(f"  Best Method: {row['best_method'] or 'Unknown'}")
        print(f"  Success Rate: {row['best_success_rate']:.0%}")

    return 0
