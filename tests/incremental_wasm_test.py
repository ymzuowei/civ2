"""CIV2-T006: small media-free incremental WASM build regression."""
import ast
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_native.py"


def builders():
    tree = ast.parse(BUILDER.read_text(encoding="utf-8"), str(BUILDER))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in ("write_generated", "needs_link")]
    if len(nodes) != 2:
        raise AssertionError("incremental build helpers unavailable")
    namespace = {"os": os}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 str(BUILDER), "exec"), namespace)
    return namespace["write_generated"], namespace["needs_link"]


class IncrementalWasmBuild(unittest.TestCase):
    def test_identical_generated_bytes_preserve_mtime(self):
        write, _ = builders()
        with tempfile.TemporaryDirectory(prefix="civ2-native-inc-") as td:
            output = Path(td) / "gen.cpp"
            self.assertTrue(write(str(output), "#define G 1\n"))
            old_mtime = output.stat().st_mtime_ns
            self.assertFalse(write(str(output), "#define G 1\n"))
            self.assertEqual(output.stat().st_mtime_ns, old_mtime)
            self.assertTrue(write(str(output), "#define G 2\n"))
            self.assertEqual(output.read_bytes(), b"#define G 2\n")
            self.assertFalse((Path(td) / "gen.cpp.part").exists())

    def test_link_only_when_inputs_or_recipe_change(self):
        _, stale = builders()
        with tempfile.TemporaryDirectory(prefix="civ2-native-link-") as td:
            exe = Path(td) / "game.wasm"
            obj = Path(td) / "game.o"
            obj.write_bytes(b"obj")
            self.assertTrue(stale(str(exe), [str(obj)], 0, True))
            exe.write_bytes(b"wasm")
            os.utime(obj, ns=(1_000_000_000, 1_000_000_000))
            os.utime(exe, ns=(2_000_000_000, 2_000_000_000))
            self.assertFalse(stale(str(exe), [str(obj)], 0, True))
            self.assertTrue(stale(str(exe), [str(obj)], 1, True))
            self.assertTrue(stale(str(exe), [str(obj)], 0, False))
            os.utime(obj, ns=(3_000_000_000, 3_000_000_000))
            self.assertTrue(stale(str(exe), [str(obj)], 0, True))

    def test_build_recipe_guards_reuse(self):
        code = BUILDER.read_text(encoding="utf-8")
        for guard in ("signature_path", "signature_matches", "recipe_hash",
                      "compiler_size_mtime", "CIV2_NATIVE_OBJECTS_REBUILT",
                      "CIV2_NATIVE_INCREMENTAL_LINK=REUSED",
                      "CIV2_NATIVE_INCREMENTAL_LINK=REBUILT"):
            self.assertIn(guard, code)


if __name__ == "__main__":
    unittest.main()
