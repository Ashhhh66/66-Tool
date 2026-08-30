import unittest
from unittest.mock import patch
from urllib.error import URLError

from tool66.http import FetchResult
from tool66.modules.username import lookup, profile_url


def _fetch(url: str, timeout: float, **kwargs) -> FetchResult:
    if "github.com" in url:
        status = 200
    elif "gitlab.com" in url:
        status = 404
    elif "bitbucket.org" in url:
        raise URLError("timed out")
    else:
        status = 404
    return FetchResult(url=url, final_url=url, status=status, headers={}, body=b"")


class UsernameTests(unittest.TestCase):
    def test_profile_url(self) -> None:
        self.assertEqual(profile_url("GitHub", "ashh66"), "https://github.com/ashh66")

    @patch("tool66.modules.username.fetch", side_effect=_fetch)
    def test_marks_200_and_errors(self, _mock_fetch) -> None:
        result = lookup("ashh66", timeout=1.0, workers=4)
        self.assertTrue(result.ok)
        self.assertEqual(result.to_payload()["notice"], "public data only")
        self.assertTrue(result.source)
        self.assertTrue(result.timestamp_utc.endswith("Z") or "T" in result.timestamp_utc)
        by_site = {row["site"]: row for row in result.data["profiles"]}
        self.assertTrue(by_site["GitHub"]["ok_http"])
        self.assertEqual(by_site["GitHub"]["status"], 200)
        self.assertFalse(by_site["GitLab"]["ok_http"])
        self.assertEqual(by_site["GitLab"]["status"], 404)
        self.assertIsNone(by_site["Bitbucket"]["status"])
        self.assertTrue(by_site["Bitbucket"]["error"])
        self.assertGreaterEqual(result.data["http_200"], 1)


if __name__ == "__main__":
    unittest.main()
