"""
CSV output formatter with support for various delimiters and options.
"""
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger


class CSVFormatter:
    """
    Formats scraped data to CSV with various options.
    Handles nested data, lists, and complex structures.
    """

    def __init__(self, config: dict):
        self.config = config.get("output", {})
        self.delimiter = self.config.get("csv_delimiter", ",")
        self.quotechar = '"'
        self.escapechar = None
        self.line_terminator = "\n"

    def flatten_record(self, record: dict, parent_key: str = "", sep: str = "_") -> dict:
        """
        Flatten nested dictionary for CSV export.

        Args:
            record: Dictionary to flatten
            parent_key: Prefix for nested keys
            sep: Separator between nested keys

        Returns:
            Flattened dictionary
        """
        items = {}

        for key, value in record.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.update(self.flatten_record(value, new_key, sep))
            elif isinstance(value, list):
                # Handle lists by joining or indexing
                if all(isinstance(v, (str, int, float)) for v in value):
                    # Simple list of primitives - join as string
                    items[new_key] = "; ".join(str(v) for v in value)
                else:
                    # Complex list - store as JSON string
                    import json
                    items[new_key] = json.dumps(value)
            elif isinstance(value, (datetime,)):
                items[new_key] = value.isoformat()
            else:
                items[new_key] = value

        return items

    def normalize_records(self, records: list[dict]) -> list[dict]:
        """
        Normalize all records to have consistent columns.
        Adds empty values for missing columns.
        """
        if not records:
            return []

        # Flatten all records
        flattened = [self.flatten_record(r) for r in records]

        # Get all unique columns
        all_columns = set()
        for record in flattened:
            all_columns.update(record.keys())

        # Sort columns for consistency
        columns = sorted(all_columns)

        # Ensure all records have all columns
        normalized = []
        for record in flattened:
            normalized_record = {col: record.get(col, "") for col in columns}
            normalized.append(normalized_record)

        return normalized

    def get_columns(self, records: list[dict]) -> list[str]:
        """Extract column names from records."""
        if not records:
            return []

        flattened = [self.flatten_record(r) for r in records]

        columns = set()
        for record in flattened:
            columns.update(record.keys())

        return sorted(columns)

    def format(
        self,
        data: list[dict],
        columns: Optional[list[str]] = None,
        include_header: bool = True,
    ) -> str:
        """
        Format data as CSV string.

        Args:
            data: List of dictionaries to format
            columns: Specific columns to include (None = all)
            include_header: Include column header row

        Returns:
            CSV string
        """
        if not data:
            return ""

        # Normalize records
        records = self.normalize_records(data)

        # Determine columns
        if columns is None:
            columns = self.get_columns(records)

        # Filter columns that exist
        columns = [c for c in columns if any(c in r for r in records)] or self.get_columns(records)

        lines = []

        # Write to string buffer
        import io
        buffer = io.StringIO()
        writer = csv.writer(
            buffer,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            escapechar=self.escapechar,
            lineterminator=self.line_terminator,
            quoting=csv.QUOTE_MINIMAL,
        )

        if include_header:
            writer.writerow(columns)

        for record in records:
            row = [str(record.get(col, "")) for col in columns]
            writer.writerow(row)

        return buffer.getvalue()

    def format_from_records(
        self,
        data: list[dict],
        columns: Optional[list[str]] = None,
    ) -> str:
        """Alias for format method."""
        return self.format(data, columns)

    def save(
        self,
        data: list[dict],
        filepath: str,
        columns: Optional[list[str]] = None,
        create_dirs: bool = True,
    ) -> bool:
        """
        Save data to CSV file.

        Args:
            data: Data to save
            filepath: Output file path
            columns: Specific columns to include
            create_dirs: Create parent directories if needed

        Returns:
            True if successful
        """
        try:
            if create_dirs:
                Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            content = self.format(data, columns=columns)

            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write(content)

            logger.info(f"Saved {len(data)} records to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
            return False

    def append(
        self,
        data: list[dict],
        filepath: str,
        columns: Optional[list[str]] = None,
    ) -> bool:
        """
        Append records to existing CSV file.

        Args:
            data: Records to append
            filepath: File to append to
            columns: Column order (from existing file if None)

        Returns:
            True if successful
        """
        try:
            # Get columns from existing file or data
            if columns is None and os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    columns = next(reader)

            # Normalize and flatten records
            records = self.normalize_records(data)
            if columns is None:
                columns = self.get_columns(records)

            # Write with append mode
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(
                    f,
                    delimiter=self.delimiter,
                    quotechar=self.quotechar,
                    lineterminator=self.line_terminator,
                )

                for record in records:
                    row = [str(record.get(col, "")) for col in columns]
                    writer.writerow(row)

            logger.info(f"Appended {len(data)} records to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to CSV: {e}")
            return False

    def load(self, filepath: str) -> list[dict]:
        """Load data from CSV file."""
        try:
            records = []
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                for row in reader:
                    records.append(dict(row))
            return records
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return []

    def load_with_types(self, filepath: str, type_map: dict[str, type]) -> list[dict]:
        """
        Load CSV with type conversion.

        Args:
            filepath: Path to CSV file
            type_map: Mapping of column names to types

        Returns:
            List of dictionaries with converted types
        """
        records = self.load(filepath)

        for record in records:
            for col, dtype in type_map.items():
                if col in record and record[col]:
                    try:
                        if dtype == int:
                            record[col] = int(record[col])
                        elif dtype == float:
                            record[col] = float(record[col])
                        elif dtype == bool:
                            record[col] = record[col].lower() in ("true", "1", "yes")
                    except ValueError:
                        pass

        return records
