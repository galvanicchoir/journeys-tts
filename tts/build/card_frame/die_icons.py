"""Boss die face symbols: 4 candidate families, each A/B/C, as SVG strings (viewBox 0 0 24 24)."""
RIM = {"A": "#b07a3a", "B": "#cfd3da", "C": "#e6c46a"}
FIELD = {"A": "#2a221b", "B": "#2a221b", "C": "#5a1210"}
INK = {"A": "#e3b878", "B": "#eef0f4", "C": "#ffd66e"}

def roundel(face, inner):
    return (f'<circle cx="12" cy="12" r="10.6" fill="{FIELD[face]}" stroke="#120c07" stroke-width="1.6"/>'
            f'<circle cx="12" cy="12" r="9.6" fill="none" stroke="{RIM[face]}" stroke-width="1.5"/>{inner}')

def claws(face):
    n = {"A": 1, "B": 2, "C": 3}[face]; xs = {1: [12], 2: [10, 14.2], 3: [8.2, 12, 15.8]}[n]
    ink = INK[face]
    return "".join(f'<path d="M{x-1.2} 6.4 Q{x+1.6} 11.5 {x-0.6} 17.6 Q{x+0.2} 11.6 {x-2.4} 7.2 Z" fill="{ink}" stroke="{ink}" stroke-width="0.9" stroke-linejoin="round"/>' for x in xs)

FLAME = "M0 -6.2 C2.4 -3 3.4 -1.2 2.9 1.2 C2.5 3.4 1.2 4.6 0 4.6 C-1.8 4.6 -3.1 3.3 -3.1 1.4 C-3.1 -0.3 -2 -1.3 -1.5 -2.5 C-1 -1.2 -0.4 -0.8 0.1 -1.2 C0.5 -2.8 0.2 -4.6 0 -6.2 Z"
def flames(face):
    ink = INK[face]
    spots = {"A": [(12, 12.6, 1.0)], "B": [(9.6, 13, 0.85), (14.4, 13, 0.85)], "C": [(8, 13.6, 0.7), (16, 13.6, 0.7), (12, 12, 1.0)]}[face]
    return "".join(f'<path transform="translate({x} {y}) scale({s})" d="{FLAME}" fill="{ink}"/>' for x, y, s in spots)

def pips(face):
    ink = INK[face]
    spots = {"A": [(12, 12)], "B": [(9, 12), (15, 12)], "C": [(12, 8.4), (8.6, 14.2), (15.4, 14.2)]}[face]
    return "".join(f'<rect x="{x-2.3}" y="{y-2.3}" width="4.6" height="4.6" transform="rotate(45 {x} {y})" fill="{ink}"/>' for x, y in spots)

def eyes(face):
    ink = INK[face]
    if face == "A":   # closed: lid line + lashes
        return (f'<path d="M6.5 11.5 Q12 15.5 17.5 11.5" fill="none" stroke="{ink}" stroke-width="1.8" stroke-linecap="round"/>'
                f'<path d="M8.6 13.4 L7.8 15.2 M12 14.4 L12 16.4 M15.4 13.4 L16.2 15.2" stroke="{ink}" stroke-width="1.4" stroke-linecap="round"/>')
    if face == "B":   # half open
        return (f'<path d="M6 12.5 Q12 6.5 18 12.5 Q12 16 6 12.5 Z" fill="none" stroke="{ink}" stroke-width="1.6" stroke-linejoin="round"/>'
                f'<path d="M6.6 12 Q12 9.6 17.4 12" fill="{ink}" stroke="{ink}" stroke-width="1"/>'
                f'<path d="M10.5 12.4 Q12 14.6 13.5 12.4 Z" fill="{ink}"/>')
    return (f'<path d="M5.5 12 Q12 4.8 18.5 12 Q12 19.2 5.5 12 Z" fill="#ffefb0" stroke="{ink}" stroke-width="1.5" stroke-linejoin="round"/>'
            f'<ellipse cx="12" cy="12" rx="2.9" ry="4.2" fill="#e0501c"/><path d="M12 8.4 V15.6" stroke="#120c07" stroke-width="1.4" stroke-linecap="round"/>')

FAMILIES = {"claws": claws, "flames": flames, "pips": pips, "eyes": eyes}

def icon(family, face, size=24, extra=""):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {extra}>{roundel(face, FAMILIES[family](face))}</svg>'
