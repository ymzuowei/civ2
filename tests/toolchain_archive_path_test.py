"""CIV2-B006: Git Bash/Windows archive-path conversion (no 520 MB download)."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = (ROOT / "tools/fetch-toolchain.sh").read_text(encoding="utf-8")
START = "normalize_toolchain_archive_dir() {"
BEGIN = FETCH.index(START)
END = FETCH.index("\n}\n", BEGIN) + 2
NORMALIZE = FETCH[BEGIN:END]

# Stub the command used by the real script; the test works even on Linux CI
# and never reads D:, downloads an asset or invokes a local Windows compiler.
MOCK_CYGPATH = r"""
cygpath() {
    [ "$1" = "-u" ] && [ "$2" = "--" ] || return 2
    case "$3" in
        'D:\DevCache\CIV2Web\Candidate\Downloads'|'D:/DevCache/CIV2Web/Candidate/Downloads')
            printf '%s\n' '/d/DevCache/CIV2Web/Candidate/Downloads' ;;
        *) return 3 ;;
    esac
}
"""


class ToolchainArchivePath(unittest.TestCase):
    def check(self, raw, expected, succeeds=True):
        env = os.environ.copy()
        env["CIV2_ARCHIVE_PATH_TEST"] = raw
        script = (
            MOCK_CYGPATH + "\n" + NORMALIZE +
            '\nnormalize_toolchain_archive_dir "$CIV2_ARCHIVE_PATH_TEST"\n'
        )
        result = subprocess.run(["sh", "-c", script], env=env,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode == 0, succeeds, result.stderr)
        if succeeds:
            self.assertEqual(result.stdout.strip(), expected)

    def test_backslash_windows_drive_from_python(self):
        self.check(r"D:\DevCache\CIV2Web\Candidate\Downloads",
                   "/d/DevCache/CIV2Web/Candidate/Downloads")

    def test_forwardslash_windows_drive(self):
        self.check("D:/DevCache/CIV2Web/Candidate/Downloads",
                   "/d/DevCache/CIV2Web/Candidate/Downloads")

    def test_already_git_bash_path(self):
        self.check("/d/DevCache/CIV2Web/Candidate/Downloads",
                   "/d/DevCache/CIV2Web/Candidate/Downloads")

    def test_bad_drive_path_fails_closed(self):
        self.check(r"Z:\invalid\path", "", succeeds=False)

    def test_tar_receives_normalized_directory(self):
        self.assertIn('supplied="$local_archive_dir/$filename"', FETCH)
        self.assertIn('archive_path="$supplied"', FETCH)
        self.assertIn('tar -tzf "$archive_path"', FETCH)
        self.assertIn('tar -xzf "$file_to_unpack"', FETCH)
        self.assertNotIn('supplied="$CIV2_TOOLCHAIN_ARCHIVE_DIR/$filename"', FETCH)


if __name__ == "__main__":
    unittest.main()
