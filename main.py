#!/usr/bin/env python3
"""
Ultimate Scraper - Main entry point
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Ultimate Scraper CLI")
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs="*", help="Arguments")
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    # Route to appropriate module
    if args.command == "scrape" or args.command is None:
        from scraper.cli import main as cli_main
        sys.exit(cli_main())

    elif args.command == "server" or args.command == "web":
        from webapp.app import create_app
        import uvicorn

        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8000)

    elif args.command == "mcp":
        from scraper.mcp_server import run_mcp_server
        run_mcp_server()

    elif args.command == "evolve":
        from scraper.ultimate_scraper_cli import handle_evolve
        handle_evolve(args)

    elif args.command == "pool":
        from scraper.ultimate_scraper_cli import handle_pool
        handle_pool(args)

    elif args.command == "firecrawl" or args.command == "fc":
        from scraper.integrations.firecrawl_client import FirecrawlClient
        fc = FirecrawlClient()

        if not fc.is_available():
            print("ERROR: Firecrawl is not running!")
            print("Start it with: cd c:/tmp/firecrawl && docker compose up -d")
            sys.exit(1)

        if args.args:
            url = args.args[0]
            result = fc.scrape(url)
            if result and result.get("success"):
                print(result.get("markdown", result.get("html", "")))
            else:
                print(f"Failed: {result.get('error', 'Unknown error')}")
        else:
            print("Usage: python main.py firecrawl <url>")

    elif args.command == "analyze":
        from scraper.ultimate_scraper import AutomaticTechniqueSelector
        selector = AutomaticTechniqueSelector()
        domain = args.args[0] if args.args else ""
        print(f"\nAnalyzing: {domain}")

    elif args.command == "help":
        print("""
Ultimate Scraper Commands:

  scrape [url]              Scrape a URL
  server                    Start web server
  mcp                       Start MCP server
  evolve                    Self-learning system stats
  pool [proxy|browser]       Manage pools
  analyze [url]              Analyze website challenges
  help                      Show this help

Examples:

  python main.py scrape https://example.com
  python main.py server
  python main.py mcp
  python main.py evolve stats
  python main.py pool browser
  python main.py analyze https://example.com
        """)

    else:
        print(f"Unknown command: {args.command}")
        print("Run 'python main.py help' for usage")


if __name__ == "__main__":
    main()
