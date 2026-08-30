import io
import unittest
from unittest.mock import patch

from tool66.result import NOTICE, Result
from tool66.tui import collect_fields, run_desk


class TuiTests(unittest.TestCase):
    def test_collect_fields_dns(self) -> None:
        answers = iter(["example.com", "8"])
        fields = collect_fields("dns", lambda _: next(answers))
        self.assertEqual(fields["domain"], "example.com")
        self.assertEqual(fields["timeout"], 8.0)

    @patch("tool66.tui.run_and_record")
    def test_desk_runs_then_quits(self, mock_run) -> None:
        mock_run.return_value = Result(
            module="dns",
            source="test source",
            target="example.com",
            ok=True,
            data={"status": "NOERROR", "records": {"A": ["1.2.3.4"]}},
        )
        answers = iter(["1", "example.com", "", "", "q"])
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            code = run_desk(
                prompt=lambda _: next(answers),
                stdout=stdout,
                clear_screen=False,
            )
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("Ashh66 66-Tool", text)
        self.assertIn(NOTICE, text)
        self.assertIn("dns", text)
        self.assertIn("1.2.3.4", text)
        self.assertIn("bye", text)
        mock_run.assert_called_once()
