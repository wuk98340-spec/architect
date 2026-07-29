from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend_api.cos_storage import CosStorageConfig, StorageConfigurationError, cos_enabled


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
                "ARCHITECT_COS_BUCKET": "architect-prod-1250000000",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "ARCHITECT_COS_PREFIX": "/architect/prod/",
                "TENCENTCLOUD_SECRET_ID": "AKIDtest",
                "TENCENTCLOUD_SECRET_KEY": "test-secret",
            },
            clear=True,
        ):
            configuration = CosStorageConfig.from_environment()
        self.assertEqual(configuration.prefix, "architect/prod")

    def test_cos_configuration_rejects_an_unsafe_prefix(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARCHITECT_COS_BUCKET": "architect-prod-1250000000",
                "ARCHITECT_COS_REGION": "ap-shanghai",
                "ARCHITECT_COS_PREFIX": "architect/../prod",
                "TENCENTCLOUD_SECRET_ID": "AKIDtest",
                "TENCENTCLOUD_SECRET_KEY": "test-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(StorageConfigurationError, "unsafe path"):
                CosStorageConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
