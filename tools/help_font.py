"""Exact text width for the Move's help display.

The host loads /data/UserData/schwung/host/font.png with charSpacing 1 and
auto-trims each 5px atlas cell to its inked columns (js_display.c
js_display_load_font / js_display_glyph), so the advance is glyph + 1 and the
font is proportional: '.' is 3px of advance, 'M' 6px.

tools/font_widths.json is that atlas measured with the host's own algorithm.
print() draws left to right and set_pixel silently drops anything past x=127 —
no ellipsis, no log line — so a line that does not fit simply loses its tail.
"""
import json
import pathlib

_W = json.loads((pathlib.Path(__file__).parent / "font_widths.json").read_text())

SCREEN_W = 128
MARGIN_X = 2          # help viewer starts its text a couple of pixels in
LINE_BUDGET = 124     # x=2 .. x=126, one px of slack

def supported(ch):
    return ch in _W

def width(s):
    """Pixel advance of s, or None if it contains a glyph the font lacks."""
    total = 0
    for c in s:
        if c not in _W:
            return None
        total += _W[c] + 1
    return total

def fits(s, budget=LINE_BUDGET):
    w = width(s)
    return w is not None and w <= budget

def wrap(text, budget=LINE_BUDGET):
    """Greedy wrap on spaces, measured in pixels rather than characters."""
    out, line = [], ""
    for word in text.split():
        trial = word if not line else line + " " + word
        if fits(trial, budget):
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out
