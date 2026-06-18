import tempfile
import unittest
from pathlib import Path

from scripts.clean_runtime import clean_path


class CleanRuntimeTest(unittest.TestCase):
    def test_clean_path_dry_run_keeps_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime"
            path.mkdir()
            (path / "file.txt").write_text("data", encoding="utf-8")

            result = clean_path(path, dry_run=True)

            self.assertTrue(result["exists"])
            self.assertFalse(result["removed"])
            self.assertTrue((path / "file.txt").exists())

    def test_clean_path_apply_recreates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime"
            path.mkdir()
            (path / "file.txt").write_text("data", encoding="utf-8")

            result = clean_path(path, dry_run=False)

            self.assertTrue(result["removed"])
            self.assertTrue(path.exists())
            self.assertFalse((path / "file.txt").exists())


if __name__ == "__main__":
    unittest.main()
