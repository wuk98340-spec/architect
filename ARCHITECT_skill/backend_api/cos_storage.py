"""Object-storage-backed durable storage for the API and worker processes.

The application keeps its existing Path-based research pipeline in a temporary
workspace. This module mirrors *one job at a time* and the published case
library to private object storage so the API and worker do not depend on a
shared filesystem. COS remains supported; S3-compatible providers such as
DigitalOcean Spaces are supported for platform-independent deployments.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class StorageConfigurationError(RuntimeError):
    """Raised when a COS production deployment has incomplete configuration."""


class StorageUnavailableError(RuntimeError):
    """Raised when configured COS storage cannot be reached safely."""


def _clean_environment_value(name: str, *legacy_names: str) -> str:
    """Read a CloudBase value without preserving accidental outer quotes."""
    raw = os.environ.get(name)
    if raw is None:
        raw = next((os.environ.get(legacy) for legacy in legacy_names if os.environ.get(legacy) is not None), "")
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def cos_enabled() -> bool:
    return os.environ.get("ARCHITECT_STORAGE_BACKEND", "local").strip().lower() == "cos"


def s3_enabled() -> bool:
    return os.environ.get("ARCHITECT_STORAGE_BACKEND", "local").strip().lower() == "s3"


def storage_enabled() -> bool:
    return cos_enabled() or s3_enabled()


def _safe_segment(value: str, *, label: str) -> str:
    candidate = value.strip()
    if not candidate or "/" in candidate or "\\" in candidate or candidate in {".", ".."}:
        raise StorageConfigurationError(f"{label} must be one safe path segment.")
    return candidate


@dataclass(frozen=True)
class CosStorageConfig:
    bucket: str
    region: str
    prefix: str
    secret_id: str
    secret_key: str
    session_token: str = ""
    credential_source: str = "static"

    @classmethod
    def from_environment(cls) -> "CosStorageConfig":
        platform_credentials = {
            "TENCENTCLOUD_SECRETID": _clean_environment_value(
                "TENCENTCLOUD_SECRETID", "TENCENTCLOUD_SECRET_ID"
            ),
            "TENCENTCLOUD_SECRETKEY": _clean_environment_value(
                "TENCENTCLOUD_SECRETKEY", "TENCENTCLOUD_SECRET_KEY"
            ),
            "TENCENTCLOUD_SESSIONTOKEN": _clean_environment_value(
                "TENCENTCLOUD_SESSIONTOKEN", "TENCENTCLOUD_SESSION_TOKEN"
            ),
        }
        credential_mode = _clean_environment_value("ARCHITECT_COS_CREDENTIAL_MODE").lower()
        use_platform_credentials = credential_mode == "platform" or all(platform_credentials.values())
        if credential_mode and credential_mode not in {"platform", "static"}:
            raise StorageConfigurationError(
                "ARCHITECT_COS_CREDENTIAL_MODE must be either 'platform' or 'static'."
            )
        values = {
            "ARCHITECT_COS_BUCKET": _clean_environment_value("ARCHITECT_COS_BUCKET"),
            "ARCHITECT_COS_REGION": _clean_environment_value("ARCHITECT_COS_REGION"),
            "ARCHITECT_COS_SECRET_ID": (
                platform_credentials["TENCENTCLOUD_SECRETID"]
                if use_platform_credentials
                else _clean_environment_value(
                    "ARCHITECT_COS_SECRET_ID", "TENCENTCLOUD_SECRETID", "TENCENTCLOUD_SECRET_ID"
                )
            ),
            "ARCHITECT_COS_SECRET_KEY": (
                platform_credentials["TENCENTCLOUD_SECRETKEY"]
                if use_platform_credentials
                else _clean_environment_value(
                    "ARCHITECT_COS_SECRET_KEY", "TENCENTCLOUD_SECRETKEY", "TENCENTCLOUD_SECRET_KEY"
                )
            ),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise StorageConfigurationError("COS storage is enabled but missing: " + ", ".join(missing))
        if not re.fullmatch(r".+-\d+", values["ARCHITECT_COS_BUCKET"]):
            raise StorageConfigurationError(
                "ARCHITECT_COS_BUCKET must use the full BucketName-APPID format."
            )
        prefix = _clean_environment_value("ARCHITECT_COS_PREFIX").strip("/") or "architect"
        if not prefix:
            raise StorageConfigurationError("ARCHITECT_COS_PREFIX must not be empty.")
        if any(part in {"", ".", ".."} for part in PurePosixPath(prefix).parts):
            raise StorageConfigurationError("ARCHITECT_COS_PREFIX contains an unsafe path.")
        return cls(
            bucket=values["ARCHITECT_COS_BUCKET"],
            region=values["ARCHITECT_COS_REGION"],
            prefix=prefix,
            secret_id=values["ARCHITECT_COS_SECRET_ID"],
            secret_key=values["ARCHITECT_COS_SECRET_KEY"],
            session_token=(
                platform_credentials["TENCENTCLOUD_SESSIONTOKEN"] if use_platform_credentials else ""
            ),
            credential_source="platform" if use_platform_credentials else "static",
        )

    def diagnostic_log(self) -> str:
        secret_id_preview = f"{self.secret_id[:4]}..." if self.secret_id else "not configured"
        return " | ".join(
            (
                "COS enabled: true",
                f"bucket: {self.bucket}",
                f"region: {self.region}",
                f"prefix: {self.prefix}",
                f"credential source: {self.credential_source}",
                f"SecretId: {secret_id_preview}",
                f"SecretKey: {'configured' if self.secret_key else 'not configured'}",
                f"SessionToken: {'configured' if self.session_token else 'not configured'}",
            )
        )


@dataclass(frozen=True)
class S3StorageConfig:
    """Configuration for DigitalOcean Spaces and other S3-compatible stores."""

    bucket: str
    region: str
    endpoint: str
    prefix: str
    access_key_id: str
    secret_access_key: str

    @classmethod
    def from_environment(cls) -> "S3StorageConfig":
        values = {
            "ARCHITECT_S3_BUCKET": _clean_environment_value("ARCHITECT_S3_BUCKET"),
            "ARCHITECT_S3_REGION": _clean_environment_value("ARCHITECT_S3_REGION"),
            "ARCHITECT_S3_ENDPOINT": _clean_environment_value("ARCHITECT_S3_ENDPOINT"),
            "ARCHITECT_S3_ACCESS_KEY_ID": _clean_environment_value("ARCHITECT_S3_ACCESS_KEY_ID"),
            "ARCHITECT_S3_SECRET_ACCESS_KEY": _clean_environment_value(
                "ARCHITECT_S3_SECRET_ACCESS_KEY"
            ),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise StorageConfigurationError("S3 storage is enabled but missing: " + ", ".join(missing))
        endpoint = values["ARCHITECT_S3_ENDPOINT"].rstrip("/")
        if not endpoint.startswith("https://"):
            raise StorageConfigurationError("ARCHITECT_S3_ENDPOINT must use HTTPS.")
        prefix = _clean_environment_value("ARCHITECT_S3_PREFIX", "ARCHITECT_COS_PREFIX").strip("/")
        if not prefix:
            prefix = "architect"
        if any(part in {"", ".", ".."} for part in PurePosixPath(prefix).parts):
            raise StorageConfigurationError("ARCHITECT_S3_PREFIX contains an unsafe path.")
        return cls(
            bucket=values["ARCHITECT_S3_BUCKET"],
            region=values["ARCHITECT_S3_REGION"],
            endpoint=endpoint,
            prefix=prefix,
            access_key_id=values["ARCHITECT_S3_ACCESS_KEY_ID"],
            secret_access_key=values["ARCHITECT_S3_SECRET_ACCESS_KEY"],
        )

    def diagnostic_log(self) -> str:
        access_key_preview = f"{self.access_key_id[:4]}..." if self.access_key_id else "not configured"
        return " | ".join(
            (
                "S3 enabled: true",
                f"bucket: {self.bucket}",
                f"region: {self.region}",
                f"endpoint: {self.endpoint}",
                f"prefix: {self.prefix}",
                f"AccessKeyId: {access_key_preview}",
                f"SecretAccessKey: {'configured' if self.secret_access_key else 'not configured'}",
            )
        )


def cos_failure_message(error: BaseException) -> str:
    """Return a useful, secret-safe message for startup and request logs."""
    detail = str(error)
    if "SignatureDoesNotMatch" in detail:
        return (
            "COS authentication failed: SignatureDoesNotMatch. Check "
            "ARCHITECT_COS_SECRET_ID, ARCHITECT_COS_SECRET_KEY, "
            "ARCHITECT_COS_REGION and ARCHITECT_COS_BUCKET."
        )
    if error.__class__.__name__ in {"CosServiceError", "CosClientError", "ConnectionError", "Timeout"}:
        return f"COS storage unavailable: {error.__class__.__name__}."
    return f"COS storage unavailable: {error.__class__.__name__}."


def storage_failure_message(error: BaseException) -> str:
    """Return a provider-neutral, secret-safe storage diagnostic."""
    if cos_enabled():
        return cos_failure_message(error)
    detail = str(error)
    if "SignatureDoesNotMatch" in detail or "InvalidAccessKeyId" in detail:
        return "S3 storage authentication failed. Check the S3 access key, secret, endpoint, region and bucket."
    if error.__class__.__name__ in {"ClientError", "BotoCoreError", "EndpointConnectionError", "ConnectionError", "Timeout"}:
        return f"S3 storage unavailable: {error.__class__.__name__}."
    return f"S3 storage unavailable: {error.__class__.__name__}."


class CosStorageMirror:
    """Mirror application-owned prefixes between COS and a local temporary path."""

    def __init__(self, config: CosStorageConfig) -> None:
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as error:  # pragma: no cover - exercised only in misconfigured deployment
            raise StorageConfigurationError(
                "COS storage requires cos-python-sdk-v5; install worker_runtime requirements."
            ) from error
        self.config = config
        options = {
            "Region": config.region,
            "SecretId": config.secret_id,
            "SecretKey": config.secret_key,
            "Scheme": "https",
            # CloudBase Run's egress path can rewrite Host.  COS signs the
            # request before that proxying occurs, so signing Host makes a
            # correct credential pair fail with SignatureDoesNotMatch.
            "SignHost": False,
        }
        if config.session_token:
            options["Token"] = config.session_token
        self.client = CosS3Client(CosConfig(**options))

    @classmethod
    def from_environment(cls) -> "CosStorageMirror":
        return cls(CosStorageConfig.from_environment())

    def diagnostic_log(self) -> str:
        return self.config.diagnostic_log()

    def _key(self, *parts: str) -> str:
        normalized = [self.config.prefix, *[part.strip("/") for part in parts if part.strip("/")]]
        return "/".join(normalized)

    def _prefix(self, *parts: str) -> str:
        return self._key(*parts).rstrip("/") + "/"

    def _list_keys(self, prefix: str) -> set[str]:
        keys: set[str] = set()
        marker: str | None = None
        while True:
            response = self.client.list_objects(
                Bucket=self.config.bucket, Prefix=prefix, Marker=marker, MaxKeys=1000
            )
            for item in response.get("Contents", []):
                key = str(item.get("Key", ""))
                if key and not key.endswith("/"):
                    keys.add(key)
            if not response.get("IsTruncated"):
                return keys
            marker = str(response.get("NextMarker", ""))
            if not marker:
                return keys

    def _mirror_from_cos(self, *, remote_prefix: str, destination: Path) -> bool:
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        keys = self._list_keys(remote_prefix)
        for key in keys:
            relative = PurePosixPath(key).relative_to(PurePosixPath(remote_prefix))
            if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
                raise StorageConfigurationError(f"unsafe COS object key: {key}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(Bucket=self.config.bucket, Key=key, DestFilePath=str(target))
        return bool(keys)

    def _mirror_to_cos(self, *, source: Path, remote_prefix: str) -> None:
        source.mkdir(parents=True, exist_ok=True)
        local_keys: set[str] = set()
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            key = remote_prefix + relative
            local_keys.add(key)
            self.client.upload_file(
                Bucket=self.config.bucket,
                LocalFilePath=str(path),
                Key=key,
                EnableMD5=False,
            )
        for key in self._list_keys(remote_prefix) - local_keys:
            self.client.delete_object(Bucket=self.config.bucket, Key=key)

    def hydrate_job(self, *, jobs_root: Path, job_id: str) -> bool:
        return self._mirror_from_cos(
            remote_prefix=self._prefix("jobs", _safe_segment(job_id, label="job_id")),
            destination=jobs_root / job_id,
        )

    def persist_job(self, *, jobs_root: Path, job_id: str) -> None:
        self._mirror_to_cos(
            source=jobs_root / _safe_segment(job_id, label="job_id"),
            remote_prefix=self._prefix("jobs", job_id),
        )

    def hydrate_all_jobs(self, *, jobs_root: Path) -> None:
        prefix = self._prefix("jobs")
        job_ids = {
            key[len(prefix):].split("/", 1)[0]
            for key in self._list_keys(prefix)
            if key.startswith(prefix) and "/" in key[len(prefix):]
        }
        jobs_root.mkdir(parents=True, exist_ok=True)
        for job_id in sorted(job_ids):
            self.hydrate_job(jobs_root=jobs_root, job_id=job_id)

    def hydrate_library(self, *, case_packages_root: Path) -> bool:
        return self._mirror_from_cos(remote_prefix=self._prefix("cases"), destination=case_packages_root)

    def persist_case_package(self, *, case_packages_root: Path, package_slug: str) -> None:
        slug = _safe_segment(package_slug, label="package_slug")
        self._mirror_to_cos(
            source=case_packages_root / slug,
            remote_prefix=self._prefix("cases", slug),
        )


class S3StorageMirror(CosStorageMirror):
    """S3-compatible mirror with the same durable queue and library semantics."""

    def __init__(self, config: S3StorageConfig) -> None:
        try:
            import boto3
        except ImportError as error:  # pragma: no cover - dependency installation failure
            raise StorageConfigurationError("S3 storage requires boto3.") from error
        self.config = config
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
        )

    @classmethod
    def from_environment(cls) -> "S3StorageMirror":
        return cls(S3StorageConfig.from_environment())

    def _list_keys(self, prefix: str) -> set[str]:
        keys: set[str] = set()
        continuation_token: str | None = None
        while True:
            request: dict[str, object] = {"Bucket": self.config.bucket, "Prefix": prefix}
            if continuation_token:
                request["ContinuationToken"] = continuation_token
            response = self.client.list_objects_v2(**request)
            for item in response.get("Contents", []):
                key = str(item.get("Key", ""))
                if key and not key.endswith("/"):
                    keys.add(key)
            if not response.get("IsTruncated"):
                return keys
            continuation_token = str(response.get("NextContinuationToken", ""))
            if not continuation_token:
                return keys

    def _mirror_from_cos(self, *, remote_prefix: str, destination: Path) -> bool:
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        keys = self._list_keys(remote_prefix)
        for key in keys:
            relative = PurePosixPath(key).relative_to(PurePosixPath(remote_prefix))
            if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
                raise StorageConfigurationError(f"unsafe S3 object key: {key}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.config.bucket, key, str(target))
        return bool(keys)

    def _mirror_to_cos(self, *, source: Path, remote_prefix: str) -> None:
        source.mkdir(parents=True, exist_ok=True)
        local_keys: set[str] = set()
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            key = remote_prefix + path.relative_to(source).as_posix()
            local_keys.add(key)
            self.client.upload_file(str(path), self.config.bucket, key)
        for key in self._list_keys(remote_prefix) - local_keys:
            self.client.delete_object(Bucket=self.config.bucket, Key=key)


def current_cos_mirror() -> CosStorageMirror | None:
    return CosStorageMirror.from_environment() if cos_enabled() else None


def current_storage_mirror() -> CosStorageMirror | S3StorageMirror | None:
    if cos_enabled():
        return CosStorageMirror.from_environment()
    if s3_enabled():
        return S3StorageMirror.from_environment()
    return None
