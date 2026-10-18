# Samantha brand kit

One page for the look. The visual version is `web/brand.html`, live at /brand.html on the site. The source of truth stays where it lives (tokens in `web/index.html`, rules in `CLAUDE.md`); this points at all of it.

## Files
`brand/` holds the kit's assets: `tokens.css` (the landing's tokens), `mark.svg` (the mascot) and `icon-1024.png` (the app icon master, opaque, no alpha, the same picture as `gui/Samantha.icon`). Web sizes are `web/icon-192.png`, `icon-512.png`, `favicon-32.png` and `apple-touch-icon.png`, all cut from that master. The words stay here in `docs/BRAND.md`.

## Logos
| Use | File |
|-----|------|
| The mascot: her portrait as a flat icon (copper hair, round glasses, freckles), friendly, never smug | `web/mascot.svg` |
| App icon on Apple platforms: the mascot, cream tile, shoulders bleeding to the edge (`gui/Samantha.icon`, `brand/icon-1024.png`). Joshua keeps it (2026-10-17) | `brand/icon-1024.png` |
| Her flower mark, rebuilt byte for byte by `tools_logo.icon_svg()`, mark 70 to 80 percent of the tile | `web/icon.svg`, `web/samantha-logo.png` |
| Medallion: engraved SAMANTHA / TURING, kept for the record, the footer uses the mascot from 6.0 | `web/badge.svg`, `art/badge-source.svg` |

Every app icon goes through the icon composer skill. Never put text in an icon.

## Color
| Token | Dark | Light |
|-------|------|-------|
| `--bg` | #000000 | #ffffff |
| `--fg` | #f2f2f2 | #151515 |
| `--muted` | #9a9a9a | #666666 |
| `--line` | #2a2a2a | #e4e4e4 |
| `--accent` / `--ember` | #e0825a | #b5502c |

One accent: terracotta, from her copper hair, #b5502c in light and #e0825a in dark (white text on the light one, black on the dark one, both past 4.5:1). It goes on Send, links, focus rings, selection, the live bar, the sliders and the main button; the iPhone app already wore it on Send and Yes. Everything else stays black, white and gray. The landing footer carries one engraved harbour plate in the accent: fine hatching on paper, which is texture, not a gradient. Banned: yellow, teal, purple, gradients, a second accent. Joshua asked for color on 2026-10-18; before that the web was fully neutral.

## Type
Samantha Sans, three weights (Regular 400, Medium 500, Semibold 600), built by `scripts/gen_font.py` into `web/fonts`. Since 2026-10-18 it is Inter, the open face drawn in the spirit of SF and Helvetica, renamed for her under its SIL Open Font License; the hand-drawn monoline cut before it read too technical. Letters and figures are proportional. Sans-serif only in the UI, no monospace UI; code blocks stay monospace. The apps register it through `gui/Typeface.swift` and fall back to the system font. Samantha Sans is the one custom typeface in the house: Joshua rejected Talli Sans and wants system type elsewhere, but chose to keep hers (2026-10-17). It is hers alone; no other app copies it.

Scale: five sizes. Display 28 to 40 (500, tracking -0.02em), title 26 (500, -0.01em), body 17 (400), small 14 (400, muted), label 12 (600, caps, +0.07em). Line height 1.6 for reading, 1.15 for headlines. The tokens are `--t-*` and `--track-*` in `brand/tokens.css`. Fallback stack: SF, Helvetica Neue, Helvetica, Lato.

## Space and shape
Radius `--r-sm` 6, `--r-md` 10, `--r-pill` 999. Spacing `--s-1` to `--s-5`: 8, 16, 24, 40, 64. Buttons and inputs are pills.

## Voice
Plain, short, direct. No em dashes. Say what she did, not how she is built. The page leads with on-device and tools.
