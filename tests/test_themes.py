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


def _channel(value):
    value = value.strip()
    return float(value[:-1]) * 2.55 if value.endswith("%") else float(value)


def resolve_colour(value, tokens, depth=0):
    """Resolves the colour syntaxes used by the token blocks to (r, g, b, alpha)."""
    value = value.strip()
    if depth > 8:
        raise ValueError(f"token cycle at {value}")
    var = re.fullmatch(r"var\((--[a-z0-9-]+)(?:,\s*(.+))?\)", value)
    if var:
        name, fallback = var.groups()
        if name in tokens:
            return resolve_colour(tokens[name], tokens, depth + 1)
        return resolve_colour(fallback, tokens, depth + 1)
    hexa = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
    if hexa:
        digits = hexa.group(1)
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        return tuple(int(digits[index:index + 2], 16) for index in (0, 2, 4)) + (1.0,)
    func = re.fullmatch(r"rgba?\((.*)\)", value)
    if not func:
        raise ValueError(f"unsupported colour: {value}")
    body = func.group(1)
    alpha = 1.0
    if "/" in body:
        body, alpha_text = body.rsplit("/", 1)
        alpha = float(alpha_text)
    body = re.sub(r"var\((--[a-z0-9-]+)(?:,\s*([^)]+))?\)", lambda m: tokens.get(m.group(1), m.group(2) or ""), body)
    parts = [part for part in re.split(r"[\s,]+", body.strip()) if part]
    if len(parts) == 4:
        alpha = float(parts.pop())
    return tuple(_channel(part) for part in parts[:3]) + (alpha,)


def composite(colour, backdrop):
    """Paints a (possibly translucent) colour over an opaque backdrop."""
    alpha = colour[3]
    return tuple(colour[index] * alpha + backdrop[index] * (1 - alpha) for index in range(3)) + (1.0,)


def contrast(foreground, background):
    def luminance(colour):
        def linear(channel):
            channel /= 255
            return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        red, green, blue = (linear(channel) for channel in colour[:3])
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def declarations(block):
    return {name: value.strip() for name, value in re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", block)}


DEFAULT_BLOCK = re.search(r'^:where\(:root\), \[data-theme="nightwatch"\] \{(.*?)^\}', STYLES, re.S | re.M).group(1)
SHARED_BLOCK = re.search(r'^:where\(\[data-theme\]:not\(\[data-theme="nightwatch"\]\)\) \{(.*?)^\}', THEMES, re.S | re.M).group(1)


def theme_tokens(theme):
    """Custom properties in effect on <html> for a theme (shared derived tokens + theme block)."""
    if theme == "nightwatch":
        return declarations(DEFAULT_BLOCK)
    return {**declarations(SHARED_BLOCK), **declarations(token_block(theme))}


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


class ThemeContrastTests(unittest.TestCase):
    """Text tokens must stay readable (WCAG 2.1 AA, 4.5:1) on the page and on panels in every theme."""

    def test_text_tokens_meet_wcag_aa_on_page_and_panels(self):
        failures = []
        for theme in APP_THEMES:
            tokens = theme_tokens(theme)
            void = resolve_colour(tokens["--void"], tokens)
            surfaces = {"page": void}
            for name in ("--panel", "--panel-deep", "--panel-soft"):
                surfaces[name.strip("-")] = composite(resolve_colour(tokens[name], tokens), void)
            for token in ("--text", "--muted", "--dim"):
                for surface_name, surface in surfaces.items():
                    colour = composite(resolve_colour(tokens[token], tokens), surface)
                    ratio = contrast(colour, surface)
                    if ratio < 4.5:
                        failures.append(f"{theme}: {token} on {surface_name} = {ratio:.2f}:1")
        self.assertEqual(failures, [])

    def test_contrast_helper_matches_known_values(self):
        white = resolve_colour("#fff", {})
        black = resolve_colour("rgb(0 0 0)", {})
        self.assertAlmostEqual(contrast(white, black), 21.0, places=2)
        grey = resolve_colour("rgb(var(--x-rgb, 118 118 118) / 1)", {})
        self.assertAlmostEqual(contrast(grey, white), 4.54, places=2)
        half = composite(resolve_colour("rgba(255, 255, 255, .5)", {}), black)
        self.assertAlmostEqual(half[0], 127.5)


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
