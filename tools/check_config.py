#!/usr/bin/env python3
"""Contract check: module.json chain_params, the C param table, the chain UI
and the ui_hierarchy pages must all describe the same parameter surface.

Runs in the build container before the cross-compile; a violation fails it.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import help_font

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- sources ----------------------------------------------------------
mod = json.loads((ROOT / "src/module.json").read_text())
chain = mod["capabilities"]["chain_params"]
params_h = (ROOT / "src/dsp/te2_params.h").read_text()
ui_chain = (ROOT / "src/ui_chain.js").read_text()

chain_by_key = {p["key"]: p for p in chain}

# ---- C param table is the source of truth -----------------------------
c_keys = re.findall(r'\{\s*"(\w+)",\s+"', params_h)
for k in chain_by_key:
    check(k in c_keys, f"chain_params key {k} not in te2_params.h")

for p in chain:
    if p["type"] != "enum":
        continue
    # every option string must appear verbatim in the C options table,
    # otherwise set_param's name lookup silently falls back to atof() -> 0
    for opt in p["options"]:
        check(f'"{opt}"' in params_h,
              f"{p['key']}: option '{opt}' missing from te2_params.h")

# ---- ui_chain.js mirrors the same keys and options --------------------
for k in chain_by_key:
    check(f'"{k}"' in ui_chain, f"ui_chain.js is missing param {k}")
for p in chain:
    if p["type"] != "enum":
        continue
    for opt in p["options"]:
        check(f'"{opt}"' in ui_chain,
              f"ui_chain.js: {p['key']} option '{opt}' missing/stale")

# ---- every published param is on a ui_hierarchy page -------------------
# repeat_rate was a chain_param that no level listed, so no hierarchy-driven
# UI could reach it and nothing here noticed (issue #2). The page tables are
# hand-maintained next to the param table, so compare them.
plugin_cpp = (ROOT / "src/dsp/tape_echo_plugin.cpp").read_text()
hier_keys = []
for arr in re.findall(r"te2_knobs_\w+\[\d+\]\s*=\s*\{(.*?)\};", plugin_cpp, re.S):
    body = re.sub(r"/\*.*?\*/", "", arr, flags=re.S)      # strip comments
    hier_keys += re.findall(r'"(\w+)"', body)
check(bool(hier_keys), "found the te2_knobs_* page tables")
check(len(hier_keys) == len(set(hier_keys)),
      "a key appears on more than one ui_hierarchy page")
for k in hier_keys:
    check(k in chain_by_key, f"hierarchy page lists {k}, which is not a chain_param")
for k in chain_by_key:
    check(k in hier_keys,
          f"{k} is a chain_param but on no ui_hierarchy page — no hierarchy-driven "
          f"UI can reach it")

# ---- the .so filename the host will actually dlopen -------------------
# An audio_fx module is loaded from "<audio_fx>/<id>/<id>.so" (chain_host.c
# builds that path literally and NEVER reads the module.json "dsp" field).
# Only sound_generators are loaded as dsp.so. Getting this wrong makes the
# module appear in the FX picker (the list comes from module.json) and then
# silently fail to load, which is exactly what shipping dsp.so did.
if mod.get("component_type") == "audio_fx":
    want = f'{mod["id"]}.so'
    check(mod.get("dsp") == want,
          f'audio_fx dsp must be "{want}", got "{mod.get("dsp")}"')
    cmake = (ROOT / "CMakeLists.txt").read_text()
    check(f'OUTPUT_NAME "{mod["id"]}"' in cmake,
          f'CMakeLists must set OUTPUT_NAME "{mod["id"]}" so the build emits {want}')
    for script, needle in (("scripts/docker-build.sh", f"build/{want}"),
                           ("scripts/deploy.sh", f'SO="{want}"')):
        check(needle in (ROOT / script).read_text(),
              f"{script} must ship {want}")

# ---- help.json is in the shape the Help viewer actually reads ---------
# The viewer's whole test is `if (helpData.children)` (shadow_ui.js), so a file
# keyed `sections` parses fine, is dropped without a warning, and the module
# reads "No help content available". This shipped that way for six releases
# (issue #3). Leaves are {title, lines}; lines are per DISPLAY LINE, nothing
# wraps, and print() drops whatever passes x=127 silently.
help_doc = json.loads((ROOT / "src/help.json").read_text())
check("children" in help_doc,
      "help.json needs a top-level `children` array or the viewer drops it "
      "silently (a `sections` key is ignored)")

def _walk_help(node, path):
    kids, lines = node.get("children"), node.get("lines")
    check(bool(node.get("title")), f"help node at {path} needs a title")
    check(bool(kids) != bool(lines),
          f"help node {path}: exactly one of children (branch) or lines (leaf)")
    if lines is not None:
        check(isinstance(lines, list),
              f"help leaf {path}: lines must be a list of display lines")
        for i, ln in enumerate(lines or []):
            check(isinstance(ln, str), f"help leaf {path} line {i} is not a string")
            if not isinstance(ln, str):
                continue
            bad = [c for c in ln if not help_font.supported(c)]
            check(not bad,
                  f"help {path} line {i}: no glyph for {bad!r} - the font is "
                  f"printable ASCII plus AOUaou/euro/dagger/degree, and an "
                  f"unmapped char renders as a 1px gap")
            if not bad:
                w = help_font.width(ln)
                check(w <= help_font.LINE_BUDGET,
                      f"help {path} line {i}: {w}px wide, over the "
                      f"{help_font.LINE_BUDGET}px display - the tail is dropped "
                      f"with no ellipsis: {ln!r}")
    for k in (kids or []):
        _walk_help(k, f"{path}/{k.get('title', '?')}")

for k in help_doc.get("children", []):
    _walk_help(k, k.get("title", "?"))

# and it has to actually ship
for script in ("scripts/docker-build.sh",):
    check("help.json" in (ROOT / script).read_text(),
          f"{script} must copy help.json into dist/")

# ---- module.json under the 8 KB loader cap ----------------------------
sz = (ROOT / "src/module.json").stat().st_size
check(sz < 8192, f"module.json {sz} bytes exceeds the 8 KB loader cap")

if fails:
    print("CONFIG CONTRACT FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)

print(f"config contract OK: {len(chain)} chain_params on "
      f"{len(hier_keys)} page slots, module.json {sz} B")
