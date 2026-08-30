import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tool66.cli import main
from tool66.http import FetchResult
from tool66.result import BANNER, NOTICE


class CliTests(unittest.TestCase):
    def test_missing_module_is_bad_args(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = main([])
        self.assertEqual(code, 2)

    def test_bad_email_is_bad_args(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = main(["email", "not-an-email"])
        self.assertEqual(code, 2)
        self.assertIn("invalid email", stderr.getvalue())

    def test_rejects_credentialed_url(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = main(["headers", "https://user:pass@example.com/"])
        self.assertEqual(code, 2)

    def test_timeout_must_be_positive(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            code = main(["dns", "example.com", "--timeout", "0"])
        self.assertEqual(code, 2)

    def test_report_without_session_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_file = Path(tmp) / "session.json"
            env = os.environ.copy()
            env["TOOL66_SESSION"] = str(session_file)
            with patch.dict(os.environ, env, clear=False):
                stderr = io.StringIO()
                stdout = io.StringIO()
                with patch("sys.stderr", stderr), patch("sys.stdout", stdout):
                    code = main(["report", "--out", str(Path(tmp) / "out")])
            self.assertEqual(code, 1)
            self.assertIn(NOTICE, stdout.getvalue())

    @patch("tool66.modules.email.fetch")
    def test_email_text_has_banner_source_and_notice(self, mock_fetch) -> None:
        mock_fetch.return_value = FetchResult(
            url="https://www.gravatar.com/avatar/x",
            final_url="https://www.gravatar.com/avatar/x",
            status=404,
            headers={},
            body=b"",
        )
        with tempfile.TemporaryDirectory() as tmp:
            env = {"TOOL66_SESSION": str(Path(tmp) / "session.json")}
            stdout = io.StringIO()
            with patch.dict(os.environ, env, clear=False), patch("sys.stdout", stdout):
                code = main(["email", "lab@example.com"])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn(BANNER, text)
        self.assertIn(NOTICE, text)
        self.assertIn("source", text)
        self.assertIn("haveibeenpwned.com", text)
        self.assertNotIn("OSINT", text)


if __name__ == "__main__":
    unittest.main()
