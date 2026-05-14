"""
Scraper Skills Database - Self-learning scraping techniques.
This module stores and manages all learned scraping techniques.
"""
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from loguru import logger


@dataclass
class ScrapingTechnique:
    """A learned scraping technique."""
    id: str = ""
    name: str = ""
    description: str = ""
    website: str = ""
    website_domain: str = ""

    # Technique details
    technique_type: str = ""  # browser, api, proxy, bypass, etc.
    method: str = ""  # specific method used
    code_snippet: str = ""

    # Context
    challenge: str = ""  # what was the problem
    solution: str = ""  # how we solved it
    success_rate: float = 1.0  # 0-1

    # Metadata
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            import hashlib
            self.id = hashlib.md5(f"{self.website}{self.technique_type}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class WebsiteProfile:
    """Profile of a website's scraping challenges."""
    domain: str = ""
    name: str = ""

    # Protection mechanisms
    has_cloudflare: bool = False
    has_antibot: bool = False
    uses_ajax: bool = False
    uses_lazy_load: bool = False
    requires_auth: bool = False

    # Working techniques
    working_techniques: List[str] = field(default_factory=list)
    failed_techniques: List[str] = field(default_factory=list)

    # Best approach
    best_method: str = ""
    best_success_rate: float = 0.0

    # Metadata
    created_at: str = ""
    last_tested: str = ""
    test_count: int = 0
    notes: str = ""


class ScraperSkillsDB:
    """
    SQLite database for storing scraping skills and techniques.
    Enables the scraper to learn from past experiences.
    """

    def __init__(self, db_path: str = "data/scraper_skills.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Techniques table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS techniques (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                website TEXT,
                website_domain TEXT,
                technique_type TEXT,
                method TEXT,
                code_snippet TEXT,
                challenge TEXT,
                solution TEXT,
                success_rate REAL DEFAULT 1.0,
                created_at TEXT,
                last_used TEXT,
                use_count INTEGER DEFAULT 0,
                tags TEXT
            )
        """)

        # Website profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS website_profiles (
                domain TEXT PRIMARY KEY,
                name TEXT,
                has_cloudflare INTEGER DEFAULT 0,
                has_antibot INTEGER DEFAULT 0,
                uses_ajax INTEGER DEFAULT 0,
                uses_lazy_load INTEGER DEFAULT 0,
                requires_auth INTEGER DEFAULT 0,
                working_techniques TEXT,
                failed_techniques TEXT,
                best_method TEXT,
                best_success_rate REAL DEFAULT 0,
                created_at TEXT,
                last_tested TEXT,
                test_count INTEGER DEFAULT 0,
                notes TEXT
            )
        """)

        # Evolution log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                website TEXT,
                challenge TEXT,
                attempts_tried INTEGER,
                technique_used TEXT,
                success INTEGER,
                result TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_technique(self, technique: ScrapingTechnique) -> bool:
        """Add a new scraping technique."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO techniques
                (id, name, description, website, website_domain, technique_type,
                 method, code_snippet, challenge, solution, success_rate,
                 created_at, last_used, use_count, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                technique.id,
                technique.name,
                technique.description,
                technique.website,
                technique.website_domain,
                technique.technique_type,
                technique.method,
                technique.code_snippet,
                technique.challenge,
                technique.solution,
                technique.success_rate,
                technique.created_at,
                technique.last_used,
                technique.use_count,
                json.dumps(technique.tags)
            ))

            conn.commit()
            conn.close()
            logger.info(f"Added technique: {technique.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add technique: {e}")
            return False

    def get_techniques_for_website(self, domain: str) -> List[ScrapingTechnique]:
        """Get all techniques that worked for a website."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM techniques
            WHERE website_domain = ? OR website LIKE ?
            ORDER BY success_rate DESC, use_count DESC
        """, (domain, f"%{domain}%"))

        results = []
        for row in cursor.fetchall():
            t = ScrapingTechnique(**dict(row))
            t.tags = json.loads(row["tags"] or "[]")
            results.append(t)

        conn.close()
        return results

    def get_techniques_by_type(self, technique_type: str) -> List[ScrapingTechnique]:
        """Get techniques by type (browser, api, proxy, bypass, etc)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM techniques
            WHERE technique_type = ?
            ORDER BY success_rate DESC
        """, (technique_type,))

        results = []
        for row in cursor.fetchall():
            t = ScrapingTechnique(**dict(row))
            t.tags = json.loads(row["tags"] or "[]")
            results.append(t)

        conn.close()
        return results

    def update_technique_stats(self, technique_id: str, success: bool):
        """Update technique usage statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE techniques
            SET use_count = use_count + 1,
                last_used = ?,
                success_rate = (success_rate * use_count + ? ) / (use_count + 1)
            WHERE id = ?
        """, (datetime.now().isoformat(), 1.0 if success else 0.0, technique_id))

        conn.commit()
        conn.close()

    def log_evolution(
        self,
        website: str,
        challenge: str,
        attempts: int,
        technique: str,
        success: bool,
        result: str = ""
    ):
        """Log an evolution attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO evolution_log
            (timestamp, website, challenge, attempts_tried, technique_used, success, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            website,
            challenge,
            attempts,
            technique,
            1 if success else 0,
            result
        ))

        conn.commit()
        conn.close()

    def get_evolution_history(self, domain: str = None, limit: int = 50) -> List[Dict]:
        """Get evolution history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if domain:
            cursor.execute("""
                SELECT * FROM evolution_log
                WHERE website LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{domain}%", limit))
        else:
            cursor.execute("""
                SELECT * FROM evolution_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def update_website_profile(self, profile: WebsiteProfile):
        """Update or create website profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO website_profiles
            (domain, name, has_cloudflare, has_antibot, uses_ajax, uses_lazy_load,
             requires_auth, working_techniques, failed_techniques, best_method,
             best_success_rate, created_at, last_tested, test_count, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.domain,
            profile.name,
            1 if profile.has_cloudflare else 0,
            1 if profile.has_antibot else 0,
            1 if profile.uses_ajax else 0,
            1 if profile.uses_lazy_load else 0,
            1 if profile.requires_auth else 0,
            json.dumps(profile.working_techniques),
            json.dumps(profile.failed_techniques),
            profile.best_method,
            profile.best_success_rate,
            profile.created_at or datetime.now().isoformat(),
            datetime.now().isoformat(),
            profile.test_count,
            profile.notes
        ))

        conn.commit()
        conn.close()

    def get_website_profile(self, domain: str) -> Optional[WebsiteProfile]:
        """Get website profile."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM website_profiles WHERE domain = ?
        """, (domain,))

        row = cursor.fetchone()
        conn.close()

        if row:
            profile = WebsiteProfile(**dict(row))
            profile.working_techniques = json.loads(row["working_techniques"] or "[]")
            profile.failed_techniques = json.loads(row["failed_techniques"] or "[]")
            return profile
        return None

    def get_all_techniques(self) -> List[ScrapingTechnique]:
        """Get all techniques."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM techniques
            ORDER BY success_rate DESC, use_count DESC
        """)

        results = []
        for row in cursor.fetchall():
            t = ScrapingTechnique(**dict(row))
            t.tags = json.loads(row["tags"] or "[]")
            results.append(t)

        conn.close()
        return results

    def export_skills(self, filepath: str = "data/scraper_skills_export.json"):
        """Export all skills to JSON."""
        techniques = self.get_all_techniques()
        profiles = self._get_all_profiles()

        data = {
            "techniques": [asdict(t) for t in techniques],
            "profiles": [asdict(p) for p in profiles],
            "exported_at": datetime.now().isoformat()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return len(techniques)

    def import_skills(self, filepath: str):
        """Import skills from JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for t_data in data.get("techniques", []):
            t = ScrapingTechnique(**t_data)
            if self.add_technique(t):
                count += 1

        return count

    def _get_all_profiles(self) -> List[WebsiteProfile]:
        """Get all website profiles."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM website_profiles")

        results = []
        for row in cursor.fetchall():
            p = WebsiteProfile(**dict(row))
            p.working_techniques = json.loads(row["working_techniques"] or "[]")
            p.failed_techniques = json.loads(row["failed_techniques"] or "[]")
            results.append(p)

        conn.close()
        return results

    def search_techniques(self, query: str) -> List[ScrapingTechnique]:
        """Search techniques by keyword."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM techniques
            WHERE name LIKE ? OR description LIKE ? OR challenge LIKE ? OR tags LIKE ?
            ORDER BY success_rate DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))

        results = []
        for row in cursor.fetchall():
            t = ScrapingTechnique(**dict(row))
            t.tags = json.loads(row["tags"] or "[]")
            results.append(t)

        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM techniques")
        technique_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM website_profiles")
        profile_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM evolution_log")
        log_count = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(success_rate) FROM techniques WHERE use_count > 0")
        avg_success = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_techniques": technique_count,
            "total_websites": profile_count,
            "total_evolution_logs": log_count,
            "average_success_rate": round(avg_success, 2),
        }


# Pre-built scraping techniques for common challenges
DEFAULT_TECHNIQUES = [
    ScrapingTechnique(
        name="Cloudflare Stealth Bypass",
        description="Bypass Cloudflare protection using stealth browser mode",
        technique_type="bypass",
        method="playwright_stealth",
        challenge="Cloudflare challenge page blocking access",
        solution="Use Playwright with automation detection disabled, custom user agent, and stealth mode",
        code_snippet="""
from playwright.sync_api import sync_playwright
browser = p.chromium.launch(
    headless=True,
    args=['--disable-blink-features=AutomationControlled']
)
context = browser.new_context(
    user_agent="Mozilla/5.0..."
)
page.add_init_script(\"\"\"
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
\"\"\")
        """,
        tags=["cloudflare", "bypass", "stealth", "protection"]
    ),
    ScrapingTechnique(
        name="AJAX/API Discovery",
        description="Find and intercept API calls for dynamic content",
        technique_type="api",
        method="network_intercept",
        challenge="Content loaded via JavaScript, not in HTML",
        solution="Intercept network requests to find API endpoints",
        code_snippet="""
def handle_response(response):
    if "/api/" in response.url:
        data = response.json()
        # Process API data
        """,
        tags=["ajax", "api", "dynamic", "javascript"]
    ),
    ScrapingTechnique(
        name="Lazy Load Trigger",
        description="Trigger lazy loading by scrolling patterns",
        technique_type="browser",
        method="scroll_pattern",
        challenge="Infinite scroll or lazy loaded content not appearing",
        solution="Use multiple scroll patterns: smooth, jump, and scroll-to-bottom",
        code_snippet="""
for i in range(20):
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
# Also try smooth scroll
for i in range(10):
    page.evaluate(f"window.scrollTo(0, {i * 500})")
    page.wait_for_timeout(500)
        """,
        tags=["lazy", "scroll", "infinite", "loading"]
    ),
    ScrapingTechnique(
        name="Human Behavior Simulation",
        description="Simulate human-like browsing behavior",
        technique_type="bypass",
        method="human_behavior",
        challenge="Bot detection based on behavior patterns",
        solution="Add random delays, varied scroll speeds, mouse movements",
        code_snippet="""
import random
import time
# Random delay between actions
time.sleep(random.uniform(1, 3))
# Random scroll distance
scroll_distance = random.randint(300, 800)
page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        """,
        tags=["human", "behavior", "simulation", "stealth"]
    ),
    ScrapingTechnique(
        name="Header Rotation",
        description="Rotate HTTP headers to avoid detection",
        technique_type="bypass",
        method="header_rotation",
        challenge="Requests blocked due to missing or suspicious headers",
        solution="Set comprehensive HTTP headers mimicking real browsers",
        code_snippet="""
page.set_extra_http_headers({
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "sec-ch-ua": '"Chromium";v="120"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
})
        """,
        tags=["headers", "rotation", "request"]
    ),
]


def init_skills_db(db_path: str = "data/scraper_skills.db") -> ScraperSkillsDB:
    """Initialize skills database with default techniques."""
    db = ScraperSkillsDB(db_path)

    # Add default techniques if DB is empty
    if len(db.get_all_techniques()) == 0:
        for technique in DEFAULT_TECHNIQUES:
            db.add_technique(technique)
        logger.info(f"Initialized database with {len(DEFAULT_TECHNIQUES)} default techniques")

    return db
