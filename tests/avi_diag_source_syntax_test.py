"""CIV2-B006: native C++ syntax-check of the REAL AVI source without WASI.

This closes the gap between regex policy tests and the owner's first WASM
compiler error. Public source/headers only: no proprietary media, toolchain
download, linking, game data image or browser profile. Uses the exact upstream
thunk generator (re/functions.tsv + auto/protos.h), but not game binary data.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AviSourceSyntax(unittest.TestCase):
    def test_actual_sound_cpp_compiles_under_host_cpp(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--require-compiler", action="store_true")
        args, _ = parser.parse_known_args()
        cxx = shutil.which("clang++") or shutil.which("g++")
        if not cxx:
            if args.require_compiler:
                self.fail("required host C++ compiler unavailable")
            self.skipTest("host C++ compiler unavailable; owner WASM compile still required")
        sys.path.insert(0, str(ROOT / "tools"))
        import build_native

        with tempfile.TemporaryDirectory(prefix="civ2-avi-cxx-") as tmp:
            gen = Path(tmp) / "gen"
            gen.mkdir()
            build_native.GEN = str(gen)
            build_native.gen_thunks(build_native.functions())
            self.assertTrue((gen / "thunks.h").is_file())
            cmd = [
                cxx, "-x", "c++", "-std=gnu++17", "-fsyntax-only",
                "-fno-exceptions", "-fno-rtti", "-fno-inline",
                "-fno-strict-aliasing", "-fwrapv", "-fno-delete-null-pointer-checks",
                "-w", "-include", "native.h",
                "-I", str(ROOT / "src/include"),
                "-I", str(ROOT / "src/auto"),
                "-I", str(ROOT / "tools"),
                "-I", str(gen),
                "-DCIV2_NATIVE", "-DCIV2_LOWMEM",
                str(ROOT / "src/auto/sound.cpp")
            ]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0,
                "Real sound.cpp failed C++ syntax check:\n" + proc.stderr[-7500:])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
