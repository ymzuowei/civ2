"""CIV2-T006: fail-fast, codepage-safe first-play Graphics locale contract.

Run on the media-free hosted source gate before the owner's expensive fonts,
WASM compilation and browser preview. Historic non-UTF-8 files must retain
their *exact* pre-existing Git blob bytes before the seven new ASCII-safe keys.
"""
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANG = ROOT / "data/native/lang"
KEYS = (
    "web.graphics_label", "web.graphics_choose_title",
    "web.graphics_choose_note", "web.graphics_classic", "web.graphics_hd",
    "web.graphics_unavailable", "web.graphics_switch_confirm",
)
ORIGINAL_BLOBS = {
    "de": "4ec83c6a3f9240a7286bf8190e76e796cae5495b",
    "el": "cc2d248b39f1dbb3a65982e628de40f01a6584b6",
    "eo": "f987cb46707e9132077a83f2089fa6db91a6c06b",
    "la": "a7e16b3ae1a0105a06a44d059dc362217ae42f9b",
}
CODEPAGES = {
    "en": "cp1252", "de": "cp1252", "el": "utf-8",
    "eo": "iso-8859-3", "la": "cp1252",
    "zh-Hans": "utf-8", "zh-Hant": "utf-8",
}


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def entry(text, key):
    marker = "@@openciv2." + key + "\n"
    assert text.count(marker) == 1, f"locale key {key}: expected exactly once"
    suffix = text.split(marker, 1)[1]
    return suffix.split("\n@@", 1)[0].rstrip("\n")


class GraphicsLanguageContract(unittest.TestCase):
    def test_source_english_matches_export_template_and_all_locales(self):
        source = (ROOT / "src/host/texts.h").read_text(encoding="ascii")
        translations = {}
        for key in KEYS:
            matches = re.findall(r'^T\("' + re.escape(key) + r'", "(.*)"\)', source, re.M)
            self.assertEqual(len(matches), 1, key)
            translations[key] = matches[0]
        for code, cp in CODEPAGES.items():
            with self.subTest(locale=code):
                data = (LANG / (code + ".txt")).read_bytes()
                text = data.decode(cp, errors="strict")
                for key in KEYS:
                    value = entry(text, key)
                    self.assertTrue(value, f"{code}: empty {key}")
                    if code == "en":
                        self.assertEqual(value, translations[key])
                    self.assertEqual(re.findall(r"%[sd]", value),
                                     re.findall(r"%[sd]", translations[key]))

    def test_every_historical_translation_prefix_is_bit_exact(self):
        marker = b"@@openciv2.web.graphics_label\n"
        for code, sha in ORIGINAL_BLOBS.items():
            with self.subTest(locale=code):
                raw = (LANG / (code + ".txt")).read_bytes()
                self.assertEqual(raw.count(marker), 1)
                original = raw.split(marker, 1)[0]
                self.assertEqual(git_blob_sha(original), sha,
                                 "Existing language content was re-encoded or rewritten")
                if code in ("de", "eo"):
                    with self.assertRaises(UnicodeDecodeError):
                        original.decode("utf-8")

    def test_english_graphics_keys_have_original_export_order(self):
        text = (LANG / "en.txt").read_text(encoding="cp1252")
        locations = [text.index("@@openciv2." + key + "\n") for key in KEYS]
        self.assertEqual(locations, sorted(locations))
        self.assertLess(locations[-1], text.index("@@openciv2.web.display\n"))


if __name__ == "__main__":
    unittest.main()
