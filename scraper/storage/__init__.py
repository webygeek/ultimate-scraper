"""Storage adapters module."""
from .cloud_storage import CloudStorage, S3Storage, GCSStorage, AzureStorage

__all__ = ["CloudStorage", "S3Storage", "GCSStorage", "AzureStorage"]
