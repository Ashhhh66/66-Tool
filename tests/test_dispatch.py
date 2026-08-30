import unittest

from tool66.dispatch import run


class DispatchTests(unittest.TestCase):
    def test_unknown_module(self) -> None:
        with self.assertRaises(ValueError):
            run("hack")

    def test_timeout_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            run("dns", timeout=0, domain="example.com")
