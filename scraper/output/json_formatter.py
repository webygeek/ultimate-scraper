"""
JSON output formatter with support for various JSON formats.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False


class JSONFormatter:
    """
    Formats scraped data to JSON with various options.
    Supports pretty printing, ndjson, and compact formats.
    """

    def __init__(self, config: dict):
        self.config = config.get("output", {})
        self.indent = self.config.get("json_indent", 2)
        self.ensure_ascii = False

    def format(self, data: list[dict], pretty: bool = True) -> str:
        """
        Format data as JSON string.

        Args:
            data: List of dictionaries to format
            pretty: Use pretty printing

        Returns:
            JSON string
        """
        if ORJSON_AVAILABLE and not pretty:
            # orjson is faster but doesn't support pretty printing
            return orjson.dumps(data).decode("utf-8")
        else:
            # Use standard json for pretty printing
            return json.dumps(
                data,
                indent=self.indent if pretty else None,
                ensure_ascii=self.ensure_ascii,
                default=str,  # Handle datetime and other non-serializable types
            )

    def format_pretty(self, data: list[dict]) -> str:
        """Format with pretty printing."""
        return self.format(data, pretty=True)

    def format_compact(self, data: list[dict]) -> str:
        """Format compact JSON (no whitespace)."""
        return self.format(data, pretty=False)

    def format_ndjson(self, data: list[dict]) -> str:
        """
        Format as Newline Delimited JSON (NDJSON).
        One JSON object per line - great for streaming.
        """
        lines = []
        for item in data:
            if ORJSON_AVAILABLE:
                lines.append(orjson.dumps(item).decode("utf-8"))
            else:
                lines.append(json.dumps(item, ensure_ascii=self.ensure_ascii, default=str))
        return "\n".join(lines)

    def format_jsonl(self, data: list[dict]) -> str:
        """Alias for NDJSON."""
        return self.format_ndjson(data)

    def format_with_metadata(
        self,
        data: list[dict],
        source: str,
        scrape_time: Optional[datetime] = None,
        url: Optional[str] = None,
    ) -> dict:
        """
        Format data with metadata wrapper.

        Returns:
            Dictionary with data and metadata
        """
        if scrape_time is None:
            scrape_time = datetime.now()

        return {
            "metadata": {
                "source": source,
                "scrape_time": scrape_time.isoformat(),
                "url": url,
                "record_count": len(data),
                "format_version": "1.0",
            },
            "data": data,
        }

    def save(
        self,
        data: list[dict],
        filepath: str,
        pretty: bool = True,
        create_dirs: bool = True,
    ) -> bool:
        """
        Save data to JSON file.

        Args:
            data: Data to save
            filepath: Output file path
            pretty: Use pretty printing
            create_dirs: Create parent directories if needed

        Returns:
            True if successful
        """
        try:
            if create_dirs:
                Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            content = self.format(data, pretty=pretty)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Saved {len(data)} records to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            return False

    def save_with_metadata(
        self,
        data: list[dict],
        filepath: str,
        source: str,
        url: Optional[str] = None,
    ) -> bool:
        """Save data with metadata wrapper."""
        output = self.format_with_metadata(data, source, url=url)
        return self.save([output], filepath, pretty=True)

    def append(self, data: list[dict], filepath: str) -> bool:
        """
        Append records to existing JSON file (as NDJSON).

        Args:
            data: Records to append
            filepath: File to append to

        Returns:
            True if successful
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            content = self.format_ndjson(data)

            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content + "\n")

            logger.info(f"Appended {len(data)} records to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to JSON: {e}")
            return False

    def load(self, filepath: str) -> list[dict]:
        """Load data from JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON: {e}")
            return []

    def load_ndjson(self, filepath: str) -> list[dict]:
        """Load data from NDJSON file."""
        try:
            records = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            return records
        except Exception as e:
            logger.error(f"Failed to load NDJSON: {e}")
            return []
