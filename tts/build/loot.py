"""Random weapon loot for Journeys (stopgap until the real loot system exists).

    python3 tts/build/loot.py <repo folder> [--reroll] [--seed N] [--per N] [--no-render]

Rolls a pool of class-locked weapons. Each weapon belongs to one class and one subclass, and every bonus on it
names a card from that class's core set or that subclass (so nothing on it is dead for its owner).

  tiers    II, III, IV  (Tier I is the class starter weapon).  Bonuses: II = 1 minor, III = minor + major,
           IV = minor + 2 majors.  Base activation: recycle a card - N{r}, with N from BASE_DAMAGE.
  pool     --per weapons per subclass per tier (default 3) -> 5 classes x 2 subclasses x 3 tiers x 3 = 90.
  storage  data/loot-weapons.json keeps the rolled pool, so weapons stay the same between builds. Only --reroll
           (or a missing file) rolls a new pool. A weapon whose bonus card has left the catalog is rerolled alone.
  output   Cards rows (set LOOT-<class>) + a Loot tab (id, class, subclass, tier) in data/journeys-cards.xlsx,
           card images in cards/framed/loot/<Class>/, and data/loot-weapons.md (the pool as a readable list).

Run after catalog.py (which rewrites the xlsx) and before build.py.  Rendering needs playwright + chromium,
like render_cards.py."""
import html, json, os, random, re, sys
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.styles import Font, PatternFill, Alignment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "card_frame"))
import gem_icons
from render_cards import SWORD, STAR as CAST    # same power / cast symbols as the encounter cards
HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "card_frame")
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
TIERS = (2, 3, 4)
BASE_DAMAGE = {2: 1, 3: 2, 4: 2}             # weapon Power by tier (or the heal on an Activate weapon)
ACTIVATE = {"Priest"}                          # these classes' weapons have no Power: an Activate ability instead
def base_line(w):
    n = BASE_DAMAGE[w["tier"]]
    if w["class"] in ACTIVATE: return f"Activate - Recycle a card: Heal an ally {n}."
    return "Activate - Recycle a card: Deal its Power to an enemy."
SLOTS = {2: ["minor"], 3: ["minor", "major"], 4: ["minor", "major", "major"]}
SUB_WEIGHT = 2                                # subclass cards are picked this many times as often as core cards

# ------------------------------------------------------------------ names
NOUNS = {
    "Mage": ["Staff", "Wand", "Rod", "Scepter", "Stave"],
    "Warrior": ["Sword", "Axe", "Mace", "Warhammer", "Blade", "Cleaver"],
    "Priest": ["Mace", "Scepter", "Censer", "Flail", "Crozier"],
    "Dragonheart": ["Glaive", "Spear", "Fang", "Talon", "Halberd"],
    "Rogue": ["Dagger", "Dirk", "Stiletto", "Knife", "Kris"],
}
SUB_NOUNS = {"Outlaw": ["Pistol", "Blunderbuss"]}       # added to the class list for that subclass
FLAVOR = {  # subclass: (adjectives, "of ..." suffixes, art tint)
    "Fire": (["Smoldering", "Cinderwood", "Ashen", "Scorched", "Blazing", "Emberforged"],
             ["Cinders", "the Pyre", "Kindling", "Ash", "the Bonfire", "Embers"], "#c2462a"),
    "Ice": (["Frostbitten", "Rimed", "Glacial", "Hoarfrost", "Wintry", "Shivering"],
            ["Rime", "the Long Winter", "Stillness", "the Glacier", "Sleet", "the Thaw"], "#4a8fc4"),
    "Blade Dancer": (["Dancing", "Whirling", "Keen", "Duelist's", "Flickering", "Balanced"],
                     ["the Riposte", "Grace", "the Edge", "Tempo", "the Feint", "Whirlwinds"], "#b08a3a"),
    "Ironclad": (["Ironbound", "Stalwart", "Riveted", "Unyielding", "Heavy", "Bulwark"],
                 ["the Rampart", "Iron", "Holding Fast", "the Wall", "the Line", "the Anvil"], "#6e7783"),
    "Anointed": (["Blessed", "Hallowed", "Consecrated", "Radiant", "Gilded", "Sanctified"],
                 ["Grace", "the Litany", "Mercy", "Devotion", "the Vigil", "Benediction"], "#a9bfdc"),
    "Seraph": (["Luminous", "Winged", "Choral", "Haloed", "Gleaming", "Feathered"],
               ["the Choir", "Wings", "the Host", "Daybreak", "Light", "the Seraphim"], "#7fbf8a"),
    "Broodmother": (["Clutchkeeper's", "Nesting", "Brooding", "Hatchling", "Matriarch's", "Wyrmling"],
                    ["the Brood", "the Clutch", "the Nest", "Hatching", "Many Wings", "the Mother"], "#8a4fa0"),
    "Scaleborn": (["Scaled", "Molting", "Wyrmblood", "Searing", "Horned", "Drakeforged"],
                  ["Scales", "the Wyrm", "Shedding", "the Hoard", "Dragonfire", "the Molt"], "#c0612b"),
    "Assassin": (["Venomous", "Silent", "Shadowed", "Black", "Whispering", "Hollow"],
                 ["Shadows", "the Unseen", "Silence", "Nightfall", "the Final Breath", "Poison"], "#5b4a78"),
    "Outlaw": (["Notorious", "Wanted", "Lucky", "Infamous", "Rakish", "Smoking"],
               ["Renown", "the Bounty", "Infamy", "the Showdown", "Fortune", "the Long Odds"], "#a07a2e"),
}

# ------------------------------------------------------------------ bonuses
# Each bonus names one card. Text uses {n} for the card name and {c} / {c2} for gem colours found in that card's text.
# who: None = any class, or a set of class / subclass names it is limited to. weight: how often it is picked.
def colors(c): return list(dict.fromkeys(re.findall(r"\{([rgb])\}", c["text"])))
def deals(c): return bool(re.search(r"\bdeal\b", c["text"], re.I))
def kw(c, k): return k.lower() in (c["keywords"] or "").lower()
def says(c, *words): return any(w.lower() in c["text"].lower() for w in words)

BONUSES = [
    # Every bonus buffs the named card itself (Nolan, 2026-11-25): more gems, an extra rider, or a keyword.
    # key, slot, who, weight, text, eligible(card)
    ("gem",       "minor", None, 10, "{n} gets +1{c}.",                                   lambda c: colors(c)),
    ("shield",    "minor", None, 2, "{n} also gives you 1 Shield.",                        lambda c: not says(c, "shield")),
    ("heal",      "minor", None, 2, "{n} also heals you 1.",                               lambda c: not says(c, "heal")),
    ("killdraw",  "minor", None, 2, "If {n} defeats an enemy, draw a card.",               lambda c: deals(c) and not says(c, "draw")),
    ("calm",      "minor", None, 1, "{n} loses Aggro.",                                    lambda c: kw(c, "Aggro")),
    ("burn",      "minor", {"Fire"}, 3, "{n} also applies 1 burn to an enemy.",            lambda c: True),
    ("frost",     "minor", {"Ice"}, 3, "{n} also applies Frost to each enemy it damages.", lambda c: deals(c) and not says(c, "frost")),
    ("ember",     "minor", {"Dragonheart"}, 3, "{n} also gains you 1 Ember.",              lambda c: not says(c, "ember")),
    ("renown",    "minor", {"Outlaw"}, 3, "If {n} defeats an enemy, gain renown.",         lambda c: deals(c) and not says(c, "renown")),
    ("fade",      "minor", {"Assassin"}, 3, "If {n} defeats an enemy, enter stealth.",     lambda c: deals(c) and not says(c, "stealth")),
    ("mend",      "minor", {"Priest"}, 3, "{n} also heals an ally 1.",                     lambda c: not says(c, "heal")),
    ("ward",      "minor", {"Ironclad"}, 3, "While you have Shield, {n} gets +1{c}.",      lambda c: colors(c)),
    ("flourish",  "minor", {"Blade Dancer"}, 3, "{n} also untaps a weapon you control.",   lambda c: not says(c, "untap")),
    ("gem2",      "major", None, 5, "{n} gets +2{c}.",                                     lambda c: colors(c)),
    ("twin",      "major", None, 3, "{n} gets +1{c} and +1{c2}.",                          lambda c: len(colors(c)) >= 2),
    ("quick",     "major", None, 3, "{n} has Quickcast.",                                  lambda c: c["card_type"] == "Skill" and not kw(c, "Quickcast")),
    ("imbue",     "major", {"Priest"}, 3, "{n} is always Imbued.",                         lambda c: says(c, "imbued")),
    ("whelp",     "major", {"Broodmother"}, 3, "{n} also creates a Whelp token.",          lambda c: True),
    ("stoke",     "major", {"Scaleborn"}, 3, "{n} also gains you 2 Embers.",               lambda c: True),
]
BONUS = {b[0]: b for b in BONUSES}

def usable_cards(cards, cls, sub):
    """Cards a bonus may name: the class core + this subclass, minus weapons, placeholders and pick-one cards
    (e.g. Scaleborn Transformations - only one is in the deck)."""
    out = []
    for c in cards:
        if c["set"] not in (cls["core_set"], sub["subclass_set"]): continue
        if c["card_type"] in ("Weapon", "Hero", "Ancestry"): continue
        if c["name"] in ("Card Name", "") : continue
        if sub["choose_one"] and sub["choose_one"].lower() in (c["traits"] or "").lower(): continue
        out.append(c)
    return out

def bonus_text(key, card, cols):
    b = BONUS[key]
    t = b[4].replace("{n}", card["name"])
    if cols: t = t.replace("{c2}", "{" + (cols[1] if len(cols) > 1 else cols[0]) + "}").replace("{c}", "{" + cols[0] + "}")
    return t

def roll_bonuses(rng, tier, cls_name, sub_name, pool, by_id):
    """Pick SLOTS[tier] bonuses, each on a different card and of a different kind."""
    picked, used_cards, used_keys = [], set(), set()   # used_keys holds bonus keys and texts (no repeats on a weapon)
    for slot in SLOTS[tier]:
        options = []
        for key, bslot, who, w, _t, ok in BONUSES:
            if bslot != slot or key in used_keys or _t in used_keys: continue
            if who and cls_name not in who and sub_name not in who: continue
            for c in pool:
                if c["id"] in used_cards or not ok(c): continue
                cw = SUB_WEIGHT if c["set"] != pool_core(pool, cls_name) else 1
                options.append((w * cw, key, c))
        if not options: continue
        tot = sum(o[0] for o in options); r = rng.uniform(0, tot)
        for w, key, c in options:
            r -= w
            if r <= 0: break
        cols = colors(c); rng.shuffle(cols)
        picked.append({"key": key, "card": c["id"], "colors": cols})
        used_cards.add(c["id"]); used_keys.update((key, BONUS[key][4]))
    return picked

_CORE = {}
def pool_core(pool, cls_name): return _CORE[cls_name]

def roll_name(rng, tier, cls_name, sub_name, taken):
    adjs, sufs, _ = FLAVOR[sub_name]
    nouns = NOUNS[cls_name] + SUB_NOUNS.get(sub_name, [])
    for _ in range(200):
        n, a, s = rng.choice(nouns), rng.choice(adjs), rng.choice(sufs)
        name = {2: f"{a} {n}", 3: f"{n} of {s}", 4: f"{a} {n} of {s}"}[tier]
        if name not in taken: taken.add(name); return name
    raise SystemExit("ran out of weapon names for " + sub_name)

def roll_weapon(rng, tier, cls_name, sub_name, pool, by_id, taken, wid):
    return {"id": wid, "class": cls_name, "subclass": sub_name, "tier": tier,
            "name": roll_name(rng, tier, cls_name, sub_name, taken),
            "bonuses": roll_bonuses(rng, tier, cls_name, sub_name, pool, by_id)}

def weapon_text(w, by_id):
    parts = [f"Weapon {ROMAN[w['tier']]}. " + base_line(w)]
    parts += [bonus_text(b["key"], by_id[b["card"]], b["colors"]) for b in w["bonuses"]]
    return " ".join(parts)

# ------------------------------------------------------------------ xlsx
def rows(ws):
    it = ws.iter_rows(values_only=True); hdr = list(next(it))
    return hdr, [dict(zip(hdr, r)) for r in it if any(v is not None for v in r)]

def rewrite(ws, hdr, data):
    ws.delete_rows(2, ws.max_row)
    for d in data: ws.append([d.get(h) for h in hdr])
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    for t in ws.tables.values():
        t.ref = f"A1:{chr(64 + len(hdr))}{max(len(data), 1) + 1}"

def safe(name): return re.sub(r'[<>:"/\\|?*]', "", name)

# ------------------------------------------------------------------ rendering (same frame as the encounter cards)
def card_html(w, by_id):
    tier, tint = w["tier"], FLAVOR[w["subclass"]][2]
    def gems(t): return re.sub(r"(\+?\d+)?\{([rgb])\}", lambda m: gem_icons.svg(m.group(2), 28 if m.group(1) else 14, label=m.group(1) or ""), t)
    bl = html.escape(base_line(w), quote=False).replace("Activate - ", "<b>Activate</b> - ", 1)
    lines = [f'<p class="base">{bl}</p>']
    if w["class"] in ACTIVATE:
        stat = f'<div class="power act" title="Activate">{CAST}</div>'
    else:
        stat = f'<div class="power">{SWORD}<span>{BASE_DAMAGE[tier]}</span></div>'
    for b in w["bonuses"]:
        c = by_id[b["card"]]
        t = html.escape(bonus_text(b["key"], c, b["colors"]), quote=False)
        t = t.replace(html.escape(c["name"], quote=False), f'<span class="cn">{html.escape(c["name"], quote=False)}</span>', 1)
        lines.append(f'<p class="bonus {BASE_SLOT(b["key"])}">{gems(t)}</p>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="frame.css"></head><body>
<div class="card weapon" id="card">
  <div class="head"><div class="titles"><div class="name" id="name">{html.escape(w["name"])}</div>
    <div class="typeline"><span class="t">{html.escape(w["class"])} Weapon — {html.escape(w["subclass"])} · Tier {ROMAN[tier]}</span></div></div>
    <div class="stats">{stat}</div></div>
  <div class="art loot" style="--tint:{tint}"><span>{ROMAN[tier]}</span></div>
  <div class="rule"><div class="l"></div><div class="d"></div><div class="o"></div><div class="d"></div><div class="l"></div></div>
  <div class="text" id="text">{"".join(lines)}</div>
  <div class="foot"><span>Loot · Tier {ROMAN[tier]}</span><span>{html.escape(w["id"])}</span></div>
</div></body></html>"""

def BASE_SLOT(key): return BONUS[key][1]

FIT = """() => {
  const n = document.getElementById('name');
  let f = 19; while (n.scrollWidth > n.clientWidth && f > 12) { f -= 0.5; n.style.fontSize = f + 'px'; }
  const t = document.getElementById('text');
  f = 19; while (t.scrollHeight > t.clientHeight && f > 13) { f -= 0.5; t.style.fontSize = f + 'px'; }
  return { name: n.scrollWidth <= n.clientWidth, text: t.scrollHeight <= t.clientHeight };
}"""

def render(weapons, by_id, root):
    from playwright.sync_api import sync_playwright
    tmp = os.path.join(FRAME, "_loot.html"); problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 381, "height": 533}, device_scale_factor=2)
        for w in weapons:
            open(tmp, "w", encoding="utf-8").write(card_html(w, by_id))
            page.goto("file://" + tmp); page.evaluate("document.fonts.ready")
            fit = page.evaluate(FIT)
            if not all(fit.values()): problems.append(f'{w["id"]} {w["name"]}: still too long')
            dest = os.path.join(root, "cards", "framed", "loot", w["class"], safe(w["name"]) + ".png")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            page.locator("#card").screenshot(path=dest, omit_background=True)
        browser.close()
    os.remove(tmp)
    for line in problems: print("CHECK:", line)

# ------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    root = os.path.abspath(args[0] if args and not args[0].startswith("--") else ".")
    def opt(name, default):
        return int(args[args.index(name) + 1]) if name in args else default
    seed, per = opt("--seed", None), opt("--per", 3)
    reroll, no_render = "--reroll" in args, "--no-render" in args

    xlsx = os.path.join(root, "data", "journeys-cards.xlsx")
    wb = load_workbook(xlsx)
    chdr, cards = rows(wb["Cards"]); shdr, sets = rows(wb["Sets"]); _, classes = rows(wb["Classes"])
    cards = [c for c in cards if not str(c["set"]).startswith("LOOT-")]
    sets = [s for s in sets if not str(s["set"]).startswith("LOOT-")]
    for c in cards:
        for k in ("text", "keywords", "traits", "name", "card_type"): c[k] = "" if c[k] is None else str(c[k])
    by_id = {c["id"]: c for c in cards}

    subs = []   # (class, class row-ish, sub row)
    for r in classes:
        r = {k: ("" if v is None else str(v)) for k, v in r.items()}
        if r["class"] not in NOUNS or r["subclass"] not in FLAVOR: print("skip (no loot tables):", r["class"], r["subclass"]); continue
        _CORE[r["class"]] = r["core_set"]
        subs.append(r)

    store = os.path.join(root, "data", "loot-weapons.json")
    old = json.load(open(store)) if os.path.exists(store) and not reroll else {"seed": None, "weapons": []}
    used_seed = seed if seed is not None else (old["seed"] if old["seed"] is not None else random.randrange(1 << 30))
    rng = random.Random(used_seed)

    keep = {w["id"]: w for w in old["weapons"]
            if all(b["card"] in by_id for b in w["bonuses"])}            # drop weapons naming a card that's gone
    taken = {w["name"] for w in keep.values()}
    weapons = []
    for r in subs:
        pool = usable_cards(cards, r, r)
        code = r["subclass_set"]
        for tier in TIERS:
            for i in range(1, per + 1):
                wid = f"LOOT-{code}-{ROMAN[tier]}-{i:02d}"
                weapons.append(keep.get(wid) or roll_weapon(rng, tier, r["class"], r["subclass"], pool, by_id, taken, wid))
    json.dump({"seed": used_seed, "weapons": weapons}, open(store, "w"), indent=1)

    # xlsx: one LOOT-<class> set per class, a Cards row per weapon, and a Loot tab for the TTS roller
    cls_code = {r["class"]: r["core_set"] for r in subs}
    for cls, code in cls_code.items():
        sets.append({"set": f"LOOT-{code}", "name": f"Loot - {cls} Weapons", "kind": "Loot", "class": cls, "subclass": "", "back": "player"})
    for w in weapons:
        cards.append({"id": w["id"], "name": w["name"], "set": f"LOOT-{cls_code[w['class']]}", "card_type": "Weapon",
                      "traits": f"{w['class']} Weapon - {w['subclass']}", "keywords": None, "text": weapon_text(w, by_id),
                      "power": None if w["class"] in ACTIVATE else BASE_DAMAGE[w["tier"]], "health": None, "channel": None, "qty": 1,
                      "source_file": f"cards/loot/{w['class']}/{safe(w['name'])}.png",
                      "notes": f"Rolled loot, tier {ROMAN[w['tier']]} (tts/build/loot.py)"})
    for c in cards:
        for k in ("keywords",): c[k] = c[k] or None
    rewrite(wb["Cards"], chdr, cards); rewrite(wb["Sets"], shdr, sets)
    if "Loot" in wb.sheetnames: del wb["Loot"]
    ws = wb.create_sheet("Loot"); hdr = ["id", "class", "subclass", "tier"]
    ws.append(hdr)
    for w in weapons: ws.append([w["id"], w["class"], w["subclass"], w["tier"]])
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="3B3054")
    t = Table(displayName="Loot", ref=f"A1:D{len(weapons) + 1}"); t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t); ws.freeze_panes = "A2"
    for col, wdt in zip("ABCD", (22, 12, 14, 6)): ws.column_dimensions[col].width = wdt
    wb.save(xlsx)

    # readable list for review
    md = [f"# Journeys loot: rolled weapons\n", f"Made by `tts/build/loot.py` (seed {used_seed}). "
          f"Power {BASE_DAMAGE[2]}/{BASE_DAMAGE[3]}/{BASE_DAMAGE[4]} at tier II/III/IV; Priest weapons have no Power and heal an ally that much instead.\n"]
    for r in subs:
        md.append(f"\n## {r['class']} - {r['subclass']}\n")
        for w in [x for x in weapons if x["subclass"] == r["subclass"] and x["class"] == r["class"]]:
            bon = " / ".join(bonus_text(b["key"], by_id[b["card"]], b["colors"]) for b in w["bonuses"])
            md.append(f"- **{w['name']}** (Tier {ROMAN[w['tier']]}): {bon}")
    open(os.path.join(root, "data", "loot-weapons.md"), "w").write("\n".join(md) + "\n")

    if not no_render: render(weapons, by_id, root)
    kept = sum(1 for w in weapons if keep.get(w["id"]) is w)
    print(f"{len(weapons)} weapons ({kept} kept from data/loot-weapons.json, {len(weapons) - kept} newly rolled), seed {used_seed}")

if __name__ == "__main__":
    main()
