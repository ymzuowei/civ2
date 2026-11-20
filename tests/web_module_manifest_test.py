"""CIV2-T006: reproduce the browser 404 that Node source-tree tests missed."""
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_web_modules import missing_modules, page_manifest


class BrowserModulePackagingTests(unittest.TestCase):
    def test_every_static_module_is_packaged_for_actual_browser(self):
        manifest = page_manifest(ROOT / "tools/build_web.py")
        self.assertIn("main.js", manifest)
        self.assertIn("graphics_choice.js", manifest)
        self.assertEqual(missing_modules(ROOT / "src/web", manifest), [])

    def test_generated_english_texts_are_not_source_tree_modules(self):
        # i18n.js imports ./texts.js; write_languages() generates that
        # file at build/web/texts.js from src/host/texts.h. It cannot be
        # copied from src/web or declared in PAGE.
        manifest = page_manifest(ROOT / "tools/build_web.py")
        self.assertNotIn("texts.js", manifest)
        self.assertIn("out = os.path.join(OUT, 'texts.js')",
                      (ROOT / "tools/build_web.py").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="civ2-generated-js-") as tmp:
            src = Path(tmp)
            (src / "i18n.js").write_text("import {EN} from './texts.js';")
            self.assertEqual(missing_modules(src, ["i18n.js"]), [])

    def test_missing_graphics_module_is_detected_before_wasm(self):
        with tempfile.TemporaryDirectory(prefix="civ2-js-manifest-") as temp:
            src = Path(temp)
            (src / "index.html").write_text("<script type='module' src='main.js'></script>")
            (src / "main.js").write_text(
                "import {hdArg} from './graphics_choice.js';\n"
            )
            (src / "graphics_choice.js").write_text("export const hdArg = () => 1;")
            self.assertIn(
                "Unpackaged browser dependency: main.js -> graphics_choice.js",
                missing_modules(src, ["index.html", "main.js"]),
            )
            self.assertEqual(
                missing_modules(src, ["index.html", "main.js", "graphics_choice.js"]),
                [],
            )
            (src / "graphics_choice.js").unlink()
            self.assertIn(
                "Missing source file: graphics_choice.js",
                missing_modules(src, ["index.html", "main.js", "graphics_choice.js"]),
            )

    def test_workers_and_dynamic_imports_are_checked(self):
        with tempfile.TemporaryDirectory(prefix="civ2-js-worker-") as temp:
            src = Path(temp)
            (src / "main.js").write_text(
                "new Worker('setup_worker.js', {type: 'module'});\n"
                "const load = import('./optional.js');\n"
            )
            self.assertIn(
                "Unpackaged browser dependency: main.js -> setup_worker.js",
                missing_modules(src, ["main.js"]),
            )
            (src / "setup_worker.js").write_text("export const ready = true;")
            (src / "optional.js").write_text("export const ready = true;")
            self.assertEqual(
                missing_modules(src, ["main.js", "setup_worker.js", "optional.js"]),
                [],
            )

    def test_nested_import_cannot_escape_public_source_root(self):
        with tempfile.TemporaryDirectory(prefix="civ2-js-escape-") as temp:
            src = Path(temp)
            (src / "main.js").write_text("export * from '../secret.js';")
            issues = missing_modules(src, ["main.js"])
            self.assertTrue(any("escapes browser root" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
