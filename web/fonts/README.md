# Gebündelte Schriften

Das Cockpit liefert seine Schriften selbst aus (die CSP erlaubt nur `font-src 'self'`),
damit Layout und Typografie auf jedem System gleich aussehen – ohne CDN-Aufruf.

## Standard-Look (Nightwatch) – `styles.css`

| Datei | Schrift | Schnitt | Lizenz |
| --- | --- | --- | --- |
| `barlow-condensed-latin-{400,700,800,900}-normal.woff2` | Barlow Condensed | Regular, Bold, ExtraBold, Black | SIL OFL 1.1 – `OFL-BarlowCondensed.txt` |
| `space-mono-latin-{400,700}-normal.woff2` | Space Mono | Regular, Bold | SIL OFL 1.1 – `OFL-SpaceMono.txt` |

## Stilwelten – `themes.css`

Diese Dateien lädt der Browser nur, wenn ein Theme (oder eine Design-Lab-Karte) sie wirklich benutzt.

| Datei | Schrift | Stilwelt | Lizenz |
| --- | --- | --- | --- |
| `antonio-latin-{400,700}-normal.woff2` | Antonio | Enterprise (LCARS) | SIL OFL 1.1 – `OFL-Antonio.txt` |
| `noto-sans-jp-119-900-normal.woff2` | Noto Sans JP (Kana-Subset) | Akira (Katakana) | SIL OFL 1.1 – `OFL-NotoSansJP.txt` |
| `noto-sans-jp-103-900-normal.woff2` | Noto Sans JP (Kanji-Subset mit 守) | Sonnenkern auf der Startseite | SIL OFL 1.1 – `OFL-NotoSansJP.txt` |
| `chakra-petch-latin-{500,700}-normal.woff2` | Chakra Petch | Cyberpunk | SIL OFL 1.1 – `OFL-ChakraPetch.txt` |
| `instrument-serif-latin-400-{normal,italic}.woff2` | Instrument Serif | Agentur (Headlines) | SIL OFL 1.1 – `OFL-InstrumentSerif.txt` |
| `instrument-sans-latin-{400,700}-normal.woff2` | Instrument Sans | Agentur (Text) | SIL OFL 1.1 – `OFL-InstrumentSans.txt` |
| `big-shoulders-stencil-display-latin-{700,900}-normal.woff2` | Big Shoulders Stencil Display | U-Boot (Schablonen-Headlines) | SIL OFL 1.1 – `OFL-BigShouldersStencil.txt` |
| `vt323-latin-400-normal.woff2` | VT323 | U-Boot (CRT-Anzeigen) | SIL OFL 1.1 – `OFL-VT323.txt` |

Quelle: [Fontsource](https://fontsource.org) 5.3.0 (`@fontsource/<schrift>`), Latin-Subset (enthält Umlaute und ß).
Die beiden Noto-Sans-JP-Dateien sind Fontsource-Unicode-Chunks; `themes.css` begrenzt sie per
`unicode-range`, damit sie nur für japanische Zeichen nachgeladen werden.
