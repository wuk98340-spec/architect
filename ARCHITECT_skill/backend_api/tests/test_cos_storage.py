from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from backend_api.cos_storage import (
    CosStorageConfig,
    CosStorageMirror,
    S3StorageConfig,
    S3StorageMirror,
    StorageConfigurationError,
    cos_enabled,
    current_storage_mirror,
    s3_enabled,
)


class CosStorageConfigurationTests(unittest.TestCase):
    def test_cos_is_disabled_by_default_for_local_tests(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(cos_enabled())

    def test_s3_configuration_uses_a_safe_normalized_prefix(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_STORAGE_BACKEND": "s3",
                "ARCHITECT_S3_BUCKET": "architect-production",
                "ARCHITECT_S3_REGION": "sgp1",
                "ARCHITECT_S3_ENDPOINT": " https://sgp1.digitaloceanspaces.com/ ",
                "ARCHITECT_S3_PREFIX": " /architect/prod/ ",
                "ARCHITECT_S3_ACCESS_KEY_ID": " spaces-id ",
                "ARCHITECT_S3_SECRET_ACCESS_KEY": " spaces-secret ",
            },
            clear=True,
        ):
            configuration = S3StorageConfig.from_environment()
            self.assertTrue(s3_enabled())
        self.assertEqual(configuration.endpoint, "https://sgp1.digitaloceanspaces.com")
        self.assertEqual(configuration.prefix, "architect/prod")

    def test_s3_configuration_requires_https_and_all_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_STORAGE_BACKEND": "s3",
                "ARCHITECT_S3_BUCKET": "architect-production",
                "ARCHITECT_S3_REGION": "sgp1",
                "ARCHITECT_S3_ENDPOINT": "http://sgp1.digitaloceanspaces.com",
                "ARCHITECT_S3_ACCESS_KEY_ID": "spaces-id",
                "ARCHITECT_S3_SECRET_ACCESS_KEY": "spaces-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(StorageConfigurationError, "must use HTTPS"):
                S3StorageConfig.from_environment()

    def test_current_storage_mirror_selects_s3_backend(self) -> None:
        configuration = S3StorageConfig(
            bucket="architect-production",
            region="sgp1",
            endpoint="https://sgp1.digitaloceanspaces.com",
            prefix="architect",
            access_key_id="spaces-id",
            secret_access_key="spaces-secret",
        )
        client = MagicMock()
        module = types.ModuleType("boto3")
        module.client = MagicMock(return_value=client)
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_STORAGE_BACKEND": "s3",
                "ARCHITECT_S3_BUCKET": configuration.bucket,
                "ARCHITECT_S3_REGION": configuration.region,
                "ARCHITECT_S3_ENDPOINT": configuration.endpoint,
                "ARCHITECT_S3_ACCESS_KEY_ID": configuration.access_key_id,
                "ARCHITECT_S3_SECRET_ACCESS_KEY": configuration.secret_access_key,
            },
            clear=True,
        ), patch.dict(sys.modules, {"boto3": module}):
            mirror = current_storage_mirror()
        self.assertIsInstance(mirror, S3StorageMirror)
        module.client.assert_called_once_with(
            "s3",
            endpoint_url=configuration.endpoint,
            region_name=configuration.region,
            aws_access_key_id=configuration.access_key_id,
            aws_secret_access_key=configuration.secret_access_key,
        )

    def test_cos_configuration_requires_bucket_region_and_credentials(self) -> None:
        with patch.dict(os.environ, {"ARCHITECT_STORAGE_BACKEND": "cos"}, clear=True):
            with self.assertRaisesRegex(StorageConfigurationError, "ARCHITECT_COS_BUCKET"):
                CosStorageConfig.from_environment()

    def test_cos_configuration_uses_a_safe_normalized_prefix(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_COS_BUCKET": "  'architect-prod-1250000000'  ",
                "ARCHITECT_COS_REGION": "  \"ap-shanghai\"  ",
                "ARCHITECT_COS_PREFIX": " '/architect/prod/' ",
                "ARCHITECT_COS_SECRET_ID": "  'AKIDtest' ",
                "ARCHITECT_COS_SECRET_KEY": " \"test-secret\" ",
            },
            clear=True,
        ):
            configuration = CosStorageConfig.from_environment()
        self.assertEqual(configuration.prefix, "architect/prod")
        self.assertEqual(configuration.bucket, "architect-prod-1250000000")
        self.assertEqual(configuration.secret_key, "test-secret")

    def test_platform_credentials_take_precedence_when_the_complete_temporary_triplet_is_present(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_COS_BUCKET": "architect-prod-1250000000",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "ARCHITECT_COS_SECRET_ID": "static-id",
                "ARCHITECT_COS_SECRET_KEY": "static-key",
                "TENCENTCLOUD_SECRETID": "temporary-id",
                "TENCENTCLOUD_SECRETKEY": "temporary-key",
                "TENCENTCLOUD_SESSIONTOKEN": "temporary-token",
            },
            clear=True,
        ):
            configuration = CosStorageConfig.from_environment()
        self.assertEqual(configuration.credential_source, "platform")
        self.assertEqual(configuration.secret_id, "temporary-id")
        self.assertEqual(configuration.session_token, "temporary-token")

    def test_platform_mode_requires_complete_temporary_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_COS_CREDENTIAL_MODE": "platform",
                "ARCHITECT_COS_BUCKET": "architect-prod-1250000000",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "TENCENTCLOUD_SECRETID": "temporary-id",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(StorageConfigurationError, "ARCHITECT_COS_SECRET_KEY"):
                CosStorageConfig.from_environment()

    def test_cos_configuration_rejects_an_unsafe_prefix(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_COS_BUCKET": "architect-prod-1250000000",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "ARCHITECT_COS_PREFIX": "architect/../prod",
                "ARCHITECT_COS_SECRET_ID": "AKIDtest",
                "ARCHITECT_COS_SECRET_KEY": "test-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(StorageConfigurationError, "unsafe path"):
                CosStorageConfig.from_environment()

    def test_cos_configuration_requires_full_bucket_name_with_appid(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_STORAGE_BACKEND": "cos",
                "ARCHITECT_COS_BUCKET": "architect-prod",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "ARCHITECT_COS_SECRET_ID": "AKIDtest",
                "ARCHITECT_COS_SECRET_KEY": "test-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(StorageConfigurationError, "BucketName-APPID"):
                CosStorageConfig.from_environment()

    def test_client_uses_cleaned_cos_configuration(self) -> None:
        configuration = CosStorageConfig(
            bucket="architect-prod-1250000000",
            region="ap-shanghai",
            prefix="architect",
            secret_id="AKIDtest",
            secret_key="test-secret",
            session_token="temporary-token",
            credential_source="platform",
        )
        config_factory = MagicMock(return_value="config")
        client_factory = MagicMock(return_value="client")
        module = types.ModuleType("qcloud_cos")
        module.CosConfig = config_factory
        module.CosS3Client = client_factory
        with patch.dict(sys.modules, {"qcloud_cos": module}):
            mirror = CosStorageMirror(configuration)
        config_factory.assert_called_once_with(
            Region="ap-shanghai",
            SecretId="AKIDtest",
            SecretKey="test-secret",
            Scheme="https",
            SignHost=False,
            Token="temporary-token",
        )
        self.assertEqual(mirror.client, "client")

    def test_diagnostic_log_masks_secret_key(self) -> None:
        configuration = CosStorageConfig(
            bucket="architect-prod-1250000000",
            region="ap-shanghai",
            prefix="architect",
            secret_id="AKIDexample",
            secret_key="super-secret-value",
        )
        diagnostic = configuration.diagnostic_log()
        self.assertIn("SecretId: AKID...", diagnostic)
        self.assertIn("SecretKey: configured", diagnostic)
        self.assertNotIn("super-secret-value", diagnostic)


if __name__ == "__main__":
    unittest.main()
