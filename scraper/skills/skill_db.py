"""
Skill Database - SQLite-based storage for learned scraping skills.
"""
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class Skill:
    """Represents a learned scraping skill."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    category: str = ""  # e.g., "anti_detection", "captcha", "pagination"
    site_pattern: str = ""  # URL pattern this applies to
    site_pattern_hash: str = ""  # Hash for faster matching

    # Problem characteristics
    problem_type: str = ""  # e.g., "bot_detected", "captcha", "rate_limited"
    problem_signature: str = ""  # Unique hash of the problem
    error_keywords: str = ""  # Comma-separated error keywords
    response_patterns: str = ""  # HTML patterns that indicate the problem

    # Solution details
    solution_type: str = ""  # e.g., "use_proxy", "add_delay", "solve_captcha"
    solution_config: str = ""  # JSON config for the solution
    code_snippet: str = ""  # Optional code to execute
    success_rate: float = 1.0  # 0.0 to 1.0
    use_count: int = 0
    success_count: int = 0

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""
    confidence: float = 0.0  # How confident we are in this skill
    tags: str = ""  # Comma-separated tags for searching

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.problem_signature and self.problem_type:
            self.problem_signature = self._generate_signature()

    def _generate_signature(self) -> str:
        """Generate unique signature for this problem."""
        components = [
            self.problem_type,
            self.site_pattern,
            self.error_keywords,
            self.response_patterns,
        ]
        return hashlib.md5("|".join(components).encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SkillDatabase:
    """
    SQLite database for storing and retrieving scraping skills.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "skills.db"
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    site_pattern TEXT,
                    site_pattern_hash TEXT,
                    problem_type TEXT,
                    problem_signature TEXT UNIQUE,
                    error_keywords TEXT,
                    response_patterns TEXT,
                    solution_type TEXT,
                    solution_config TEXT,
                    code_snippet TEXT,
                    success_rate REAL DEFAULT 1.0,
                    use_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    last_used_at TEXT,
                    confidence REAL DEFAULT 0.5,
                    tags TEXT,
                    INDEX idx_problem_type (problem_type),
                    INDEX idx_site_pattern_hash (site_pattern_hash),
                    INDEX idx_problem_signature (problem_signature),
                    INDEX idx_category (category)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    site_pattern_hash TEXT,
                    problem_type TEXT,
                    skill_id INTEGER,
                    success BOOLEAN,
                    response_time_ms INTEGER,
                    data_quality REAL,
                    created_at TEXT,
                    FOREIGN KEY (skill_id) REFERENCES skills(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id INTEGER NOT NULL,
                    feedback_type TEXT,
                    rating INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    FOREIGN KEY (skill_id) REFERENCES skills(id)
                )
            """)

            # Insert built-in starter skills
            self._insert_builtin_skills(conn)
            conn.commit()

    def _insert_builtin_skills(self, conn: sqlite3.Connection):
        """Insert built-in starter skills for common problems."""
        builtin_skills = [
            {
                "name": "Cloudflare Challenge Bypass",
                "description": "Handle Cloudflare protection by waiting and clicking checkbox",
                "category": "protection",
                "problem_type": "cloudflare",
                "error_keywords": "cloudflare,checking your browser,ray id",
                "solution_type": "cloudflare_wait_and_click",
                "solution_config": json.dumps({"wait_time": 5, "click_checkbox": True}),
                "confidence": 0.9,
                "tags": "cloudflare,protection,bot_detection",
            },
            {
                "name": "Google Rate Limit Recovery",
                "description": "Recover from Google rate limiting with extended delay",
                "category": "rate_limiting",
                "problem_type": "rate_limited",
                "error_keywords": "429,too many requests,rate limit",
                "solution_type": "adaptive_delay",
                "solution_config": json.dumps({"delay_multiplier": 5, "max_retries": 3}),
                "confidence": 0.85,
                "tags": "google,rate_limit,backoff",
            },
            {
                "name": "Simple Math CAPTCHA",
                "description": "Solve simple math-based CAPTCHA challenges",
                "category": "captcha",
                "problem_type": "math_captcha",
                "error_keywords": "what is,calculate,solve",
                "solution_type": "math_solver",
                "solution_config": json.dumps({"allowed_ops": ["+", "-", "x", "/"]}),
                "confidence": 0.8,
                "tags": "captcha,math,challenge",
            },
            {
                "name": "Pagination via URL Parameter",
                "description": "Handle pagination using URL parameters like ?page=N",
                "category": "pagination",
                "problem_type": "pagination",
                "error_keywords": "",
                "solution_type": "url_param_pagination",
                "solution_config": json.dumps({"param_name": "page", "start": 1, "increment": 1}),
                "confidence": 0.9,
                "tags": "pagination,url,parameters",
            },
            {
                "name": "JSON-LD Structured Data",
                "description": "Extract data from JSON-LD structured data in HTML",
                "category": "data_extraction",
                "problem_type": "json_ld",
                "error_keywords": "",
                "solution_type": "json_ld_parser",
                "solution_config": json.dumps({"schema_types": ["Product", "Article", "Event"]}),
                "confidence": 0.95,
                "tags": "jsonld,structured_data,schema",
            },
            {
                "name": "JavaScript Rendering Required",
                "description": "Site requires JavaScript to render content",
                "category": "rendering",
                "problem_type": "js_required",
                "error_keywords": "empty,no content,loading",
                "solution_type": "use_browser",
                "solution_config": json.dumps({"browser_wait": 3000, "scroll_after_load": True}),
                "confidence": 0.9,
                "tags": "javascript,browser,rendering",
            },
        ]

        for skill_data in builtin_skills:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO skills (name, description, category, problem_type,
                        error_keywords, solution_type, solution_config, confidence, tags,
                        created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    skill_data["name"],
                    skill_data["description"],
                    skill_data["category"],
                    skill_data["problem_type"],
                    skill_data.get("error_keywords", ""),
                    skill_data["solution_type"],
                    skill_data["solution_config"],
                    skill_data["confidence"],
                    skill_data["tags"],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ))
            except sqlite3.IntegrityError:
                pass  # Skill already exists

    def add_skill(self, skill: Skill) -> int:
        """Add a new skill to the database."""
        with self._get_connection() as conn:
            skill.updated_at = datetime.now().isoformat()
            cursor = conn.execute("""
                INSERT INTO skills (
                    name, description, category, site_pattern, site_pattern_hash,
                    problem_type, problem_signature, error_keywords, response_patterns,
                    solution_type, solution_config, code_snippet, success_rate,
                    use_count, success_count, created_at, updated_at, last_used_at,
                    confidence, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.name, skill.description, skill.category, skill.site_pattern,
                skill.site_pattern_hash, skill.problem_type, skill.problem_signature,
                skill.error_keywords, skill.response_patterns, skill.solution_type,
                skill.solution_config, skill.code_snippet, skill.success_rate,
                skill.use_count, skill.success_count, skill.created_at,
                skill.updated_at, skill.last_used_at, skill.confidence, skill.tags
            ))
            conn.commit()
            return cursor.lastrowid

    def update_skill(self, skill: Skill):
        """Update an existing skill."""
        with self._get_connection() as conn:
            skill.updated_at = datetime.now().isoformat()
            conn.execute("""
                UPDATE skills SET
                    name = ?, description = ?, category = ?, site_pattern = ?,
                    error_keywords = ?, response_patterns = ?, solution_type = ?,
                    solution_config = ?, code_snippet = ?, success_rate = ?,
                    use_count = ?, success_count = ?, updated_at = ?,
                    last_used_at = ?, confidence = ?, tags = ?
                WHERE id = ?
            """, (
                skill.name, skill.description, skill.category, skill.site_pattern,
                skill.error_keywords, skill.response_patterns, skill.solution_type,
                skill.solution_config, skill.code_snippet, skill.success_rate,
                skill.use_count, skill.success_count, skill.updated_at,
                skill.last_used_at, skill.confidence, skill.tags, skill.id
            ))
            conn.commit()

    def get_skill(self, skill_id: int) -> Optional[Skill]:
        """Get a skill by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            if row:
                return Skill(**dict(row))
            return None

    def find_skills(
        self,
        problem_type: Optional[str] = None,
        site_pattern: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> List[Skill]:
        """Find skills matching criteria."""
        query = "SELECT * FROM skills WHERE 1=1"
        params = []

        if problem_type:
            query += " AND problem_type = ?"
            params.append(problem_type)

        if site_pattern:
            hash_val = hashlib.md5(site_pattern.encode()).hexdigest()[:16]
            query += " AND site_pattern_hash = ?"
            params.append(hash_val)

        if category:
            query += " AND category = ?"
            params.append(category)

        if min_confidence > 0:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY confidence DESC, success_rate DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Skill(**dict(row)) for row in rows]

    def find_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Skill]:
        """Find skills by keywords in error_keywords or tags."""
        patterns = " OR ".join(["error_keywords LIKE ? OR tags LIKE ?" for _ in keywords])
        query = f"SELECT * FROM skills WHERE ({patterns}) ORDER BY confidence DESC LIMIT ?"

        params = []
        for kw in keywords:
            params.extend([f"%{kw}%", f"%{kw}%"])
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Skill(**dict(row)) for row in rows]

    def record_skill_usage(self, skill_id: int, success: bool):
        """Record that a skill was used and whether it worked."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE skills SET
                    use_count = use_count + 1,
                    success_count = success_count + ?,
                    success_rate = CAST(success_count + ? AS REAL) / (use_count + 1),
                    last_used_at = ?,
                    confidence = MIN(1.0, confidence + ?)
                WHERE id = ?
            """, (
                1 if success else 0,
                1 if success else 0,
                datetime.now().isoformat(),
                0.05 if success else -0.1,
                skill_id
            ))
            conn.commit()

    def record_scrape_attempt(
        self,
        url: str,
        problem_type: Optional[str],
        skill_id: Optional[int],
        success: bool,
        response_time_ms: int = 0,
    ):
        """Record a scrape attempt for learning."""
        with self._get_connection() as conn:
            site_hash = hashlib.md5(url.encode()).hexdigest()[:16]
            conn.execute("""
                INSERT INTO scrape_history
                (url, site_pattern_hash, problem_type, skill_id, success, response_time_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (url, site_hash, problem_type, skill_id, success, response_time_ms, datetime.now().isoformat()))
            conn.commit()

    def get_statistics(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}

            stats["total_skills"] = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
            stats["skills_by_category"] = dict(conn.execute("""
                SELECT category, COUNT(*) FROM skills GROUP BY category
            """).fetchall())

            stats["avg_confidence"] = conn.execute("SELECT AVG(confidence) FROM skills").fetchone()[0] or 0
            stats["avg_success_rate"] = conn.execute("SELECT AVG(success_rate) FROM skills").fetchone()[0] or 0

            stats["total_scrape_attempts"] = conn.execute("SELECT COUNT(*) FROM scrape_history").fetchone()[0]
            stats["successful_scrapes"] = conn.execute("SELECT COUNT(*) FROM scrape_history WHERE success = 1").fetchone()[0]

            return stats

    def delete_skill(self, skill_id: int):
        """Delete a skill."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            conn.commit()

    def export_skills(self, filepath: str):
        """Export all skills to JSON."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM skills").fetchall()
            skills = [Skill(**dict(row)).to_dict() for row in rows]

        with open(filepath, "w") as f:
            json.dump(skills, f, indent=2)
        logger.info(f"Exported {len(skills)} skills to {filepath}")

    def import_skills(self, filepath: str) -> int:
        """Import skills from JSON."""
        with open(filepath) as f:
            skills_data = json.load(f)

        count = 0
        for skill_dict in skills_data:
            skill = Skill.from_dict(skill_dict)
            skill.id = None  # Let DB assign new ID
            try:
                self.add_skill(skill)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to import skill: {e}")

        logger.info(f"Imported {count} skills from {filepath}")
        return count
