"""Boss die face symbols for Journeys: simple abstract shapes, one per face, peers rather than a power ladder.
icon(family, face, size) -> SVG string (viewBox 0 0 24 24). Families: solid (ivory shapes on a dark coin), outline, ink."""
COIN, RIM, IVORY, INK = "#2a221b", "#c9a24a", "#f3e6c6", "#2c1f14"
SHAPES = {   # A circle, B triangle, C square, all about the same visual weight
    "A": '<circle cx="12" cy="12" r="{r}"/>',
    "B": '<path d="M12 {t} L{br} {b} L{bl} {b} Z"/>',
    "C": '<rect x="{q0}" y="{q0}" width="{q}" height="{q}" rx="0.6"/>',
}
def _shape(face, k):  # k scales the shape (1 = sized for the coin)
    r = 4.6 * k; t = 12 - 5.8 * k; b = 12 + 4.4 * k; bl = 12 - 5.6 * k; br = 12 + 5.6 * k; q = 9.0 * k; q0 = 12 - q / 2
    return SHAPES[face].format(r=round(r, 2), t=round(t, 2), b=round(b, 2), bl=round(bl, 2), br=round(br, 2), q=round(q, 2), q0=round(q0, 2))

def icon(family, face, size=24, extra=""):
    if family == "ink":
        body = f'<g fill="{INK}">{_shape(face, 1.45)}</g>'
    else:
        coin = (f'<circle cx="12" cy="12" r="10.6" fill="{COIN}" stroke="#120c07" stroke-width="1.4"/>'
                f'<circle cx="12" cy="12" r="9.6" fill="none" stroke="{RIM}" stroke-width="1.3"/>')
        if family == "outline":
            body = coin + f'<g fill="none" stroke="{IVORY}" stroke-width="1.8" stroke-linejoin="round">{_shape(face, 1)}</g>'
        else:
            body = coin + f'<g fill="{IVORY}">{_shape(face, 1)}</g>'
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {extra}>{body}</svg>'

FAMILIES = ("solid", "outline", "ink")
