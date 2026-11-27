"""Cache sigils (chosen by Nolan, 2026-11-27): joined-ring marks, drawn in dark ink in card text.
    &  = Wave     %  = Bowl      $  = Fan
Card text keeps using & % $; render_cards.py swaps them for these sigils."""
RING_R = 10.2
SIGIL = {   # viewBox 0 0 24 24; strokes run out to the ring and are clipped by it
    "&": ("Wave", "M1.9 9.6Q7 4.2 12 9.6T22.1 9.6M2.2 15.4Q7 10 12 15.4T21.8 15.4", None),
    "%": ("Bowl", "M3.2 7Q12 27.5 20.8 7", (12, 8.2, 2.1)),
    "$": ("Fan",  "M12 20.6 3 6.4M12 20.6V1.4M12 20.6 21 6.4", None),
}
INK = "#2c1f14"

def svg(sym, size=24, color=INK, cls="cache"):
    name, d, dot = SIGIL[sym]
    cid = "cc" + name
    dot_svg = f'<circle cx="{dot[0]}" cy="{dot[1]}" r="{dot[2]}" fill="{color}"/>' if dot else ""
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-label="{name} cache">'
            f'<defs><clipPath id="{cid}"><circle cx="12" cy="12" r="{RING_R}"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{d}"/>{dot_svg}</g>'
            f'<circle cx="12" cy="12" r="{RING_R}" fill="none" stroke="{color}" stroke-width="1.8"/></svg>')
