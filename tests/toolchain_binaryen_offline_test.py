"""CIV2-B006: pinned Binaryen 130 offline archive and atomic install.

No network, user-owned game media, full toolchain or original CUE/BIN.
"""
import io
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = (ROOT / "tools/fetch-toolchain.sh").read_text(encoding="utf-8")


def extract_function(name):
    start = FETCH.index(name + "() {")
    stop = FETCH.index("\n}\n", start) + 2
    return FETCH[start:stop]


class OfflineBinaryen(unittest.TestCase):
    def test_pinned_source(self):
        for s in (
            'binaryen_name="binaryen-version_130-$binaryen"',
            "binaryen_expected_size=80320428",
            "binaryen_expected_sha=cc09c874f4332d00aa32ab72745a9b98c9a172f795762f21d03e70638a3f7f4c",
            'fetch_archive "$binaryen_name.tar.gz"',
            '[ "$binaryen_sum" = "$binaryen_expected_sha" ]',
            'install_archive "binaryen-version_130" binaryen',
        ):
            self.assertIn(s, FETCH)
        self.assertNotIn('curl -fL# --retry 5 --retry-all-errors --retry-delay 5 "$url" -o binaryen.tar.gz', FETCH)

    def run_fixture(self, valid):
        with tempfile.TemporaryDirectory(prefix="civ2-binaryen-test-") as tmp:
            root = Path(tmp)
            archive = root / "binaryen-version_130-x86_64-windows.tar.gz"
            payload = b"synthetic non-executable wasm-opt\n"
            with tarfile.open(archive, "w:gz") as tf:
                member = tarfile.TarInfo(
                    "binaryen-version_130/bin/wasm-opt.exe" if valid else
                    "binaryen-version_130/bin/not-wasm-opt.exe"
                )
                member.size = len(payload)
                tf.addfile(member, io.BytesIO(payload))
            script = (
                'set -eu\narchive_path="binaryen-version_130-x86_64-windows.tar.gz"\n'
                + extract_function("install_archive") + "\n"
                + 'install_archive "binaryen-version_130" binaryen\n'
            )
            result = subprocess.run(["sh", "-c", script], cwd=tmp,
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)
            self.assertEqual((root / "binaryen").exists(), valid)
            self.assertTrue(archive.is_file())
            if valid:
                self.assertIn("CIV2_TOOLCHAIN_INSTALLED=binaryen", result.stdout)
                self.assertEqual((root / "binaryen/bin/wasm-opt.exe").read_bytes(), payload)
                self.assertFalse(list(root.glob(".civ2-tool-unpack.*")))
            else:
                self.assertIn("missing wasm-opt", result.stderr)

    def test_install_synthetic_binaryen(self):
        self.run_fixture(True)

    def test_missing_wasm_opt_rejected(self):
        self.run_fixture(False)


if __name__ == "__main__":
    unittest.main()
