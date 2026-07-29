from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from backend_api import render_start


class RenderStartupTests(unittest.TestCase):
    def test_cos_failure_falls_back_to_bundled_case_library(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "case-packages"
            source.mkdir()
            (source / "case.json").write_text("{}", encoding="utf-8")
            data_root = root / "data"
            output = io.StringIO()
            with (
                patch.object(render_start, "workspace_root", return_value=root),
                patch.object(
                    render_start,
                    "current_cos_mirror",
                    side_effect=RuntimeError("SignatureDoesNotMatch secret-value"),
                ),
                patch.object(render_start, "rebuild_site"),
                patch.object(render_start, "serve"),
                patch.dict(os.environ, {"ARCHITECT_DATA_ROOT": str(data_root)}, clear=True),
                redirect_stderr(output),
            ):
                render_start.main()

            self.assertEqual((data_root / "case-packages" / "case.json").read_text(encoding="utf-8"), "{}")
            self.assertIn("COS authentication failed: SignatureDoesNotMatch", output.getvalue())
            self.assertNotIn("secret-value", output.getvalue())

    def test_cos_failure_after_creating_empty_directory_still_seeds_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "case-packages"
            source.mkdir()
            (source / "case.json").write_text("{}", encoding="utf-8")
            data_root = root / "data"

            class FailingMirror:
                def diagnostic_log(self) -> str:
                    return "COS enabled: true"

                def hydrate_library(self, *, case_packages_root: Path) -> bool:
                    case_packages_root.mkdir(parents=True, exist_ok=True)
                    raise RuntimeError("SignatureDoesNotMatch")

            with (
                patch.object(render_start, "workspace_root", return_value=root),
                patch.object(render_start, "current_cos_mirror", return_value=FailingMirror()),
                patch.object(render_start, "rebuild_site"),
                patch.object(render_start, "serve"),
                patch.dict(os.environ, {"ARCHITECT_DATA_ROOT": str(data_root)}, clear=True),
            ):
                render_start.main()

            self.assertTrue((data_root / "case-packages" / "case.json").is_file())


if __name__ == "__main__":
    unittest.main()
