"""
MCP Server - Model Context Protocol integration.
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class MCPResource:
    """An MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


@dataclass
class MCPTool:
    """An MCP tool."""
    name: str
    description: str
    input_schema: Dict


class MCPServer:
    """
    MCP Server for AI agent integration.
    Allows Claude, Cursor, etc. to use the scraper.
    """

    def __init__(self, config: Dict):
        self.config = config

        # Initialize scraper components
        from .enhanced_orchestrator import UltimateSelfEvolvingScraper
        from .nlp import NLPScraper
        from .advanced_selectors import XPathSelector, LinkExtractor
        from .output_utils import MarkdownConverter, PydanticOutput

        self.scraper = UltimateSelfEvolvingScraper(config)
        self.nlp = NLPScraper(config)
        self.xpath = XPathSelector()
        self.links = LinkExtractor()
        self.markdown = MarkdownConverter()
        self.pydantic = PydanticOutput()

        # Define resources
        self.resources = [
            MCPResource(
                uri="scrape://stats",
                name="scraper_stats",
                description="Get scraper statistics and capabilities",
            ),
            MCPResource(
                uri="scrape://skills",
                name="learned_skills",
                description="List all learned scraping skills",
            ),
        ]

        # Define tools
        self.tools = [
            MCPTool(
                name="scrape_url",
                description="Scrape data from a URL using intelligent extraction",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                        "prompt": {"type": "string", "description": "What to extract (natural language)"},
                        "selectors": {"type": "object", "description": "CSS selectors if known"},
                    },
                    "required": ["url"],
                },
            ),
            MCPTool(
                name="scrape_with_template",
                description="Scrape using a built-in template",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "template": {
                            "type": "string",
                            "enum": ["products", "articles", "contacts", "jobs", "prices"],
                        },
                    },
                    "required": ["url", "template"],
                },
            ),
            MCPTool(
                name="scrape_multiple",
                description="Scrape multiple URLs in parallel",
                input_schema={
                    "type": "object",
                    "properties": {
                        "urls": {"type": "array", "items": {"type": "string"}},
                        "prompt": {"type": "string"},
                    },
                    "required": ["urls"],
                },
            ),
            MCPTool(
                name="xpath_extract",
                description="Extract data using XPath selectors",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "xpath": {"type": "string", "description": "XPath expression"},
                    },
                    "required": ["url", "xpath"],
                },
            ),
            MCPTool(
                name="html_to_markdown",
                description="Convert HTML to clean markdown",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            ),
            MCPTool(
                name="crawl_site",
                description="Crawl entire website",
                input_schema={
                    "type": "object",
                    "properties": {
                        "start_url": {"type": "string"},
                        "max_pages": {"type": "integer", "default": 100},
                        "selectors": {"type": "object"},
                    },
                    "required": ["start_url"],
                },
            ),
            MCPTool(
                name="discover_api",
                description="Find hidden REST/GraphQL APIs",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                },
            ),
            MCPTool(
                name="get_skills",
                description="List all learned scraping skills",
                input_schema={"type": "object", "properties": {}},
            ),
            MCPTool(
                name="get_stats",
                description="Get scraper statistics",
                input_schema={"type": "object", "properties": {}},
            ),
        ]

    # Tool implementations
    async def scrape_url(self, url: str, prompt: str = None, selectors: Dict = None) -> Dict:
        """Scrape URL with optional prompt or selectors."""
        if prompt:
            return await self.nlp.scrape(url, prompt)
        else:
            result = self.scraper.scrape(url, selectors)
            return {
                "success": result.success,
                "data": result.data,
                "method": result.method,
            }

    async def scrape_with_template(self, url: str, template: str) -> Dict:
        """Scrape using template."""
        return self.nlp.scrape_with_template(url, template)

    async def scrape_multiple(self, urls: List[str], prompt: str = None) -> List[Dict]:
        """Scrape multiple URLs."""
        results = []
        for url in urls:
            result = await self.scrape_url(url, prompt)
            results.append({"url": url, "result": result})
        return results

    async def xpath_extract(self, url: str, xpath: str) -> Dict:
        """Extract using XPath."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession(self.config)
        response = session.get(url)

        elements = self.xpath.select(response.text, xpath)
        return {
            "success": len(elements) > 0,
            "data": elements,
            "count": len(elements),
        }

    async def html_to_markdown(self, url: str) -> Dict:
        """Convert HTML to markdown."""
        from ..modules.anti_detection import RequestSession

        session = RequestSession(self.config)
        response = session.get(url)

        markdown = self.markdown.convert(response.text)
        return {
            "success": True,
            "markdown": markdown,
            "url": url,
        }

    async def crawl_site(
        self,
        start_url: str,
        max_pages: int = 100,
        selectors: Dict = None,
    ) -> Dict:
        """Crawl website."""
        from .distributed import ParallelScraper

        parallel = ParallelScraper(self.config)
        results = parallel.crawl_site(
            start_url=start_url,
            selectors=selectors or {},
            max_pages=max_pages,
        )

        all_data = []
        for result in results:
            if result.success:
                all_data.extend(result.data)

        return {
            "success": len(all_data) > 0,
            "data": all_data,
            "pages_crawled": len(results),
        }

    async def discover_api(self, url: str) -> Dict:
        """Discover APIs."""
        from .api_discovery import APIDiscovery

        finder = APIDiscovery(self.config)
        apis = finder.discover(url)

        return {
            "success": len(apis) > 0,
            "apis": [
                {
                    "url": api.url,
                    "method": api.method,
                    "type": api.api_type,
                    "confidence": api.confidence,
                }
                for api in apis
            ],
        }

    async def get_skills(self) -> Dict:
        """Get learned skills."""
        skills = self.scraper.skill_db.find_skills(limit=50)
        return {
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "confidence": s.confidence,
                    "success_rate": s.success_rate,
                }
                for s in skills
            ],
        }

    async def get_stats(self) -> Dict:
        """Get scraper stats."""
        return self.scraper.get_all_stats()

    # MCP protocol handlers
    async def handle_request(self, method: str, params: Dict) -> Dict:
        """Handle MCP request."""
        if method == "tools/list":
            return {"tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema,
                }
                for t in self.tools
            ]}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Map to implementation
            tool_map = {
                "scrape_url": self.scrape_url,
                "scrape_with_template": self.scrape_with_template,
                "scrape_multiple": self.scrape_multiple,
                "xpath_extract": self.xpath_extract,
                "html_to_markdown": self.html_to_markdown,
                "crawl_site": self.crawl_site,
                "discover_api": self.discover_api,
                "get_skills": self.get_skills,
                "get_stats": self.get_stats,
            }

            if tool_name in tool_map:
                result = await tool_map[tool_name](**arguments)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}

        elif method == "resources/list":
            return {"resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type,
                }
                for r in self.resources
            ]}

        return {"error": f"Unknown method: {method}"}

    def run_stdio(self):
        """Run MCP server over stdio."""
        import sys
        import json

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                params = request.get("params", {})

                result = asyncio.run(self.handle_request(method, params))

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result,
                }
                print(json.dumps(response))
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"MCP error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32603, "message": str(e)},
                }
                print(json.dumps(error_response))
                sys.stdout.flush()


def run_mcp_server(config_path: str = None):
    """Run MCP server."""
    import yaml

    config = {}
    if config_path:
        with open(config_path) as f:
            config = yaml.safe_load(f)

    server = MCPServer(config)
    server.run_stdio()


if __name__ == "__main__":
    run_mcp_server()
