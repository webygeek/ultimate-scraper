"""
Cloud Storage Adapters - Export to S3, GCS, Azure Blob.
"""
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from loguru import logger


class CloudStorage(ABC):
    """Base class for cloud storage."""

    @abstractmethod
    def upload(self, data: Any, path: str) -> bool:
        """Upload data to cloud storage."""
        pass

    @abstractmethod
    def download(self, path: str) -> Any:
        """Download data from cloud storage."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files with prefix."""
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file."""
        pass


class LocalStorage(CloudStorage):
    """Local file system storage."""

    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, data: Any, path: str) -> bool:
        """Upload to local filesystem."""
        try:
            file_path = self.base_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(data, (dict, list)):
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
            elif isinstance(data, str):
                with open(file_path, "w") as f:
                    f.write(data)
            else:
                with open(file_path, "wb") as f:
                    f.write(data)

            logger.info(f"Uploaded to local: {path}")
            return True

        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            return False

    def download(self, path: str) -> Optional[Any]:
        """Download from local filesystem."""
        try:
            file_path = self.base_dir / path
            if not file_path.exists():
                return None

            if path.endswith(".json"):
                with open(file_path) as f:
                    return json.load(f)
            else:
                with open(file_path) as f:
                    return f.read()

        except Exception as e:
            logger.error(f"Local download failed: {e}")
            return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List local files."""
        prefix_path = self.base_dir / prefix
        if not prefix_path.exists():
            return []

        return [str(p.relative_to(self.base_dir)) for p in prefix_path.rglob("*") if p.is_file()]

    def delete(self, path: str) -> bool:
        """Delete local file."""
        try:
            file_path = self.base_dir / path
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Local delete failed: {e}")
            return False


class S3Storage(CloudStorage):
    """
    Amazon S3 storage adapter.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: str = None,
        secret_key: str = None,
    ):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self._client = None

    def _get_client(self):
        """Get S3 client."""
        if self._client:
            return self._client

        try:
            import boto3
            self._client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
            return self._client
        except ImportError:
            logger.warning("boto3 not installed")
            return None
        except Exception as e:
            logger.error(f"S3 client failed: {e}")
            return None

    def upload(self, data: Any, path: str) -> bool:
        """Upload to S3."""
        client = self._get_client()
        if not client:
            return False

        try:
            if isinstance(data, (dict, list)):
                content = json.dumps(data, indent=2)
                content_type = "application/json"
            elif isinstance(data, str):
                content = data
                content_type = "text/plain"
            else:
                content = data
                content_type = "application/octet-stream"

            client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=content,
                ContentType=content_type,
            )

            logger.info(f"Uploaded to S3: {path}")
            return True

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def download(self, path: str) -> Optional[Any]:
        """Download from S3."""
        client = self._get_client()
        if not client:
            return None

        try:
            response = client.get_object(Bucket=self.bucket, Key=path)
            content = response["Body"].read()

            if path.endswith(".json"):
                return json.loads(content)
            return content.decode()

        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List S3 files."""
        client = self._get_client()
        if not client:
            return []

        try:
            response = client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return []

    def delete(self, path: str) -> bool:
        """Delete S3 object."""
        client = self._get_client()
        if not client:
            return False

        try:
            client.delete_object(Bucket=self.bucket, Key=path)
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False


class GCSStorage(CloudStorage):
    """
    Google Cloud Storage adapter.
    """

    def __init__(
        self,
        bucket: str,
        project_id: str = None,
        credentials_path: str = None,
    ):
        self.bucket = bucket
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._client = None

    def _get_client(self):
        """Get GCS client."""
        if self._client:
            return self._client

        try:
            from google.cloud import storage

            if self.credentials_path:
                client = storage.Client.from_service_account_json(
                    self.credentials_path,
                    project=self.project_id,
                )
            else:
                client = storage.Client(project=self.project_id)

            self._client = client
            return client
        except ImportError:
            logger.warning("google-cloud-storage not installed")
            return None
        except Exception as e:
            logger.error(f"GCS client failed: {e}")
            return None

    def upload(self, data: Any, path: str) -> bool:
        """Upload to GCS."""
        client = self._get_client()
        if not client:
            return False

        try:
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(path)

            if isinstance(data, (dict, list)):
                blob.upload_from_string(
                    json.dumps(data, indent=2),
                    content_type="application/json",
                )
            elif isinstance(data, str):
                blob.upload_from_string(data)
            else:
                blob.upload_from_string(data)

            logger.info(f"Uploaded to GCS: {path}")
            return True

        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return False

    def download(self, path: str) -> Optional[Any]:
        """Download from GCS."""
        client = self._get_client()
        if not client:
            return None

        try:
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(path)
            content = blob.download_as_string()

            if path.endswith(".json"):
                return json.loads(content)
            return content.decode()

        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List GCS files."""
        client = self._get_client()
        if not client:
            return []

        try:
            bucket = client.bucket(self.bucket)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"GCS list failed: {e}")
            return []

    def delete(self, path: str) -> bool:
        """Delete GCS object."""
        client = self._get_client()
        if not client:
            return False

        try:
            bucket = client.bucket(self.bucket)
            blob = bucket.blob(path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"GCS delete failed: {e}")
            return False


class AzureStorage(CloudStorage):
    """
    Azure Blob Storage adapter.
    """

    def __init__(
        self,
        connection_string: str = None,
        container: str = None,
        account_name: str = None,
        account_key: str = None,
    ):
        self.connection_string = connection_string
        self.container = container
        self.account_name = account_name
        self.account_key = account_key
        self._client = None

    def _get_client(self):
        """Get Azure Blob client."""
        if self._client:
            return self._client

        try:
            from azure.storage.blob import BlobServiceClient

            if self.connection_string:
                self._client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self._client = BlobServiceClient(account_url, self.account_key)

            return self._client
        except ImportError:
            logger.warning("azure-storage-blob not installed")
            return None
        except Exception as e:
            logger.error(f"Azure client failed: {e}")
            return None

    def upload(self, data: Any, path: str) -> bool:
        """Upload to Azure Blob."""
        client = self._get_client()
        if not client:
            return False

        try:
            container_client = client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(path)

            if isinstance(data, (dict, list)):
                data = json.dumps(data, indent=2)
                content_type = "application/json"
            elif isinstance(data, str):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

            blob_client.upload_blob(data, overwrite=True, content_type=content_type)

            logger.info(f"Uploaded to Azure: {path}")
            return True

        except Exception as e:
            logger.error(f"Azure upload failed: {e}")
            return False

    def download(self, path: str) -> Optional[Any]:
        """Download from Azure Blob."""
        client = self._get_client()
        if not client:
            return None

        try:
            container_client = client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(path)
            content = blob_client.download_blob().readall()

            if path.endswith(".json"):
                return json.loads(content)
            return content.decode()

        except Exception as e:
            logger.error(f"Azure download failed: {e}")
            return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List Azure blobs."""
        client = self._get_client()
        if not client:
            return []

        try:
            container_client = client.get_container_client(self.container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Azure list failed: {e}")
            return []

    def delete(self, path: str) -> bool:
        """Delete Azure blob."""
        client = self._get_client()
        if not client:
            return False

        try:
            container_client = client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(path)
            blob_client.delete_blob()
            return True
        except Exception as e:
            logger.error(f"Azure delete failed: {e}")
            return False


class StorageManager:
    """
    Unified storage manager supporting multiple backends.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.storages: Dict[str, CloudStorage] = {}
        self._init_storages()

    def _init_storages(self):
        """Initialize storage backends from config."""
        storage_config = self.config.get("storage", {})

        # Local
        if storage_config.get("local", {}).get("enabled", True):
            local_dir = storage_config.get("local", {}).get("path", "data/storage")
            self.storages["local"] = LocalStorage(local_dir)

        # S3
        s3_config = storage_config.get("s3", {})
        if s3_config.get("enabled"):
            self.storages["s3"] = S3Storage(
                bucket=s3_config["bucket"],
                region=s3_config.get("region", "us-east-1"),
                access_key=s3_config.get("access_key"),
                secret_key=s3_config.get("secret_key"),
            )

        # GCS
        gcs_config = storage_config.get("gcs", {})
        if gcs_config.get("enabled"):
            self.storages["gcs"] = GCSStorage(
                bucket=gcs_config["bucket"],
                project_id=gcs_config.get("project_id"),
                credentials_path=gcs_config.get("credentials_path"),
            )

        # Azure
        azure_config = storage_config.get("azure", {})
        if azure_config.get("enabled"):
            self.storages["azure"] = AzureStorage(
                connection_string=azure_config.get("connection_string"),
                container=azure_config.get("container"),
                account_name=azure_config.get("account_name"),
                account_key=azure_config.get("account_key"),
            )

    def get_storage(self, name: str = "local") -> CloudStorage:
        """Get storage by name."""
        return self.storages.get(name, self.storages.get("local"))

    def upload_all(
        self,
        data: Any,
        path: str,
        storages: List[str] = None,
    ) -> Dict[str, bool]:
        """Upload to multiple storages."""
        if storages is None:
            storages = list(self.storages.keys())

        results = {}
        for name in storages:
            storage = self.storages.get(name)
            if storage:
                results[name] = storage.upload(data, path)

        return results
