"""Gem symbols: one shape per colour so gems read without colour (Nolan, 2026-11-26).
    Red  = diamond     Green = hexagon     Blue = teardrop
svg(color, size, outline) -> inline SVG for the card renderers;  polygon(color, box) -> points for Pillow (stickers)."""
import math

FILL = {"r": "#d2413a", "g": "#36a865", "b": "#3b74d9"}
SHINE = {"r": "#f08a80", "g": "#8fe0ae", "b": "#9cc0ff"}
NAME = {"r": "Red", "g": "Green", "b": "Blue"}

# viewBox 0 0 24 24
SHAPE = {
    "r": "M12 1.5 20.5 12 12 22.5 3.5 12Z",
    "g": "M12 1.8 20.8 6.9V17.1L12 22.2 3.2 17.1V6.9Z",
    "b": "M12 1.8C14.6 5.6 19.6 10.6 19.6 15.2A7.6 7.6 0 0 1 4.4 15.2C4.4 10.6 9.4 5.6 12 1.8Z",
}
FACET = {   # a lighter facet so they read as cut stones
    "r": "M12 4.2 17.6 12H12Z",
    "g": "M12 4.6 18.4 8.3 12 12Z",
    "b": "M9.2 12.4C9.6 10.6 10.8 8.8 12 7.4 11.4 9.4 10.8 11.4 10.9 13.2Z",
}

def svg(color, size=14, outline="#8a6a2e", cls="gem"):
    c = color.lower()
    return (f'<svg class="{cls} {c}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-label="{NAME[c]} gem">'
            f'<path d="{SHAPE[c]}" fill="{FILL[c]}" stroke="{outline}" stroke-width="1.8" stroke-linejoin="round"/>'
            f'<path d="{FACET[c]}" fill="{SHINE[c]}" opacity=".8"/></svg>')

def polygon(color, box):
    """Outline points for Pillow inside box=(x0, y0, x1, y1)."""
    c = color.lower(); x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    P = lambda u, v: (x0 + u / 24 * w, y0 + v / 24 * h)
    if c == "r":
        return [P(12, 1.5), P(20.5, 12), P(12, 22.5), P(3.5, 12)]
    if c == "g":
        return [P(12, 1.8), P(20.8, 6.9), P(20.8, 17.1), P(12, 22.2), P(3.2, 17.1), P(3.2, 6.9)]
    pts = []   # teardrop: straight-ish sides from the tip down to a round bottom
    cx, cy, r = 12, 15.2, 7.6
    for i in range(0, 181, 6):                       # bottom half-circle, right to left
        a = math.radians(i)
        pts.append(P(cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.insert(0, P(12, 1.8)); pts.insert(1, P(16.6, 7.6)); pts.insert(2, P(19.6, 13.4))
    pts += [P(4.4, 13.4), P(7.4, 7.6)]
    return pts
