"""Build the Journeys TTS mod from data/journeys-cards.xlsx + cards/.
Usage: python build.py <project_root> <asset_root_for_tts>
  project_root      folder containing cards/, data/, tts/
  asset_root_for_tts how TTS should reach tts/ images, e.g. file:///C:/Users/nolan/Desktop/Journeys TTS
Outputs: tts/sheets/*.png, tts/images/*.png, tts/Journeys.json (TTS save), tts/src/data.lua"""
import re, sys, os, json, math
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont

ROOT, ASSET = sys.argv[1], sys.argv[2].rstrip("/")
CARDS_DIR = os.path.join(ROOT, "cards"); TTS = os.path.join(ROOT, "tts")
CW, CH = 500, 700  # card size on deck sheets
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"; FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
def font(sz, bold=True): return ImageFont.truetype(FONT_B if bold else FONT_R, sz)

def pretty(t):  # {r} -> R etc. for in-game descriptions
    return (t or "").replace("{r}", "[R]").replace("{b}", "[B]").replace("{g}", "[G]")

def rows(ws):
    it = ws.iter_rows(values_only=True); hdr = next(it)
    return [dict(zip(hdr, r)) for r in it if any(v is not None for v in r)]

wb = load_workbook(os.path.join(ROOT, "data", "journeys-cards.xlsx"))
cards, sets, classes, advs, journey, bosses = (rows(wb[n]) for n in ("Cards", "Sets", "Classes", "Adventures", "Journey", "Bosses"))
enhs = [r for r in rows(wb["Enhancements"]) if r.get("enh_id") and not str(r["enh_id"]).startswith("(example)")] if "Enhancements" in wb.sheetnames else []
set_by = {s["set"]: s for s in sets}

# A card drawn in the new frame by render_cards.py (cards/framed/...) replaces its export; delete it to go back.
def card_image(c):
    rel = str(c["source_file"]).replace("\\", "/")
    framed = os.path.join(ROOT, "cards", "framed", rel[len("cards/"):] if rel.startswith("cards/") else rel)
    return framed if os.path.exists(framed) else os.path.join(ROOT, c["source_file"])

# ---------- deck sheets, one per back type ----------
os.makedirs(os.path.join(TTS, "sheets"), exist_ok=True); os.makedirs(os.path.join(TTS, "images"), exist_ok=True)
sheets, card_out = [], {}
for back in ("player", "encounter"):
    group = [c for c in cards if set_by[c["set"]]["back"] == back]
    for start in range(0, len(group), 69):
        chunk = group[start:start + 69]
        n = len(sheets) + 1
        cols = min(10, max(2, math.ceil(math.sqrt(len(chunk) * 1.4))))
        rws = math.ceil(len(chunk) / cols)
        if rws < 2: rws = 2
        img = Image.new("RGB", (CW * cols, CH * rws), (25, 25, 25))
        os.makedirs(os.path.join(TTS, "images", "cards"), exist_ok=True)
        for i, c in enumerate(chunk):
            im = Image.open(card_image(c)).convert("RGB").resize((CW, CH), Image.LANCZOS)
            im.resize((300, 420), Image.LANCZOS).save(os.path.join(TTS, "images", "cards", c["id"] + ".png"), optimize=True)
            img.paste(im, ((i % cols) * CW, (i // cols) * CH))
            card_out[c["id"]] = (n, i)
        # content fingerprint in the name: TTS caches images by URL, so a changed sheet must get a new name
        import hashlib
        tag = hashlib.md5(img.tobytes()).hexdigest()[:8]
        fname = f"{back}-{n:02d}-{tag}.png"; img.save(os.path.join(TTS, "sheets", fname), optimize=True)
        sheets.append({"face": f"{ASSET}/tts/sheets/{fname}", "back": f"{ASSET}/tts/sheets/back-{back}.png", "w": cols, "h": rws})

# ---------- generated images: backs, adventure tiles, seat mats ----------
def card_back(path, title, sub, bg, edge):
    im = Image.new("RGB", (CW, CH), bg); d = ImageDraw.Draw(im)
    d.rounded_rectangle((18, 18, CW - 18, CH - 18), radius=28, outline=edge, width=8)
    d.text((CW / 2, CH / 2 - 20), title, fill=edge, font=font(64), anchor="mm")
    d.text((CW / 2, CH / 2 + 50), sub, fill=edge, font=font(30, False), anchor="mm")
    im.save(path)
card_back(os.path.join(TTS, "sheets", "back-player.png"), "JOURNEYS", "player", (38, 32, 52), (210, 180, 100))
card_back(os.path.join(TTS, "sheets", "back-encounter.png"), "JOURNEYS", "encounter", (58, 22, 22), (220, 150, 90))

def wrap(d, text, f, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) > width and line: out.append(line); line = w
        else: line = t
    return out + ([line] if line else [])

adv_list = []
for aid in dict.fromkeys(a["adventure_id"] for a in advs):
    rs = [a for a in advs if a["adventure_id"] == aid]; a0 = rs[0]
    im = Image.new("RGB", (1024, 1024), (32, 28, 44)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((24, 24, 1000, 1000), radius=40, outline=(210, 180, 100), width=10)
    y = 110
    for ln in wrap(d, a0["name"], font(84), 880): d.text((512, y), ln, fill=(240, 220, 160), font=font(84), anchor="mm"); y += 100
    d.text((512, y + 30), f"Level {a0['level']}   ·   {a0['players']} players", fill=(230, 230, 230), font=font(48, False), anchor="mm")
    y += 130
    for r in rs:
        tag = {"all": "deck", "staged": "set aside", "setaside": "set aside"}.get(r["use"], r["use"])
        d.text((512, y), f"{set_by[r['set']]['name']}  ({tag})", fill=(200, 200, 200), font=font(36, False), anchor="mm"); y += 52
    fname = f"adventure-{aid.lower()}.png"; im.save(os.path.join(TTS, "images", fname))
    adv_list.append({"id": aid, "name": a0["name"], "level": int(a0["level"]), "players": str(a0["players"]),
                     "description": str(a0.get("description") or ""),
                     "image": f"{ASSET}/tts/images/{fname}",
                     "summary": "; ".join(f"{set_by[r['set']]['name']} ({r['use']})" for r in rs),
                     "sets": [{"set": r["set"], "use": str(r["use"]),
                              "set_aside": [x.strip() for x in str(r.get("set_aside") or "").split(",") if x.strip()]} for r in rs]})

SEAT_RGB = {"White": (235, 235, 235), "Red": (210, 60, 60), "Green": (60, 170, 80), "Blue": (70, 120, 220)}
# Playmat: 24 x 14 proportions (standard playmat), 18 x 10.5 TTS units. Local coords: x,z in -1..1, +z = toward the player.
MAT_W, MAT_D = 18.0, 10.5
CARD_W, CARD_D = 2.2, 3.1                      # TTS card footprint at scale 1
MAT_SLOTS = [("Hero", -0.80, 0.45), ("Weapon", -0.53, 0.45), ("Weapon 2", -0.26, 0.45),
             ("Cycle", 0.26, 0.45), ("Deck", 0.53, 0.45), ("Discard", 0.80, 0.45)]
MPX_W, MPX_H = 1536, 896
mats = {}
for seat, rgb in SEAT_RGB.items():
    im = Image.new("RGB", (MPX_W, MPX_H), (30, 27, 38)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 12, MPX_W - 12, MPX_H - 12), radius=36, outline=rgb, width=12)
    sw, sh = CARD_W / MAT_W * MPX_W, CARD_D / MAT_D * MPX_H
    for name, x, z in MAT_SLOTS:
        cx, cy = (x + 1) / 2 * MPX_W, (z + 1) / 2 * MPX_H
        d.rounded_rectangle((cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2), radius=14, outline=(95, 88, 112), width=4)
        d.text((cx, cy), name, fill=(110, 104, 128), font=font(26, False), anchor="mm")
        if name == "Cycle":
            d.text((cx, cy + 34), "to bottom", fill=(90, 84, 108), font=font(20, False), anchor="mm")
            d.text((cx, cy + 58), "of deck", fill=(90, 84, 108), font=font(20, False), anchor="mm")
    d.text((MPX_W / 2, 40), seat.upper(), fill=rgb, font=font(30), anchor="mm")
    fname = f"mat-{seat.lower()}-{hashlib.md5(im.tobytes()).hexdigest()[:8]}.png"   # fingerprint: TTS caches by URL
    im.save(os.path.join(TTS, "images", fname))
    mats[seat] = f"{ASSET}/tts/images/{fname}"
MAT_LAYOUT = {"w": MAT_W, "d": MAT_D, "slots": [{"name": n, "x": x, "z": z} for n, x, z in MAT_SLOTS]}

# ---------- journey boards + boss tiles ----------
BOARD_PX = 1024
NODE_X = [170, 512, 854]; NODE_Y = [190, 320, 450]; NODE_W, NODE_H = 280, 96
BOSS_FRAME = (287, 545, 737, 995)      # where the boss tile sits on the board (pixels)
def px_to_local(x, y): return round((x / BOARD_PX - 0.5) * 2, 3), round((y / BOARD_PX - 0.5) * 2, 3)  # image down = local +z

JOURNEYS_L = {}
for aid in dict.fromkeys(j["adventure_id"] for j in journey):
    nodes = [j for j in journey if j["adventure_id"] == aid]
    adv_name = next(a["name"] for a in advs if a["adventure_id"] == aid)
    im = Image.new("RGB", (BOARD_PX, BOARD_PX), (30, 27, 38)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((14, 14, 1010, 1010), radius=36, outline=(210, 180, 100), width=10)
    d.text((512, 70), adv_name, fill=(240, 220, 160), font=font(54), anchor="mm")
    pos = {n["node"]: (NODE_X[int(n["col"])], NODE_Y[int(n["row"])]) for n in nodes}
    for n in nodes:                                    # arrows first, boxes on top
        for nx in [x.strip() for x in str(n["next"] or "").split(",") if x.strip()]:
            (x1, y1), (x2, y2) = pos[n["node"]], pos[nx]
            d.line((x1 + NODE_W / 2, y1, x2 - NODE_W / 2, y2), fill=(150, 130, 90), width=6)
            d.polygon([(x2 - NODE_W / 2, y2), (x2 - NODE_W / 2 - 22, y2 - 12), (x2 - NODE_W / 2 - 22, y2 + 12)], fill=(150, 130, 90))
    for n in nodes:
        x, y = pos[n["node"]]
        d.rounded_rectangle((x - NODE_W / 2, y - NODE_H / 2, x + NODE_W / 2, y + NODE_H / 2), radius=14, fill=(48, 42, 62), outline=(120, 110, 140), width=3)
        lines = wrap(d, f"{n['node']}  {n['name']}", font(26), NODE_W - 24)
        for k, ln in enumerate(lines):
            d.text((x, y + (k - (len(lines) - 1) / 2) * 30), ln, fill=(225, 215, 190), font=font(26), anchor="mm")
    fx1, fy1, fx2, fy2 = BOSS_FRAME
    d.rounded_rectangle(BOSS_FRAME, radius=20, outline=(170, 60, 60), width=6)
    d.text(((fx1 + fx2) / 2, (fy1 + fy2) / 2), "BOSS", fill=(90, 50, 55), font=font(80), anchor="mm")
    fname = f"journey-{aid.lower()}.png"; im.save(os.path.join(TTS, "images", fname))
    bx, bz = px_to_local((fx1 + fx2) / 2, (fy1 + fy2) / 2)
    JOURNEYS_L[aid] = {"board": f"{ASSET}/tts/images/{fname}", "start": nodes[0]["node"], "boss_pos": [bx, bz],
        "boss_scale": round((fx2 - fx1) / BOARD_PX * 5, 3),   # frame width as a share of a scale-5 board
        "order": [n["node"] for n in nodes],
        "node_w": round(NODE_W / BOARD_PX * 2, 3), "node_h": round(NODE_H / BOARD_PX * 2, 3),
        "nodes": {n["node"]: {"name": n["name"], "rules": pretty(n["rules"]), "local": list(px_to_local(*pos[n["node"]])),
                              "next": [x.strip() for x in str(n["next"] or "").split(",") if x.strip()],
                              "actions": [a.strip() for a in str(n["actions"] or "").split(";") if a.strip()]} for n in nodes}}

BOSSES_L = {}
for b in bosses:
    im = Image.new("RGB", (BOARD_PX, BOARD_PX), (245, 242, 236)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 1014, 1014), radius=40, outline=(150, 40, 40), width=16)
    d.text((512, 85), b["name"], fill=(40, 30, 30), font=font(70), anchor="mm")
    d.text((512, 155), b["traits"], fill=(90, 80, 80), font=font(36, False), anchor="mm")
    d.text((512, 225), f"Power {b['power']}     Health {b['health']}", fill=(150, 30, 30), font=font(48), anchor="mm")
    y = 290; body = font(34, False)
    def para(label, text):
        global y
        lines = wrap(d, (label + "  " if label else "") + pretty(text), body, 900)
        for i, ln in enumerate(lines):
            d.text((62, y), ln, fill=(30, 30, 30), font=body); y += 44
        y += 18
    para("", b["text"])
    for k in ("A", "B", "C"): para(k + " -", b[k])
    fname = f"boss-{b['boss_id'].lower()}.png"; im.save(os.path.join(TTS, "images", fname))
    hp = str(b["health"]); per = hp.endswith("*")
    BOSSES_L[b["boss_id"]] = {"name": b["name"], "image": f"{ASSET}/tts/images/{fname}", "power": int(b["power"] or 0),
        "health": int(hp.rstrip("*") or 0), "per_player": per, "abc": [pretty(b[k]) for k in "ABC"],
        "text": "\n".join([b["traits"], f"P {b['power']}  H {b['health']}", pretty(b["text"])] + [f"{k} - {pretty(b[k])}" for k in "ABC"])}

# ---------- tokens + phase tracker ----------
TOKENS = [  # name, label, rgb, kind, owner
    # kind: "stack" = bottomless bag of stackable tokens, "single" = one token, "counter" = TTS's built-in number counter
    # owner: "" = shared supply at the table edge; a set code = spawns on the playmat of a character whose class
    #        core set or subclass set matches (removed again with the character)
    ("Burn", "BURN", (230, 110, 30), "stack", ""), ("Frost", "FROST", (120, 200, 240), "stack", ""),
    ("Stun", "STUN", (235, 205, 60), "stack", ""), ("Power", "+1 P", (200, 40, 40), "stack", ""),
    ("Armor", "ARMOR", (140, 140, 150), "stack", ""), ("Strength", "STR", (150, 30, 30), "stack", ""),
    ("Intellect", "INT", (50, 90, 200), "stack", ""), ("Agility", "AGI", (40, 150, 70), "stack", ""),
    ("Counter", "", (40, 90, 200), "counter", ""),
    ("Ember", "EMBER", (235, 90, 20), "stack", "DRG"), ("Renown", "FAME", (200, 160, 40), "stack", "ROG-OUT"),
    ("Stealth", "STEALTH", (60, 60, 70), "single", "ROG"),
]
TOKENS_L = []
for name, label, rgb, kind, owner in TOKENS:
    entry = {"name": name, "kind": kind, "owner": owner, "rgb": [round(c / 255, 3) for c in rgb]}
    if kind != "counter":
        im = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((6, 6, 250, 250), fill=rgb + (255,), outline=(245, 235, 210, 255), width=10)
        f = font(64 if len(label) <= 4 else (50 if len(label) <= 5 else 40))
        d.text((128, 128), label, fill=(255, 255, 255, 255), font=f, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 255))
        fname = f"token-{name.lower()}.png"; im.save(os.path.join(TTS, "images", fname))
        entry["image"] = f"{ASSET}/tts/images/{fname}"
    TOKENS_L.append(entry)

im = Image.new("RGB", (1024, 1024), (30, 27, 38)); d = ImageDraw.Draw(im)
d.rounded_rectangle((14, 14, 1010, 1010), radius=36, outline=(210, 180, 100), width=10)
im.save(os.path.join(TTS, "images", "phase-tracker.png"))
PHASE_IMAGE = f"{ASSET}/tts/images/phase-tracker.png"

# ---------- battlefield: one board across the middle of the table ----------
# West end: Encounter Deck over Discard. Middle: six enemy-stack columns in a row, all read from the south side,
# numbered west to east. East end: 2x2 block of obstacle spaces. Must match the layout constants in global.lua.
BF_W, BF_D, BF_PX = 26.4, 8.4, 80                     # world size, pixels per world unit
ENC_DECK, ENC_DISC = (-11.6, 1.8), (-11.6, -1.8)
STACK_X0, STACK_DX = -7.75, 2.7
STACK_ZMIN, STACK_ZMAX, STACK_BAR_Z = -2.45, 3.95, -3.05
OBSTACLES = [(9.0, 1.8), (11.6, 1.8), (9.0, -1.8), (11.6, -1.8)]
W, H = int(BF_W * BF_PX), int(BF_D * BF_PX)
def bf_px(x, z):   # world -> pixel (rot 0 tile: image left = world +x, image down = world +z)
    return W / 2 - x * BF_PX, H / 2 + z * BF_PX
def bf_text(im, x, z, text, size, fill):              # drawn upside down in the image = upright for the south side
    f = font(size)
    l, t, r, b = ImageDraw.Draw(im).textbbox((0, 0), text, font=f)
    tw, th = r - l + 8, b - t + 8
    t_im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(t_im).text((tw / 2, th / 2), text, font=f, fill=fill, anchor="mm")
    t_im = t_im.rotate(180)
    u, v = bf_px(x, z)
    im.alpha_composite(t_im, (int(u - tw / 2), int(v - th / 2)))
def bf_box(d, x0, z0, x1, z1, **kw):
    (u0, v0), (u1, v1) = bf_px(x0, z0), bf_px(x1, z1)
    d.rounded_rectangle((min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)), radius=12, **kw)

GOLD = (210, 180, 100, 255)
im = Image.new("RGBA", (W, H), (28, 25, 36, 255)); d = ImageDraw.Draw(im)
d.rounded_rectangle((6, 6, W - 6, H - 6), radius=30, outline=GOLD, width=8)
for (x, z), lines in [(ENC_DECK, ["ENCOUNTER", "DECK"]), (ENC_DISC, ["DISCARD"])]:
    bf_box(d, x - 1.2, z - 1.65, x + 1.2, z + 1.65, outline=GOLD, width=5)
    for k, ln in enumerate(lines):
        bf_text(im, x, z - (k - (len(lines) - 1) / 2) * 0.4, ln, 24, GOLD)
for n in range(1, 7):
    cx = STACK_X0 + (n - 1) * STACK_DX
    bf_box(d, cx - 1.25, STACK_ZMIN, cx + 1.25, STACK_ZMAX, fill=(40, 34, 50, 255), outline=(150, 70, 70, 255), width=4)
    bf_text(im, cx, STACK_ZMAX - 0.35, "rear", 24, (130, 110, 130, 220))
    bf_text(im, cx, 0.2, f"STACK {n}", 34, (110, 70, 80, 255))
    u, v = bf_px(cx - 0.55, STACK_BAR_Z)
    d.ellipse((u - 34, v - 34, u + 34, v + 34), outline=(150, 70, 70, 255), width=3)
bf_box(d, 7.6, -3.65, 13.0, 3.65, outline=(100, 140, 100, 160), width=3)              # obstacle block
for x, z in OBSTACLES:
    bf_box(d, x - 1.2, z - 1.6, x + 1.2, z + 1.6, fill=(34, 40, 36, 255), outline=(100, 140, 100, 255), width=4)
    bf_text(im, x, z, "OBSTACLE", 24, (100, 140, 100, 255))
im = im.convert("RGB")
fname = f"battlefield-{hashlib.md5(im.tobytes()).hexdigest()[:8]}.png"; im.save(os.path.join(TTS, "images", fname))
BATTLEFIELD_IMAGE = f"{ASSET}/tts/images/{fname}"

AGGRO_TOKENS = {}      # one round token per seat colour, marks who a stack is aggro'd to
for seat, rgb in SEAT_RGB.items():
    t = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
    td.ellipse((6, 6, 250, 250), fill=rgb + (255,), outline=(30, 25, 35, 255), width=12)
    td.text((128, 128), "AGGRO", font=font(46), fill=(255, 255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 255))
    fn = f"aggro-{seat.lower()}.png"; t.save(os.path.join(TTS, "images", fn))
    AGGRO_TOKENS[seat] = f"{ASSET}/tts/images/{fn}"

# ---------- Steam Cloud links (tts/build/cloud_urls.json): used instead of local files where listed ----------
_cloud_path = os.path.join(TTS, "build", "cloud_urls.json")
CLOUD = {k: v for k, v in json.load(open(_cloud_path)).items() if not k.startswith("_")} if os.path.exists(_cloud_path) else {}
def url(rel):  # rel = path under tts/
    return CLOUD.get(rel, f"{ASSET}/tts/{rel}")

# ---------- Forge stickers: gem badges + enhancement banners ----------
os.makedirs(os.path.join(TTS, "images", "stickers"), exist_ok=True)
GEM_RGB = {"R": (225, 45, 45), "B": (105, 130, 240), "G": (35, 195, 90)}
GEMS_L = []
for col, rgb in GEM_RGB.items():
    for size in (1, 2):
        im = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((8, 8, 248, 248), fill=rgb + (255,), outline=(255, 245, 215, 255), width=14)
        d.text((128, 132), f"+{size}", fill=(255, 255, 255, 255), font=font(110), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 255))
        key = f"{col}{size}"; fname = f"gem-{key}.png"; im.save(os.path.join(TTS, "images", "stickers", fname))
        GEMS_L.append({"key": key, "color": col, "size": size, "rgb": [round(c / 255, 3) for c in rgb],
                       "label": f"+{size} {dict(R='Red', B='Blue', G='Green')[col]}", "image": url(f"images/stickers/{fname}")})
ENH_L = []
for e in enhs:
    im = Image.new("RGBA", (1000, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, 994, 254), radius=30, fill=(245, 225, 150, 255), outline=(120, 80, 20, 255), width=8)
    lines = wrap(d, pretty(str(e["sticker_text"])), font(44), 920)[:3]
    for k, ln in enumerate(lines):
        d.text((500, 130 + (k - (len(lines) - 1) / 2) * 54), ln, fill=(40, 25, 10, 255), font=font(44), anchor="mm")
    fname = f"enh-{e['enh_id']}.png"; im.save(os.path.join(TTS, "images", "stickers", fname))
    ENH_L.append({"id": str(e["enh_id"]), "card": str(e["card_id"]), "name": str(e["name"]), "text": pretty(str(e["sticker_text"])),
                  "image": url(f"images/stickers/{fname}")})

# ---------- Lua data ----------
def lua(v, ind=0):
    p = "  " * ind
    if isinstance(v, dict):
        return "{\n" + ",\n".join(f"{p}  [{json.dumps(str(k))}] = {lua(x, ind + 1)}" for k, x in v.items()) + f"\n{p}}}"
    if isinstance(v, list): return "{" + ", ".join(lua(x, ind + 1) for x in v) + "}"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return str(v)
    return json.dumps("" if v is None else str(v))


# Stacking, read from an enemy's type line: "Goblin - Backline (Generic)", "Goblin - Vanguard (Any)",
# "Goblin - Unique (Behind Any)". The role sets where it sits in a stack (rank: lower = further back);
# the brackets say what it stacks with, or force it to the very back/front ("Behind ..."/"Front ...").
STACK_RANK = {"Backline": 1, "Vanguard": 3}           # everything else (Generic, Unique, Elite...) = 2
def stack_info(traits):
    m = re.search(r"-\s*([A-Za-z]+)\s*(?:\(([^)]*)\))?\s*$", traits)
    role, paren = (m.group(1), (m.group(2) or "").strip()) if m else ("Generic", "")
    rank = STACK_RANK.get(role, 2)
    if re.match(r"(?i)behind\b", paren): rank, paren = 0, re.sub(r"(?i)^behind\s*", "", paren)
    elif re.match(r"(?i)front\b", paren): rank, paren = 4, re.sub(r"(?i)^front\s*", "", paren)
    return {"role": role, "rank": rank, "with": paren or "Any"}

CARDS_L = {}
for c in cards:
    n, i = card_out[c["id"]]
    stats = " ".join(x for x in [f"P {c['power']}" if c["power"] not in (None, "") else "",
                                 f"H {c['health']}" if c["health"] not in (None, "") else "",
                                 f"Channel {pretty(str(c['channel']))}" if c["channel"] else ""] if x)
    desc = "\n".join(x for x in [c["traits"] or "", stats, pretty(c["text"])] if x)
    CARDS_L[c["id"]] = {"name": c["name"], "set": c["set"], "type": c["card_type"] or "", "text": desc,
                        "qty": int(c["qty"] or 1), "sheet": n, "idx": i,
                        "enc": set_by[c["set"]]["back"] == "encounter"}
    if c["card_type"] == "Enemy":
        CARDS_L[c["id"]]["stack"] = stack_info(c["traits"] or "")
        CARDS_L[c["id"]]["power"] = str(c["power"] or "")
        CARDS_L[c["id"]]["health"] = str(c["health"] or "")
        CARDS_L[c["id"]]["keywords"] = c["keywords"] or ""
SETS_L = {s["set"]: {"name": s["name"], "kind": s["kind"], "cards": [c["id"] for c in cards if c["set"] == s["set"]]} for s in sets}
CLASSES_L, order = {}, []
for r in classes:
    if r["class"] not in CLASSES_L:
        hp = r.get("health")
        order.append(r["class"]); CLASSES_L[r["class"]] = {"hero": r["hero"], "weapon": r["weapon"] or "", "core": r["core_set"],
                                                           "health": int(hp) if str(hp or "").strip() else 10, "subclasses": []}
    sub = {"name": r["subclass"], "set": r["subclass_set"]}
    kw = str(r.get("choose_one") or "").strip()
    if kw:   # pick-one group: subclass cards whose traits mention the keyword
        sub["choose_label"] = kw
        sub["choose"] = [c["id"] for c in cards if c["set"] == r["subclass_set"] and kw.lower() in str(c["traits"] or "").lower()]
    CLASSES_L[r["class"]]["subclasses"].append(sub)
ANC_L = [{"name": c["name"].replace(" Ancestry", ""), "id": c["id"]} for c in cards if c["set"] == "ANC"]

data = "-- GENERATED by tts/build/build.py from data/journeys-cards.xlsx - do not edit by hand\n"
data += "SHEETS = " + lua(sheets) + "\n"
data += "CARDS = " + lua(CARDS_L) + "\n"
data += "SETS = " + lua(SETS_L) + "\n"
data += "CLASSES = " + lua(CLASSES_L) + "\n"
data += "CLASS_ORDER = " + lua(order) + "\n"
data += "ANCESTRIES = " + lua(ANC_L) + "\n"
data += "ADVENTURES = " + lua(adv_list) + "\n"
data += "SET_ORDER = " + lua([s["set"] for s in sets]) + "\n"
ASSETS = [{"name": c["id"], "url": f"{ASSET}/tts/images/cards/{c['id']}.png"} for c in cards]
ASSETS += [{"name": "MAP_" + k, "url": v["board"]} for k, v in JOURNEYS_L.items()]
ASSETS += [{"name": "BOSS_" + k, "url": v["image"]} for k, v in BOSSES_L.items()]
ASSETS += [{"name": "ADV_" + a["id"], "url": a["image"]} for a in adv_list]
ASSETS += [{"name": "GEM_" + g["key"], "url": g["image"]} for g in GEMS_L]
ASSETS += [{"name": "ENH_" + e["id"], "url": e["image"]} for e in ENH_L]
data += "UI_ASSETS = " + lua(ASSETS) + "\n"
data += "GEMS = " + lua(GEMS_L) + "\n"
data += "ENHANCEMENTS = " + lua(ENH_L) + "\n"
data += "ADVENTURE_BY_ID = {}\nfor _, a in ipairs(ADVENTURES) do ADVENTURE_BY_ID[a.id] = a end\n"
data += "MAT_IMAGES = " + lua(mats) + "\n"
data += "MAT_LAYOUT = " + lua(MAT_LAYOUT) + "\n"
data += "TOKENS = " + lua(TOKENS_L) + "\n"
data += f"BATTLEFIELD_IMAGE = {lua(BATTLEFIELD_IMAGE)}\nBF_W, BF_D = {BF_W}, {BF_D}\n"
data += "AGGRO_TOKENS = " + lua(AGGRO_TOKENS) + "\n"
data += "PHASE_IMAGE = " + lua(PHASE_IMAGE) + "\n"
data += "JOURNEYS = " + lua(JOURNEYS_L) + "\n"
data += "BOSSES = " + lua(BOSSES_L) + "\n"
# Every link to one of our own files gets ?v=<content hash>, so when an image changes its link changes too and
# TTS (which caches images by link) fetches the new one instead of showing a stale copy.
_hash_cache = {}
def _stamp(m):
    rel = m.group(1)
    path = os.path.join(TTS, rel)
    if rel not in _hash_cache:
        _hash_cache[rel] = hashlib.md5(open(path, "rb").read()).hexdigest()[:8] if os.path.exists(path) else None
    h = _hash_cache[rel]
    return m.group(0) + (f"?v={h}" if h else "")
data = re.sub(re.escape(ASSET) + r"/tts/([^\"?\s]+\.png)", _stamp, data)
open(os.path.join(TTS, "src", "data.lua"), "w").write(data)
script = data + "\n" + open(os.path.join(TTS, "src", "global.lua")).read()

# ---------- TTS save ----------
PLAYER_RGB = {"White": (1.0, 1.0, 1.0), "Red": (0.856, 0.1, 0.094), "Green": (0.192, 0.701, 0.168), "Blue": (0.118, 0.53, 1.0)}
def hand(color, x, z, roty):
    r, g, b = PLAYER_RGB[color]
    return {"Name": "HandTrigger", "GUID": {"White": "a1f001", "Red": "a1f002", "Green": "a1f003", "Blue": "a1f004"}[color],
            "FogColor": color, "ColorDiffuse": {"r": r, "g": g, "b": b, "a": 0.0}, "Locked": True,
            "Nickname": "", "Description": "", "GMNotes": "", "LuaScript": "", "LuaScriptState": "", "XmlUI": "",
            "Transform": {"posX": x, "posY": 4.5, "posZ": z, "rotX": 0, "rotY": roty, "rotZ": 0, "scaleX": 16, "scaleY": 6, "scaleZ": 4}}
save = {
    "SaveName": "Journeys - Playtest", "GameMode": "Journeys", "Gravity": 0.5, "PlayArea": 0.6, "Date": "", "VersionNumber": "",
    "GameType": "", "GameComplexity": "", "Tags": [], "Table": "Table_RPG", "Sky": "Sky_Museum", "Note": "",
    "Rules": "", "XmlUI": "", "LuaScript": script, "LuaScriptState": "", "TabStates": {},
    "ObjectStates": [hand("White", -10, -21.5, 0), hand("Red", 10, -21.5, 0), hand("Green", -10, 21.5, 180), hand("Blue", 10, 21.5, 180)],
}
json.dump(save, open(os.path.join(TTS, "Journeys.json"), "w"), indent=1)
print("sheets:", [(s["face"].rsplit("/", 1)[1], s["w"], s["h"]) for s in sheets])
print("cards:", len(CARDS_L), "adventures:", [a["id"] for a in adv_list], "classes:", order)
