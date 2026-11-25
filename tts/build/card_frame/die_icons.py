"""Boss die face symbols for Journeys: small esoteric sigils built from plain lines and shapes.
Each set is a family that shares one rule, so A, B and C read as peers (no face looks 'stronger').
icon(family, face, size, extra, style) -> SVG (viewBox 0 0 24 24). style: "coin" (ivory on a dark coin) or "ink" (dark lines, no coin)."""
COIN, RIM, IVORY, INK = "#2a221b", "#c9a24a", "#f3e6c6", "#2c1f14"

SIGILS = {
    # Pierced: a base shape crossed by one line that runs past it
    "pierced": {
        "A": '<circle cx="12" cy="12" r="3.9"/><path d="M12 5.2V18.8"/>',
        "B": '<path d="M12 7.4 16.6 15.4H7.4Z"/><path d="M5.6 12.6H18.4"/>',
        "C": '<rect x="8.3" y="8.3" width="7.4" height="7.4"/><path d="M6.2 17.8 17.8 6.2"/>',
    },
    # Stems: one upright stroke with a foot dot; only the head changes
    "stems": {
        "A": '<path d="M12 10.6V16.6"/><circle cx="12" cy="8.2" r="2.4"/><circle cx="12" cy="18.6" r="0.9" class="f"/>',
        "B": '<path d="M12 9.8V16.6M12 9.8 8.6 6.2M12 9.8l3.4-3.6"/><circle cx="12" cy="18.6" r="0.9" class="f"/>',
        "C": '<path d="M12 7.2V16.6M8 7.2H16M8 7.2V9.6M16 7.2V9.6"/><circle cx="12" cy="18.6" r="0.9" class="f"/>',
    },
    # Seals: a base shape holding a dot, with one mark outside on the same side
    "seals": {
        "A": '<circle cx="12" cy="12.8" r="4.2"/><circle cx="12" cy="12.8" r="1" class="f"/><path d="M12 5.4V7.2"/>',
        "B": '<path d="M12 8.2 16.4 16.2H7.6Z"/><circle cx="12" cy="13.4" r="1" class="f"/><path d="M12 4.8V6.4"/>',
        "C": '<rect x="8.2" y="9" width="7.6" height="7.6"/><circle cx="12" cy="12.8" r="1" class="f"/><path d="M12 5.4V7.2"/>',
    },
}
FAMILIES = tuple(SIGILS)

def icon(family, face, size=24, extra="", style="coin"):
    color = INK if style == "ink" else IVORY
    marks = (f'<g fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
             + SIGILS[family][face].replace(' class="f"', f' fill="{color}" stroke="none"') + "</g>")
    coin = "" if style == "ink" else (f'<circle cx="12" cy="12" r="10.6" fill="{COIN}" stroke="#120c07" stroke-width="1.4"/>'
                                      f'<circle cx="12" cy="12" r="9.6" fill="none" stroke="{RIM}" stroke-width="1.3"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {extra}>{coin}{marks}</svg>'
