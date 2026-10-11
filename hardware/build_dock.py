# SPDX-License-Identifier: MIT
# Copyright (c) 2026 neko1000nin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Note: the STL/STEP files this script generates are licensed separately under CC BY 4.0.
"""
Trackball dock for tws_lp_jis60 (right half) -- 3 printed parts
  A  bracket   : clamped under the keyboard's front-left spacer (H4), carries the pad-side (female) pogo connector
  B  upper body: ball cup + hood (covers the bracket box, holds the pogo-pin side (male) connector)
  C  bottom plate: closes B and clamps the sensor board

Requirements: Python 3.11-3.14, CadQuery 2.x (tested: Python 3.13 / CadQuery 2.8.0)
    pip install cadquery
Run (from the folder that contains this file):
    python build_dock.py   ->  out/A_bracket.stl, out/B_upper_body.stl, out/C_bottom_plate.stl,
                               out/trackball_dock_assembly.step
All dimensions (mm) are in the P = dict(...) block below.

Coordinate system of the exported files (mm, right-handed):
    x = right (0 at the left edge of the right half),
    y = toward the keyboard rear (0 at the keyboard's front edge; the dock sits at y < 0),
    z = up (0 = desk).
(Inside this script the parameters are written with y = toward the user; parts are mirrored on export.)
Keyboard tilt (2.3 deg) is NOT modelled.
"""
import math, os
import cadquery as cq

# ------------------------------------------------------------------ parameters
P = dict(
    # keyboard-side bracket
    plate_z0=2.6, plate_t=1.0,            # ring at the spacer: 1.0 mm (4 mm spacer + 1 = original 5 mm)
    arm_t=1.4, tongue_depth=3.5, tongue_x=(13.5, 32.5),   # tongue position is fixed by the keyboard (lane between space and henkan); now at the box's LEFT end
    h4=(25.4, -20.2), h4_ring_od=6.4, ring_hole=2.3,   # spacer position (measured: 2 mm LEFT of the KiCad-derived 27.4), M2 clearance
    arm_pts=[(24, -20.2), (31, -20.2), (31, -16.7), (25, -14.0), (25, 2.0),
             (18, 2.0), (18, -14.5), (24, -17.2)],    # lane between space (1.25U) and henkan (1U)
    box_x=(13.5, 45.2), box_y=(0.5, 8.5), box_z=(0.8, 13.0),   # box shifted right so the tongue leaves its left end -> the whole dock (and the ball) moves 14 mm toward the thumb
    wire_groove=((25.5, 31.5), 0.7),      # 6 mm wide groove in the right part of the tongue, beside the arm, exits toward the XIAO side
    # magnetic pogo connector (6P, 2.3 mm pitch) -- from the drawings supplied
    con_len=26.5, con_h=6.0, con_flange_len=28.5, con_flange_h=8.0,
    con_face_to_flange=0.9, con_flange_t=1.0, con_depth_f=5.7, con_depth_m=4.7,   # measured: neck 0.9 (mating face -> flange), flange 1.0 thick
    con_cx=29.35, con_cz=8.2, clr=0.1,   # connector centred in the box; z 8.2: flange 4.1..12.3 above the tongue
    lid_t=0.8, lid_groove=0.5,            # sliding lid over the open-top box (slides in from the keyboard side); 0.35 lip above it
    # dock
    ball_d=25.0, cup_r=13.5, cup_c=(0.0, 23.0),     # ball centre on the keyboard's left-edge line, 23 from the front edge (10.7 left of the space key centre)
    sensor_from_rear=18.75,               # sensor centre from the board edge that faces the keyboard (with J1 facing the hood). Measured on the real board
    plate_c_t=3.1,                        # 0.6 skin + 0.2 clearance + 2.3 sensor body below the board
    sensor_pcb=(23.5, 31.5), pcb_t=1.8, pcb_to_surface=5.7,   # PCB top -> ACTUAL ball bottom on the seats (lens top 2.5 + 3.2). 2.8 tracked but stopped when the ball was pressed -> +0.4 margin
    pocket_headroom=1.9,                  # free height above the board top inside the pocket
    pcb_hole_inset=3.0,
    ball_region=((-14.8, 16.0), (0.5, 40.5)),  # left wall 1.3 outside the cup cavity (-13.5); right edge 1.0 outside the board pocket wall
    hood=((11.45, 47.25), (0.5, 24.5)), hood_h=15.0, chamber_front=17.0,   # walls 1.55 outside the box pocket; front wall 7.5 holds the M3 insert
    pocket=((13.0, 45.7), (0.5, 8.5)), pocket_top=13.5,   # box + 0.5 clearance per side; far wall at the box face
    frame_t=1.0, frame_out=0.6, frame_clr=0.15,           # frame: wall 1.0, protrusion 0.6, clearance 0.15. Protrusion+clearance must stay under the neck (0.9),
                                                          # otherwise a frame piece would hit the OTHER connector's flange behind its wall
    snap_rib=0.2, snap_rib_len=0.5, snap_rib_span=20.0,   # A only: the flange (8.0) is pushed past a 7.8 throat and is then captured
    plate_stop=(20.0, 1.2, 1.9),          # B side: boss on the bottom plate behind the flange (width, depth, height above the plate)
    wall=2.6,
    retainer="snap",                      # "snap": one-piece cup with a flexible lip (Keyball style), "ring": separate ring D
    snap_opening=25.2, lip_z=1.5, lip_h=0.8, lip_chamfer=0.6,   # 25.15 was a light snap; 25.2 a hair looser. Lower lip stack: top = ball centre + 2.9 (was +3.6)
    ring_od=31.0, ring_id_top=24.4, ring_id_bot=27.0, ring_h=4.0,
    sensor_body_cut=(11.0, 17.0),         # measured body 10 x 16 (+1 mm)
    sensor_pocket_closed=True, sensor_skin=0.4,   # blind pocket, 0.4 skin (lens pegs heat-staked flat)
    board_recess=1.2,                     # recess under the whole board (SMD parts on its underside); board rests on 4 pads at the M3 holes
    m2_pilot=1.8,                         # (used only when m2_insert=False) self-tapping pilot for M2 in PLA
    m2_insert=True, m2_insert_od=3.0, m2_insert_len=4.0,   # heat-press the spare M2 brass spacers (measure OD!) into the hood front wall -> metal threads for the plate screws
    lens_window=(14.0, 17.0),             # measured lens 8.2 x 13; widened in x so the sensor pin stubs beside the lens have room
    seat_ball=2.5, seat_hole=2.1, seat_depth=1.9, seat_angle=50.0,   # the press fit that worked (centre 0.65 in, no glue). Protrusion above the cavity comes from the pedestal
    seat_pedestal=(3.2, 0.4), seat_azimuths=(60.0, 180.0, 300.0),    # pedestal dia/height: 3.2 leaves a 0.55 collar around the 2.1 hole (4.5 looked bulky)
    boss_d=7.5, insert_hole=4.3, insert_depth=6.5,   # uxcell M3 x 5.7L x 4.6OD heat-set insert; 4.3 prints ~4.1 (install HOT with a soldering iron)
    finger_notch=False,                   # True: fingertip scallop on the left side of the cup rim (opens to the side face) to pry the ball out
    spacer_collar=False, spacer_od=3.0,   # True: 0.8 mm collar around the keyboard spacer on the bracket ring (heat-press the brass spacer into it)
)

# derived
plate_c_t = P["plate_c_t"]
pcb_top = plate_c_t + P["pcb_t"]                      # 4.1
ball_cz = pcb_top + P["pcb_to_surface"] + P["ball_d"] / 2      # centre of the ball as it actually rests on the three seats
seat_protrude = P["seat_ball"] / 2 - (P["seat_depth"] - P["seat_ball"] / 2) + P["seat_pedestal"][1]   # above the cavity surface
_rc = P["cup_r"] - seat_protrude                                 # radius of the seat-ball tops from the cavity centre
_th = math.radians(P["seat_angle"])
seat_delta = math.sqrt((P["ball_d"] / 2) ** 2 - (_rc * math.sin(_th)) ** 2) - _rc * math.cos(_th)   # ball centre minus cavity centre (negative: ball sits low)
cav_cz = ball_cz - seat_delta                                    # where the spherical cavity must be centred
body_top = (ball_cz + P["lip_z"] + P["lip_h"] + P["lip_chamfer"]) if P["retainer"] == "snap" else (ball_cz - 0.6)
cx, cy = P["cup_c"]
(bx0, bx1), (by0, by1) = P["ball_region"]
(hx0, hx1), (hy0, hy1) = P["hood"]
(px0, px1), (py0, py1) = P["pocket"]

pcb_w, pcb_l = P["sensor_pcb"]
pcb_x0, pcb_x1 = cx - pcb_w / 2, cx + pcb_w / 2      # -25.75 .. -2.25
pcb_y0, pcb_y1 = cy - P["sensor_from_rear"], cy - P["sensor_from_rear"] + pcb_l
ins = P["pcb_hole_inset"]
pcb_holes = [(pcb_x0 + ins, pcb_y0 + ins), (pcb_x1 - ins, pcb_y0 + ins),
             (pcb_x0 + ins, pcb_y1 - ins), (pcb_x1 - ins, pcb_y1 - ins)]
m3_hood = [(43.35, 20.8)]   # one M3 heat-set insert in the hood's front wall (1.65 to the chamber, 1.55 to the front, 1.75 to the right wall)
m2_plate = []              # the M2 brass-spacer sockets are gone             # bottom plate -> hood front wall
ring_ears = [(cx + 17.5 * math.cos(math.radians(a)), cy + 17.5 * math.sin(math.radians(a)))
             for a in (135, 315)]

# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))

def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))

def fillet_boxes(shape, r, boxes):
    """fillet every edge whose bounding box lies inside one of the given (x0,x1,y0,y1,z0,z1) boxes"""
    sel = []
    for e in shape.edges().vals():
        bb = e.BoundingBox()
        for (x0, x1, y0, y1, z0, z1) in boxes:
            if bb.xmin >= x0 and bb.xmax <= x1 and bb.ymin >= y0 and bb.ymax <= y1 and bb.zmin >= z0 and bb.zmax <= z1:
                sel.append(e); break
    if not sel:
        print("fillet: no edges matched"); return shape
    try:
        return shape.newObject(sel).fillet(r)
    except Exception as ex:
        print("fillet failed:", ex); return shape

def corner_boxes(zlo, zhi):
    d = 0.3
    return [(bx0 - d, bx0 + d, by1 - d, by1 + d, zlo, zhi),   # ball region front-left
            (bx1 - d, bx1 + d, by1 - d, by1 + d, zlo, zhi),   # ball region front-right
            (hx1 - d, hx1 + d, hy1 - d, hy1 + d, zlo, zhi),   # hood front-right
            (bx1 - d, bx1 + d, hy1 - d, hy1 + d, zlo, zhi)]   # inner (concave) corner of the L

def front_fillets(shape, r):
    """user's fillet scheme: vertical corners toward the user + all top edges except the keyboard side"""
    zb, zt, zh = plate_c_t, body_top, P["hood_h"]
    d = 0.3
    boxes = corner_boxes(zb - 1, zt + 1) + [
        (bx0 - d, bx1 + d, by1 - d, by1 + d, zt - d, zt + d),       # ball top front edge
        (bx0 - d, bx0 + d, by0 - d, by1 + d, zt - d, zt + d),       # ball top left edge
        (bx1 - d, bx1 + d, by0 - d, by1 + d, zt - d, zt + d),       # ball top right edge
        (bx1 - d, hx1 + d, hy1 - d, hy1 + d, zh - d, zh + d),       # hood top front edge
        (hx1 - d, hx1 + d, hy0 - d, hy1 + d, zh - d, zh + d),       # hood top right edge
        (bx1 - d, bx1 + d, hy0 - d, hy1 + d, zh - d, zh + d),       # concave edge: hood top meets ball region wall
    ]
    return fillet_boxes(shape, r, boxes)

def plate_fillets(shape, r):
    return fillet_boxes(shape, r, corner_boxes(-1, plate_c_t + 1))

def kb_mark(z0, z1):
    """small triangle pointing toward the keyboard, on the ball region beside the cup (internal frame: keyboard at low y)"""
    return cq.Workplane("XY").polyline([(cx - 3.5, 5.0), (cx + 3.5, 5.0), (cx, 1.5)]).close().extrude(z1 - z0).translate((0, 0, z0))

def csk_hole(x, y, d, csk_d, t):
    """through hole + 90 deg countersink opening at z=0 (bottom face)"""
    h = cyl(x, y, -1, t + 1, d)
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(csk_d / 2, d / 2, (csk_d - d) / 2,
                                                    pnt=cq.Vector(x, y, 0), dir=cq.Vector(0, 0, 1)))
    return h.union(cone)


# ------------------------------------------------------------------ interlocking frame around the connector
def seat_depth_ok(b):
    """walk along each seat normal from the pedestal top and check the hole ends at seat_depth (+-0.06)"""
    cx_, cy_ = P["cup_c"]
    ang = math.radians(P["seat_angle"])
    for az in P["seat_azimuths"]:
        a_ = math.radians(az)
        n = cq.Vector(math.cos(a_) * math.sin(ang), math.sin(a_) * math.sin(ang), -math.cos(ang))
        top = cq.Vector(cx_, cy_, cav_cz) + n * (P["cup_r"] - P["seat_pedestal"][1])
        d = 0.0
        while d < 4.0 and not b.val().isInside(top + n * d):
            d += 0.02
        if abs(d - P["seat_depth"]) > 0.06:
            print("   seat az %.0f: depth %.2f" % (az, d)); return False
    return True


def frame_zones():
    """(B pieces, A pieces) as (x0, x1, z0, z1) boxes just outside the connector body, in the mating plane"""
    c, cz = P["con_cx"], P["con_cz"]
    hl = P["con_len"] / 2 + 0.1                      # just outside the body (26.5 x 6.0)
    hh = P["con_h"] / 2 + 0.1
    t = P["frame_t"]
    b_pieces = [(c - hl - t, c - hl, cz - hh - t, cz + hh + t),          # left end
                (c + hl, c + hl + t, cz - hh - t, cz + hh + t),          # right end
                (c - hl, c - 6.0, cz + hh, cz + hh + t),                 # top, left of centre
                (c + 6.0, c + hl, cz + hh, cz + hh + t),                 # top, right of centre
                (c - hl, c - 6.0, cz - hh - t, cz - hh),                 # bottom, left of centre
                (c + 6.0, c + hl, cz - hh - t, cz - hh)]
    a_pieces = [(c - 5.8, c + 5.8, cz + hh, cz + hh + t),                # top centre
                (c - 5.8, c + 5.8, cz - hh - t, cz - hh)]                # bottom centre
    return b_pieces, a_pieces


def frame_add(shape, pieces, y0, y1):
    for (x0, x1, z0, z1) in pieces:
        shape = shape.union(box(x0, x1, y0, y1, z0, z1))
    return shape


def snap_ribs(shape, y0, y1, z_top, z_bot):
    """ribs hanging into the tunnel from its top and bottom, just behind the flange seat.
    The flange is pushed past them once and is then held between the ribs and the front ledges."""
    r, sp, c = P["snap_rib"], P["snap_rib_span"] / 2, P["con_cx"]
    shape = shape.union(box(c - sp, c + sp, y0, y1, z_top - r, z_top))
    shape = shape.union(box(c - sp, c + sp, y0, y1, z_bot, z_bot + r))
    return shape


def frame_cut(shape, pieces, y0, y1):
    k = P["frame_clr"]
    for (x0, x1, z0, z1) in pieces:
        shape = shape.cut(box(x0 - k, x1 + k, y0, y1, z0 - k, z1 + k))
    return shape


# ------------------------------------------------------------------ A: bracket
def build_bracket():
    z0, t, ta = P["plate_z0"], P["plate_t"], P["arm_t"]
    ring_right = P["h4"][0] + P["h4_ring_od"] / 2          # the cross arm must not stick out past the ring's right edge
    pts = [(min(x, ring_right), y) for (x, y) in P["arm_pts"]]
    plate = cq.Workplane("XY").polyline(pts).close().extrude(ta).translate((0, 0, z0))
    ring = cyl(*P["h4"], z0, z0 + t, P["h4_ring_od"])
    (x0, x1), (y0, y1), (z0b, z1b) = P["box_x"], P["box_y"], P["box_z"]
    body = box(x0, x1, y0, y1, z0b, z1b)
    tongue = box(P["tongue_x"][0], P["tongue_x"][1], y0 - P["tongue_depth"], y0 + 2.0, z0, z0 + ta)   # tongue in the gap
    a = plate.union(ring).union(tongue).union(body)
    a = a.cut(cyl(*P["h4"], z0 - 1, z0 + t + 1, P["ring_hole"]))
    a = a.cut(cyl(*P["h4"], z0 + t, z0 + ta + 1, 7.0))        # keep exactly 1.0 mm under the spacer (dia 7 zone)
    if P["spacer_collar"]:
        a = a.union(cyl(*P["h4"], z0 + t, z0 + t + 0.8, P["h4_ring_od"]))
        a = a.cut(cyl(*P["h4"], z0 + t - 0.1, z0 + t + 1.0, P["spacer_od"] - 0.2))
    # --- connector housing: the connector slides in from the keyboard side through a flange-sized tunnel and
    #     stops against the ledges above and below the neck slit. Floor (z 0.8..3.15) keeps the tongue joined.
    L, H, c = P["con_len"] + P["clr"], P["con_h"] + P["clr"], P["con_cx"]
    cz = P["con_cz"]
    FL, FH = P["con_flange_len"] + 2 * P["clr"], P["con_flange_h"] + 2 * P["clr"]
    face = y1                                                # mating plane = the box's front face
    neck = P["con_face_to_flange"]
    a = a.cut(box(c - FL / 2, c + FL / 2, y0 - 0.1, face - neck, cz - FH / 2, cz + FH / 2))                  # tunnel from the back, flange size
    a = a.cut(box(c - L / 2, c + L / 2, face - neck, face + 0.01, cz - H / 2, cz + H / 2))                   # neck slit through the front wall
    fl_back = face - neck - P["con_flange_t"] - P["clr"]                                                    # 6.1
    a = snap_ribs(a, fl_back - P["snap_rib_len"], fl_back, cz + FH / 2, cz - FH / 2)                         # retaining ribs
    b_pieces, a_pieces = frame_zones()
    a = frame_add(a, a_pieces, face, face + P["frame_out"])                                                  # A's frame pieces stick out
    a = frame_cut(a, b_pieces, face - P["frame_out"] - P["frame_clr"], face + 0.01)                           # recesses for B's pieces
    (gx0, gx1), gd = P["wire_groove"]
    a = a.cut(box(gx0, gx1, y0 - P["tongue_depth"] - 0.1, face - P["con_depth_f"], z0 + ta - gd, cz - FH / 2 + 0.3))   # wire groove: tongue end -> under the tails
    return a

# ------------------------------------------------------------------ B: upper body
def build_upper():
    zb = plate_c_t
    ball = box(bx0, bx1, by0, by1, zb, body_top)
    hood = box(hx0, hx1, hy0, hy1, zb, P["hood_h"])
    b = front_fillets(ball.union(hood), 2.0)
    # pocket for the bracket box (open at the bottom and toward the keyboard)
    b = b.cut(box(px0, px1, py0 - 1, py1, zb - 1, P["pocket_top"]))
    # pogo-pin side connector in the back wall of the pocket
    L, H, c, cz = P["con_len"] + P["clr"], P["con_h"] + P["clr"], P["con_cx"], P["con_cz"]
    FL, FH = P["con_flange_len"] + 2 * P["clr"], P["con_flange_h"] + 2 * P["clr"]
    face = py1                                                # mating plane = the pocket's far wall
    neck = P["con_face_to_flange"]
    b = b.cut(box(c - L / 2, c + L / 2, face - 0.01, face + neck, cz - H / 2, cz + H / 2))      # neck through the wall (closed bottom)
    fl_seat = face + neck + P["con_flange_t"] + P["clr"]                                       # flange back face
    b = b.cut(box(c - FL / 2, c + FL / 2, face + neck, fl_seat, cz - FH / 2, cz + FH / 2))      # flange pocket (plain)
    b = b.cut(box(c - FL / 2, c + FL / 2, fl_seat, P["chamber_front"], zb - 1, P["pocket_top"]))  # wire chamber (insertion path)
    b_pieces, a_pieces = frame_zones()
    b = frame_add(b, b_pieces, face - P["frame_out"], face)                                    # B's frame pieces stick out toward the keyboard
    b = frame_cut(b, a_pieces, face - 0.01, face + P["frame_out"] + P["frame_clr"])            # recesses for A's pieces
    # wire channel from the board pocket to the chamber (through the hood's left wall)
    # wire path: (a) slot along the board pocket's right side, kept 1 mm inside the outer wall,
    #            (b) passage into the wire chamber, kept behind the hood's front wall
    b = b.cut(box(pcb_x1 - 0.5, bx1 - 1.0, pcb_y0 + 7.5, pcb_y0 + 24.5, zb - 1, zb + 5.9))     # slot along the J1 pins, open to the bottom
    fl_seat_b = py1 + P["con_face_to_flange"] + P["con_flange_t"] + P["clr"]
    b = b.cut(box(bx1 - 1.5, c - L / 2 + 3.0, fl_seat_b, P["chamber_front"], zb - 1, zb + 5.9))   # partition removed: pocket <-> chamber opening, open to the bottom
    # sensor board pocket
    b = b.cut(box(pcb_x0 - 0.25, pcb_x1 + 0.25, pcb_y0 - 0.25, pcb_y1 + 0.25, zb - 1, pcb_top + P["pocket_headroom"]))
    # bosses down to the board top + insert holes
    for (hx, hy) in pcb_holes:
        b = b.union(cyl(hx, hy, pcb_top, pcb_top + P["pocket_headroom"] + 0.1, P["boss_d"]))
        b = b.cut(cyl(hx, hy, pcb_top - 0.5, pcb_top + P["insert_depth"], P["insert_hole"]))
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCone(P["insert_hole"] / 2 + 0.5, P["insert_hole"] / 2, 0.5,
                                                             pnt=cq.Vector(hx, hy, pcb_top), dir=cq.Vector(0, 0, 1))))   # entry chamfer for the insert
    # ball cup
    sphere = cq.Workplane("XY").sphere(P["cup_r"]).translate((cx, cy, cav_cz))
    if P["retainer"] == "snap":
        sphere = sphere.intersect(box(cx - 20, cx + 20, cy - 20, cy + 20, 0, ball_cz + P["lip_z"]))   # sphere below the lip only
        b = b.cut(sphere)
        b = b.cut(cyl(cx, cy, ball_cz + P["lip_z"], body_top + 1, P["snap_opening"]))                # lip opening
        ch = P["lip_chamfer"]
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCone(P["snap_opening"] / 2 + ch, P["snap_opening"] / 2, ch,
                                                             pnt=cq.Vector(cx, cy, body_top - ch), dir=cq.Vector(0, 0, 1))))  # entry chamfer
    else:
        b = b.cut(sphere)
    if P["finger_notch"]:
        b = b.cut(cyl(cx - 14.5, cy, ball_cz, body_top + 1, 8.0))     # left side, down to the ball's equator
    # lens window (from the board pocket up into the cup)
    lw, ll = P["lens_window"]
    b = b.cut(box(cx - lw / 2, cx + lw / 2, cy - ll / 2, cy + ll / 2, zb + 3.0, cav_cz - 9.0))   # 4.5 into the cavity so the whole 14x17 window opens into it (a shallower cut leaves a round hole)
    # zirconia support-ball seats: pedestal (raised pad inside the cavity) + radial press-fit hole, 50 deg from the bottom pole
    ang = math.radians(P["seat_angle"])
    pd, ph = P["seat_pedestal"]
    for az in P["seat_azimuths"]:
        a_ = math.radians(az)
        n = cq.Vector(math.cos(a_) * math.sin(ang), math.sin(a_) * math.sin(ang), -math.cos(ang))  # outward normal
        surf = cq.Vector(cx, cy, cav_cz) + n * P["cup_r"]
        b = b.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(pd / 2, ph + 1.0, surf - n * ph, n)))   # pedestal: from ph inside the cavity out into the wall
        start = surf - n * (ph + 0.3)                                                                            # 0.3 above the pedestal top
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(P["seat_hole"] / 2, P["seat_depth"] + 0.3, start, n)))   # hole depth = seat_depth from the pedestal top
    # pilot holes: ring ears (M2) and bottom-plate screws at the hood's front wall (M2)
    if P["retainer"] == "ring":
        for (ex, ey) in ring_ears:
            b = b.cut(cyl(ex, ey, body_top - 5, body_top + 1, 1.6))
    for (mx, my) in m3_hood:                                        # same M3 heat-set insert as the four board bosses
        b = b.cut(cyl(mx, my, zb - 1, zb + P["insert_depth"], P["insert_hole"]))
        b = b.cut(cq.Workplane("XY").add(cq.Solid.makeCone(P["insert_hole"] / 2 + 0.5, P["insert_hole"] / 2, 0.5,
                                                             pnt=cq.Vector(mx, my, zb), dir=cq.Vector(0, 0, 1))))
    return b

# ------------------------------------------------------------------ C: bottom plate
def build_plate():
    t = plate_c_t
    c = box(bx0, bx1, by0, by1, 0, t).union(box(hx0, hx1, py1, hy1, 0, t))
    c = c.cut(box(px0, px1, py0 - 1, py1, -1, t + 1))          # no plate under the bracket box
    c = plate_fillets(c, 2.0)
    # recess under the whole board except 4 pads (dia 7) at the M3 holes on which the board rests
    r = P["board_recess"]
    c = c.cut(box(pcb_x0 - 0.25, pcb_x1 + 0.25, pcb_y0 - 0.25, pcb_y1 + 0.25, t - r, t + 1))
    for (hx, hy) in pcb_holes:
        c = c.union(cyl(hx, hy, t - r - 0.01, t, 7.0))
    for (hx, hy) in pcb_holes:
        c = c.cut(csk_hole(hx, hy, 3.4, 6.5, t))
    for (mx, my) in m3_hood:
        c = c.cut(csk_hole(mx, my, 3.4, 6.5, t))
    # recess for the pogo-pin side connector: its body (z 2.75..8.75) and flange (z 1.75..9.75) sit lower than the plate top (3.1)
    L, FL = P["con_len"] + P["clr"], P["con_flange_len"] + 2 * P["clr"]
    cc, w = P["con_cx"], P["wall"]
    # boss that traps the male connector: it stands behind the flange, under the connector body
    sw, sd, sh = P["plate_stop"]
    fl_seat = py1 + P["con_face_to_flange"] + P["con_flange_t"] + P["clr"]
    c = c.union(box(cc - sw / 2, cc + sw / 2, fl_seat + 0.1, fl_seat + 0.1 + sd, t - 0.01, t + sh))
    # through-cut under the sensor body (the PMW3610 package sits below the board)
    sx, sy = P["sensor_body_cut"]
    zcut = P["sensor_skin"] if P["sensor_pocket_closed"] else -1
    c = c.cut(box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, zcut, t + 1))
    # 1.0 mm recess under the J1 row so the solder joints on the board's underside have room
    c = c.cut(box(pcb_x1 - 4.5, pcb_x1 + 0.75, pcb_y0 + 8.5, pcb_y0 + 23.0, t - 1.0, t + 1))
    return c

# ------------------------------------------------------------------ D: ring
def build_ring():
    h = P["ring_h"]
    d = cyl(cx, cy, body_top, body_top + h, P["ring_od"])
    for (ex, ey) in ring_ears:
        d = d.union(cyl(ex, ey, body_top, body_top + 3.0, 6.0))
        d = d.cut(cyl(ex, ey, body_top - 1, body_top + 4, 2.2))
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(P["ring_id_bot"] / 2, P["ring_id_top"] / 2, h,
                                                    pnt=cq.Vector(cx, cy, body_top), dir=cq.Vector(0, 0, 1)))
    d = d.cut(cone)
    return d

# ------------------------------------------------------------------ self-check
def self_check(parts):
    """cheap pre-print checks: interference between parts, wire path open, walls around screws intact"""
    import itertools
    ok = True
    CX = P["con_cx"]
    names = list(parts)
    for n1, n2 in itertools.combinations(names, 2):
        inter = parts[n1].intersect(parts[n2])
        v = inter.val().Volume() if inter.solids().vals() else 0.0
        flag = "OK " if v < 0.01 else "NG "
        ok &= v < 0.01
        print(f"[{flag}] interference {n1} x {n2}: {v:.2f} mm3")
    b = parts["B_upper_body"]; c = parts["C_bottom_plate"]; a = parts["A_bracket"]
    # the checks below use the internal (y toward user) frame, so mirror back
    b, c, a = b.mirror("XZ"), c.mirror("XZ"), a.mirror("XZ")
    zb = plate_c_t
    def empty(sh, p): return not sh.val().isInside(cq.Vector(*p))
    def solid(sh, p): return sh.val().isInside(cq.Vector(*p))
    L = P["con_len"] + P["clr"]; cc = P["con_cx"]
    tests = [
        ("wire path: board pocket edge", empty(b, (pcb_x1 - 0.3, pcb_y0 + 16, zb + 1.5))),
        ("wire path: no sill (open at z = plate top + 0.2)", empty(b, (pcb_x1 + 0.5, pcb_y0 + 16, zb + 0.2)) and empty(b, (P["con_cx"] - 13.3 + 1.5, 14.0, zb + 0.2))),
        ("wire path: slot beside pocket", empty(b, (pcb_x1 + 0.5, pcb_y0 + 16, zb + 1.5))),
        ("wire path: passage into chamber", empty(b, (cc - L / 2 + 1.5, 15.0, zb + 1.5))),
        ("wire path: chamber", empty(b, (cc, 14.5, zb + 1.5))),
        ("outer wall beside wire slot", solid(b, (bx1 - 0.5, cy + 6, zb + 1.5))),
        ("hood M3 insert hole open", all(empty(b, (mx, my, zb + 3)) for mx, my in m3_hood)),
        ("hood M3: wall >= 1.5 on all four sides", all(solid(b, (mx + dx, my + dy, zb + 3)) for mx, my in m3_hood for dx, dy in ((P["insert_hole"] / 2 + 1.5, 0), (-P["insert_hole"] / 2 - 1.5, 0), (0, P["insert_hole"] / 2 + 1.5), (0, -P["insert_hole"] / 2 - 1.5)))),
        ("hood M3: wall to the chamber intact", all(solid(b, (mx, P["chamber_front"] + 0.8, zb + 3)) and empty(b, (mx, P["chamber_front"] - 0.8, zb + 3)) for mx, my in m3_hood)),
        ("plate: M3 countersink fully inside the plate", all(solid(c, (mx + 3.4, my, 0.2)) and solid(c, (mx, my + 3.4, 0.2)) and solid(c, (mx, my - 3.4, 0.2)) for mx, my in m3_hood)),
        ("male clear of the plate (flange bottom %.1f > plate %.1f)" % (P["con_cz"] - P["con_flange_h"] / 2, plate_c_t), P["con_cz"] - P["con_flange_h"] / 2 > plate_c_t + 0.5),
        ("wire slot/passage taller than the tails", zb + 5.9 >= P["con_cz"] + 0.4),
        ("plate: board rests on 4 pads", all(solid(c, (hx + 2.5, hy, plate_c_t - 0.3)) for hx, hy in pcb_holes)),
        ("plate: recess under board open", empty(c, (cx - 6, pcb_y0 + 16, plate_c_t - 0.3))),
        ("plate: sensor pocket " + ("skin intact" if P["sensor_pocket_closed"] else "through (temporary)"),
         (solid(c, (cx, cy, 0.2)) and empty(c, (cx, cy, P["sensor_skin"] + 0.3))) if P["sensor_pocket_closed"] else empty(c, (cx, cy, 0.2))),
        ("bracket: ring 1.0 under spacer", solid(a, (P["h4"][0] + 2.2, P["h4"][1], 3.5)) and empty(a, (P["h4"][0] + 2.2, P["h4"][1], 3.7))),
        ("bracket: arm joined to box (one solid)", len(a.solids().vals()) == 1),
        ("bracket: tongue joined to box floor across its width", all(solid(a, (x, 1.0, 3.0)) for x in (14.0, 20.0, 26.0, 31.0)) and all(solid(a, (x, 1.0, 3.9)) for x in (14.0, 20.0))),
        ("bracket: wire groove open at tongue (z 3.5)", empty(a, (29.0, -2.0, 3.5)) and solid(a, (29.0, -2.0, 3.0)) and solid(a, (20.0, -2.0, 3.8))),
        ("bracket: connector space open, floor solid", empty(a, (CX, 4.0, P["con_cz"])) and solid(a, (CX, 4.0, 3.9))),
        ("bracket: tunnel floor above the tongue", empty(a, (CX, 6.6, 4.4)) and solid(a, (CX, 6.6, 3.9))),
        ("bracket: neck slit open, closed above/below", empty(a, (CX, 7.8, 8.2)) and solid(a, (CX, 7.8, 11.7)) and solid(a, (CX, 7.8, 4.6))),
        ("bracket: ledges stop the flange (centre, 12 mm, both sides)", all(solid(a, (x, 7.8, z)) for x in (CX - 5.0, CX, CX + 5.0) for z in (4.6, 11.7))),
        ("mating faces coincide", abs(py1 - P["box_y"][1]) < 1e-6),
        ("frame: recess (%.2f) stays inside the neck (%.2f)" % (P["frame_out"] + P["frame_clr"], P["con_face_to_flange"]), P["frame_out"] + P["frame_clr"] < P["con_face_to_flange"] - 0.1),
        ("frame: A pieces clear of B's flange", solid(b, (CX, py1 + P["con_face_to_flange"] - 0.2, P["con_cz"] + 3.6)) is False),
        ("snap: throat narrower than the flange (%.1f vs %.1f)" % (P["con_flange_h"] + 2 * P["clr"] - 2 * P["snap_rib"], P["con_flange_h"]), P["con_flange_h"] + 2 * P["clr"] - 2 * P["snap_rib"] < P["con_flange_h"]),
        ("snap: A ribs present behind the flange seat", solid(a, (CX, 6.3, P["con_cz"] + 4.0)) and solid(a, (CX, 6.3, P["con_cz"] - 4.0)) and empty(a, (CX, 6.3, P["con_cz"]))),
        ("snap: A flange seat clear in front of the ribs", empty(a, (CX, 7.0, P["con_cz"] + 4.0)) and empty(a, (CX, 7.0, P["con_cz"] - 4.0))),
        ("B: flange pocket plain (no ribs)", all(empty(b, (CX, y, z)) for y in (9.6, 10.3) for z in (P["con_cz"] + 4.0, P["con_cz"] - 4.0, P["con_cz"]))),
        ("C: stop boss behind the flange", solid(c, (CX, py1 + P["con_face_to_flange"] + P["con_flange_t"] + P["clr"] + 0.7, plate_c_t + 1.0))),
        ("C: boss clears the connector body (top %.1f < body bottom %.1f)" % (plate_c_t + P["plate_stop"][2], P["con_cz"] - P["con_h"] / 2), plate_c_t + P["plate_stop"][2] < P["con_cz"] - P["con_h"] / 2),
        ("C: boss inside the chamber void in B", all(empty(b, (CX + dx, py1 + P["con_face_to_flange"] + P["con_flange_t"] + P["clr"] + 0.7, plate_c_t + h)) for dx in (-9.0, 0.0, 9.0) for h in (0.3, 1.8))),
        ("frame: A pieces present beyond the face", solid(a, (CX, P["box_y"][1] + 0.6, P["con_cz"] + 3.6)) and solid(a, (CX, P["box_y"][1] + 0.6, P["con_cz"] - 3.6))),
        ("frame: B pieces present beyond the face", solid(b, (CX - 13.8, py1 - 0.6, P["con_cz"])) and solid(b, (CX + 13.8, py1 - 0.6, P["con_cz"])) and solid(b, (CX - 9.0, py1 - 0.6, P["con_cz"] + 3.6))),
        ("frame: B window bottom closed", solid(b, (CX + 8.0, py1 + 0.6, P["con_cz"] - P["con_h"] / 2 - 0.4))),
        ("bracket: back tunnel passes the flange", all(empty(a, (x, 0.8, z)) for x in (CX, CX + 14.0, CX - 14.0) for z in (4.4, 8.2, 12.0)) and solid(a, (CX, 0.8, 12.7))),
        ("bracket: box flush with the hood pocket (depth %.1f = %.1f)" % (P["box_y"][1] - P["box_y"][0], py1 - py0), abs((P["box_y"][1] - P["box_y"][0]) - (py1 - py0)) < 1e-6 and abs(P["box_y"][0] - py0) < 1e-6),
        ("bracket: box closed on top", solid(a, (CX, 4.0, 12.7))),
        ("upper body one solid", len(b.solids().vals()) == 1),
        ("seat hole depth from pedestal top == %.2f" % P["seat_depth"], seat_depth_ok(b)),
        ("lens window fully open into the cavity (corners)", all(empty(b, (cx + sx * (P["lens_window"][0] / 2 - 0.3), cy + sy * (P["lens_window"][1] / 2 - 0.3), cav_cz - P["cup_r"] + 0.3)) for sx in (-1, 1) for sy in (-1, 1))),
        ("ball vs cavity floor gap %.2f >= 0.6" % ((cav_cz - P["cup_r"]) * -1 + (ball_cz - P["ball_d"] / 2)), (ball_cz - P["ball_d"] / 2) - (cav_cz - P["cup_r"]) >= 0.6),
        ("ball vs lip clearance %.2f >= 0.1/side" % ((P["snap_opening"] - 2 * math.sqrt((P["ball_d"] / 2) ** 2 - P["lip_z"] ** 2)) / 2), (P["snap_opening"] - 2 * math.sqrt((P["ball_d"] / 2) ** 2 - P["lip_z"] ** 2)) / 2 >= 0.1),
        ("opening vs ball: %s" % ("snap (needs a flexible lip)" if P["snap_opening"] < P["ball_d"] else "clearance %.2f/side, no retention" % ((P["snap_opening"] - P["ball_d"]) / 2)), True),
    ]
    for name, res in tests:
        print(f"[{'OK ' if res else 'NG '}] {name}")
        ok &= bool(res)
    print("SELF-CHECK", "PASSED" if ok else "FAILED")
    return ok


# ------------------------------------------------------------------ build + export
if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    # The parameters above use y = toward the user for readability.  A right-handed CAD frame with
    # x = right and z = up needs y = away from the user, so every part is mirrored about XZ on export.
    def rh(shape):
        return shape.mirror("XZ")
    parts = {
        "A_bracket": (rh(build_bracket()), cq.Color(0.55, 0.45, 0.85)),
        "B_upper_body": (rh(build_upper()), cq.Color(0.75, 0.72, 0.95)),
        "C_bottom_plate": (rh(build_plate()), cq.Color(0.62, 0.58, 0.9)),
    }
    if P["retainer"] == "ring":
        parts["D_ring"] = (rh(build_ring()), cq.Color(0.45, 0.4, 0.8))
    assy = cq.Assembly(name="trackball_dock")
    for name, (solid, color) in parts.items():
        assert solid.val().isValid(), name
        assy.add(solid, name=name, color=color)
        cq.exporters.export(solid, f"out/{name}.stl", tolerance=0.02, angularTolerance=0.1)
        bb = solid.val().BoundingBox()
        print(f"{name:15s} x {bb.xmin:7.2f}..{bb.xmax:6.2f}  y {bb.ymin:6.2f}..{bb.ymax:6.2f}  z {bb.zmin:5.2f}..{bb.zmax:5.2f}  vol {solid.val().Volume():8.0f} mm3")
    assy.save("out/trackball_dock_assembly.step")
    print("ball centre z = %.2f  ball top = %.2f  body top = %.2f  cavity centre = %.2f (ball sits %.2f low on the seats, protrusion %.2f)  lens top -> ball %.2f" % (ball_cz, ball_cz + P["ball_d"] / 2, body_top, cav_cz, -seat_delta, seat_protrude, P["pcb_to_surface"] - 2.5))
    solids = {n: s for n, (s, _) in parts.items()}
    self_check(solids)
