import hashlib
import socket
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tool66.dnsproto import build_query, decode_name, encode_name, parse_message
from tool66.modules import whois as whois_mod
from tool66.modules.email import gravatar_hash
from tool66.modules.meta import parse_jpeg_exif, parse_png_text
from tool66.modules.subdomains import names_from_certspotter, names_from_crtsh
from tool66.modules.wayback import parse_cdx
from tool66.validate import (
    normalize_domain,
    validate_email,
    validate_handle,
    validate_public_url,
)


def _exif_jpeg(make: str = "66-Tool") -> bytes:
    payload = make.encode("ascii") + b"\x00"
    ifd = bytearray()
    ifd += struct.pack("<H", 1)
    ifd += struct.pack("<HHI", 0x010F, 2, len(payload))
    ifd += struct.pack("<I", 8 + 2 + 12 + 4)
    ifd += struct.pack("<I", 0)
    tiff = b"II" + struct.pack("<HI", 42, 8) + bytes(ifd) + payload
    exif = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
    return b"\xff\xd8" + app1 + b"\xff\xd9"


def _png_with_text(key: str, value: str) -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        body = name + data
        crc = struct.pack(">I", zlib_crc(body))
        return struct.pack(">I", len(data)) + body + crc

    def zlib_crc(data: bytes) -> int:
        import binascii

        return binascii.crc32(data) & 0xFFFFFFFF

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    text = key.encode("latin-1") + b"\x00" + value.encode("latin-1")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"tEXt", text)
        + chunk(b"IEND", b"")
    )


class ValidateTests(unittest.TestCase):
    def test_domain_accepts_and_strips(self) -> None:
        self.assertEqual(normalize_domain("EXAMPLE.COM."), "example.com")
        self.assertEqual(normalize_domain("https://Example.com/path"), "example.com")

    def test_domain_rejects_single_label(self) -> None:
        with self.assertRaises(ValueError):
            normalize_domain("localhost")

    def test_handle(self) -> None:
        self.assertEqual(validate_handle("@Ashh66"), "Ashh66")
        with self.assertRaises(ValueError):
            validate_handle("bad handle")

    def test_email(self) -> None:
        self.assertEqual(validate_email("lab@example.com"), "lab@example.com")
        with self.assertRaises(ValueError):
            validate_email("not-an-email")
        with self.assertRaises(ValueError):
            validate_email("a@b..com")

    def test_public_url(self) -> None:
        self.assertEqual(
            validate_public_url("https://example.com/a"),
            "https://example.com/a",
        )
        with self.assertRaises(ValueError):
            validate_public_url("file:///tmp/x")
        with self.assertRaises(ValueError):
            validate_public_url("https://user:pass@example.com/")


class DnsProtoTests(unittest.TestCase):
    def test_name_roundtrip(self) -> None:
        encoded = encode_name("www.example.com")
        name, end = decode_name(encoded, 0)
        self.assertEqual(name, "www.example.com")
        self.assertEqual(end, len(encoded))

    def test_parse_a_response(self) -> None:
        query = build_query("example.com", "A", ident=0x1234)
        header = struct.pack("!HHHHHH", 0x1234, 0x8180, 1, 1, 0, 0)
        answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton(
            "93.184.216.34"
        )
        parsed = parse_message(header + query[12:] + answer)
        self.assertEqual(parsed["rcode_name"], "NOERROR")
        self.assertEqual(parsed["answers"][0]["data"], "93.184.216.34")


class ExtractorTests(unittest.TestCase):
    def test_gravatar_hash_is_md5_of_trimmed_lower(self) -> None:
        self.assertEqual(
            gravatar_hash("  Lab@Example.com "),
            hashlib.md5(b"lab@example.com").hexdigest(),
        )

    def test_crtsh_names(self) -> None:
        records = [
            {"name_value": "example.com\nwww.example.com"},
            {"name_value": "*.cdn.example.com,other.net"},
        ]
        self.assertEqual(
            names_from_crtsh(records, "example.com"),
            ["cdn.example.com", "example.com", "www.example.com"],
        )
        self.assertEqual(
            names_from_certspotter(
                [{"dns_names": ["example.com", "*.www.example.com", "other.net"]}],
                "example.com",
            ),
            ["example.com", "www.example.com"],
        )

    def test_cdx_rows(self) -> None:
        payload = [
            ["timestamp", "original", "statuscode"],
            ["20200101000000", "http://example.com/", "200"],
        ]
        rows = parse_cdx(payload)
        self.assertEqual(rows[0]["statuscode"], "200")
        self.assertEqual(rows[0]["original"], "http://example.com/")

    def test_jpeg_exif_make(self) -> None:
        fields = parse_jpeg_exif(_exif_jpeg("66-Tool"))
        self.assertEqual(fields.get("make"), "66-Tool")

    def test_png_text(self) -> None:
        fields = parse_png_text(_png_with_text("Comment", "desk"))
        self.assertEqual(fields.get("Comment"), "desk")

    def test_meta_file_roundtrip(self) -> None:
        from tool66.modules.meta import lookup

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shot.jpg"
            path.write_bytes(_exif_jpeg("Ashh66"))
            result = lookup(str(path))
        self.assertTrue(result.ok)
        self.assertEqual(result.data["kind"], "jpeg")
        self.assertEqual(result.data["metadata"]["make"], "Ashh66")
        payload = result.to_payload()
        self.assertEqual(payload["notice"], "public data only")
        self.assertIn("timestamp_utc", payload)
        self.assertTrue(payload["source"])


class WhoisExtractTests(unittest.TestCase):
    @patch.object(whois_mod, "query_whois")
    def test_extracts_indented_verisign_fields(self, mock_query) -> None:
        mock_query.side_effect = [
            "whois: whois.verisign-grs.com\n",
            (
                "   Registrar: RESERVED-Internet Assigned Numbers Authority\n"
                "   Registrar WHOIS Server: whois.iana.org\n"
                "   Creation Date: 1995-08-14T04:00:00Z\n"
                "   Name Server: A.IANA-SERVERS.NET\n"
            ),
        ]
        result = whois_mod.lookup("example.com", 1.0)
        self.assertTrue(result.ok)
        self.assertEqual(
            result.data["extracted"]["registrar"],
            "RESERVED-Internet Assigned Numbers Authority",
        )
        self.assertEqual(result.data["extracted"]["created"], "1995-08-14T04:00:00Z")
        self.assertIn("A.IANA-SERVERS.NET", result.data["name_servers"])


if __name__ == "__main__":
    unittest.main()
