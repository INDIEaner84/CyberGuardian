"""Static checks for the style worlds: tokens, theme ids and bundled assets stay consistent."""

import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
STYLES = (WEB / "styles.css").read_text(encoding="utf-8")
THEMES = (WEB / "themes.css").read_text(encoding="utf-8")
APP = (WEB / "app.js").read_text(encoding="utf-8")
BOOT = (WEB / "theme-boot.js").read_text(encoding="utf-8")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")

APP_THEMES = re.findall(r"'([a-z]+)'", re.search(r"const THEME_IDS = \[([^\]]+)\]", APP).group(1))
STYLE_WORLDS = [theme for theme in APP_THEMES if theme != "nightwatch"]


def token_block(theme):
    """The declaration block of the exact `[data-theme="<theme>"] {` token selector in themes.css."""
    match = re.search(r'^\[data-theme="%s"\] \{(.*?)^\}' % re.escape(theme), THEMES, re.S | re.M)
    return match.group(1) if match else None


class ThemeTokenTests(unittest.TestCase):
    def test_default_look_keeps_its_literal_colours(self):
        # Every family token used by styles.css carries its original colour as fallback ...
        missing = re.search(r"var\(--[a-z-]+-rgb\)", STYLES)
        self.assertIsNone(missing, f"family token without fallback: {missing and missing.group(0)}")
        # ... and outside the named default tokens no colour is hard-coded any more.
        root = re.search(r'^:where\(:root\), \[data-theme="nightwatch"\] \{.*?^\}', STYLES, re.S | re.M)
        self.assertIsNotNone(root, "default token block")
        rules = STYLES.replace(root.group(0), "")
        leftovers = re.findall(r".{0,40}(?:rgba\(\s*\d|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)", rules)
        self.assertEqual(leftovers, [], "hard-coded colours bypass the theme tokens")
        # ... and styles.css never assigns a family (except resetting them for nested Nightwatch scopes).
        for value in re.findall(r"--[a-z-]+-rgb:\s*([^;]+);", STYLES):
            self.assertEqual(value.strip(), "initial")

    def test_every_style_world_defines_every_colour_family(self):
        families = sorted(set(re.findall(r"var\(--([a-z-]+)-rgb,", STYLES)))
        self.assertGreaterEqual(len(families), 12)
        resets = set(re.findall(r"--([a-z-]+)-rgb: initial", STYLES))
        self.assertEqual(set(families), resets, "the Nightwatch reset must cover every family")
        for theme in STYLE_WORLDS:
            block = token_block(theme)
            self.assertIsNotNone(block, f"missing token block for {theme}")
            defined = set(re.findall(r"--([a-z-]+)-rgb:\s*\d", block))
            self.assertEqual(sorted(set(families) - defined), [], f"{theme} leaves colour families undefined")
            for font in ("--display", "--headline"):
                self.assertIn(f"{font}:", block, f"{theme} must choose {font}")


class ThemeRegistryTests(unittest.TestCase):
    def test_theme_ids_match_across_boot_script_app_and_markup(self):
        self.assertEqual(APP_THEMES[0], "nightwatch")
        self.assertEqual(len(APP_THEMES), 6)
        boot = re.findall(r"'([a-z]+)'", re.search(r"var themes = \[([^\]]+)\]", BOOT).group(1))
        self.assertEqual(boot, STYLE_WORLDS)
        selects = re.findall(r"<select data-theme-select[^>]*>(.*?)</select>", INDEX, re.S)
        self.assertEqual(len(selects), 2, "landing header + cockpit top bar")
        for select in selects:
            self.assertEqual(re.findall(r'<option value="([a-z]+)"', select), APP_THEMES)
        cards = re.findall(r'<article class="world-card" data-theme="([a-z]+)"', INDEX)
        self.assertEqual(cards, STYLE_WORLDS)
        for theme in STYLE_WORLDS:
            self.assertIn(f'data-theme-preview="{theme}"', INDEX)
            self.assertIn(f'data-theme-apply="{theme}"', INDEX)
            self.assertRegex(APP, r"\n    %s: \{\n      index:" % theme, f"themeWorlds preview copy for {theme}")
            self.assertRegex(APP, r"%s: \{ label: '[^']+', color: '#[0-9a-f]{6}' \}" % theme)

    def test_study_thumbnails_stay_in_the_nightwatch_palette(self):
        thumbs = re.findall(r'<span class="variant-thumb variant-thumb--[a-z]+"([^>]*)>', INDEX)
        self.assertEqual(len(thumbs), 4)
        for attributes in thumbs:
            self.assertIn('data-theme="nightwatch"', attributes)

    def test_head_applies_theme_before_first_paint(self):
        head = INDEX.split("</head>", 1)[0]
        boot = head.index('<script src="/theme-boot.js"></script>')
        styles = head.index('href="/styles.css"')
        themes = head.index('href="/themes.css"')
        self.assertLess(boot, styles)
        self.assertLess(styles, themes, "themes.css must override styles.css")
        self.assertNotIn(" defer", head[boot - 5:boot + 45])
        self.assertIn("localStorage.getItem('cyberguardian.theme')", BOOT)
        self.assertIn("themes.indexOf(stored) !== -1", BOOT, "only known ids may reach the DOM")


class BundledFontTests(unittest.TestCase):
    def test_every_font_file_is_referenced_and_licensed(self):
        referenced = set(re.findall(r"url\('fonts/([^']+\.woff2)'\)", STYLES + THEMES))
        on_disk = {path.name for path in (WEB / "fonts").glob("*.woff2")}
        self.assertEqual(referenced, on_disk, "orphaned or missing font files")
        readme = (WEB / "fonts" / "README.md").read_text(encoding="utf-8")
        for license_file in re.findall(r"`(OFL-[A-Za-z]+\.txt)`", readme):
            self.assertTrue((WEB / "fonts" / license_file).is_file(), license_file)
        for family in set(re.findall(r"font-family: '([^']+)'", STYLES + THEMES)):
            self.assertIn(family, readme, f"{family} missing from fonts/README.md")


if __name__ == "__main__":
    unittest.main()
