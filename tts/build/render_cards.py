"""Render the encounter cards in the new frame.

    python3 tts/build/render_cards.py <repo folder> [card id ...]

Reads the encounter cards (sets with the encounter back) from data/journeys-cards.xlsx and draws each one with
the frame in tts/build/card_frame/ (HTML + CSS, rendered by headless Chromium at 762x1067).

  art      art/encounters/<card name>.png (or .jpg). Missing art is cut out of the card's current export in cards/
           the first time, unless that export only has a placeholder silhouette; then the card shows an ART box.
  output   cards/framed/ + the source_file path under cards/, e.g. cards/framed/encounters/Trouble with Goblins/Goblin Lackey x3.png.
           build.py uses a framed image instead of the export whenever one exists.

Needs:  pip install playwright openpyxl pillow   then   python -m playwright install chromium
Give card ids to render only those (e.g. TWG-004 IGK-003)."""
import html, os, re, sys
from openpyxl import load_workbook
from PIL import Image, ImageChops
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_frame"))
import die_icons
import gem_icons
DIE_FAMILY = "solid"                        # boss die symbols (A circle, B triangle, C square): solid, outline or ink

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
ONLY = set(sys.argv[2:])
HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "card_frame")
ART = os.path.join(ROOT, "art", "encounters")
OUT = os.path.join(ROOT, "cards", "framed")
OLD_ART_BOX = (64, 168, 698, 620)          # where the art sits on the old 762x1067 export

def rows(ws):
    it = ws.iter_rows(values_only=True); hdr = next(it)
    return [dict(zip(hdr, r)) for r in it if any(v is not None for v in r)]

def s(v): return "" if v is None else str(v).strip()

# ---------------------------------------------------------------- type line -> stacking
# "Goblin - Backline (Generic)": role sets the rank glyph, brackets become the "stacks with" chip.
# "(Behind X)" / "(Front X)" pin the card to the very back / front. Same reading as build.py's stack_info.
def type_info(traits, kind):
    if kind != "Enemy":
        return {"type": traits or kind, "rank": None, "joins": ""}
    m = re.match(r"^(.*?)\s*-\s*([A-Za-z]+)\s*(?:\(([^)]*)\))?\s*$", traits or "")
    if not m:
        return {"type": traits or "Enemy", "rank": "mid", "joins": ""}
    head, role, paren = m.group(1), m.group(2), (m.group(3) or "").strip()
    if role == "Unique":                      # uniques follow their own stacking rules (in their text): star, not bars
        return {"type": f"{head} \u2014 {role}", "rank": "unique", "joins": ""}
    rank = {"Backline": "back", "Vanguard": "front"}.get(role, "mid")
    if re.match(r"(?i)behind\b", paren): rank, paren = "behind", re.sub(r"(?i)^behind\s*", "", paren)
    elif re.match(r"(?i)front\b", paren): rank, paren = "fore", re.sub(r"(?i)^front\s*", "", paren)
    return {"type": f"{head} — {role}", "rank": rank, "joins": paren}

def rank_svg(rank, size=18):
    on, off = "#e6c46a", "rgba(0,0,0,0.35)"
    if rank == "unique":
        return (f'<svg class="rank" width="{size}" height="{size}" viewBox="0 0 16 16"><path d="M8 0.8 10.1 5.6 15.3 6.1 11.4 9.6 '
                f'12.5 14.7 8 12.1 3.5 14.7 4.6 9.6 0.7 6.1 5.9 5.6Z" fill="{on}" stroke="#5c4520" stroke-width="0.6" stroke-linejoin="round"/></svg>')
    slot = {"behind": 1, "back": 1, "mid": 2, "front": 3, "fore": 3}[rank]
    bars = "".join(f'<rect x="2" y="{y}" width="12" height="3.4" rx="1.2" fill="{on if i + 1 == slot else off}" stroke="{on}" stroke-width="0.8"/>'
                   for i, y in enumerate((4, 9.3, 14.6)))
    top = f'<path d="M2 2.2 5 0l3 2.2L11 0l3 2.2" fill="none" stroke="{on}" stroke-width="1.6" stroke-linejoin="round"/>' if rank == "behind" else ""
    bot = f'<path d="M2 19.8 5 22l3-2.2 3 2.2 3-2.2" fill="none" stroke="{on}" stroke-width="1.6" stroke-linejoin="round"/>' if rank == "fore" else ""
    return f'<svg class="rank" width="{round(size * 16 / 22)}" height="{size}" viewBox="0 0 16 22">{top}{bars}{bot}</svg>'

CHAIN = ('<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#f0d58c" stroke-width="3" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>')
SWORD = ('<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#e6c46a" stroke-width="2" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M14.5 17.5 3 6V3h3l11.5 11.5"/><path d="m13 19 6-6"/><path d="m16 16 4 4"/><path d="m19 21 2-2"/></svg>')
SHIELD = ('<svg width="44" height="50" viewBox="0 0 30 33"><path d="M15 1.5 27.5 5.5v10c0 8-6 13.5-12.5 16C8.5 29 2.5 23.5 2.5 15.5v-10z" '
          'fill="{fill}" stroke="#e6c46a" stroke-width="1.6"/><path d="M15 4 25 7.2v8.3c0 6.6-4.9 11.2-10 13.3-5.1-2.1-10-6.7-10-13.3V7.2z" '
          'fill="none" stroke="rgba(0,0,0,0.35)" stroke-width="0.8"/></svg>')
STAR = ('<svg width="34" height="34" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7.2" fill="none" stroke="#b89cf0" stroke-width="1" opacity=".7"/>'
        '<circle cx="12" cy="12" r="7.2" fill="none" stroke="#e6c46a" stroke-width="0.8" stroke-dasharray="1.2 2.2"/>'
        '<path d="M12 2.5 13.7 10.3 21.5 12 13.7 13.7 12 21.5 10.3 13.7 2.5 12 10.3 10.3Z" fill="#fbecc4" stroke="#e6c46a" stroke-width=".6" stroke-linejoin="round"/>'
        '<path d="M12 7.5 12.8 11.2 16.5 12 12.8 12.8 12 16.5 11.2 12.8 7.5 12 11.2 11.2Z" fill="#c9a6ff"/></svg>')
PICTURE = ('<svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="#6d5f4c" stroke-width="1.4" stroke-linecap="round" '
           'stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/></svg>')

# ---------------------------------------------------------------- rules text
LEAD = r"(Enter|Act|Defeat|Tap|Activate|Action|Imbued|A|B|C)"
def rules_html(text, keywords, name=""):
    t = s(text)
    nm = html.escape(s(name), quote=False)
    kws = [k.strip() for k in s(keywords).split(",") if k.strip()]
    flavor = t.startswith('"') and t.endswith('"')
    out = html.escape(t, quote=False)
    if flavor:
        return f'<p class="flavor">{out}</p>'
    out = re.sub(r"\(([^)]*)\)", r"<i>(\1)</i>", out)                        # reminder text
    out = re.sub(r"(^|(?<=[.:,] ))" + LEAD + r"(\s-\s)", r"\1<b>\2</b>\3", out)    # "Enter - ", "A - " ...
    if nm: out = out.replace(nm, "\x00")                                      # the card's own name never gets keyword-bolded
    for k in kws:                                                             # keywords from the keywords column
        out = re.sub(r"(?<![\w>])(" + re.escape(k) + r")(?![\w<])", r"<b>\1</b>", out, flags=re.I)
    out = re.sub(r"(?<![\w>])(reinforces?|cascade)(?![\w<])", r"<b>\1</b>", out, flags=re.I)
    if nm: out = out.replace("\x00", nm)
    out = re.sub(r"(\+?\d+)?\{([rgb])\}", lambda m: gem_icons.svg(m.group(2), 28 if m.group(1) else 14, label=m.group(1) or ""), out)
    gemify = lambda x: re.sub(r"(\+?\d+)?\{([rgb])\}", lambda m: gem_icons.svg(m.group(2), 28 if m.group(1) else 14, label=m.group(1) or ""), x)
    body = t.replace(s(name), "") if name else t
    missing = [gemify(html.escape(k)) for k in kws if k.lower() not in body.lower()]   # e.g. "Lasting 2{g}"
    lead = f"<p><b>{' \u00b7 '.join(missing)}</b></p>" if missing else ""            # all keywords on one line: "Focus · Aggro"
    # break before each boss-die result so "A - ... B - ... C - ..." reads as a list
    out = re.sub(r"(?<=\.)\s(?=<b>[ABC]</b> - )", "</p><p>", out)
    out = re.sub(r"<b>([ABC])</b> - ", lambda m: f'<span class="die">{die_icons.icon(DIE_FAMILY, m.group(1), 18)}</span> ', out)
    return lead + (f"<p>{out}</p>" if out else "")

def is_short(rules):
    """Short text (up to two lines/paragraphs, e.g. a keyword line + one ability): centre it across as well as down."""
    words = re.sub(r"<[^>]+>", "", rules)
    return len(re.findall(r"<p[ >]", rules)) <= 2 and len(words) <= 110

def clear_html(channel):
    parts = []
    for tok in re.findall(r"\{([rgb])\}|(\|)", s(channel)):
        parts.append(gem_icons.svg(tok[0], 19, "#e6c46a", "pip") if tok[0] else "<em>|</em>")
    return f'<div class="clear"><b>CLEAR</b>{"".join(parts)}</div>'

# ---------------------------------------------------------------- art
def art_for(c):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(ART, c["name"] + ext)
        if os.path.exists(p): return p
    src = os.path.join(ROOT, s(c["source_file"]))
    if not os.path.exists(src): return None
    crop = Image.open(src).convert("RGB").resize((762, 1067)).crop(OLD_ART_BOX)
    r, g, b = crop.resize((80, 57)).split()
    lo = ImageChops.darker(r, ImageChops.darker(g, b))          # darkest channel per pixel
    white = sum(lo.histogram()[233:]) / (80 * 57)
    if white > 0.30:                                   # the old placeholder silhouette on white: no real art yet
        return None
    os.makedirs(ART, exist_ok=True)
    p = os.path.join(ART, c["name"] + ".png"); crop.save(p, optimize=True)
    return p

def framed_path(root, source_file):
    """cards/encounters/X/Name x2.png -> <root>/cards/framed/encounters/X/Name x2.png (build.py uses the same rule)."""
    rel = s(source_file).replace("\\", "/")
    rel = rel[len("cards/"):] if rel.startswith("cards/") else rel
    return os.path.join(root, "cards", "framed", rel)

# ---------------------------------------------------------------- one card
def card_html(c, set_name):
    kind = s(c["card_type"])
    ti = type_info(s(c["traits"]), kind)
    horde = kind == "Enemy" and ("Horde" in s(c["name"]) or "reinforce" in s(c["keywords"]).lower())
    cls = {"Enemy": "horde" if horde else "enemy", "Event": "event", "Obstacle": "obstacle"}.get(kind, "event")
    name = html.escape(s(c["name"]))
    tl = rank_svg(ti["rank"]) if ti["rank"] else ""
    tl += f'<span class="t">{html.escape(ti["type"])}</span>'
    right = ""
    if kind == "Enemy":
        hp = s(c["health"]) or "–"
        acts = s(c["power"]) in ("", "0") and re.search(r"\bAct\s-", s(c["text"]))
        power = (f'<div class="power act" title="Acts">{STAR}</div>' if acts else
                 f'<div class="power">{SWORD}<span>{html.escape(s(c["power"]) or "0")}</span></div>')
        right = (f'<div class="stats">{power}'
                 f'<div class="health">{SHIELD.format(fill="#2f5fb0" if horde else "#a82a24")}'
                 f'<span class="{"small" if len(hp) > 2 else ""}">{html.escape(hp)}</span></div></div>')
    elif kind == "Obstacle" and s(c["channel"]):
        right = clear_html(c["channel"])
    art = art_for(c)
    rules = rules_html(c["text"], c["keywords"], c["name"])
    art_html = (f'<img src="file://{art}">' if art else f'<div class="ph">{PICTURE}<span>ART</span></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="frame.css"></head><body>
<div class="card {cls}" id="card">
  <div class="head"><div class="titles"><div class="name" id="name">{name}</div><div class="typeline">{tl}</div></div>{right}</div>
  <div class="art">{art_html}</div>
  <div class="rule"><div class="l"></div><div class="d"></div><div class="o"></div><div class="d"></div><div class="l"></div></div>
  <div class="text{' short' if is_short(rules) else ''}" id="text">{rules}</div>
  <div class="foot"><span>{html.escape(set_name)}</span><span>{html.escape(s(c["id"]))}</span></div>
</div></body></html>"""

FIT = """() => {
  const n = document.getElementById('name');
  let f = 19; while (n.scrollWidth > n.clientWidth && f > 13) { f -= 0.5; n.style.fontSize = f + 'px'; }
  const t = document.getElementById('text');
  f = 19; while (t.scrollHeight > t.clientHeight && f > 11) { f -= 0.5; t.style.fontSize = f + 'px'; }
  return { name: n.scrollWidth <= n.clientWidth, text: t.scrollHeight <= t.clientHeight };
}"""

def main():
    from playwright.sync_api import sync_playwright
    wb = load_workbook(os.path.join(ROOT, "data", "journeys-cards.xlsx"), read_only=True)
    cards, sets = rows(wb["Cards"]), rows(wb["Sets"])
    set_by = {x["set"]: x for x in sets}
    todo = [c for c in cards if set_by.get(c["set"], {}).get("back") == "encounter" and (not ONLY or c["id"] in ONLY)]
    tmp = os.path.join(FRAME, "_card.html")
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 381, "height": 533}, device_scale_factor=2)
        for c in todo:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(card_html(c, s(set_by[c["set"]]["name"])))
            page.goto("file://" + tmp); page.evaluate("document.fonts.ready")
            fit = page.evaluate(FIT)
            if not all(fit.values()): problems.append(f'{c["id"]} {c["name"]}: {"name" if not fit["name"] else "text"} still too long')
            dest = framed_path(ROOT, c["source_file"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            page.locator("#card").screenshot(path=dest, omit_background=True)
            print("rendered", c["id"], c["name"])
        browser.close()
    os.remove(tmp)
    for line in problems: print("CHECK:", line)

if __name__ == "__main__":
    main()
