"""Regression tests for the generator's archive input boundary."""

import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import generate_timezone_fixture as generator


class ArchiveTest(unittest.TestCase):
    def test_oversized_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "oversized.tar.gz"
            archive.write_bytes(b"12345")
            with patch.object(generator, "MAX_ARCHIVE_BYTES", 4):
                with self.assertRaisesRegex(ValueError, "archive exceeds size limit"):
                    generator.read_verified_archive(archive)

    def test_wrong_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "incorrect.tar.gz"
            archive.write_bytes(b"not the pinned archive")
            with self.assertRaisesRegex(ValueError, "archive checksum"):
                generator.read_verified_archive(archive)

    def test_generation_uses_the_verified_snapshot(self):
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            for name in generator.SOURCE_FILES:
                archive.addfile(tarfile.TarInfo(name))
        data = payload.getvalue()

        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.tar.gz"
            archive.write_bytes(data)

            def run(*command):
                if command[1] == "--version":
                    archive.write_bytes(b"replacement with a different digest")
                    return f"{command[0]} (tzcode) {generator.TOOL_VERSION}"
                return ""

            with patch.object(generator, "ARCHIVE_SHA256", hashlib.sha256(data).hexdigest()):
                with patch.object(generator, "run", side_effect=run):
                    result = generator.generate(archive, (), fixture_mode=True)
            self.assertIn("class FixtureZoneProvider:", result)


if __name__ == "__main__":
    unittest.main()
