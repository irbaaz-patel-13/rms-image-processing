#!/usr/bin/env python3
"""
Generate two publication-quality SVG + PNG diagrams for C11SL coursework:
  Figure 1: Customer Journey Swim Lane Diagram
  Figure 2: Causal Loop Diagram — B&B Profitability System

DEPENDENCIES (all pure Python, no system libs needed):
  pip install pymupdf

OUTPUT FILES (written to same folder as this script):
  fig1_final.svg / fig1_final.png
  fig2_final.svg / fig2_final.png
"""

import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# FIGURE 1: SWIM LANE DIAGRAM
# ═══════════════════════════════════════════════════════════════

def fig1():
    W, H = 1340, 820
    LL = 90
    PH = [LL, 340, 610, 890, 1120, W]
    phase_names = ["PRE-BOOKING", "BOOKING", "STAY", "POST-STAY", "FEEDBACK"]

    TITLE_H = 60
    PHASE_H = 24
    TOP = TITLE_H + PHASE_H + 4
    lane_heights = [185, 155, 175, 130]
    lane_tops = []
    y = TOP
    for h in lane_heights:
        lane_tops.append(y)
        y += h
    BOTTOM = y
    lane_names = ["GUEST", "DIGITAL\nPLATFORM", "B&B OWNER\n/ STAFF", "EXTERNAL"]
    lane_colors = ["#1565C0", "#2E7D32", "#E65100", "#6A1B9A"]
    lane_fills  = ["#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5"]

    BW, BH = 110, 46
    DIA = 54  # enlarged for text breathing room

    def pcx(i): return (PH[i] + PH[i+1]) / 2
    def lcy(i): return lane_tops[i] + lane_heights[i] / 2
    def owner_top(): return lane_tops[2] + 18
    def owner_bot(): return lane_tops[2] + lane_heights[2] - BH - 14

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    svg.append('''<defs>
  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>
  <marker id="ah" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
    <path d="M0,0 L7,2.5 L0,5 Z" fill="#455A64"/>
  </marker>
  <marker id="ahp" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
    <path d="M0,0 L7,2.5 L0,5 Z" fill="#7B1FA2"/>
  </marker>
</defs>''')

    svg.append(f'<rect width="{W}" height="{H}" fill="#FAFBFC"/>')
    svg.append(f'<text x="{W/2}" y="32" text-anchor="middle" font-size="16" font-weight="bold" fill="#1B2A4A">'
               f'Figure 1: Customer Journey Swim Lane Diagram \u2014 B&amp;B Booking to Post-Stay Review</text>')

    for i, name in enumerate(phase_names):
        x1, x2 = PH[i], PH[i+1]
        cx = (x1+x2)/2
        svg.append(f'<rect x="{x1}" y="{TITLE_H}" width="{x2-x1}" height="{PHASE_H}" fill="#546E7A"/>')
        svg.append(f'<text x="{cx}" y="{TITLE_H+16}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#fff">{name}</text>')

    for i in range(4):
        yt, h = lane_tops[i], lane_heights[i]
        svg.append(f'<rect x="2" y="{yt}" width="{LL-2}" height="{h}" rx="4" fill="{lane_colors[i]}"/>')
        cy = yt + h/2
        lines = lane_names[i].split('\n')
        if len(lines) == 1:
            svg.append(f'<text x="46" y="{cy+4}" text-anchor="middle" font-size="12" font-weight="bold" fill="#fff" transform="rotate(-90,46,{cy})">{lines[0]}</text>')
        else:
            svg.append(f'<text x="40" y="{cy+4}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#fff" transform="rotate(-90,40,{cy})">{lines[0]}</text>')
            svg.append(f'<text x="54" y="{cy+4}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#fff" transform="rotate(-90,54,{cy})">{lines[1]}</text>')
        svg.append(f'<rect x="{LL}" y="{yt}" width="{W-LL}" height="{h}" fill="{lane_fills[i]}" opacity="0.35"/>')

    for x in PH[1:-1]:
        svg.append(f'<line x1="{x}" y1="{TOP}" x2="{x}" y2="{BOTTOM+70}" stroke="#CFD8DC" stroke-width="0.8" stroke-dasharray="5,4"/>')
    for i in range(1, 4):
        svg.append(f'<line x1="{LL}" y1="{lane_tops[i]}" x2="{W}" y2="{lane_tops[i]}" stroke="#CFD8DC" stroke-width="0.8"/>')

    def box(cx, cy, t1, t2, li):
        x, y = cx-BW/2, cy-BH/2
        stroke = lane_colors[li]
        s  = f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="5" fill="#fff" stroke="{stroke}" stroke-width="1.5"/>'
        s += f'<text x="{cx}" y="{cy-4}" text-anchor="middle" font-size="10" fill="#1a1a1a">{t1}</text>'
        if t2:
            s += f'<text x="{cx}" y="{cy+9}" text-anchor="middle" font-size="10" fill="#1a1a1a">{t2}</text>'
        return s

    def diamond(cx, cy, t1, t2, li):
        d = DIA
        pts = f"{cx},{cy-d} {cx+d},{cy} {cx},{cy+d} {cx-d},{cy}"
        stroke = lane_colors[li]
        s  = f'<polygon points="{pts}" fill="#fff" stroke="{stroke}" stroke-width="1.5"/>'
        s += f'<text x="{cx}" y="{cy-3}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#1a1a1a">{t1}</text>'
        s += f'<text x="{cx}" y="{cy+10}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#1a1a1a">{t2}</text>'
        return s

    def term(cx, cy, lbl, color):
        w, h = 76, 28
        s  = f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="14" fill="{color}"/>'
        s += f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="10" font-weight="bold" fill="#fff">{lbl}</text>'
        return s

    def arrow(pts, dashed=False):
        d = "M"+" L".join(f"{x},{y}" for x,y in pts)
        mk = "url(#ahp)" if dashed else "url(#ah)"
        st = ('stroke:#7B1FA2;stroke-width:1.5;fill:none;stroke-dasharray:6,4'
              if dashed else 'stroke:#455A64;stroke-width:1.5;fill:none')
        return f'<path d="{d}" style="{st}" marker-end="{mk}" stroke-linejoin="round" stroke-linecap="round"/>'

    def lbl(x, y, text, color, anchor="middle"):
        return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="9" font-weight="bold" fill="{color}">{text}</text>'

    gy = lcy(0); dy = lcy(1); ey = lcy(3)
    oy_top = owner_top() + BH/2
    oy_bot = owner_bot() + BH/2

    p0  = p0_x = PH[0] + 75   # align START and Search at same x
    p1l = PH[1] + 65
    p1r = PH[2] - 65
    p2a = PH[2] + 70
    p2b = PH[2] + 170
    p2c = PH[3] - 60
    p3r = PH[4] - 60
    p4  = pcx(4)
    d1x = PH[1] - 55
    d2x = PH[3] + 50

    # ── NODES ──────────────────────────────────────────────────
    start_cx, start_cy = p0, lane_tops[0] + 22   # aligned to p0
    svg.append(term(start_cx, start_cy, "START", "#1565C0"))

    p1_cx, p1_cy = p0, gy
    svg.append(box(p1_cx, p1_cy, "Search for B&amp;B", "(online / referral)", 0))
    b1_cx, b1_cy = p0, dy
    svg.append(box(b1_cx, b1_cy, "Display listings,", "photos &amp; reviews", 1))
    d1_cy = gy
    svg.append(diamond(d1x, d1_cy, "Meets", "needs?", 0))
    b2_cx, b2_cy = p1l, dy
    svg.append(box(b2_cx, b2_cy, "Check availability", "&amp; show pricing", 1))
    a3_cx, a3_cy = p1l, gy
    svg.append(box(a3_cx, a3_cy, "Submit booking", "&amp; guest details", 0))
    e1_cx, e1_cy = p1l, ey
    svg.append(box(e1_cx, e1_cy, "Process payment", "(gateway / bank)", 3))
    c1_cx, c1_cy = p1r, oy_top
    svg.append(box(c1_cx, c1_cy, "Confirm booking", "&amp; send details", 2))
    b3_cx, b3_cy = p1r, dy
    svg.append(box(b3_cx, b3_cy, "Email confirmation", "to guest", 1))
    c2_cx, c2_cy = p2a, oy_top
    svg.append(box(c2_cx, c2_cy, "Prepare room", "&amp; amenities", 2))
    a5_cx, a5_cy = p2a, gy
    svg.append(box(a5_cx, a5_cy, "Arrive &amp;", "check in", 0))
    # Personal welcome raised into mid-lane (not at bottom edge)
    c3_cx, c3_cy = p2b, lane_tops[2] + 110
    svg.append(box(c3_cx, c3_cy, "Personal welcome", "&amp; orientation", 2))
    a7_cx, a7_cy = p2c, gy
    svg.append(box(a7_cx, a7_cy, "Experience stay:", "room, food, service", 0))
    c4_cx, c4_cy = p2c, oy_top
    svg.append(box(c4_cx, c4_cy, "Serve breakfast &amp;", "manage experience", 2))
    d2_cy = gy
    svg.append(diamond(d2x, d2_cy, "Guest", "satisfied?", 0))
    c5_cx, c5_cy = d2x + 20, oy_top
    svg.append(box(c5_cx, c5_cy, "Address complaint", "(service recovery)", 2))
    a9_cx, a9_cy = p3r, gy
    svg.append(box(a9_cx, a9_cy, "Check out &amp;", "settle bill", 0))
    a10_cx, a10_cy = p4, gy
    svg.append(box(a10_cx, a10_cy, "Leave review", "(OTA / Google)", 0))
    b4_cx, b4_cy = p4, dy
    svg.append(box(b4_cx, b4_cy, "Review published;", "rating updated", 1))
    c6_cx, c6_cy = p4, oy_top
    svg.append(box(c6_cx, c6_cy, "Respond to", "review online", 2))
    end_cx, end_cy = p4, oy_bot + 8
    svg.append(term(end_cx, end_cy, "END", "#E65100"))

    # ── ARROWS ─────────────────────────────────────────────────
    # START → straight down to Search (both at x=p0)
    svg.append(arrow([(start_cx, start_cy+14), (p1_cx, p1_cy-BH/2)]))
    svg.append(arrow([(p1_cx, p1_cy+BH/2), (p1_cx, b1_cy-BH/2)]))
    svg.append(arrow([(b1_cx+BW/2, b1_cy), (d1x, b1_cy), (d1x, d1_cy+DIA)]))

    # "No" → side entry to Search box at mid-height
    svg.append(arrow([
        (d1x, d1_cy-DIA),
        (d1x, lane_tops[0]+15),
        (p1_cx-BW/2-15, lane_tops[0]+15),
        (p1_cx-BW/2-15, p1_cy),
        (p1_cx-BW/2, p1_cy)
    ]))
    svg.append(lbl(d1x+8, lane_tops[0]+13, "No", "#C62828", "start"))

    svg.append(arrow([(d1x+DIA, d1_cy), (PH[1], d1_cy), (PH[1], b2_cy), (b2_cx-BW/2, b2_cy)]))
    svg.append(lbl(d1x+DIA+4, d1_cy-6, "Yes", "#2E7D32", "start"))

    svg.append(arrow([(b2_cx, b2_cy-BH/2), (b2_cx, a3_cy+BH/2)]))

    ch_x1 = 475
    svg.append(arrow([(a3_cx+BW/2, a3_cy), (ch_x1, a3_cy), (ch_x1, e1_cy), (e1_cx+BW/2, e1_cy)]))
    svg.append(arrow([(e1_cx+BW/2, e1_cy), (ch_x1, e1_cy), (ch_x1, c1_cy), (c1_cx-BW/2, c1_cy)]))
    svg.append(arrow([(c1_cx, c1_cy-BH/2), (c1_cx, b3_cy+BH/2)]))
    svg.append(arrow([(c1_cx+BW/2, c1_cy), (c2_cx-BW/2, c2_cy)]))
    svg.append(arrow([(c2_cx, c2_cy-BH/2), (c2_cx, a5_cy+BH/2)]))

    ch_x2 = 725
    svg.append(arrow([(a5_cx+BW/2, a5_cy), (ch_x2, a5_cy), (ch_x2, c3_cy), (c3_cx-BW/2, c3_cy)]))
    # c3→c4: waypoint y=502 sits cleanly between the two boxes
    svg.append(arrow([(c3_cx, c3_cy-BH/2), (c3_cx, 502), (c4_cx, 502), (c4_cx, c4_cy+BH/2)]))
    svg.append(arrow([(c4_cx, c4_cy-BH/2), (c4_cx, a7_cy+BH/2)]))
    svg.append(arrow([(a7_cx+BW/2, a7_cy), (d2x-DIA, d2_cy)]))

    svg.append(arrow([(d2x, d2_cy+DIA), (d2x, c5_cy-BH/2)]))
    svg.append(lbl(d2x+6, d2_cy+DIA+12, "No", "#C62828", "start"))

    ch_x3 = 1030
    svg.append(arrow([(c5_cx+BW/2, c5_cy), (ch_x3, c5_cy),
                      (ch_x3, d2_cy-DIA-15), (d2x, d2_cy-DIA-15), (d2x, d2_cy-DIA)]))

    svg.append(arrow([(d2x+DIA, d2_cy), (a9_cx-BW/2, a9_cy)]))
    svg.append(lbl(d2x+DIA+4, d2_cy-6, "Yes", "#2E7D32", "start"))
    svg.append(arrow([(a9_cx+BW/2, a9_cy), (a10_cx-BW/2, a10_cy)]))
    svg.append(arrow([(a10_cx, a10_cy+BH/2), (a10_cx, b4_cy-BH/2)]))
    svg.append(arrow([(b4_cx, b4_cy+BH/2), (b4_cx, c6_cy-BH/2)]))
    svg.append(arrow([(c6_cx, c6_cy+BH/2), (c6_cx, end_cy-14)]))

    fb_y = BOTTOM + 40
    svg.append(arrow([(b4_cx-BW/2, b4_cy), (b4_cx-BW/2-12, b4_cy),
                      (b4_cx-BW/2-12, fb_y), (b1_cx-BW/2-8, fb_y),
                      (b1_cx-BW/2-8, b1_cy), (b1_cx-BW/2, b1_cy)], dashed=True))
    svg.append(f'<text x="{W/2}" y="{fb_y-6}" text-anchor="middle" font-size="10" fill="#7B1FA2" font-style="italic">'
               f'Feedback loop: Published reviews shape future guest search and booking decisions</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


# ═══════════════════════════════════════════════════════════════
# FIGURE 2: CAUSAL LOOP DIAGRAM
# ═══════════════════════════════════════════════════════════════

def fig2():
    W, H = 1160, 860
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    svg.append('''<defs>
  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>
  <marker id="ap" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
    <path d="M0,0 L7,2.5 L0,5 Z" fill="#1565C0"/>
  </marker>
  <marker id="an" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
    <path d="M0,0 L7,2.5 L0,5 Z" fill="#C62828"/>
  </marker>
</defs>''')
    svg.append(f'<rect width="{W}" height="{H}" fill="#FAFBFC"/>')
    svg.append(f'<text x="{W/2}" y="30" text-anchor="middle" font-size="16" font-weight="bold" fill="#1B2A4A">'
               f'Figure 2: Causal Loop Diagram \u2014 B&amp;B Profitability System</text>')
    svg.append('<rect x="25" y="50" width="520" height="740" rx="10" fill="none" stroke="#90A4AE" stroke-width="1" stroke-dasharray="7,4"/>')
    svg.append('<text x="285" y="70" text-anchor="middle" font-size="11" fill="#607D8B" font-style="italic">Tangible / Hard Factors</text>')
    svg.append('<rect x="615" y="50" width="520" height="740" rx="10" fill="none" stroke="#90A4AE" stroke-width="1" stroke-dasharray="7,4"/>')
    svg.append('<text x="875" y="70" text-anchor="middle" font-size="11" fill="#607D8B" font-style="italic">Intangible / Soft Factors</text>')

    NW, NH = 165, 42
    lx1, lx2 = 150, 390
    rx1, rx2  = 720, 960
    rows = [110, 220, 340, 450, 560, 680]

    def node(cx, cy, t1, t2, side):
        x, y = cx-NW/2, cy-NH/2
        if side=="L":   fill, stroke = "#E3F2FD","#1565C0"
        elif side=="R": fill, stroke = "#FFF3E0","#E65100"
        else:           fill, stroke = "#1B2A4A","#1B2A4A"
        tc = "#fff" if side=="C" else "#1a1a1a"
        sc = "#fff" if side=="C" else "#666"
        s  = f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        if t2:
            s += f'<text x="{cx}" y="{cy-3}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="{tc}">{t1}</text>'
            s += f'<text x="{cx}" y="{cy+10}" text-anchor="middle" font-size="8.5" fill="{sc}">{t2}</text>'
        else:
            s += f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="{tc}">{t1}</text>'
        return s

    def link(pts, pol):
        color = "#1565C0" if pol=="+" else "#C62828"
        mk = "url(#ap)" if pol=="+" else "url(#an)"
        d = "M"+" L".join(f"{x},{y}" for x,y in pts)
        return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" marker-end="{mk}" stroke-linejoin="round"/>'

    def pl(x, y, text, pol):
        color = "#1565C0" if pol=="+" else "#C62828"
        return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="12" font-weight="bold" fill="{color}">{text}</text>'

    def ll(cx, cy, text, pol):
        color = "#1565C0" if pol=="+" else "#C62828"
        fill  = "#E3F2FD"  if pol=="+" else "#FFEBEE"
        s  = f'<circle cx="{cx}" cy="{cy}" r="18" fill="{fill}" stroke="{color}" stroke-width="1"/>'
        s += f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="13" font-weight="bold" fill="{color}">{text}</text>'
        return s

    # ── NODES ──────────────────────────────────────────────────
    svg.append(node(lx1, rows[0], "Online Presence",    "&amp; Marketing",           "L"))
    svg.append(node(lx2, rows[0], "Occupancy Rate",     "(Bookings / Capacity)",     "L"))
    svg.append(node(lx1, rows[1], "Online Reviews",     "&amp; Ratings",             "L"))
    svg.append(node(lx1, rows[2], "Revenue per Guest",  "(Pricing Strategy)",        "L"))
    svg.append(node(lx2, rows[2], "PROFITABILITY",      "(Net Revenue)",             "C"))
    svg.append(node(lx1, rows[3], "Reinvestment",       "in Property",               "L"))
    svg.append(node(lx2, rows[3], "Operational Costs",  "(Maintenance, Supply)",     "L"))
    svg.append(node(lx1, rows[4], "Property Condition", "&amp; Room Quality",        "L"))
    svg.append(node(lx1, rows[5], "Breakfast Quality",  None,                        "L"))
    svg.append(node(rx1, rows[0], "Guest Satisfaction", "&amp; Experience",          "R"))
    svg.append(node(rx2, rows[0], "Owner Mindset",      "(Growth vs Fixed)",         "R"))
    svg.append(node(rx1, rows[1], "Word-of-Mouth",      "Reputation",                "R"))
    svg.append(node(rx2, rows[1], "Family Dynamics",    "&amp; Cohesion",            "R"))
    svg.append(node(rx1, rows[2], "Staff Morale",       "&amp; Motivation",          "R"))
    svg.append(node(rx2, rows[2], "Emotional Attachment","to Existing Style",        "R"))
    svg.append(node(rx1, rows[3], "Service Quality",    "(Hospitality Warmth)",      "R"))
    svg.append(node(rx2, rows[3], "Willingness to",     "Change &amp; Adapt",        "R"))
    svg.append(node(rx1, rows[4], "Owner Stress",       "&amp; Burnout",             "R"))
    svg.append(node(rx2, rows[4], "Competitive Pressure","(Airbnb etc.)",            "R"))

    # ── LINKS ──────────────────────────────────────────────────
    svg.append(link([(lx2, rows[0]+NH/2), (lx2, rows[2]-NH/2)], "+"))
    svg.append(pl(lx2+12, rows[1], "+", "+"))

    svg.append(link([(lx1+NW/2, rows[2]), (lx2-NW/2, rows[2])], "+"))
    svg.append(pl((lx1+lx2)/2, rows[2]-8, "+", "+"))

    svg.append(link([(lx2, rows[3]-NH/2), (lx2, rows[2]+NH/2)], "-"))
    svg.append(pl(lx2+12, (rows[3]+rows[2])/2, "\u2212", "-"))

    svg.append(link([(lx2-NW/2, rows[2]), (270, rows[2]), (270, rows[3]), (lx1+NW/2, rows[3])], "+"))
    svg.append(pl(285, rows[2]+20, "+", "+"))

    svg.append(link([(lx1, rows[3]+NH/2), (lx1, rows[4]-NH/2)], "+"))
    svg.append(pl(lx1+12, (rows[3]+rows[4])/2, "+", "+"))

    svg.append(link([(lx1-NW/2, rows[3]), (50, rows[3]), (50, rows[5]), (lx1-NW/2, rows[5])], "+"))
    svg.append(pl(60, rows[4], "+", "+"))

    svg.append(link([(lx1+NW/2, rows[3]), (lx2-NW/2, rows[3])], "+"))
    svg.append(pl((lx1+lx2)/2, rows[3]-8, "+", "+"))

    svg.append(link([(lx1+NW/2, rows[4]), (490, rows[4]), (490, rows[0]), (rx1-NW/2, rows[0])], "+"))
    svg.append(pl(502, rows[2], "+", "+"))

    svg.append(link([(lx1+NW/2, rows[5]), (470, rows[5]), (470, rows[0]+15), (rx1-NW/2, rows[0]+15)], "+"))
    svg.append(pl(482, rows[4], "+", "+"))

    svg.append(link([(rx1-NW/2, rows[0]-10), (620, rows[0]-10), (620, rows[1]), (lx1+NW/2, rows[1])], "+"))
    svg.append(pl(632, rows[0]+30, "+", "+"))

    svg.append(link([(rx1, rows[0]+NH/2), (rx1, rows[1]-NH/2)], "+"))
    svg.append(pl(rx1+12, (rows[0]+rows[1])/2, "+", "+"))

    svg.append(link([(lx1+NW/2, rows[1]-15), (lx2, rows[1]-15), (lx2, rows[0]+NH/2)], "+"))
    svg.append(pl(lx2-25, rows[1]-25, "+", "+"))

    svg.append(link([(rx1-NW/2, rows[1]-10), (580, rows[1]-10), (580, rows[0]+15), (lx2+NW/2, rows[0]+15)], "+"))
    svg.append(pl(590, rows[0]+35, "+", "+"))

    svg.append(link([(lx1+NW/2, rows[0]), (lx2-NW/2, rows[0])], "+"))
    svg.append(pl((lx1+lx2)/2, rows[0]-8, "+", "+"))

    svg.append(link([(lx2-NW/2, rows[2]-15), (255, rows[2]-15), (255, rows[0]+15), (lx1+NW/2, rows[0]+15)], "+"))
    svg.append(pl(267, rows[1]+30, "+", "+"))

    svg.append(link([(rx1+NW/2, rows[3]), (840, rows[3]), (840, rows[0]), (rx1+NW/2, rows[0])], "+"))
    svg.append(pl(850, rows[1], "+", "+"))

    svg.append(link([(rx2+NW/2, rows[0]), (1060, rows[0]), (1060, rows[3]), (rx2+NW/2, rows[3])], "+"))
    svg.append(pl(1072, rows[1], "+", "+"))

    svg.append(link([(rx2, rows[2]+NH/2), (rx2, rows[3]-NH/2)], "-"))
    svg.append(pl(rx2+12, (rows[2]+rows[3])/2, "\u2212", "-"))

    # Polarity labels near arrowheads for long paths
    svg.append(link([(rx2-NW/2, rows[3]+15), (840, rows[3]+15), (840, 740), (270, 740), (270, rows[3]+15), (lx1+NW/2, rows[3]+15)], "+"))
    svg.append(pl(290, rows[3]+27, "+", "+"))

    svg.append(link([(rx2+NW/2, rows[3]-15), (1080, rows[3]-15), (1080, 35), (lx1, 35), (lx1, rows[0]-NH/2)], "+"))
    svg.append(pl(lx1+12, 60, "+", "+"))

    svg.append(link([(rx2-NW/2, rows[1]), (840, rows[1]), (840, rows[2]), (rx1+NW/2, rows[2])], "+"))
    svg.append(pl(825, rows[2]-10, "+", "+"))

    svg.append(link([(rx1, rows[2]+NH/2), (rx1, rows[3]-NH/2)], "+"))
    svg.append(pl(rx1+12, (rows[2]+rows[3])/2, "+", "+"))

    svg.append(link([(lx2+NW/2, rows[2]), (490, rows[2]), (490, rows[4]), (rx1-NW/2, rows[4])], "-"))
    svg.append(pl(502, rows[3]+20, "\u2212", "-"))

    svg.append(link([(rx1, rows[4]-NH/2), (rx1, rows[3]+NH/2)], "-"))
    svg.append(pl(rx1+12, (rows[4]+rows[3])/2, "\u2212", "-"))

    svg.append(link([(rx1+NW/2, rows[4]), (825, rows[4]), (825, rows[1]+15), (rx2-NW/2, rows[1]+15)], "-"))
    svg.append(pl(810, rows[1]+27, "\u2212", "-"))

    svg.append(link([(rx2-NW/2, rows[4]), (855, rows[4]), (855, 395), (lx1, 395), (lx1, rows[2]+NH/2)], "-"))
    svg.append(pl(lx1+12, 420, "\u2212", "-"))

    # ── LOOP LABELS ────────────────────────────────────────────
    svg.append(ll(320, 158, "R2", "+"))   # clear gap between column paths
    svg.append(ll(270, 395, "R1", "+"))
    svg.append(ll(270, 500, "B1", "-"))
    svg.append(ll(790, 505, "R3", "-"))

    # ── LEGEND ─────────────────────────────────────────────────
    ly = H - 35
    svg.append(f'<rect x="30" y="{ly-5}" width="{W-60}" height="30" rx="4" fill="#ECEFF1"/>')
    svg.append(f'<line x1="50" y1="{ly+10}" x2="85" y2="{ly+10}" stroke="#1565C0" stroke-width="1.8" marker-end="url(#ap)"/>')
    svg.append(f'<text x="92" y="{ly+14}" font-size="9.5" fill="#444">Positive (+) link</text>')
    svg.append(f'<line x1="200" y1="{ly+10}" x2="235" y2="{ly+10}" stroke="#C62828" stroke-width="1.8" marker-end="url(#an)"/>')
    svg.append(f'<text x="242" y="{ly+14}" font-size="9.5" fill="#444">Negative (\u2212) link</text>')
    svg.append(f'<circle cx="370" cy="{ly+10}" r="9" fill="#E3F2FD" stroke="#1565C0" stroke-width="0.8"/>')
    svg.append(f'<text x="370" y="{ly+14}" text-anchor="middle" font-size="9" font-weight="bold" fill="#1565C0">R</text>')
    svg.append(f'<text x="386" y="{ly+14}" font-size="9.5" fill="#444">Reinforcing loop</text>')
    svg.append(f'<circle cx="500" cy="{ly+10}" r="9" fill="#FFEBEE" stroke="#C62828" stroke-width="0.8"/>')
    svg.append(f'<text x="500" y="{ly+14}" text-anchor="middle" font-size="9" font-weight="bold" fill="#C62828">B</text>')
    svg.append(f'<text x="516" y="{ly+14}" font-size="9.5" fill="#444">Balancing loop</text>')
    svg.append(f'<rect x="620" y="{ly+3}" width="14" height="14" rx="2" fill="#E3F2FD" stroke="#1565C0" stroke-width="1"/>')
    svg.append(f'<text x="640" y="{ly+14}" font-size="9.5" fill="#444">Tangible variable</text>')
    svg.append(f'<rect x="760" y="{ly+3}" width="14" height="14" rx="2" fill="#FFF3E0" stroke="#E65100" stroke-width="1"/>')
    svg.append(f'<text x="780" y="{ly+14}" font-size="9.5" fill="#444">Intangible variable</text>')
    svg.append(f'<rect x="900" y="{ly+3}" width="18" height="14" rx="2" fill="#1B2A4A"/>')
    svg.append(f'<text x="924" y="{ly+14}" font-size="9.5" fill="#444">Central outcome</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


# ═══════════════════════════════════════════════════════════════
# EXPORT — SVG + PNG
# ═══════════════════════════════════════════════════════════════

def save_png(svg_path, png_path, scale=3):
    """
    Convert SVG -> PNG using PyMuPDF (fitz).
    Pure Python wheel, no system Cairo/GTK needed.
    Install: pip install pymupdf
    """
    import fitz  # PyMuPDF
    doc = fitz.open(str(svg_path))
    page = doc[0]
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(str(png_path))
    doc.close()


if __name__ == "__main__":
    here = Path(__file__).parent

    # Write SVGs
    svg1 = here / "fig1_final.svg"
    svg2 = here / "fig2_final.svg"
    svg1.write_text(fig1(), encoding="utf-8")
    svg2.write_text(fig2(), encoding="utf-8")
    print("SVGs written.")

    # Convert to PNG
    try:
        save_png(svg1, here / "fig1_final.png")
        save_png(svg2, here / "fig2_final.png")
        print("PNGs written successfully.")
    except Exception as e:
        print(f"\nPNG export failed: {e}")
        print("SVG files are ready — open them in any browser to view.")