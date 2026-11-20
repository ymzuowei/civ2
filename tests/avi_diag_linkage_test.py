"""CIV2-B006: compile/link guard for native C logger invoked by C++ AVI code.

No WASI SDK, licensed game media, browser storage or network access needed.
Checks the real game-source declaration and, where host CC/CXX are available,
compiles a tiny C implementation against the equivalent C++ declaration.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOUND = (ROOT / "src/auto/sound.cpp").read_text(encoding="utf-8")


class VideoDiagnosticLoggerLinkage(unittest.TestCase):
    def test_c_linkage_is_declared_before_avi_update(self):
        declaration = "EXTERN_C void plat_log(const char *fmt, ...);"
        self.assertIn(declaration, SOUND)
        self.assertLess(SOUND.index(declaration), SOUND.index("void __cdecl avi_update_frame"))
        self.assertIn('plat_log("video: clock playing=', SOUND)
        self.assertNotIn('#include "../platform/plat.h"', SOUND)

    def test_c_logger_can_link_from_cpp_caller(self):
        cc = shutil.which("cc")
        cxx = shutil.which("c++")
        if not (cc and cxx):
            self.skipTest("host C/C++ compilers not installed: source declaration guard remains active")
        signature = "EXTERN_C void plat_log(const char *fmt, ...);"
        self.assertIn(signature, SOUND)
        with tempfile.TemporaryDirectory(prefix="civ2-avi-link-") as tmp:
            root = Path(tmp)
            (root / "logger.c").write_text(
                "void plat_log(const char *fmt, ...) { (void)fmt; }\n", encoding="utf-8"
            )
            (root / "caller.cpp").write_text(
                '#define EXTERN_C extern "C"\n'
                + signature + '\n'
                + 'int main() { plat_log("frame=%lu", 42UL); return 0; }\n',
                encoding="utf-8",
            )
            obj = root / "logger.o"
            exe = root / ("avi-link.exe" if os.name == "nt" else "avi-link")
            subprocess.run([cc, "-c", str(root / "logger.c"), "-o", str(obj)],
                           check=True, capture_output=True, text=True)
            subprocess.run([cxx, str(root / "caller.cpp"), str(obj), "-o", str(exe)],
                           check=True, capture_output=True, text=True)
            self.assertTrue(exe.is_file())


if __name__ == "__main__":
    unittest.main()
