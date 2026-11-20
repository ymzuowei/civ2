"""CIV2-B006: WABT 1.0.41 release filename is NOT its tar top-level dir.

No network, original game media, installed WASI SDK or local toolchain access.
The fixture is a few-byte synthetic gzip under the test temp directory.
"""
import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = (ROOT / "tools/fetch-toolchain.sh").read_text(encoding="utf-8")


def shell_function(name):
    start = FETCH.index(name + "() {")
    end = FETCH.index("\n}\n", start) + 2
    return FETCH[start:end]


class ToolchainReleaseArchiveLayout(unittest.TestCase):
    def test_wabt_tag_matches_archive_root_not_platform_filename(self):
        self.assertIn('wabt_name="wabt-1.0.41-$wabt"', FETCH)
        self.assertIn('fetch_archive "$wabt_name.tar.gz"', FETCH)
        self.assertIn('install_archive "wabt-1.0.41" wabt', FETCH)
        self.assertNotIn('install_archive "$wabt_name" wabt', FETCH)

    def test_atomic_install_accepts_synthetic_wabt_release_layout(self):
        with tempfile.TemporaryDirectory(prefix="civ2-wabt-layout-") as temp:
            archive = Path(temp) / "fixture.tar.gz"
            with tarfile.open(archive, "w:gz") as out:
                payload = b"fixture executable -- not a real compiler\n"
                member = tarfile.TarInfo("wabt-1.0.41/bin/wasm2c.exe")
                member.size = len(payload)
                out.addfile(member, io.BytesIO(payload))

            script = (
                "set -eu\n"
                'archive_path="fixture.tar.gz"\n'
                + shell_function("install_archive") + "\n"
                'install_archive "wabt-1.0.41" wabt\n'
            )
            proc = subprocess.run(
                ["sh", "-c", script], cwd=temp, env=os.environ.copy(),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("CIV2_TOOLCHAIN_INSTALLED=wabt", proc.stdout)
            self.assertEqual(
                (Path(temp) / "wabt/bin/wasm2c.exe").read_bytes(), payload
            )
            self.assertTrue(archive.is_file(), "archive is retained for reuse")
            self.assertFalse(
                list(Path(temp).glob(".civ2-tool-unpack.*")),
                "temporary extraction directory must not persist",
            )

    def test_installer_fails_closed_without_expected_layout(self):
        with tempfile.TemporaryDirectory(prefix="civ2-wabt-wrong-") as temp:
            archive = Path(temp) / "fixture.tar.gz"
            with tarfile.open(archive, "w:gz") as out:
                payload = b"fixture\n"
                member = tarfile.TarInfo("wrong-archive-root/bin/wasm2c.exe")
                member.size = len(payload)
                out.addfile(member, io.BytesIO(payload))
            script = (
                "set -eu\n"
                'archive_path="fixture.tar.gz"\n'
                + shell_function("install_archive") + "\n"
                'install_archive "wabt-1.0.41" wabt\n'
            )
            proc = subprocess.run(
                ["sh", "-c", script], cwd=temp, env=os.environ.copy(),
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unexpected archive layout", proc.stderr)
            self.assertFalse((Path(temp) / "wabt").exists())
            self.assertTrue(archive.is_file())


if __name__ == "__main__":
    unittest.main()
