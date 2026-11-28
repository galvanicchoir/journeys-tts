"""Render the boss tiles (landscape frame: name top left, power + health top right, art left, abilities right).
Usage: python tts/build/render_bosses.py [repo root]   ->  cards/framed/bosses/<boss id>.png  (1200x660)
Boss art goes in art/bosses/<boss id>.png (any size; cropped to fill the art panel)."""
import os, sys, html, re
from openpyxl import load_workbook
import render_cards as rc
from card_frame import die_icons

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = os.path.join(ROOT, "cards", "framed", "bosses")
HEART = ('<svg width="48" height="44" viewBox="0 0 27 25"><path d="M13.5 23.5C6 18.2 1.5 13.6 1.5 8.4 1.5 4.6 4.3 1.8 7.8 1.8c2.4 0 4.4 1.3 5.7 3.3 '
         '1.3-2 3.3-3.3 5.7-3.3 3.5 0 6.3 2.8 6.3 6.6 0 5.2-4.5 9.8-12 15.1z" fill="#a82a24" stroke="#f0d58c" stroke-width="1.4"/>'
         '<path d="M6 6.2c1-1.4 2.6-1.8 3.8-1.2" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.2" stroke-linecap="round"/></svg>')

def ability(text, name):
    return re.sub(r"^<p>|</p>$", "", rc.rules_html(text, "", name))

def boss_html(b, adventure):
    name = html.escape(rc.s(b["name"]))
    hp = rc.s(b["health"]); per = hp.endswith("*")
    art = os.path.join(ROOT, "art", "bosses", f"{b['boss_id']}.png")
    art_html = f'<img src="file://{art}">' if os.path.exists(art) else f'<div class="ph">{rc.PICTURE}<span>ART</span></div>'
    rows = "".join(f'<div class="row"><span class="die">{die_icons.icon(rc.DIE_FAMILY, k, 22)}</span><p>{ability(b[k], b["name"])}</p></div>'
                   for k in "ABC" if rc.s(b[k]))
    passive = f'<p class="passive">{ability(b["text"], b["name"])}</p>' if rc.s(b["text"]) else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="boss.css"></head><body>
<div class="boss" id="card">
  <div class="head"><div class="titles"><div class="name" id="name">{name}</div>
    <div class="typeline"><span class="t">{html.escape(rc.s(b["traits"]))}</span></div></div>
    <div class="stats"><div class="power">{rc.SWORD}<span>{html.escape(rc.s(b["power"]) or "0")}</span></div>
      <div class="heart{" per" if per else ""}">{HEART}<span>{html.escape(hp.rstrip("*"))}</span>{"<small>PER HERO</small>" if per else ""}</div></div></div>
  <div class="body"><div class="art">{art_html}</div><div class="abil" id="text">{passive}{rows}</div></div>
  <div class="foot"><span>{html.escape(adventure)}</span><span>{html.escape(b["boss_id"])}</span></div>
</div></body></html>"""

FIT = rc.FIT.replace("f = 19; while (t", "f = 16; while (t").replace("let f = 19", "let f = 27")

def main():
    from playwright.sync_api import sync_playwright
    wb = load_workbook(os.path.join(ROOT, "data", "journeys-cards.xlsx"), read_only=True)
    bosses, advs, journey = rc.rows(wb["Bosses"]), rc.rows(wb["Adventures"]), rc.rows(wb["Journey"])
    adv_name = {a["adventure_id"]: a["name"] for a in advs}
    where = {}                                         # boss id -> the adventure whose journey ends in it ("boss:<id>")
    for j in journey:
        for m in re.finditer(r"boss:([^:;\s]+)", rc.s(j["actions"])): where.setdefault(m.group(1), adv_name.get(j["adventure_id"], "Boss"))
    tmp = os.path.join(rc.FRAME, "_boss.html"); os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 600, "height": 330}, device_scale_factor=2)
        for b in bosses:
            with open(tmp, "w", encoding="utf-8") as f: f.write(boss_html(b, where.get(b["boss_id"], "Boss")))
            page.goto("file://" + tmp); page.evaluate("document.fonts.ready")
            fit = page.evaluate(FIT)
            page.locator("#card").screenshot(path=os.path.join(OUT, f"{b['boss_id'].lower()}.png"), omit_background=True)
            print("rendered", b["boss_id"], "" if all(fit.values()) else "CHECK: text too long")
    os.remove(tmp)

if __name__ == "__main__":
    main()
