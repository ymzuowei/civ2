"""CIV2-T015: native C++ syntax-check of the actual setup side-picture provider.

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


class IntroAtlasSourceSyntax(unittest.TestCase):
    def test_actual_game_setup_cpp_compiles_under_host_cpp(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--require-compiler", action="store_true")
        args, _ = parser.parse_known_args()
        # GNU C++ -fpermissive can parse the legacy 32-bit pointer-to-int
        # casts under a 64-bit host without treating them as fatal errors.
        # Undeclared identifiers (the actual CIV2-B006 failure) still fail.
        # The real wasm32 build continues to use strict upstream flags.
        cxx = shutil.which("g++") or shutil.which("clang++")
        if not cxx:
            if args.require_compiler:
                self.fail("required host C++ compiler unavailable")
            self.skipTest("host C++ compiler unavailable; owner WASM compile still required")
        sys.path.insert(0, str(ROOT / "tools"))
        import build_native

        with tempfile.TemporaryDirectory(prefix="civ2-intro-atlas-cxx-") as tmp:
            gen = Path(tmp) / "gen"
            gen.mkdir()
            build_native.GEN = str(gen)
            build_native.gen_thunks(build_native.functions())
            self.assertTrue((gen / "thunks.h").is_file())
            cmd = [
                cxx, "-x", "c++", "-std=gnu++17", "-fsyntax-only",
                *(["-fpermissive"] if Path(cxx).name.startswith("g++") else []),
                "-fno-exceptions", "-fno-rtti", "-fno-inline",
                "-fno-strict-aliasing", "-fwrapv", "-fno-delete-null-pointer-checks",
                # Host compiler is 64-bit, while game layout assertions target
                # the original 32-bit ABI. Disable only these assertions for
                # this supplementary syntax probe; the real wasm32 compiler
                # retains every native static_assert during owner builds.
                "-Dstatic_assert(...)=", "-w", "-include", "native.h",
                "-I", str(ROOT / "src/include"),
                "-I", str(ROOT / "src/auto"),
                "-I", str(ROOT / "tools"),
                "-I", str(gen),
                "-DCIV2_NATIVE", "-DCIV2_LOWMEM",
                str(ROOT / "src/auto/game_setup.cpp")
            ]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0,
                "Real game_setup.cpp failed C++ syntax check:\n" + proc.stderr[-7500:])
            cc = shutil.which("gcc") or shutil.which("clang")
            self.assertTrue(cc, "required host C compiler unavailable")
            cproc = subprocess.run([cc, "-std=gnu17", "-fsyntax-only", "-w",
                                    str(ROOT / "src/platform/hd.c")],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(cproc.returncode, 0, cproc.stderr[-7500:])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
