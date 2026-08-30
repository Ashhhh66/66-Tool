import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tool66 import session
from tool66.cli import main
from tool66.result import NOTICE, Result


class ReportTests(unittest.TestCase):
    def test_records_and_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "last.json"
            out = Path(tmp) / "desk"
            with patch.dict(os.environ, {"TOOL66_SESSION": str(session_file)}):
                session.record(
                    Result(
                        module="dns",
                        source="test source",
                        target="example.com",
                        ok=True,
                        data={"status": "NOERROR", "records": {"A": ["1.2.3.4"]}},
                    )
                )
                with patch("sys.stdout", io.StringIO()):
                    code = main(["report", "--out", str(out)])
            self.assertEqual(code, 0)
            payload = json.loads((Path(tmp) / "desk.json").read_text(encoding="utf-8"))
            markdown = (Path(tmp) / "desk.md").read_text(encoding="utf-8")
            self.assertEqual(payload["notice"], NOTICE)
            self.assertEqual(len(payload["runs"]), 1)
            self.assertEqual(payload["runs"][0]["source"], "test source")
            self.assertIn(NOTICE, markdown)
            self.assertIn("example.com", markdown)
            self.assertIn("test source", markdown)


if __name__ == "__main__":
    unittest.main()
