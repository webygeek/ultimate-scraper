"""
Hidden API Discovery
Finds and scrapes hidden REST and GraphQL APIs.
Often faster and more reliable than HTML scraping.
"""
import re
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
from loguru import logger

from ..modules.anti_detection import AntiDetection


@dataclass
class DiscoveredAPI:
    """A discovered API endpoint."""
    url: str
    method: str  # GET, POST, etc.
    api_type: str  # rest, graphql, websocket
    parameters: List[str]
    response_format: str  # json, xml
    sample_response: str = ""
    confidence: float = 0.5  # 0-1, how confident we are


class APIDiscovery:
    """
    Discovers hidden APIs by analyzing JavaScript, network requests, and patterns.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.anti_detection = AntiDetection(config)

    def discover(self, url: str, use_browser: bool = False) -> List[DiscoveredAPI]:
        """
        Discover APIs on a page.

        Args:
            url: Target URL
            use_browser: Use browser to intercept network requests

        Returns:
            List of discovered APIs
        """
        apis = []

        # Strategy 1: Analyze page JavaScript
        apis.extend(self._discover_from_html(url))

        # Strategy 2: Analyze JS files
        apis.extend(self._discover_from_js_files(url))

        # Strategy 3: Use browser to intercept (if available)
        if use_browser:
            apis.extend(self._intercept_network_requests(url))

        # Strategy 4: Guess common API patterns
        apis.extend(self._guess_common_apis(url))

        # Deduplicate
        seen = set()
        unique_apis = []
        for api in apis:
            key = f"{api.method}:{api.url}"
            if key not in seen:
                seen.add(key)
                unique_apis.append(api)

        logger.info(f"Discovered {len(unique_apis)} potential APIs")
        return unique_apis

    def _discover_from_html(self, url: str) -> List[DiscoveredAPI]:
        """Discover APIs from HTML source."""
        apis = []
        try:
            import requests
            response = requests.get(url, timeout=30)
            html = response.text

            # Look for API patterns in HTML/JS
            api_patterns = [
                r'fetch\(["\']([^"\']+)["\']',
                r'axios\.get\(["\']([^"\']+)["\']',
                r'axios\.post\(["\']([^"\']+)["\']',
                r'\.get\(["\']([^"\']+)["\']',
                r'\.post\(["\']([^"\']+)["\']',
                r'api["\']?\s*:\s*["\']([^"\']+)["\']',
                r'endpoint["\']?\s*:\s*["\']([^"\']+)["\']',
                r'baseURL["\']?\s*:\s*["\']([^"\']+)["\']',
                r'url["\']?\s*:\s*["\']([^"\']+)["\']',
                r'"/api/[^"\']+"',
                r'"/v\d+/api/[^"\']+"',
                r'graphql',
                r'"/rest/[^"\']+"',
            ]

            for pattern in api_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches[:5]:  # Limit to 5 per pattern
                    if isinstance(match, tuple):
                        match = match[0]

                    if match and len(match) > 3:
                        # Determine method
                        method = "GET"
                        if ".post(" in pattern or "post(" in pattern:
                            method = "POST"
                        elif ".put(" in pattern or "put(" in pattern:
                            method = "PUT"
                        elif ".delete(" in pattern or "delete(" in pattern:
                            method = "DELETE"

                        # Determine type
                        api_type = "rest"
                        if "graphql" in match.lower():
                            api_type = "graphql"

                        # Make absolute URL
                        if match.startswith("/"):
                            parsed = urlparse(url)
                            full_url = f"{parsed.scheme}://{parsed.netloc}{match}"
                        elif not match.startswith("http"):
                            full_url = urljoin(url, match)
                        else:
                            full_url = match

                        apis.append(DiscoveredAPI(
                            url=full_url,
                            method=method,
                            api_type=api_type,
                            parameters=self._extract_params(match),
                            response_format="json",
                            confidence=0.6,
                        ))

        except Exception as e:
            logger.debug(f"HTML API discovery failed: {e}")

        return apis

    def _discover_from_js_files(self, url: str) -> List[DiscoveredAPI]:
        """Discover APIs by analyzing JS files."""
        apis = []

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=30)
            html = response.text
            soup = BeautifulSoup(html, "lxml")

            # Find JS files
            js_files = []
            for script in soup.select("script[src]"):
                src = script.get("src", "")
                if ".js" in src:
                    js_files.append(urljoin(url, src))

            # Analyze each JS file
            for js_url in js_files[:10]:  # Limit to 10 files
                try:
                    js_response = requests.get(js_url, timeout=10)
                    js_content = js_response.text

                    # Look for API patterns
                    api_patterns = [
                        r'["\']\/api\/[a-zA-Z0-9\/_\-]+["\']',
                        r'["\']\/v\d+\/[a-zA-Z0-9\/_\-]+["\']',
                        r'["\']https?:\/\/[a-zA-Z0-9\.\-_]+\/api\/["\']',
                        r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                        r'endpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    ]

                    for pattern in api_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        for match in matches[:3]:
                            if match:
                                parsed = urlparse(url)
                                if match.startswith("/"):
                                    full_url = f"{parsed.scheme}://{parsed.netloc}{match}"
                                else:
                                    full_url = match

                                apis.append(DiscoveredAPI(
                                    url=full_url.strip('"\''),
                                    method="GET",
                                    api_type="rest",
                                    parameters=[],
                                    response_format="json",
                                    confidence=0.5,
                                ))

                except Exception as e:
                    logger.debug(f"JS file analysis failed: {e}")

        except Exception as e:
            logger.debug(f"JS discovery failed: {e}")

        return apis

    def _intercept_network_requests(self, url: str) -> List[DiscoveredAPI]:
        """Intercept network requests using browser."""
        apis = []

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                # Collect requests
                requests = []

                def handle_request(request):
                    req_url = request.url
                    # Only track API-like requests
                    if any(x in req_url for x in ["/api/", "/v1/", "/v2/", "graphql", ".json"]):
                        requests.append({
                            "url": req_url,
                            "method": request.method,
                        })

                page.on("request", handle_request)

                # Navigate
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)

                # Extract APIs
                for req in requests:
                    apis.append(DiscoveredAPI(
                        url=req["url"],
                        method=req["method"],
                        api_type="rest" if "graphql" not in req["url"] else "graphql",
                        parameters=[],
                        response_format="json",
                        confidence=0.8,  # Higher confidence from interception
                    ))

                browser.close()

        except ImportError:
            logger.warning("Playwright not available for request interception")
        except Exception as e:
            logger.debug(f"Request interception failed: {e}")

        return apis

    def _guess_common_apis(self, url: str) -> List[DiscoveredAPI]:
        """Guess common API patterns."""
        apis = []
        parsed = urlparse(url)

        # Common API patterns
        patterns = [
            f"{parsed.scheme}://{parsed.netloc}/api/products",
            f"{parsed.scheme}://{parsed.netloc}/api/items",
            f"{parsed.scheme}://{parsed.netloc}/api/data",
            f"{parsed.scheme}://{parsed.netloc}/graphql",
            f"{parsed.scheme}://{parsed.netloc}/api/v1/products",
            f"{parsed.scheme}://{parsed.netloc}/api/search",
        ]

        for api_url in patterns:
            apis.append(DiscoveredAPI(
                url=api_url,
                method="GET",
                api_type="rest",
                parameters=[],
                response_format="json",
                confidence=0.3,  # Low confidence - just a guess
            ))

        return apis

    def _extract_params(self, url: str) -> List[str]:
        """Extract parameter names from URL."""
        params = []
        if "?" in url:
            query = url.split("?")[1]
            for param in query.split("&"):
                if "=" in param:
                    params.append(param.split("=")[0])
        return params

    def test_api(self, api: DiscoveredAPI) -> Optional[Dict]:
        """
        Test an API endpoint.

        Returns response data if successful.
        """
        try:
            import requests

            headers = self.anti_detection.get_headers(api.url)
            headers["Accept"] = "application/json"

            if api.method == "GET":
                response = requests.get(api.url, headers=headers, timeout=30)
            elif api.method == "POST":
                response = requests.post(api.url, headers=headers, timeout=30)
            else:
                response = requests.request(api.method, api.url, headers=headers, timeout=30)

            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"raw": response.text[:500]}

        except Exception as e:
            logger.debug(f"API test failed: {e}")

        return None

    def scrape_via_api(
        self,
        url: str,
        use_browser: bool = False,
        prefer_apis: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape using discovered APIs instead of HTML.

        Args:
            url: Target URL
            use_browser: Use browser for request interception
            prefer_apis: Prefer API scraping over HTML

        Returns:
            {"success": bool, "data": [], "method": "api"|"html", "apis_found": int}
        """
        logger.info(f"Discovering APIs on {url}")

        apis = self.discover(url, use_browser=use_browser)

        if not apis and prefer_apis:
            # Fall back to HTML scraping
            return self._scrape_html(url)

        # Test each API
        for api in sorted(apis, key=lambda x: -x.confidence):
            logger.info(f"Testing API: {api.url} (confidence: {api.confidence:.0%})")

            data = self.test_api(api)
            if data:
                if isinstance(data, list):
                    return {
                        "success": True,
                        "data": data,
                        "method": "api",
                        "api_used": api.url,
                        "apis_found": len(apis),
                    }
                elif isinstance(data, dict):
                    # Try to find array in response
                    for key in ["data", "results", "items", "products"]:
                        if key in data and isinstance(data[key], list):
                            return {
                                "success": True,
                                "data": data[key],
                                "method": "api",
                                "api_used": api.url,
                                "apis_found": len(apis),
                            }
                    # Return entire response
                    return {
                        "success": True,
                        "data": [data],
                        "method": "api",
                        "api_used": api.url,
                        "apis_found": len(apis),
                    }

        # All APIs failed, try HTML
        if prefer_apis:
            logger.info("APIs failed, falling back to HTML scraping")
            return self._scrape_html(url)

        return {"success": False, "data": [], "method": "none", "apis_found": len(apis)}

    def _scrape_html(self, url: str) -> Dict[str, Any]:
        """Fallback HTML scraping."""
        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, "lxml")

            # Simple extraction
            items = []
            for elem in soup.select("a, img, p, h1, h2, h3"):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    items.append({"type": elem.name, "text": text[:200]})

            return {
                "success": True,
                "data": items,
                "method": "html",
                "apis_found": 0,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "method": "html"}


class GraphQLScanner:
    """
    Specialized scanner for GraphQL APIs.
    """

    def __init__(self):
        self.introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
                types {
                    ...FullType
                }
                directives {
                    name
                    description
                    locations
                    args {
                        ...InputValue
                    }
                }
            }
        }

        fragment FullType on __Type {
            kind
            name
            description
            fields(includeDeprecated: true) {
                name
                description
                args {
                    ...InputValue
                }
                type {
                    ...TypeRef
                }
                isDeprecated
                deprecationReason
            }
            inputFields {
                ...InputValue
            }
            interfaces {
                ...TypeRef
            }
            enumValues(includeDeprecated: true) {
                name
                description
                isDeprecated
                deprecationReason
            }
        }

        fragment InputValue on __InputValue {
            name
            description
            type {
                ...TypeRef
            }
            defaultValue
        }

        fragment TypeRef on __Type {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

    def find_graphql_endpoint(self, url: str) -> Optional[str]:
        """Find GraphQL endpoint on a page."""
        common_paths = [
            "/graphql",
            "/api/graphql",
            "/api/v1/graphql",
            "/query",
            "/graphql/v1",
        ]

        for path in common_paths:
            try:
                import requests
                full_url = url.rstrip("/") + path

                # Try OPTIONS request first
                response = requests.options(full_url, timeout=5)
                if response.status_code in (200, 204, 405):
                    return full_url

                # Try POST with introspection
                response = requests.post(
                    full_url,
                    json={"query": "{ __typename }"},
                    timeout=10,
                )
                if response.status_code == 200:
                    return full_url

            except:
                continue

        return None

    def introspect(self, endpoint: str) -> Optional[Dict]:
        """Run GraphQL introspection query."""
        try:
            import requests

            response = requests.post(
                endpoint,
                json={"query": self.introspection_query},
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.debug(f"GraphQL introspection failed: {e}")

        return None

    def generate_queries(self, schema: Dict) -> List[str]:
        """Generate example queries from schema."""
        queries = []

        if "data" in schema:
            schema = schema["data"]

        types = schema.get("__schema", {}).get("types", [])

        for type_info in types:
            name = type_info.get("name", "")

            # Skip internal types
            if name.startswith("__"):
                continue

            kind = type_info.get("kind", "")
            fields = type_info.get("fields", [])

            if kind == "OBJECT" and fields:
                # Generate query
                field_names = [f["name"] for f in fields[:5]]
                query = f"""
query {name}Query {{
    {name.lower()} {{
        {chr(10).join(field_names)}
    }}
}}
                """
                queries.append(query.strip())

        return queries[:10]  # Limit queries

    def scrape_graphql(
        self,
        url: str,
        selectors: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Scrape using GraphQL.

        Args:
            url: Target URL
            selectors: Fields to extract (maps to GraphQL fields)

        Returns:
            Scraped data
        """
        # Find endpoint
        endpoint = self.find_graphql_endpoint(url)
        if not endpoint:
            return {"success": False, "error": "No GraphQL endpoint found"}

        logger.info(f"Found GraphQL endpoint: {endpoint}")

        # Introspect
        schema = self.introspect(endpoint)
        if not schema:
            return {"success": False, "error": "Introspection failed"}

        # Generate queries
        queries = self.generate_queries(schema)

        results = []
        for query in queries:
            try:
                import requests
                response = requests.post(
                    endpoint,
                    json={"query": query},
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        results.extend(self._flatten_data(data["data"]))

            except Exception as e:
                logger.debug(f"Query failed: {e}")

        return {
            "success": len(results) > 0,
            "data": results,
            "endpoint": endpoint,
            "schema": schema,
        }

    def _flatten_data(self, data: Dict) -> List[Dict]:
        """Flatten nested GraphQL response."""
        results = []

        def flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    flatten(value, f"{prefix}{key}_" if prefix else key)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        results.append(item)

        flatten(data)
        return results
