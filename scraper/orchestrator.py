"""
Main orchestrator for the Ultimate Scraper.
Coordinates all components and handles output.
"""
import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


class ScraperOrchestrator:
    """
    Main orchestrator that coordinates all scraper components.
    Handles configuration, scraping, and output.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Import components
        from .sources import GenericScraper, GoogleSERPScraper
        from .output import JSONFormatter, CSVFormatter, ExcelFormatter
        from .modules.rate_limiter import GlobalRateLimiter
        from .modules.retry import RetryHandler, RetryConfig

        # Initialize components
        self.scrapers = {
            "generic": GenericScraper(self.config),
            "google": GoogleSERPScraper(self.config),
        }

        self.formatters = {
            "json": JSONFormatter(self.config),
            "csv": CSVFormatter(self.config),
            "xlsx": ExcelFormatter(self.config),
        }

        # Rate limiter
        rate_config = self.config.get("requests", {})
        self.rate_limiter = GlobalRateLimiter()

        # Retry handler
        self.retry_handler = RetryHandler(RetryConfig(
            max_attempts=rate_config.get("max_retries", 3),
            initial_delay=rate_config.get("retry_delay", 2),
        ))

        self.output_dir = self.config.get("output", {}).get("output_directory", "data/output")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file."""
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return yaml.safe_load(f)

        # Try default locations
        default_paths = [
            "config.yaml",
            "./config.yaml",
            os.path.join(os.path.dirname(__file__), "..", "config.yaml"),
        ]

        for path in default_paths:
            if os.path.exists(path):
                with open(path) as f:
                    return yaml.safe_load(f)

        # Return minimal default config
        return {
            "anti_detection": {"enabled": True},
            "requests": {"timeout": 30, "max_retries": 3},
            "output": {"formats": ["json", "csv", "xlsx"]},
        }

    def _setup_logging(self):
        """Configure logging based on config."""
        log_config = self.config.get("logging", {})

        level = log_config.get("level", "INFO")
        logger.remove()
        logger.add(sys.stderr, level=level)

        if log_config.get("console", True):
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
                level=level,
            )

        log_file = log_config.get("file")
        if log_file:
            logger.add(
                log_file,
                rotation=log_config.get("rotation", "100 MB"),
                retention=log_config.get("retention", "7 days"),
                level=level,
            )

    def scrape(
        self,
        source: str,
        url: str = None,
        query: str = None,
        selectors: dict = None,
        pagination: dict = None,
        **kwargs,
    ) -> list[dict]:
        """
        Scrape data from a source.

        Args:
            source: Source type ('generic', 'google')
            url: Target URL (for generic scraper)
            query: Search query (for Google scraper)
            selectors: CSS selectors for data extraction
            pagination: Pagination configuration
            **kwargs: Additional arguments

        Returns:
            List of scraped records
        """
        scraper = self.scrapers.get(source)
        if not scraper:
            logger.error(f"Unknown source: {source}")
            return []

        try:
            if source == "google":
                results = scraper.scrape(
                    query=query,
                    pages=kwargs.get("pages", 1),
                )
            else:
                results = scraper.scrape(
                    url=url,
                    selectors=selectors,
                    pagination=pagination,
                )

            logger.info(f"Scraped {len(results)} records from {source}")
            return results

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []

    def save(
        self,
        data: list[dict],
        filename: str = None,
        formats: list = None,
        metadata: dict = None,
    ) -> dict:
        """
        Save data to multiple formats.

        Args:
            data: Data to save
            filename: Base filename (without extension)
            formats: List of formats ('json', 'csv', 'xlsx')
            metadata: Additional metadata to include

        Returns:
            Dict mapping format to file path
        """
        if formats is None:
            formats = self.config.get("output", {}).get("formats", ["json"])

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_data_{timestamp}"

        output_paths = {}
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for fmt in formats:
            formatter = self.formatters.get(fmt)
            if not formatter:
                logger.warning(f"Unknown format: {fmt}")
                continue

            filepath = output_dir / f"{filename}.{fmt}"

            try:
                if fmt == "json":
                    # Add metadata if requested
                    if metadata:
                        output_data = [{
                            "metadata": metadata,
                            "data": data,
                            "scraped_at": datetime.now().isoformat(),
                        }]
                    else:
                        output_data = data

                    success = formatter.save(output_data, str(filepath))
                else:
                    success = formatter.save(data, str(filepath))

                if success:
                    output_paths[fmt] = str(filepath)
                    logger.info(f"Saved {fmt.upper()} to {filepath}")

            except Exception as e:
                logger.error(f"Failed to save {fmt}: {e}")

        return output_paths

    def scrape_and_save(
        self,
        source: str,
        filename: str = None,
        formats: list = None,
        **scrape_kwargs,
    ) -> dict:
        """
        Convenience method to scrape and save in one call.

        Args:
            source: Source type
            filename: Output filename
            formats: Output formats
            **scrape_kwargs: Arguments passed to scrape()

        Returns:
            Dict mapping format to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            filename = f"{source}_scrape_{timestamp}"

        # Scrape
        data = self.scrape(source, **scrape_kwargs)

        if not data:
            logger.warning("No data scraped")
            return {}

        # Save
        return self.save(data, filename, formats)

    def get_stats(self) -> dict:
        """Get scraper statistics."""
        return {
            "rate_limiter": self.rate_limiter.get_stats(),
            "config_sources": list(self.scrapers.keys()),
            "output_formats": list(self.formatters.keys()),
            "output_directory": str(self.output_dir),
        }


class DataNormalizer:
    """
    Normalizes scraped data into consistent formats.
    Handles type conversions, deduplication, and merging.
    """

    def __init__(self):
        self.seen_urls = set()
        self.seen_hashes = set()

    def normalize_records(self, records: list[dict]) -> list[dict]:
        """Normalize a list of records."""
        normalized = []

        for record in records:
            norm = self.normalize_record(record)
            if norm and self._is_unique(norm):
                normalized.append(norm)

        return normalized

    def normalize_record(self, record: dict) -> dict:
        """Normalize a single record."""
        # Convert to lowercase keys
        normalized = {}

        for key, value in record.items():
            # Normalize key
            if key.startswith("_"):
                continue

            new_key = key.lower().strip().replace(" ", "_")

            # Normalize value
            if isinstance(value, str):
                value = value.strip()

            normalized[new_key] = value

        # Ensure URL is normalized
        if "url" in normalized and normalized["url"]:
            normalized["url"] = self._normalize_url(normalized["url"])

        return normalized

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        if not url:
            return ""

        url = url.strip().split("?")[0]  # Remove query params
        url = url.rstrip("/")

        return url

    def _is_unique(self, record: dict) -> bool:
        """Check if record is unique."""
        # Check URL-based deduplication
        url = record.get("url", "")
        if url:
            if url in self.seen_urls:
                return False
            self.seen_urls.add(url)

        # Check hash-based deduplication
        record_hash = hash(json.dumps(record, sort_keys=True))
        if record_hash in self.seen_hashes:
            return False
        self.seen_hashes.add(record_hash)

        return True

    def merge_records(self, *record_lists: list[dict]) -> list[dict]:
        """Merge multiple record lists with deduplication."""
        all_records = []
        for records in record_lists:
            all_records.extend(records)
        return self.normalize_records(all_records)


def create_scrape_job(
    source: str,
    params: dict,
    schedule: str = None,
    output_formats: list = None,
) -> dict:
    """
    Create a scrape job configuration.

    Args:
        source: Source type
        params: Scrape parameters
        schedule: Cron-style schedule
        output_formats: Output formats

    Returns:
        Job configuration dict
    """
    return {
        "source": source,
        "params": params,
        "schedule": schedule,
        "output_formats": output_formats or ["json", "csv"],
        "created_at": datetime.now().isoformat(),
    }
