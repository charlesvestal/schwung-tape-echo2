#!/usr/bin/env python3
"""Generate src/help.json for the on-device Help viewer.

The viewer's loader is one line (shadow_ui.js):

    if (helpData.children) helpMap[id] = helpData.children;

so the topic array MUST be called `children`. A leaf is {title, lines}, where
lines is one string PER DISPLAY LINE - nothing wraps, and print() drops
whatever runs past x=127 with no ellipsis and no log line. This module shipped
`sections`/`body` prose for six releases and the viewer silently showed
"No help content available" the whole time (issue #3).

So the source text lives here as sentences and gets wrapped with the real
font metrics (tools/help_font.py) at build time. Text is written for a
~20-character screen: short lines, ASCII only.

    python3 tools/gen_help.py        # rewrites src/help.json
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import help_font

# (title, [paragraph, ...]) - a blank string forces a blank display line.
TOPICS = [
    ("Overview", [
        "Vintage 3-head tape echo with spring reverb.",
        "",
        "Record EQ and tape saturation sit inside the feedback loop, so each repeat gets darker and more compressed.",
    ]),
    ("Main page", [
        "TIME SYNC FBK MIX",
        "TONE WID TAPE MODE",
        "",
        "TONE, TAPE and WID are macros. They move the real controls on ADVANCED and OUT.",
    ]),
    ("TIME", [
        "Delay in ms. Stays within the head MODE selected, so the two never fight.",
        "",
        "H1 reaches 69-177 ms, H2 to 339, H3 to 490.",
    ]),
    ("TONE", [
        "One tilt across BASS and TREBLE. Left is dark, right is bright.",
    ]),
    ("TAPE", [
        "Wear: moves W&F and AGE together.",
        "",
        "Age scales flutter, so an old tape runs worse. That is why they share a knob.",
    ]),
    ("WID", [
        "How far PONG swings, 0 to 100.",
        "",
        "Turning it up from 0 arms PONG. Turning PONG off by hand keeps it off.",
    ]),
    ("MODE", [
        "Which heads play, and whether the spring is in circuit.",
        "",
        "H1 H2 H3 H2+3",
        "H1+R H2+R H3+R",
        "H12+R H23+R H13+R",
        "H123R Rev",
        "",
        "Digits are heads. R is reverb. Rev is spring only.",
    ]),
    ("FBK", [
        "Feedback. Above about 75% it self oscillates and builds.",
        "",
        "It gets loud. Ride ECHO.",
    ]),
    ("MIX", [
        "Dry against wet. 50% is both at unity, 0 dry only, 100 wet only.",
    ]),
    ("SYNC", [
        "Locks the leading head to host tempo. DIV on OUT picks the note.",
    ]),
    ("ARM", [
        "The dub switch.",
        "",
        "Off stops feeding the tape while the repeats already on it wash out.",
        "",
        "The spring is fed before the gate, so a +R mode still reverberates.",
    ]),
    ("DRIVE", [
        "Preamp gain into the record stage. Higher settings saturate the tape.",
    ]),
    ("AGE", [
        "New, Used or Old tape. Older adds noise, HF loss, wobble and splice wear.",
    ]),
    ("W&F", [
        "Wow and flutter, plus a scrape band around 6 Hz.",
        "",
        "0 is not still. The transport always moves a little, like the real one.",
    ]),
    ("BASS / TREBLE", [
        "Shelves on the echo path only. The dry stays as it is.",
        "",
        "Treble cut inside the loop makes each repeat darker than the last.",
    ]),
    ("RATE", [
        "The raw motor knob. TIME drives this, in ms.",
    ]),
    ("ECHO / VERB", [
        "Levels for the tape echo and the spring tank.",
        "",
        "VERB is only audible in a +R mode.",
    ]),
    ("PONG", [
        "Sends each repeat to the opposite side.",
        "",
        "Every head swaps on its own delay, so multi head modes separate too.",
        "",
        "Off, the echo is mono and matches the original exactly.",
    ]),
    ("DIV", [
        "The 11 tempo sync detents. The note follows the leading head, as on the hardware.",
    ]),
    ("TapeDelay presets", [
        "Old TapeDelay settings are read and converted.",
        "",
        "Time picks the head that reaches it. Feedback, mix, tone, division and width carry over.",
        "",
        "A patch names the module it wants, so point it here first with the converter in tools/.",
    ]),
    ("Credits", [
        "DSP: Tape Echo 2 by Dusk Audio, GPL-3.0.",
        "",
        "The core carries one Schwung change, a per head ping pong on the output tap. With PONG off it is the original sample for sample.",
        "",
        "Move port by athousanddetails.",
        "Macro page and legacy calibration by charlesvestal.",
    ]),
]


def build():
    children = []
    for title, paras in TOPICS:
        lines = []
        for para in paras:
            if para == "":
                lines.append("")
            else:
                lines.extend(help_font.wrap(para))
        children.append({"title": title, "lines": lines})
    return {"title": "Tape Echo 2", "children": children}


if __name__ == "__main__":
    doc = build()
    bad = []
    for topic in doc["children"]:
        if not help_font.fits(topic["title"]):
            bad.append(("title", topic["title"]))
        for ln in topic["lines"]:
            if not help_font.fits(ln):
                bad.append((topic["title"], ln))
    if bad:
        for where, ln in bad:
            print(f"  too wide or unsupported glyph in {where}: {ln!r}")
        raise SystemExit(1)
    out = pathlib.Path(__file__).parent.parent / "src/help.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    n = sum(len(t["lines"]) for t in doc["children"])
    print(f"help.json: {len(doc['children'])} topics, {n} lines, all within "
          f"{help_font.LINE_BUDGET}px")
