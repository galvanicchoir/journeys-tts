import math, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
FONT_B = sys.argv[1]
SRC = "/mnt/user-data/uploads/Journeys TTS/cards/"
S = 1024
# background: dark radial glow
bg = Image.new("RGB", (S, S), (14, 11, 20))
glow = Image.new("L", (S, S), 0); gd = ImageDraw.Draw(glow)
for r in range(620, 0, -8):
    gd.ellipse((S/2 - r, S*0.62 - r, S/2 + r, S*0.62 + r), fill=int(120 * (1 - r / 620) ** 1.6))
warm = Image.new("RGB", (S, S), (120, 60, 40))
bg = Image.composite(warm, bg, glow)
im = bg.convert("RGBA")

def card(path, w):
    c = Image.open(SRC + path).convert("RGBA")
    c = c.resize((w, int(w * c.height / c.width)), Image.LANCZOS)
    m = Image.new("L", c.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), radius=int(w * 0.05), fill=255)
    c.putalpha(m)
    return c
def place(c, cx, cy, ang):
    r = c.rotate(ang, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", r.size, (0, 0, 0, 0)); sh.putalpha(r.getchannel("A").point(lambda a: int(a * 0.7)))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(sh, (int(cx - r.width / 2 + 10), int(cy - r.height / 2 + 18)))
    im.alpha_composite(r, (int(cx - r.width / 2), int(cy - r.height / 2)))

# goblin horde lurking behind, then the five heroes fanned out
place(card("encounters/Trouble with Goblins/Goblin Horde x4.png", 270), S/2, 505, 0)
heroes = ["Warrior x1.png", "Rogue x1.png", "Mage x1.png", "Priest x1.png", "Dragonheart x1.png"]
order = [0, 4, 1, 3, 2]                     # draw outer cards first so the middle one sits on top
for i in order:
    k = i - 2
    ang = -k * 11
    cx = S/2 + k * 150
    cy = 700 + abs(k) ** 1.5 * 22
    place(card("character cards/" + heroes[i], 280), cx, cy, ang)

d = ImageDraw.Draw(im)
def text(y, s, size, fill, stroke=6, spacing=0):
    f = ImageFont.truetype(FONT_B, size)
    if spacing:
        widths = [d.textlength(ch, font=f) for ch in s]
        x = S/2 - (sum(widths) + spacing * (len(s) - 1)) / 2
        for ch, w in zip(s, widths):
            d.text((x, y), ch, font=f, fill=fill, anchor="lm", stroke_width=stroke, stroke_fill=(20, 12, 8)); x += w + spacing
    else:
        d.text((S/2, y), s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(20, 12, 8))
# title with a soft gold glow
t = Image.new("RGBA", (S, S), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
f = ImageFont.truetype(FONT_B, 150)
td.text((S/2, 150), "JOURNEYS", font=f, fill=(255, 200, 90, 255), anchor="mm")
im.alpha_composite(t.filter(ImageFilter.GaussianBlur(18)))
text(150, "JOURNEYS", 150, (236, 196, 106), stroke=7)
d.line((S/2 - 300, 245, S/2 + 300, 245), fill=(200, 160, 80), width=3)
text(282, "A CO-OP LEGACY CARD GAME", 40, (225, 215, 195), stroke=4, spacing=3)
# playtest ribbon, bottom
d.rounded_rectangle((S/2 - 170, S - 96, S/2 + 170, S - 36), radius=14, fill=(120, 30, 30), outline=(236, 196, 106), width=3)
text(S - 66, "PLAYTEST", 40, (250, 240, 220), stroke=0, spacing=6)
im.convert("RGB").save("Journeys.png", optimize=True)
