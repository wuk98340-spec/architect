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
            (source / "example.txt").write_text("case", encoding="utf-8")
            data_root = root / "data"
            output = io.StringIO()
            with (
                patch.object(render_start, "workspace_root", return_value=root),
                patch.object(render_start, "current_cos_mirror", side_effect=RuntimeError("bad COS credentials")),
                patch.object(render_start, "rebuild_site"),
                patch.object(render_start, "serve"),
                patch.dict(os.environ, {"ARCHITECT_DATA_ROOT": str(data_root)}, clear=True),
                redirect_stderr(output),
            ):
                render_start.main()

            self.assertEqual((data_root / "case-packages" / "example.txt").read_text(encoding="utf-8"), "case")
            self.assertIn("COS mirror unavailable", output.getvalue())


if __name__ == "__main__":
    unittest.main()
