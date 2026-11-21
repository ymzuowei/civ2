"""Check the actual static browser module manifest before expensive WASM builds.

Node's source-tree unit tests resolve imports directly from src/web and thus
cannot catch missing files in the published build/web/ directory. This guard
checks the *packaged* entry-point dependency closure with no SDK or game media.
"""
import ast
import posixpath
import re
from pathlib import Path


# Static ES module import/export, literal dynamic import, and module worker.
_STATIC = re.compile(
    r"""(?m)^\s*(?:import|export)\s+(?:[^;\n]*?\s+from\s*)?["']([^"'\n]+\.js)["']"""
)
_DYNAMIC = re.compile(r"""\bimport\s*\(\s*["']([^"'\n]+\.js)["']\s*\)""")
_WORKER = re.compile(r"""\bnew\s+(?:SharedWorker|Worker)\s*\(\s*["']([^"'\n]+\.js)["']""")

# tools/build_web.py.write_languages() generates build/web/texts.js from
# src/host/texts.h. It deliberately has no src/web/texts.js counterpart.
GENERATED_MODULES = {"texts.js"}


def page_manifest(build_script):
    tree = ast.parse(Path(build_script).read_text(encoding="utf-8"))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PAGE"
            for t in statement.targets
        ):
            manifest = ast.literal_eval(statement.value)
            if not isinstance(manifest, list) or not all(
                isinstance(name, str) for name in manifest
            ):
                raise ValueError("Invalid browser PAGE manifest")
            return manifest
    raise ValueError("Browser PAGE manifest not found")


def references(source):
    return (set(_STATIC.findall(source)) |
            set(_DYNAMIC.findall(source)) |
            set(_WORKER.findall(source)))


def missing_modules(source_dir, manifest):
    source_dir = Path(source_dir)
    entries = set(manifest)
    missing = []
    if len(entries) != len(manifest):
        missing.append("Duplicate entries in PAGE")
    for name in sorted(entries):
        if name.startswith("/") or posixpath.normpath(name).startswith("../"):
            missing.append("Unsafe PAGE entry: " + name)
            continue
        path = source_dir / name
        if not path.is_file():
            missing.append("Missing source file: " + name)
            continue
        if not name.endswith(".js"):
            continue
        for ref in references(path.read_text(encoding="utf-8")):
            if ref.startswith(("https:", "http:", "/")):
                continue
            if ref.startswith("node:"):
                missing.append("Node-only module in browser: " + ref)
                continue
            resolved = posixpath.normpath(posixpath.join(
                posixpath.dirname(name), ref))
            if resolved.startswith("../") or resolved == "..":
                missing.append("Module escapes browser root: " + name + " -> " + ref)
            elif resolved not in entries and resolved not in GENERATED_MODULES:
                missing.append("Unpackaged browser dependency: " + name + " -> " + resolved)
    return sorted(set(missing))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    missing = missing_modules(root / "src/web",
                              page_manifest(root / "tools/build_web.py"))
    if missing:
        raise SystemExit("\n".join(missing))
    print("CIV2_BROWSER_MODULE_MANIFEST=PASS")
