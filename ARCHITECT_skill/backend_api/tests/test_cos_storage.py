from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from backend_api.cos_storage import CosStorageConfig, CosStorageMirror, StorageConfigurationError, cos_enabled


class CosStorageConfigurationTests(unittest.TestCase):
    def test_cos_is_disabled_by_default_for_local_tests(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(cos_enabled())

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
        )
        config_factory = MagicMock(return_value="config")
        client_factory = MagicMock(return_value="client")
        module = types.ModuleType("qcloud_cos")
        module.CosConfig = config_factory
        module.CosS3Client = client_factory
        with patch.dict(sys.modules, {"qcloud_cos": module}):
            mirror = CosStorageMirror(configuration)
        config_factory.assert_called_once_with(
            Region="ap-shanghai", SecretId="AKIDtest", SecretKey="test-secret", Scheme="https"
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
