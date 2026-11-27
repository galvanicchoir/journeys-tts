"""Gem symbols: one shape per colour so gems read without colour, roomy enough to hold a number (Nolan, 2026-11-26).
    Red  = cut gem (flat top, pointed bottom)     Green = hexagon     Blue = teardrop (pointed top, round bottom)
svg(color, size, outline, cls, label) -> inline SVG for the card renderers ("2{r}" -> red gem with 2 inside);
polygon(color, box) and label_y(color, box) -> Pillow drawing for the Forge stickers."""
import math

FILL = {"r": "#ff1414", "g": "#00c94f", "b": "#1f5bff"}   # fully saturated, red most of all (Nolan, 2026-11-26)
SHINE = {"r": "#ff7a6e", "g": "#7dffb0", "b": "#8fb2ff"}
NAME = {"r": "Red", "g": "Green", "b": "Blue"}

# viewBox 0 0 24 24
SHAPE = {
    "r": "M6.6 2.4H17.4L22 8.6 12 22.6 2 8.6Z",
    "g": "M12 1.2 21.6 6.6V17.4L12 22.8 2.4 17.4V6.6Z",
    "b": "M12 1.2C14.8 5.2 20.6 10.4 20.6 15A8.6 8.6 0 0 1 3.4 15C3.4 10.4 9.2 5.2 12 1.2Z",
}
FACET = {   # a lighter facet so they read as cut stones
    "r": "M6.6 2.4H12L8.4 8.6H2Z",
    "g": "M12 1.2 21.6 6.6 18.6 8.4 12 4.6Z",
    "b": "M7.2 11.2C8.2 9.4 9.8 7.4 11.2 5.8 10.2 8 9.4 9.8 9 11.8Z",
}
TEXT_Y = {"r": 11.2, "g": 12.4, "b": 15.4}   # optical centre of each shape (where a number sits)

def svg(color, size=14, outline="#8a6a2e", cls="gem", label=""):
    c = color.lower()
    num = ""
    if label:   # a big digit; a leading "+" is drawn smaller so the number stays readable
        plus, digits = ("+", label[1:]) if label.startswith("+") else ("", label)
        body = (f'<tspan font-size="9" dy="-0.6">+</tspan><tspan font-size="15" dy="0.6">{digits}</tspan>' if plus
                else f'<tspan font-size="15.5">{digits}</tspan>')
        num = (f'<text x="12" y="{TEXT_Y[c]}" text-anchor="middle" dominant-baseline="central" font-family="Cinzel, serif" '
               f'font-weight="800" letter-spacing="-0.4" fill="#fff" stroke="#1b1612" stroke-width="2.6" paint-order="stroke" '
               f'stroke-linejoin="round">{body}</text>')
    title = f"{label} {NAME[c]}" if label else f"{NAME[c]} gem"
    return (f'<svg class="{cls} {c}{" num" if label else ""}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-label="{title}">'
            f'<path d="{SHAPE[c]}" fill="{FILL[c]}" stroke="{outline}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="{FACET[c]}" fill="{SHINE[c]}" opacity="{".45" if label else ".8"}"/>{num}</svg>')

def _P(box):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    return lambda u, v: (x0 + u / 24 * w, y0 + v / 24 * h)

def polygon(color, box):
    """Outline points for Pillow inside box=(x0, y0, x1, y1)."""
    c = color.lower(); P = _P(box)
    if c == "r":
        return [P(6.6, 2.4), P(17.4, 2.4), P(22, 8.6), P(12, 22.6), P(2, 8.6)]
    if c == "g":
        return [P(12, 1.2), P(21.6, 6.6), P(21.6, 17.4), P(12, 22.8), P(2.4, 17.4), P(2.4, 6.6)]
    pts = [P(12, 1.2), P(16.4, 6.6), P(19.6, 11)]    # teardrop: tip, right side, round bottom, left side
    for i in range(0, 181, 6):
        a = math.radians(i)
        pts.append(P(12 + 8.6 * math.cos(a), 15 + 8.6 * math.sin(a)))
    pts += [P(4.4, 11), P(7.6, 6.6)]
    return pts

def label_y(color, box):
    return _P(box)(12, TEXT_Y[color.lower()])[1]
