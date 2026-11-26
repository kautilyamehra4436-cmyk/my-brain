import stat
import tempfile
import unittest
from pathlib import Path

from scripts.safe_output import write_new_json


class SafeOutputTests(unittest.TestCase):
    def test_private_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reports" / "audit.json"
            write_new_json(path, {"status": "ok"})
            original = path.read_bytes()
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                write_new_json(path, {"status": "changed"})
            self.assertEqual(path.read_bytes(), original)

    def test_symlinked_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = Path(tmp) / "link.json"
            link.symlink_to(target)
            with self.assertRaises(PermissionError):
                write_new_json(link, {"status": "blocked"})

    def test_symlinked_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            link = Path(tmp) / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(PermissionError):
                write_new_json(link / "report.json", {"status": "blocked"})

    def test_report_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "report_too_large"):
                write_new_json(Path(tmp) / "report.json", {"data": "x" * 100}, max_bytes=32)


if __name__ == "__main__":
    unittest.main()
