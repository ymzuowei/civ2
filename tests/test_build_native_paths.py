"""Regression: object output basenames must remain flat on Windows and POSIX.

Runs without the compiler toolchain or original Civilization II assets:
    python -m unittest tests.test_build_native_paths -v
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_native


class FlatObjectNameTests(unittest.TestCase):
    def test_posix_relative_source(self):
        self.assertEqual(build_native.flat_object_name("src/auto/ai.cpp"), "src_auto_ai.cpp.o")

    def test_windows_relative_source(self):
        self.assertEqual(build_native.flat_object_name(r"src\auto\ai.cpp"), "src_auto_ai.cpp.o")

    def test_generated_helpers_in_windows_paths(self):
        self.assertEqual(
            build_native.flat_object_name(r"build\native\gen\calltable.cpp"),
            "build_native_gen_calltable.cpp.o",
        )

    def test_windows_third_party_c_gets_gnu99(self):
        for path in (r"D:\CIV2\src\third_party\indeo4\vlc.c",
                     "/work/src/third_party/indeo4/vlc.c"):
            with self.subTest(path=path):
                with patch.object(build_native.subprocess, "run",
                                  return_value=SimpleNamespace(returncode=0, stderr="")) as compiler:
                    _, err = build_native.compile_one(("clang", path, "dummy.o", True, [], None))
                self.assertIsNone(err)
                flags = compiler.call_args.args[0]
                self.assertIn("-std=gnu99", flags)
                self.assertNotIn("-std=gnu89", flags)

    def test_windows_platform_c_has_portable_c_flags(self):
        for path in (r"D:\CIV2\src\platform\controls.c",
                     "/work/src/platform/controls.c"):
            with self.subTest(path=path):
                with patch.object(build_native.subprocess, "run",
                                  return_value=SimpleNamespace(returncode=0, stderr="")) as compiler:
                    _, err = build_native.compile_one(("clang", path, "dummy.o", True, [], None))
                self.assertIsNone(err)
                flags = compiler.call_args.args[0]
                self.assertIn("-std=gnu99", flags)
                self.assertIn("-D_GNU_SOURCE", flags)

    def test_no_directory_separators_in_output(self):
        for source in ("src/auto/map.cpp", r"src\game\timer_display.cpp", "src/data/gamedata.cpp"):
            name = build_native.flat_object_name(source)
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)


if __name__ == "__main__":
    unittest.main()
