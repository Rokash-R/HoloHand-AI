import math
import time

from direct.gui.DirectGui import DirectLabel, DirectButton, DGG
from panda3d.core import (
    TextNode, Vec4, LineSegs, NodePath, Point3,
    TransparencyAttrib, ColorBlendAttrib, ClockObject,
    CardMaker, Geom, GeomNode, GeomTriangles,
    GeomVertexData, GeomVertexFormat, GeomVertexWriter,
)


# ============================================================
# SMALL GEOMETRY HELPERS (BUILT ONCE, NEVER PER FRAME)
# ============================================================

def _mix(a, b, t):
    """Linear blend of two RGB tuples."""
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _disc_geom(radius, segments=48, center_alpha=1.0, edge_alpha=1.0,
               center_shade=1.0, edge_shade=1.0):
    """Filled disc in the XZ plane with a radial alpha + brightness gradient.
    Tint it afterwards with setColorScale(). Scale it non-uniformly to get an
    ellipse (used for the angled drum / cymbal look)."""
    vdata = GeomVertexData("DrumDisc", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vdata.setNumRows(segments + 2)
    vw = GeomVertexWriter(vdata, "vertex")
    cw = GeomVertexWriter(vdata, "color")

    vw.addData3(0.0, 0.0, 0.0)
    cw.addData4(center_shade, center_shade, center_shade, center_alpha)
    for i in range(segments + 1):
        a = (i / segments) * math.pi * 2.0
        vw.addData3(math.cos(a) * radius, 0.0, math.sin(a) * radius)
        cw.addData4(edge_shade, edge_shade, edge_shade, edge_alpha)

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        tris.addVertices(0, i + 1, i + 2)
    tris.closePrimitive()

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("DrumDisc")
    node.addGeom(geom)

    np_ = NodePath(node)
    np_.setTwoSided(True)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    return np_


def _ring_geom(r_in, r_out, segments=64, in_alpha=1.0, out_alpha=1.0):
    """Annulus in the XZ plane. Tint with setColorScale()."""
    vdata = GeomVertexData("DrumRing", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vdata.setNumRows((segments + 1) * 2)
    vw = GeomVertexWriter(vdata, "vertex")
    cw = GeomVertexWriter(vdata, "color")

    for i in range(segments + 1):
        a = (i / segments) * math.pi * 2.0
        c, s = math.cos(a), math.sin(a)
        vw.addData3(c * r_in, 0.0, s * r_in)
        cw.addData4(1.0, 1.0, 1.0, in_alpha)
        vw.addData3(c * r_out, 0.0, s * r_out)
        cw.addData4(1.0, 1.0, 1.0, out_alpha)

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        k = i * 2
        tris.addVertices(k, k + 1, k + 2)
        tris.addVertices(k + 1, k + 3, k + 2)
    tris.closePrimitive()

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("DrumRing")
    node.addGeom(geom)

    np_ = NodePath(node)
    np_.setTwoSided(True)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    return np_


def _band_geom(rx, rz, top, bottom, segments=40, alpha=0.95, shade_edge=0.45):
    """The visible FRONT wall of a cylinder seen from slightly above.

    The band follows the lower half of an ellipse (radii rx, rz) and spans
    vertically from `top` to `bottom` (both are z offsets, bottom < top).
    Shading is brighter in the middle and darker at the sides, with a soft
    highlight, so a drum shell reads as round. Radii are baked in, so place
    it with scale 1. Tint with setColorScale()."""
    vdata = GeomVertexData("DrumBand", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vdata.setNumRows((segments + 1) * 2)
    vw = GeomVertexWriter(vdata, "vertex")
    cw = GeomVertexWriter(vdata, "color")

    for i in range(segments + 1):
        a = math.pi + (i / segments) * math.pi        # lower half: pi .. 2pi
        c, s = math.cos(a), math.sin(a)
        x = c * rx
        shade = shade_edge + (1.0 - shade_edge) * (1.0 - abs(c) ** 1.6)
        shade = min(1.0, shade + 0.22 * math.exp(-((c + 0.35) / 0.20) ** 2))
        vw.addData3(x, 0.0, s * rz + top)
        cw.addData4(shade, shade, shade, alpha)
        vw.addData3(x, 0.0, s * rz + bottom)
        cw.addData4(shade, shade, shade, alpha)

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        k = i * 2
        tris.addVertices(k, k + 1, k + 2)
        tris.addVertices(k + 1, k + 3, k + 2)
    tris.closePrimitive()

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("DrumBand")
    node.addGeom(geom)

    np_ = NodePath(node)
    np_.setTwoSided(True)
    np_.setTransparency(TransparencyAttrib.MAlpha)
    return np_


def _make_additive(np_):
    """Glow blending: colour is added to whatever is behind it."""
    np_.setAttrib(
        ColorBlendAttrib.make(
            ColorBlendAttrib.MAdd,
            ColorBlendAttrib.OIncomingAlpha,
            ColorBlendAttrib.OOne,
        )
    )
    np_.setTransparency(TransparencyAttrib.MAlpha)


class Drums:
    """
    HoloHand AI - Drum Studio (Stage 3, Checkpoint A).

    Layout: console with one drum kit in the middle, DRUM GUIDE on the left,
    PERFORMANCE on the right, and a new SETTINGS dock along the bottom.

    Two playing modes (like the Piano Studio)
      AIR   - a short, deliberate downward tap of the index finger over a drum
              plays it once. The finger must rise a little (or leave the drum)
              before the same hand can hit that drum again, so resting a finger
              on a drum never repeats. Speed / distance thresholds depend on
              the SENSITIVITY setting (see AIR_PROFILES).
      PINCH - Stage 2 behaviour, unchanged: pinch thumb + index over a drum to
              play it once; open the pinch to hit again.

    In both modes each hand keeps its own state, cooldown and cursor
    (cyan = left hand, pink = right hand). A pinch over a *button* presses that
    button (in AIR mode a pinch never plays a drum, so it is free for the UI).

    Settings (all functional): play mode, AIR sensitivity, visual effects,
    metronome on/off + tempo 60-180 BPM, reset to defaults. Master volume keeps
    its existing -/+ control in the PERFORMANCE panel.

    HOME: this module no longer draws its own HOME button. main.py already
    shows one in Drums mode (mouse + pinch), so there is exactly one.

    Hand identity: the tracker gives NO left/right labels, so the two hands
    are told apart by position ("L" = hand on the left of the screen) and then
    followed frame to frame by nearest position.

    Hit zones are built from the same numbers that draw the instruments, so
    what you see is what you hit. The cursor uses the same screen mapping as
    main.py's own cursor, and no drum zone reaches the HOME button area.

    All geometry is built once at start-up. Per frame only the two cursors
    move, and only pads that were just hit animate.
    """

    PADS = [
        {
            "id": "kick",
            "name": "KICK",
            "emoji": "[O]",
            "color": (0.65, 0.1, 0.8, 0.88),
            "active_color": (1.0, 0.3, 1.0, 1.0),
            "finger": "Pinky",
            "finger_idx": 4,   # extended finger tip landmark
            "zone": (0.0, 0.17),
            "kind": "kick",
            "pos": (0.0, -0.34),          # centre of the front head
            "radius": 0.25,
            "rx": 0.25, "rz": 0.25, "depth": 0.0,
            "hit": (0.0, -0.34, 0.26, 0.26),
            "hint": "PINKY",
            "desc": "DEEP BASS THUMP",
            "where": "BOTTOM",
        },
        {
            "id": "snare",
            "name": "SNARE",
            "emoji": "[*]",
            "color": (0.1, 0.55, 1.0, 0.88),
            "active_color": (0.4, 0.95, 1.0, 1.0),
            "finger": "Index",
            "finger_idx": 1,
            "zone": (0.17, 0.34),
            "kind": "snare",
            "pos": (-0.44, -0.10),        # centre of the top head
            "radius": 0.19,
            "rx": 0.19, "rz": 0.062, "depth": 0.11,
            "hit": (-0.44, -0.162, 0.20, 0.13),
            "hint": "INDEX",
            "desc": "SHARP CRACK",
            "where": "LEFT",
        },
        {
            "id": "hat",
            "name": "HI-HAT",
            "emoji": "[^]",
            "color": (0.85, 0.75, 0.05, 0.88),
            "active_color": (1.0, 0.95, 0.4, 1.0),
            "finger": "Middle",
            "finger_idx": 2,
            "zone": (0.34, 0.51),
            "kind": "hat",
            "pos": (-0.72, 0.12),
            "radius": 0.17,
            "rx": 0.17, "rz": 0.055, "depth": 0.0,
            "hit": (-0.72, 0.106, 0.18, 0.08),
            "hint": "MIDDLE",
            "desc": "TIGHT TICK",
            "where": "FAR LEFT",
        },
        {
            "id": "tom",
            "name": "TOM",
            "emoji": "[#]",
            "color": (0.05, 0.80, 0.35, 0.88),
            "active_color": (0.3, 1.0, 0.6, 1.0),
            "finger": "Ring",
            "finger_idx": 3,
            "zone": (0.51, 0.68),
            "kind": "tom",
            "pos": (0.50, -0.10),
            "radius": 0.21,
            "rx": 0.21, "rz": 0.066, "depth": 0.13,
            "hit": (0.50, -0.172, 0.22, 0.145),
            "hint": "RING",
            "desc": "ROUND BOOM",
            "where": "RIGHT",
        },
        {
            "id": "crash",
            "name": "CRASH",
            "emoji": "[!]",
            "color": (1.0, 0.45, 0.1, 0.88),
            "active_color": (1.0, 0.75, 0.3, 1.0),
            "finger": "Thumb",
            "finger_idx": 0,
            "zone": (0.68, 0.84),
            "kind": "cymbal",
            "pos": (-0.46, 0.47),
            "radius": 0.23,
            "rx": 0.23, "rz": 0.075, "depth": 0.0,
            "hit": (-0.46, 0.463, 0.24, 0.09),
            "hint": "THUMB",
            "desc": "LOUD SPLASH",
            "where": "TOP LEFT",
        },
        {
            "id": "ride",
            "name": "RIDE",
            "emoji": "[+]",
            "color": (0.1, 0.75, 0.85, 0.88),
            "active_color": (0.4, 1.0, 0.95, 1.0),
            "finger": "All",
            "finger_idx": -1,
            "zone": (0.84, 1.00),
            "kind": "cymbal",
            "pos": (0.55, 0.45),
            "radius": 0.27,
            "rx": 0.27, "rz": 0.085, "depth": 0.0,
            "hit": (0.55, 0.443, 0.28, 0.10),
            "hint": "4 FINGERS",
            "desc": "STEADY SHIMMER",
            "where": "TOP RIGHT",
        },
    ]

    # Back-to-front painting order of the instruments (index -> draw layers)
    DRAW_ORDER = ("ride", "crash", "kick", "hat", "tom", "snare")

    # Map finger index -> which drum to prioritize
    FINGER_DRUM = {
        1: "snare",   # index
        2: "hat",     # middle
        3: "tom",     # ring
        4: "kick",    # pinky
        0: "crash",   # thumb
    }

    # ---- Workstation palette (shared look with the Piano Studio) ----
    CYAN = (0.30, 0.95, 1.0)
    CYAN_DIM = (0.35, 0.70, 0.95)
    GOLD = (0.85, 0.70, 0.25)
    WHITE = (0.93, 0.97, 1.0)
    GREY = (0.62, 0.70, 0.80)
    BLUE_TRIM = (0.10, 0.45, 0.75)

    # ---- Panel geometry (identical placement to the Piano side docks) ----
    LEFT_X = -1.35
    RIGHT_X = 1.35
    PANEL_HW = 0.36
    PANEL_BOTTOM = -0.70
    PANEL_TOP = 0.66

    FLOOR_Z = -0.60

    # ---- Stage 2: hand interaction tuning ----
    LEGACY_POSE_MODE = False    # True = old "raise a finger" triggering (Stage 1)
    SWAP_HAND_COLORS = False    # True if cyan/pink look reversed on your camera
    LEFT_COLOR = (0.25, 0.85, 1.00)     # cyan
    RIGHT_COLOR = (1.00, 0.30, 0.85)    # magenta / pink

    CURSOR_GAIN = 1.0           # keep >= 1.0 so drum zones never meet the HOME area
    FRAME_ASPECT = 4.0 / 3.0    # main.py opens the camera at 320x240
    PINCH_ON = 0.38             # pinch closes below this (relative to palm size)
    PINCH_OFF = 0.50            # pinch opens above this (hysteresis)
    HIT_COOLDOWN = 0.10         # seconds, per hand
    LOOKBACK = 0.10             # seconds: where the cursor was before the pinch closed
    LOOKBACK_STILL = 0.06       # use that earlier spot only if the hand was this still
    SMOOTH_MIN = 0.35           # cursor smoothing at rest (lower = smoother)
    SMOOTH_GAIN = 3.5           # how quickly smoothing relaxes when moving fast
    HAND_MEMORY = 0.6           # seconds a hand's identity is remembered
    LOSS_GRACE = 0.30           # seconds a cursor survives a tracking dropout
    HIT_MARGIN_DRUM = 0.010     # forgiveness around drums (screen units)
    HIT_MARGIN_CYMBAL = 0.022   # thin cymbals get a bit more
    HOVER_STICKY = 0.018        # extra edge hold so highlights don't flicker

    # ---- Stage 3: settings defaults ----
    DEFAULT_PLAY_MODE = "AIR"          # "AIR" or "PINCH"
    DEFAULT_SENSITIVITY = "NORMAL"     # "LOW" / "NORMAL" / "HIGH"
    DEFAULT_TEMPO = 100
    TEMPO_MIN = 60
    TEMPO_MAX = 180
    TEMPO_STEP = 5
    BEATS_PER_BAR = 4                  # metronome accents beat 1 of every 4

    # ---- Stage 3: AIR MODE tuning (INITIAL ESTIMATES - calibrate on your camera) ----
    # Units are aspect2d units: the camera image height is 2.0 units, so
    # 0.05 units is about 2.5 % of the image height.
    #   dist  : minimum downward travel inside AIR_WINDOW for a hit
    #   speed : minimum downward speed (units / second)
    #   rise  : upward travel needed to re-arm after a hit on the same drum
    # LOW sensitivity needs a bigger / faster tap, HIGH reacts to a smaller one.
    AIR_PROFILES = {
        "LOW":    {"dist": 0.075, "speed": 0.80, "rise": 0.030},
        "NORMAL": {"dist": 0.050, "speed": 0.50, "rise": 0.020},
        "HIGH":   {"dist": 0.032, "speed": 0.32, "rise": 0.014},
    }
    AIR_WINDOW = 0.12            # seconds of finger history examined for a tap
    AIR_MIN_DT = 0.03            # ignore stroke samples closer than this (noise)
    AIR_COOLDOWN = 0.12          # seconds between AIR hits of the same hand
    AIR_ARRIVAL_GUARD = 0.15     # a hand that just appeared cannot hit yet
    AIR_DEBUG = False            # True = print tap measurements to the console (calibration)
    AIR_DOWN_DOMINANCE = 0.70    # downward travel must be >= this * sideways travel

    UI_CLICK_COOLDOWN = 0.50     # seconds between pinch-presses of buttons

    def __init__(self, base, sound_manager):
        self.base = base
        self.sound_manager = sound_manager
        self._alive = True
        self._visible = False

        self.last_drum = None
        self.last_time = 0
        self.cooldown = 0.18
        self.pulse_phase = 0.0
        self.hit_timers = {}     # pad_id -> last hit time
        self.hit_intensity = {}  # pad_id -> 0.0-1.0

        # Beat counter
        self.beat_count = 0
        self.beat_times = []
        self.bpm = 0

        # Legacy shockwave state (kept for compatibility)
        self.shockwave_pad = None
        self.shockwave_phase = 0.0

        # Session / visual state
        self.pad_counts = {p["id"]: 0 for p in self.PADS}
        self.pad_levels = {p["id"]: 0.0 for p in self.PADS}
        self.history = []                      # most recent pad ids (max 8)
        self.last_hit_id = None
        self.last_color = self.CYAN
        self.last_hit_time = -999.0
        self.accent_bar = None
        self._accent_active = False
        self.pad_parts = {}
        self._buttons = []
        self._text_cache = {}
        self._hist_cells = []
        self._pad_layers = {}
        self._slots = {}
        self._hover_state = {}
        self._input_key = None
        self._shapes = {}
        self._margins = {}

        # ---- Stage 3 settings state ----
        self.play_mode = self.DEFAULT_PLAY_MODE
        self.sensitivity = self.DEFAULT_SENSITIVITY
        self.fx_enabled = True
        self.metro_on = False
        self.tempo = self.DEFAULT_TEMPO
        self._metro_next = 0.0
        self._metro_last = -999.0
        self._metro_beat = 0
        self._metro_flash_t = -999.0
        self._metro_flash_accent = False
        self._metro_lamp_key = None
        self._metro_sounds = (None, None)     # (accent click, normal click)
        self._ui_targets = []                 # pinch-pressable buttons
        self._seg = {}                        # key -> {"btn", "lbl"}
        self._last_ui_click = -999.0
        self._build_click_sounds()

        # Kept so main.py / show() / cleanup() keep working. It is an empty
        # node now: the spinning 3D rings and grid were removed on purpose
        # (no background animation, less distraction, less load).
        self._build_drum_3d_world()

        # 2D workstation: plain node root (no full-screen GUI region, so the
        # HOME button owned by main.py always receives clicks).
        self.frame = self.base.aspect2d.attachNewNode("DrumStudioRoot")
        self._layers = {}
        # Pad layers are created on demand with orders 8 .. 55 (see _pad_layer).
        for name, order in (
            ("floor", 2), ("platform", 3), ("shadow", 4), ("panel", 5),
            ("stand", 6), ("glow", 7),
            ("rows", 60), ("rows2", 62), ("ctrl", 64), ("text", 80), ("cursor", 85),
        ):
            layer = self.frame.attachNewNode("DrumLayer_" + name)
            layer.setBin("fixed", order)   # stays below main.py's HOME button (bin 90)
            self._layers[name] = layer

        self._build_console()
        self._build_kit()
        self._build_hit_shapes()
        self._init_slots()
        self._build_cursors()
        self._build_left_panel()
        self._build_right_panel()
        self._build_settings_dock()
        self._refresh_stats()
        self._refresh_volume()
        self._refresh_audio_status()
        self._refresh_settings_ui()

        if hasattr(self.base, "accept"):
            self.base.accept("mouse1", self._on_mouse_click)

        self.base.taskMgr.add(self._animate, "DrumsAnimation")
        self.base.taskMgr.add(self._metro_tick, "DrumsMetronome")
        self.hide()

    # ====================================================
    # GENERIC UI BUILDERS
    # ====================================================

    def _pad_layer(self, index, sub):
        """One draw layer per (instrument, part). Distinct fixed-bin orders
        make the painting order of overlapping parts deterministic."""
        key = (index, sub)
        node = self._pad_layers.get(key)
        if node is None:
            node = self.frame.attachNewNode("DrumPad_%d_%d" % (index, sub))
            node.setBin("fixed", 8 + index * 8 + sub)
            self._pad_layers[key] = node
        return node

    def _card(self, layer, left, right, bottom, top, color):
        cm = CardMaker("DrumCard")
        cm.setFrame(left, right, bottom, top)
        node = self._layers[layer].attachNewNode(cm.generate())
        node.setColor(color[0], color[1], color[2], color[3])
        node.setTransparency(TransparencyAttrib.MAlpha)
        return node

    def _line_node(self, parent, segs, color, thickness, ox=0.0, oz=0.0):
        """Several line segments [((x1,z1),(x2,z2)), ...] in one node."""
        ls = LineSegs()
        ls.setThickness(thickness)
        ls.setColor(color[0], color[1], color[2], color[3])
        for (x1, z1), (x2, z2) in segs:
            ls.moveTo(Point3(x1, 0, z1))
            ls.drawTo(Point3(x2, 0, z2))
        node = parent.attachNewNode(ls.create())
        node.setPos(ox, 0, oz)
        node.setTransparency(TransparencyAttrib.MAlpha)
        return node

    def _label(self, text, x, z, scale, color, align=TextNode.ACenter):
        """Text label centred vertically on z. Always drawn above everything."""
        lbl = DirectLabel(
            parent=self._layers["text"],
            text=text,
            pos=(x, 0, z - scale * 0.30),
            scale=scale,
            text_fg=Vec4(color[0], color[1], color[2], color[3] if len(color) > 3 else 1.0),
            text_align=align,
            text_shadow=(0.0, 0.0, 0.02, 0.9),
            frameColor=(0, 0, 0, 0),
            relief=None,
            state=DGG.DISABLED,
        )
        self._text_cache[id(lbl)] = text
        return lbl

    def _set_text(self, lbl, text):
        if self._text_cache.get(id(lbl)) != text:
            self._text_cache[id(lbl)] = text
            lbl["text"] = text

    def _register_ui(self, x, z, half_w, half_h, command, extra):
        """Remember a button's screen rectangle so a hand pinch can press it
        exactly like a mouse click (see _ui_click)."""
        self._ui_targets.append({
            "x": x, "z": z, "hw": half_w, "hh": half_h,
            "cmd": command, "args": list(extra or []),
        })

    def _button(self, x, z, half_w, half_h, text, text_scale, color, command, extra=None):
        hover = (min(1.0, color[0] + 0.12), min(1.0, color[1] + 0.12), min(1.0, color[2] + 0.12), 1.0)
        press = (color[0] * 0.65, color[1] * 0.65, color[2] * 0.65, 1.0)
        base_c = (color[0], color[1], color[2], 1.0)

        # cyan outline sits just below the button face
        self._card("rows2", x - half_w - 0.004, x + half_w + 0.004,
                   z - half_h - 0.004, z + half_h + 0.004,
                   (self.CYAN[0], self.CYAN[1], self.CYAN[2], 0.55))

        btn = DirectButton(
            parent=self._layers["ctrl"],
            text="",
            pos=(x, 0, z),
            frameSize=(-half_w, half_w, -half_h, half_h),
            frameColor=(base_c, press, hover, base_c),
            relief=DGG.FLAT,
            command=command,
            extraArgs=extra or [],
        )
        self._buttons.append(btn)
        self._label(text, x, z, text_scale, (0.92, 0.98, 1.0, 1.0))
        self._register_ui(x, z, half_w, half_h, command, extra)
        return btn

    def _seg_button(self, key, x, z, half_w, half_h, text, text_scale, command, extra=None):
        """Settings button whose colour shows its state (see _paint)."""
        self._card("rows2", x - half_w - 0.003, x + half_w + 0.003,
                   z - half_h - 0.003, z + half_h + 0.003, (0.30, 0.42, 0.58, 0.55))
        btn = DirectButton(
            parent=self._layers["ctrl"],
            text="",
            pos=(x, 0, z),
            frameSize=(-half_w, half_w, -half_h, half_h),
            frameColor=(0.08, 0.10, 0.15, 1.0),
            relief=DGG.FLAT,
            command=command,
            extraArgs=extra or [],
        )
        self._buttons.append(btn)
        lbl = self._label(text, x, z, text_scale, (0.92, 0.98, 1.0, 1.0))
        self._seg[key] = {"btn": btn, "lbl": lbl}
        self._register_ui(x, z, half_w, half_h, command, extra)
        return btn

    def _paint(self, key, col, text_bright=True):
        """Colour a settings button (face + label) for its current state."""
        rec = self._seg[key]
        base_c = (col[0], col[1], col[2], 1.0)
        hover = (min(1.0, col[0] + 0.10), min(1.0, col[1] + 0.10), min(1.0, col[2] + 0.10), 1.0)
        press = (col[0] * 0.65, col[1] * 0.65, col[2] * 0.65, 1.0)
        rec["btn"]["frameColor"] = (base_c, press, hover, base_c)
        if text_bright:
            rec["lbl"]["text_fg"] = Vec4(0.95, 1.0, 1.0, 1.0)
        else:
            rec["lbl"]["text_fg"] = Vec4(0.60, 0.70, 0.80, 1.0)

    def _navigate_to(self, mode_name):
        """Safely navigate to another screen mode in HoloHand."""
        target_mode = mode_name.upper() if isinstance(mode_name, str) else mode_name
        if hasattr(self.base, "set_mode"):
            self.base.set_mode(target_mode)
        elif hasattr(self.base, "app") and hasattr(self.base.app, "set_mode"):
            self.base.app.set_mode(target_mode)
        else:
            print(f"[Drums] Mode navigation: {target_mode}")

    def _panel_chassis(self, cx, title):
        """Dark navy dock with cyan / gold trim, same style as Piano side docks."""
        left, right = cx - self.PANEL_HW, cx + self.PANEL_HW
        bot, top = self.PANEL_BOTTOM, self.PANEL_TOP
        self._card("panel", left, right, bot, top, (0.025, 0.035, 0.06, 0.92))
        self._card("panel", left + 0.008, right - 0.008, bot + 0.008, top - 0.008,
                   (0.065, 0.08, 0.115, 0.88))
        self._card("panel", left, right, top - 0.006, top, (0.0, 0.85, 1.0, 0.85))
        self._card("panel", left, right, bot, bot + 0.006, (0.85, 0.70, 0.25, 0.90))
        self._card("panel", left + 0.02, right - 0.02, 0.535, 0.539, (0.10, 0.45, 0.75, 0.75))

    # ====================================================
    # 3D WORLD (intentionally empty)
    # ====================================================

    def _build_drum_3d_world(self):
        self.drum_world = NodePath("DrumWorld")
        self.drum_world.reparentTo(self.base.render)

    # ====================================================
    # REALISTIC MUSIC RECORDING STUDIO ENVIRONMENT & CONSOLE
    # ====================================================

    def _build_studio_background(self):
        """Constructs a realistic, premium music recording studio environment.
        Features dark acoustic foam wall panels, subtle professional studio lighting,
        natural depth, and a dark studio floor behind the drum kit."""
        L = self._layers
        floor_layer = L["floor"]

        # 1. Main Studio Acoustic Wall (Deep matte charcoal backdrop)
        self._card("floor", -0.96, 0.96, -0.22, 0.98, (0.022, 0.025, 0.030, 0.98))

        # 2. Studio Acoustic Foam Soundproofing Panels (SIDE FLANKS ONLY - Left & Right)
        # Keeps center stage clear for optimal drum kit visibility and hand air-strikes
        side_flanks = [
            (-0.95, -0.65),  # Left side flank
            (0.65, 0.95)     # Right side flank
        ]

        tile_segs = []
        for flank_x0, flank_x1 in side_flanks:
            num_cols = 3
            num_rows = 5
            col_w = (flank_x1 - flank_x0) / num_cols
            row_h = (0.78 - (-0.20)) / num_rows
            pad_gap = 0.005

            for r in range(num_rows):
                t_z0 = -0.20 + r * row_h + pad_gap
                t_z1 = -0.20 + (r + 1) * row_h - pad_gap
                for c in range(num_cols):
                    t_x0 = flank_x0 + c * col_w + pad_gap
                    t_x1 = flank_x0 + (c + 1) * col_w - pad_gap

                    self._card("floor", t_x0, t_x1, t_z0, t_z1, (0.035, 0.038, 0.046, 0.90))

                    if (r + c) % 2 == 0:
                        mid_z = (t_z0 + t_z1) * 0.5
                        tile_segs.append(((t_x0 + 0.004, mid_z), (t_x1 - 0.004, mid_z)))
                    else:
                        mid_x = (t_x0 + t_x1) * 0.5
                        tile_segs.append(((mid_x, t_z0 + 0.004), (mid_x, t_z1 - 0.004)))

        if tile_segs:
            self._line_node(floor_layer, tile_segs, (0.055, 0.060, 0.072, 0.45), 1.0)

        # 3. Acoustic Wood Diffuser Side Accents (Natural walnut slats at wall borders)
        slat_segs = []
        for side in (-1.0, 1.0):
            bx0 = side * 0.83 if side > 0 else -0.96
            bx1 = side * 0.96 if side > 0 else -0.83
            self._card("floor", min(bx0, bx1), max(bx0, bx1), -0.22, 0.78, (0.018, 0.020, 0.025, 0.95))
            for i in range(5):
                sx = min(bx0, bx1) + i * 0.024 + 0.006
                slat_segs.append(((sx, -0.21), (sx, 0.77)))
        if slat_segs:
            self._line_node(floor_layer, slat_segs, (0.13, 0.09, 0.06, 0.55), 2.5)

        # 4. Realistic Dark Studio Floor (z: -0.72 to -0.22)
        # Deep dark studio floor deck
        self._card("floor", -0.96, 0.96, -0.72, -0.22, (0.018, 0.020, 0.024, 0.98))

        # Baseboard runner connecting wall and floor
        self._card("floor", -0.96, 0.96, -0.228, -0.220, (0.045, 0.050, 0.060, 0.95))
        self._card("floor", -0.96, 0.96, -0.220, -0.217, (0.075, 0.082, 0.095, 0.75))

        # Subtle natural floor plank seams
        floor_lines = [
            ((-0.96, -0.32), (0.96, -0.32)),
            ((-0.96, -0.43), (0.96, -0.43)),
            ((-0.96, -0.55), (0.96, -0.55)),
            ((-0.96, -0.68), (0.96, -0.68)),
        ]
        self._line_node(floor_layer, floor_lines, (0.012, 0.014, 0.018, 0.65), 1.5)

        # 5. Soft Professional Studio Lighting (Warm key light behind the drum kit)
        key_light = _disc_geom(0.78, 48, 0.09, 0.0, 1.0, 0.0)
        key_light.reparentTo(floor_layer)
        key_light.setPos(0.0, 0, 0.08)
        key_light.setScale(1.10, 1.0, 0.60)
        key_light.setColorScale(0.95, 0.88, 0.72, 1.0)
        _make_additive(key_light)

        # Subtle ambient fill glow
        fill_light = _disc_geom(0.95, 48, 0.04, 0.0, 1.0, 0.0)
        fill_light.reparentTo(floor_layer)
        fill_light.setPos(0.0, 0, -0.05)
        fill_light.setScale(1.0, 1.0, 0.40)
        fill_light.setColorScale(0.55, 0.70, 0.90, 1.0)
        _make_additive(fill_light)

    def _build_background_hologram(self):
        """Compatibility alias: builds the realistic studio background."""
        self._build_studio_background()

    def _build_console(self):
        # 1. Realistic recording studio environment
        self._build_studio_background()

        # Subtle console border outline
        for (l, r, b, t) in (
            (-0.96, 0.96, 0.976, 0.980),
            (-0.96, -0.954, -0.72, 0.980),
            (0.954, 0.96, -0.72, 0.980),
        ):
            self._card("floor", l, r, b, t, (0.08, 0.18, 0.30, 0.55))

        # ====================================================
        # TOP FEATURE CONTROL PODS (Dedicated, well-spaced compartments)
        # ====================================================

        # POD 1: PLAY MODE & SENSITIVITY (x: -0.94 to -0.36, z: 0.800 to 0.970)
        self._card("panel", -0.94, -0.36, 0.800, 0.970, (0.025, 0.035, 0.06, 0.92))
        self._card("panel", -0.94, -0.36, 0.966, 0.970, (0.0, 0.85, 1.0, 0.90))
        self._card("panel", -0.94, -0.36, 0.880, 0.883, (0.08, 0.22, 0.40, 0.60))

        # Mode row (top) - prominent font size as requested
        self._label("MODE:", -0.89, 0.925, 0.024, self.GOLD, TextNode.ALeft)
        self.mode_value = self._label("AIR MODE", -0.80, 0.925, 0.046, self.CYAN, TextNode.ALeft)
        self._seg_button("air", -0.52, 0.925, 0.045, 0.020, "AIR", 0.022, self.set_play_mode, ["AIR"])
        self._seg_button("pinch", -0.42, 0.925, 0.050, 0.020, "PINCH", 0.022, self.set_play_mode, ["PINCH"])

        # Sensitivity row (bottom)
        self._label("SENSITIVITY", -0.89, 0.840, 0.020, (0.60, 0.75, 0.90, 1.0), TextNode.ALeft)
        self._seg_button("sens_LOW", -0.66, 0.840, 0.038, 0.018, "LOW", 0.019, self.set_sensitivity, ["LOW"])
        self._seg_button("sens_NORMAL", -0.56, 0.840, 0.050, 0.018, "NORMAL", 0.019, self.set_sensitivity, ["NORMAL"])
        self._seg_button("sens_HIGH", -0.45, 0.840, 0.040, 0.018, "HIGH", 0.019, self.set_sensitivity, ["HIGH"])

        # POD 2: STUDIO BRANDING & CORE NAVIGATION (x: -0.34 to 0.06, z: 0.800 to 0.970)
        self._card("panel", -0.34, 0.06, 0.800, 0.970, (0.02, 0.03, 0.055, 0.92))
        self._card("panel", -0.34, 0.06, 0.966, 0.970, (0.0, 0.85, 1.0, 0.90))
        self._card("panel", -0.34, 0.06, 0.880, 0.883, (0.08, 0.22, 0.40, 0.60))

        # Branding
        self._label("HOLOHAND  AI", -0.14, 0.932, 0.038, self.WHITE)
        self._label("DRUM STUDIO", -0.14, 0.898, 0.022, (0.35, 0.78, 1.0, 1.0))
        # Navigation & Reset buttons
        self._button(-0.25, 0.840, 0.055, 0.019, "HOME", 0.020, (0.12, 0.16, 0.24), self._navigate_to, ["HOME"])
        self._seg_button("reset_cfg", -0.05, 0.840, 0.075, 0.019, "RESET ALL", 0.019, self.reset_settings)

        # POD 3: METRONOME & VISUAL EFFECTS (x: 0.08 to 0.94, z: 0.800 to 0.970)
        self._card("panel", 0.08, 0.94, 0.800, 0.970, (0.025, 0.035, 0.06, 0.92))
        self._card("panel", 0.08, 0.94, 0.966, 0.970, (0.85, 0.70, 0.25, 0.90))
        self._card("panel", 0.08, 0.94, 0.880, 0.883, (0.08, 0.22, 0.40, 0.60))

        # Metronome row (top)
        self._seg_button("metro", 0.22, 0.925, 0.075, 0.020, "METRONOME", 0.020, self.toggle_metronome)
        # Metronome indicator lamp
        self.metro_lamp = self._card("rows", 0.315, 0.335, 0.913, 0.937, (0.10, 0.12, 0.16, 0.85))
        # Tempo controls
        self._seg_button("tempo_dn", 0.40, 0.925, 0.028, 0.020, "-", 0.024, self.adjust_tempo, [-self.TEMPO_STEP])
        self.tempo_value = self._label(f"{self.tempo} BPM", 0.50, 0.925, 0.025, self.WHITE)
        self._seg_button("tempo_up", 0.60, 0.925, 0.028, 0.020, "+", 0.024, self.adjust_tempo, [self.TEMPO_STEP])
        self.metro_value = self._label("OFF", 0.76, 0.925, 0.026, self.GREY)

        # Visual Effects & Audio Status row (bottom)
        self._seg_button("fx", 0.22, 0.840, 0.065, 0.018, "EFFECTS", 0.019, self.toggle_effects)
        self._label("DYNAMIC HOLOGRAPHIC RIG", 0.60, 0.840, 0.020, (0.40, 0.75, 1.0, 0.85))

        # Status strip: INPUT | LAST HIT | AUDIO
        self._card("panel", -0.94, 0.94, 0.685, 0.778, (0.035, 0.045, 0.065, 0.84))

        self._label("INPUT", -0.62, 0.750, 0.024, self.GREY)
        self.input_value = self._label("SHOW YOUR HANDS", -0.62, 0.710, 0.032, self.GREY)

        self._card("rows", -0.27, 0.27, 0.692, 0.771, (0.0, 0.04, 0.08, 0.92))
        self.accent_bar = self._card("rows", -0.27, 0.27, 0.692, 0.696, (0.0, 0.85, 1.0, 0.80))
        self._label("LAST HIT", 0.0, 0.757, 0.022, self.GREY)
        self.feedback_display = self._label("READY", 0.0, 0.719, 0.052, self.CYAN)

        self._label("AUDIO", 0.62, 0.750, 0.024, self.GREY)
        self.audio_value = self._label("READY", 0.62, 0.710, 0.036, (0.3, 1.0, 0.5, 1.0))

        # Bottom trim runners (blue + gold, as on the Piano chassis)
        self._card("rows", -0.94, 0.94, -0.700, -0.694, (0.10, 0.45, 0.75, 0.90))
        self._card("rows", -0.94, 0.94, -0.711, -0.708, (0.85, 0.70, 0.25, 0.90))

    # ====================================================
    # THE DRUM KIT
    # ====================================================

    def _build_kit(self):
        L = self._layers

        # Professional studio drum rug / non-slip stage mat
        plat = _disc_geom(1.0, 64, 0.90, 0.75)
        plat.reparentTo(L["platform"])
        plat.setPos(0.0, 0, self.FLOOR_Z - 0.012)
        plat.setScale(0.92, 1.0, 0.080)
        plat.setColorScale(0.065, 0.070, 0.078, 0.96)

        # Clean stitched rug border trim (matte dark charcoal, no artificial glow)
        edge = _ring_geom(0.975, 1.0, 72)
        edge.reparentTo(L["platform"])
        edge.setPos(0.0, 0, self.FLOOR_Z - 0.012)
        edge.setScale(0.92, 1.0, 0.080)
        edge.setColorScale(0.12, 0.13, 0.15, 0.85)

        # Hardware first (it sits behind the instruments), then the pads.
        for pad in self.PADS:
            self._build_hardware(pad)
        for pad in self.PADS:
            self._build_pad(pad)

    def _build_hardware(self, pad):
        """Stands, legs, spurs and the floor shadow under one instrument."""
        L = self._layers
        pid = pad["id"]
        x, z = pad["pos"]
        rx, rz, depth = pad["rx"], pad["rz"], pad["depth"]
        fz = self.FLOOR_Z
        steel = (0.62, 0.72, 0.85, 0.50)
        segs = []
        shadow_w = 0.15

        if pid in ("crash", "ride"):
            segs += [
                ((x, z - 0.016), (x, fz)),
                ((x, fz + 0.17), (x - 0.12, fz)),
                ((x, fz + 0.17), (x + 0.12, fz)),
            ]
        elif pid == "hat":
            segs += [
                ((x, z - 0.03), (x, fz)),
                ((x, fz + 0.16), (x - 0.11, fz)),
                ((x, fz + 0.16), (x + 0.11, fz)),
                # foot pedal
                ((x + 0.03, fz + 0.016), (x + 0.21, fz + 0.004)),
            ]
        elif pid == "snare":
            y0 = z - depth - rz - 0.014
            segs += [
                ((x, y0), (x, fz)),
                ((x, fz + 0.14), (x - 0.13, fz)),
                ((x, fz + 0.14), (x + 0.13, fz)),
                ((x - rx * 0.5, y0), (x + rx * 0.5, y0)),     # basket
            ]
        elif pid == "tom":
            ys = z - depth - rz * 0.69 - 0.01
            for sgn in (-1.0, 1.0):
                segs.append(((x + sgn * rx * 0.72, ys), (x + sgn * rx * 0.82, fz)))
            shadow_w = rx * 0.95
        elif pid == "kick":
            for sgn in (-1.0, 1.0):
                segs.append(((x + sgn * rx * 0.80, z - rx * 0.60), (x + sgn * rx * 1.22, fz)))
            shadow_w = rx * 1.0

        if segs:
            self._line_node(L["stand"], segs, steel, 3.0)

        shadow = _disc_geom(1.0, 32, 0.55, 0.0)
        shadow.reparentTo(L["shadow"])
        shadow.setPos(x, 0, fz - 0.004)
        shadow.setScale(shadow_w, 1.0, 0.022)
        shadow.setColorScale(0.0, 0.01, 0.03, 0.9)

    def _build_pad(self, pad):
        L = self._layers
        pid = pad["id"]
        index = self.DRAW_ORDER.index(pid)
        x, z = pad["pos"]
        rx, rz, depth = pad["rx"], pad["rz"], pad["depth"]
        kind = pad["kind"]
        col = pad["color"][:3]
        act = pad["active_color"][:3]

        # Drum heads are deeper / darker; cymbals are brighter (metal).
        if kind == "cymbal" or kind == "hat":
            body_base = (col[0] * 0.80, col[1] * 0.80, col[2] * 0.80)
            rim_base = (min(1.0, col[0] * 1.25 + 0.12),
                        min(1.0, col[1] * 1.25 + 0.12),
                        min(1.0, col[2] * 1.25 + 0.12))
        else:
            body_base = (col[0] * 0.62, col[1] * 0.62, col[2] * 0.62)
            rim_base = (min(1.0, col[0] * 1.15 + 0.10),
                        min(1.0, col[1] * 1.15 + 0.10),
                        min(1.0, col[2] * 1.15 + 0.10))

        move = []   # (node, offset_x, offset_z, scale_x, scale_z) relative to pad

        def add(np_, sub, ox, oz, sx, sz, color=None):
            np_.reparentTo(self._pad_layer(index, sub))
            np_.setPos(x + ox, 0, z + oz)
            np_.setScale(sx, 1.0, sz)
            if color is not None:
                np_.setColorScale(color[0], color[1], color[2],
                                  color[3] if len(color) > 3 else 1.0)
            move.append((np_, ox, oz, sx, sz))
            return np_

        def add_lines(sub, segs, color, thickness):
            node = self._line_node(self._pad_layer(index, sub), segs, color, thickness, x, z)
            move.append((node, 0.0, 0.0, 1.0, 1.0))
            return node

        def add_specular(sub, ox, oz, sx, sz, alpha):
            spec = _disc_geom(1.0, 28, alpha, 0.0)
            _make_additive(spec)
            add(spec, sub, ox, oz, sx, sz, (1.0, 1.0, 1.0, 1.0))

        body = None
        rim = None

        # ---------------- SNARE / TOM: a drum with a visible shell ----------------
        if kind in ("snare", "tom"):
            shell_c = (col[0] * 0.42, col[1] * 0.42, col[2] * 0.42, 1.0)
            hoop_c = (rim_base[0], rim_base[1], rim_base[2], 1.0)
            hoop_h = 0.014

            add(_band_geom(rx, rz, -hoop_h, -depth), 0, 0.0, 0.0, 1.0, 1.0, shell_c)   # shell wall
            add(_band_geom(rx, rz, 0.0, -hoop_h), 1, 0.0, 0.0, 1.0, 1.0, hoop_c)       # top hoop face
            add(_band_geom(rx, rz, -depth, -depth - hoop_h), 1, 0.0, 0.0, 1.0, 1.0, hoop_c)  # bottom hoop

            body = add(_disc_geom(1.0, 48, 0.72, 0.88, 1.0, 0.78), 2, 0.0, 0.0,
                       rx * 0.93, rz * 0.93, body_base)
            add(_ring_geom(0.55, 0.575, 48, 0.30, 0.30), 3, 0.0, 0.0,
                rx * 0.93, rz * 0.93, (1.0, 1.0, 1.0, 1.0))
            rim = add(_ring_geom(0.90, 1.0, 64), 4, 0.0, 0.0, rx, rz, rim_base)
            add_specular(6, -rx * 0.30, rz * 0.25, rx * 0.42, rz * 0.24, 0.16)

            # tension lugs on the front of the shell
            lugs = 8 if kind == "snare" else 6
            segs = []
            for i in range(lugs):
                a = math.pi + 0.45 + (i / (lugs - 1)) * (math.pi - 0.90)
                lx = math.cos(a) * rx * 0.96
                lz = math.sin(a) * rz - hoop_h
                segs.append(((lx, lz - 0.016), (lx, lz - depth + 0.018)))
            add_lines(5, segs, (0.92, 0.96, 1.0, 0.80), 3.0)

            name_size = 0.036 if kind == "snare" else 0.038
            self._label(pad["name"], x, z + 0.004, name_size, (1.0, 1.0, 1.0, 1.0))

        # ---------------- KICK: big front-facing bass drum ----------------
        elif kind == "kick":
            r = rx
            body = add(_disc_geom(1.0, 56, 0.72, 0.88, 1.0, 0.78), 2, 0.0, 0.0,
                       r * 0.90, r * 0.90, body_base)
            add(_ring_geom(0.50, 0.515, 56, 0.30, 0.30), 3, 0.0, 0.0, r, r, (1.0, 1.0, 1.0, 1.0))
            add(_disc_geom(1.0, 28, 0.85, 0.85, 1.0, 1.0), 3, 0.0, -r * 0.52,
                r * 0.12, r * 0.12, (0.02, 0.03, 0.06, 1.0))                # beater port
            rim = add(_ring_geom(0.90, 1.0, 72), 4, 0.0, 0.0, r, r, rim_base)

            segs = []
            for i in range(10):
                a = (i / 10.0) * math.pi * 2.0 + 0.15
                segs.append(((math.cos(a) * r * 0.90, math.sin(a) * r * 0.90),
                             (math.cos(a) * r * 0.99, math.sin(a) * r * 0.99)))
            add_lines(5, segs, (0.03, 0.04, 0.08, 0.85), 3.0)
            add_specular(6, -r * 0.28, r * 0.32, r * 0.50, r * 0.28, 0.14)

            self._label(pad["name"], x, z + 0.004, 0.048, (1.0, 1.0, 1.0, 1.0))

        # ---------------- CYMBALS and HI-HAT ----------------
        else:
            def cymbal(oz, crx, crz, bright, with_bell, bell_w, n_rings, subs):
                s_band, s_body, s_ring, s_rim, s_bell, s_spec = subs
                thick_c = (col[0] * 0.50 * bright, col[1] * 0.50 * bright,
                           col[2] * 0.50 * bright, 1.0)
                body_c = (body_base[0] * bright, body_base[1] * bright,
                          body_base[2] * bright, 1.0)
                add(_band_geom(crx, crz, 0.0, -0.014), s_band, 0.0, oz, 1.0, 1.0, thick_c)
                cb = add(_disc_geom(1.0, 56, 0.70, 0.88, 0.80, 1.0), s_body, 0.0, oz,
                         crx, crz, body_c)
                cr = None
                if n_rings:
                    for f in (0.82, 0.64, 0.46)[:n_rings]:
                        add(_ring_geom(f - 0.012, f + 0.012, 56, 0.30, 0.30), s_ring, 0.0, oz,
                            crx, crz, (1.0, 1.0, 1.0, 1.0))
                    cr = add(_ring_geom(0.94, 1.0, 64), s_rim, 0.0, oz, crx, crz, rim_base)
                if with_bell:
                    bell_c = (min(1.0, body_base[0] * 1.30 + 0.08),
                              min(1.0, body_base[1] * 1.30 + 0.08),
                              min(1.0, body_base[2] * 1.30 + 0.08), 1.0)
                    add(_disc_geom(1.0, 32, 0.95, 0.80, 1.0, 0.80), s_bell,
                        0.0, oz + crz * 0.42, crx * bell_w, crz * 0.30, bell_c)
                if n_rings:
                    add_specular(s_spec, -crx * 0.35, oz + crz * 0.15, crx * 0.35, crz * 0.25, 0.12)
                return cb, cr

            if kind == "hat":
                # bottom cymbal peeks out under the top one
                cymbal(-0.034, rx * 0.98, rz, 0.55, False, 0.0, 0, (0, 0, 0, 0, 0, 0))
                body, rim = cymbal(0.0, rx, rz, 1.0, False, 0.0, 2, (1, 2, 3, 4, 5, 6))
                self._label(pad["name"], x, z + 0.002, 0.030, (1.0, 1.0, 1.0, 1.0))
            else:
                is_ride = (pid == "ride")
                body, rim = cymbal(0.0, rx, rz, 1.0, True, 0.26 if is_ride else 0.20,
                                   3, (1, 2, 3, 4, 5, 6))
                self._label(pad["name"], x, z - 0.016, 0.036, (1.0, 1.0, 1.0, 1.0))

        # ---------------- hit effects (hidden until a hit) ----------------
        hx = rx * 1.55
        hz = hx if kind == "kick" else rz * 1.9 + depth * 0.8 + 0.02
        halo = _disc_geom(1.0, 40, 0.6, 0.0)
        halo.reparentTo(L["glow"])
        halo.setPos(x, 0, z - depth * 0.5)
        halo.setScale(hx, 1.0, hz)
        _make_additive(halo)
        halo.hide()

        flash = _disc_geom(1.0, 48, 1.0, 0.30)
        flash.reparentTo(self._pad_layer(index, 7))
        flash.setPos(x, 0, z)
        flash.setScale(rx, 1.0, rz)
        _make_additive(flash)
        flash.hide()

        shock = _ring_geom(0.93, 1.0, 64, 0.0, 1.0)
        shock.reparentTo(self._pad_layer(index, 7))
        shock.setPos(x, 0, z)
        shock.setScale(rx, 1.0, rz)
        _make_additive(shock)
        shock.hide()

        # hover highlight (shown while a cursor is over this instrument)
        hover_root = self._pad_layer(index, 7).attachNewNode("DrumHover")
        hover_root.setPos(x, 0, z)
        hv_ring = _ring_geom(0.90, 1.08, 64)
        hv_ring.reparentTo(hover_root)
        hv_ring.setScale(rx * 1.03, 1.0, rz * 1.03)
        _make_additive(hv_ring)
        hv_fill = _disc_geom(1.0, 48, 0.22, 0.22)
        hv_fill.reparentTo(hover_root)
        hv_fill.setScale(rx * 0.97, 1.0, rz * 0.97)
        _make_additive(hv_fill)
        if depth > 0:
            hv_shell = _band_geom(rx, rz, -0.014, -depth, 40, 0.30)
            hv_shell.reparentTo(hover_root)
            _make_additive(hv_shell)
        hover_root.hide()

        if kind == "cymbal":
            motion = "shake"
        elif kind == "hat":
            motion = "hat"
        elif kind == "kick":
            motion = "kick"
        else:
            motion = "press"

        self.pad_parts[pid] = {
            "col": col,
            "act": act,
            "body_base": body_base,
            "rim_base": rim_base,
            "halo": halo,
            "halo_on": False,
            "body": body,
            "rim": rim,
            "flash": flash,
            "flash_on": False,
            "shock": shock,
            "shock_on": False,
            "hover": hover_root,
            "hover_on": False,
            "move": move,
            "motion": motion,
            "x": x,
            "z": z,
            "rx": rx,
            "rz": rz,
            "radius": pad["radius"],
            "active": False,
        }

    # ====================================================
    # LEFT PANEL: DRUM GUIDE
    # ====================================================

    def _build_left_panel(self):
        cx = self.LEFT_X
        self._panel_chassis(cx, "DRUM GUIDE")

        # No HOME button here on purpose: main.py already shows exactly one
        # (bottom centre, mouse + pinch).
        self._label("DRUM GUIDE", cx, 0.595, 0.040, self.WHITE)
        self._label("WHAT EACH DRUM DOES", cx, 0.500, 0.026, self.CYAN)

        row_h = 0.052
        z0 = 0.395
        pitch = 0.125
        for i, pad in enumerate(self.PADS):
            z = z0 - i * pitch
            col = pad["color"][:3]
            base = (col[0] * 0.62, col[1] * 0.62, col[2] * 0.62, 0.92)

            card = self._card("rows", cx - 0.32, cx + 0.32, z - row_h, z + row_h, base)
            self._card("rows2", cx - 0.32, cx - 0.30, z - row_h, z + row_h,
                       (min(1.0, col[0] + 0.2), min(1.0, col[1] + 0.2), min(1.0, col[2] + 0.2), 1.0))
            dot = self._card("rows2", cx + 0.275, cx + 0.305, z + 0.010, z + 0.040, (1.0, 1.0, 1.0, 0.25))

            self._label(pad["name"], cx - 0.28, z + 0.017, 0.038, (1.0, 1.0, 1.0, 1.0), TextNode.ALeft)
            self._label(pad["desc"], cx - 0.28, z - 0.027, 0.021, (0.92, 0.97, 1.0, 0.90), TextNode.ALeft)
            self._label(pad["where"], cx + 0.305, z - 0.022, 0.022, (1.0, 1.0, 1.0, 1.0), TextNode.ARight)

            parts = self.pad_parts[pad["id"]]
            parts["row_card"] = card
            parts["row_base"] = base
            parts["row_dot"] = dot

        # Hidden HOW-TO labels (kept for internal logic but invisible)
        hint = (0, 0, 0, 0)  # fully transparent
        # index 0 – original instructional text (kept invisible)
        lbl0 = self._label("POINT WITH YOUR INDEX FINGER", cx, -0.415, 0.025, hint)
        lbl1 = self._label("", cx, -0.455, 0.025, hint)
        lbl2 = self._label("", cx, -0.495, 0.025, hint)
        # Store in self._howto to avoid AttributeError; labels are invisible
        self._howto = [lbl0, lbl1, lbl2]

    # ====================================================
    # RIGHT PANEL: PERFORMANCE
    # ====================================================

    def _build_right_panel(self):
        cx = self.RIGHT_X
        self._panel_chassis(cx, "PERFORMANCE")

        self._button(cx - 0.17, 0.60, 0.11, 0.034, "RESET", 0.030,
                     (0.30, 0.14, 0.16), self.reset_session)
        self._label("PERFORMANCE", cx + 0.12, 0.595, 0.036, self.WHITE)
        self._label("LIVE SESSION", cx, 0.500, 0.028, self.CYAN)

        # BPM + HITS cards
        for dx, caption in ((-0.165, "BPM"), (0.165, "TOTAL HITS")):
            self._card("rows", cx + dx - 0.15, cx + dx + 0.15, 0.285, 0.475, (0.0, 0.04, 0.08, 0.92))
            self._card("rows", cx + dx - 0.15, cx + dx + 0.15, 0.285, 0.289, (0.0, 0.85, 1.0, 0.8))
            self._label(caption, cx + dx, 0.440, 0.026, self.GREY)
        self.bpm_value = self._label("---", cx - 0.165, 0.360, 0.090, self.CYAN)
        self.hits_value = self._label("0", cx + 0.165, 0.360, 0.090, self.WHITE)

        # Hit meters
        self._label("HIT METERS", cx, 0.222, 0.030, self.GOLD)
        track_left = cx - 0.16
        track_w = 0.36
        for i, pad in enumerate(self.PADS):
            z = 0.150 - i * 0.075
            col = pad["color"][:3]
            self._label(pad["name"], cx - 0.33, z, 0.027, (0.90, 0.95, 1.0, 1.0), TextNode.ALeft)
            self._card("rows", track_left, track_left + track_w, z - 0.015, z + 0.015, (0.01, 0.02, 0.04, 0.95))
            fill = self._card("rows2", 0.0, track_w, -0.015, 0.015, (col[0], col[1], col[2], 0.95))
            fill.setPos(track_left, 0, z)
            fill.setSx(0.0001)
            count_lbl = self._label("0", cx + 0.33, z, 0.027, (0.80, 0.90, 1.0, 1.0), TextNode.ARight)
            parts = self.pad_parts[pad["id"]]
            parts["meter_fill"] = fill
            parts["count_lbl"] = count_lbl

        # Master volume
        self._label("MASTER VOLUME", cx, -0.315, 0.030, self.GOLD)
        self._button(cx - 0.27, -0.390, 0.05, 0.034, "-", 0.045,
                     (0.12, 0.16, 0.24), self._adjust_volume, [-0.10])
        self._button(cx + 0.30, -0.390, 0.05, 0.034, "+", 0.045,
                     (0.12, 0.16, 0.24), self._adjust_volume, [0.10])
        vol_left = cx - 0.19
        vol_w = 0.32
        self._card("rows", vol_left, vol_left + vol_w, -0.405, -0.375, (0.01, 0.02, 0.04, 0.95))
        self.volume_fill = self._card("rows2", 0.0, vol_w, -0.015, 0.015, (0.0, 0.80, 1.0, 0.95))
        self.volume_fill.setPos(vol_left, 0, -0.390)
        self._vol_width = vol_w
        self.volume_value = self._label("100%", cx + 0.19, -0.390, 0.028, self.WHITE)

        # Recent hits
        self._label("RECENT HITS", cx, -0.480, 0.030, self.GOLD)
        cell_w = 0.062
        gap = 0.010
        total = 8 * cell_w + 7 * gap
        start = cx - total / 2.0
        self._hist_cells = []
        for i in range(8):
            l = start + i * (cell_w + gap)
            self._card("rows", l, l + cell_w, -0.592, -0.532, (0.01, 0.02, 0.04, 0.95))
            cell = self._card("rows2", l + 0.004, l + cell_w - 0.004, -0.588, -0.536, (0.0, 0.0, 0.0, 0.0))
            self._hist_cells.append(cell)

    # ====================================================
    # STAGE 3: SETTINGS DOCK (bottom of the screen)
    # ====================================================
    #
    # The dock sits below the console. main.py's HOME button lives in the
    # centre of this strip (x within +-0.28), so every control stays at
    # |x| >= 0.34 and nothing overlaps it.

    def _build_settings_dock(self):
        # All functional controls are now on the top toolbar; the bottom dock is intentionally left empty.
        pass

    # ---- settings actions (used by mouse, pinch and the dock buttons) ----

    def set_play_mode(self, mode):
        if mode not in ("AIR", "PINCH"):
            return
        changed = (mode != self.play_mode)
        self.play_mode = mode
        if changed:
            self._reset_hand_states()
        self._refresh_settings_ui()

    def set_sensitivity(self, level):
        if level not in self.AIR_PROFILES:
            return
        self.sensitivity = level
        self._refresh_settings_ui()

    def toggle_effects(self):
        self.fx_enabled = not self.fx_enabled
        self._refresh_settings_ui()

    def toggle_metronome(self):
        self.metro_on = not self.metro_on
        if self.metro_on:
            self._metro_restart()
        self._refresh_settings_ui()

    def adjust_tempo(self, delta):
        self.tempo = int(max(self.TEMPO_MIN, min(self.TEMPO_MAX, self.tempo + delta)))
        # keep the beat grid: the next click follows the last one at the new spacing
        now = time.perf_counter()
        self._metro_next = max(now, self._metro_last + 60.0 / self.tempo)
        self._refresh_settings_ui()

    def reset_settings(self):
        """Back to defaults: mode, sensitivity, effects, metronome, tempo, volume."""
        self.play_mode = self.DEFAULT_PLAY_MODE
        self.sensitivity = self.DEFAULT_SENSITIVITY
        self.fx_enabled = True
        self.metro_on = False
        self.tempo = self.DEFAULT_TEMPO
        if hasattr(self.sound_manager, "set_master_volume"):
            self.sound_manager.set_master_volume(1.0)
        self._reset_hand_states()
        self._refresh_volume()
        self._refresh_settings_ui()

    def _refresh_settings_ui(self):
        """Repaint every settings control from the current state."""
        on = (0.08, 0.48, 0.78)
        off = (0.08, 0.10, 0.15)
        amber = (0.62, 0.44, 0.10)
        neutral = (0.12, 0.16, 0.24)

        air = (self.play_mode == "AIR")
        self._paint("air", on if air else off, air)
        self._paint("pinch", on if not air else off, not air)
        for level in self.AIR_PROFILES:
            sel = (level == self.sensitivity)
            self._paint("sens_" + level, on if sel else off, sel)

        if "metro" in self._seg:
            self._set_text(self._seg["metro"]["lbl"], "METRO: ON" if self.metro_on else "METRO: OFF")
            self._paint("metro", amber if self.metro_on else off, self.metro_on)
        if "fx" in self._seg:
            self._set_text(self._seg["fx"]["lbl"], "FX: ON" if self.fx_enabled else "FX: OFF")
            self._paint("fx", on if self.fx_enabled else off, self.fx_enabled)
        for key in ("tempo_dn", "tempo_up", "reset_cfg"):
            if key in self._seg:
                self._paint(key, neutral, True)
        if hasattr(self, "tempo_value") and self.tempo_value:
            self._set_text(self.tempo_value, "%d BPM" % self.tempo)

        # header indicators
        if hasattr(self, "mode_value") and self.mode_value:
            if air:
                self._set_text(self.mode_value, "AIR MODE")
                self.mode_value["text_fg"] = Vec4(self.CYAN[0], self.CYAN[1], self.CYAN[2], 1.0)
            else:
                self._set_text(self.mode_value, "PINCH MODE")
                self.mode_value["text_fg"] = Vec4(self.GOLD[0], self.GOLD[1], self.GOLD[2], 1.0)
        if hasattr(self, "metro_value") and self.metro_value:
            if self.metro_on:
                self._set_text(self.metro_value, "%d BPM" % self.tempo)
                self.metro_value["text_fg"] = Vec4(self.GOLD[0], self.GOLD[1], self.GOLD[2], 1.0)
            else:
                self._set_text(self.metro_value, "OFF")
                self.metro_value["text_fg"] = Vec4(self.GREY[0], self.GREY[1], self.GREY[2], 1.0)

        # left-panel how-to lines
        if air:
            self._set_text(self._howto[1], "TAP DOWNWARD OVER A DRUM")
            self._set_text(self._howto[2], "LIFT UP BEFORE THE NEXT HIT")
        else:
            self._set_text(self._howto[1], "PINCH THUMB + INDEX TO HIT")
            self._set_text(self._howto[2], "OPEN THE PINCH TO HIT AGAIN")

    # ====================================================
    # STAGE 3: METRONOME
    # ====================================================
    #
    # The click is generated here (short sine bursts) so sound_manager.py does
    # not need to change. It is played straight through pygame and never goes
    # through play_drum(), so it can never be counted as a drum hit.

    def _build_click_sounds(self):
        sm = self.sound_manager
        if not getattr(sm, "audio_ready", False):
            return
        try:
            import numpy as np
            import pygame
            init = pygame.mixer.get_init()
            if not init:
                return
            sr, _fmt, channels = init

            def make(freq, amp):
                n = int(sr * 0.050)
                t = np.arange(n) / float(sr)
                env = np.exp(-t * 85.0)
                a = max(1, int(0.001 * sr))
                env[:a] *= np.linspace(0.0, 1.0, a)
                wave_ = (np.sin(2 * np.pi * freq * t)
                         + 0.35 * np.sin(2 * np.pi * freq * 2.0 * t)) * env
                mono = np.clip(wave_ * amp * 32767.0 / 1.35, -32767, 32767).astype(np.int16)
                data = np.column_stack((mono, mono)) if channels >= 2 else mono
                return pygame.sndarray.make_sound(np.ascontiguousarray(data))

            self._metro_sounds = (make(1500.0, 0.80), make(1000.0, 0.60))
        except Exception as error:
            print("[Drums] Metronome click unavailable:", error)
            self._metro_sounds = (None, None)

    def _play_click(self, accent):
        snd = self._metro_sounds[0 if accent else 1]
        if snd is None:
            return
        try:
            vol = getattr(self.sound_manager, "master_volume", 1.0)
            snd.set_volume(max(0.0, min(1.0, float(vol))))
            snd.play()
        except Exception as error:
            print("[Drums] Metronome playback error:", error)

    def _metro_restart(self):
        self._metro_next = time.perf_counter()     # first click right away
        self._metro_last = -999.0
        self._metro_beat = 0

    def _metro_tick(self, task):
        if not self._alive:
            return task.done
        if self._visible and self.metro_on:
            now = time.perf_counter()
            if now >= self._metro_next:
                accent = (self._metro_beat % self.BEATS_PER_BAR == 0)
                self._play_click(accent)
                self._metro_flash_t = now
                self._metro_flash_accent = accent
                self._metro_last = now
                interval = 60.0 / self.tempo
                self._metro_next += interval
                if self._metro_next < now:          # fell behind (stall): resync
                    self._metro_next = now + interval
                self._metro_beat += 1
        self._update_metro_lamp()
        return task.cont

    def _update_metro_lamp(self):
        if not self._visible:
            return
        f = 0.0
        if self.metro_on:
            f = max(0.0, 1.0 - (time.perf_counter() - self._metro_flash_t) / 0.12)
        key = (self.metro_on, int(f * 4.0), self._metro_flash_accent)
        if key == self._metro_lamp_key:
            return
        self._metro_lamp_key = key
        if not self.metro_on:
            self.metro_lamp.setColor(0.20, 0.24, 0.30, 1.0)
            return
        lit = self.GOLD if self._metro_flash_accent else self.CYAN
        idle = (0.20, 0.24, 0.30)
        c = _mix(idle, lit, int(f * 4.0) / 4.0)
        self.metro_lamp.setColor(c[0], c[1], c[2], 1.0)

    # ====================================================
    # SESSION STATS / VOLUME / AUDIO STATUS
    # ====================================================

    def _refresh_stats(self):
        if self.bpm <= 0:
            bpm_text = "---"
        elif self.bpm > 999:
            bpm_text = "999+"
        else:
            bpm_text = str(self.bpm)
        self._set_text(self.bpm_value, bpm_text)
        self._set_text(self.hits_value, str(self.beat_count))

    def _refresh_volume(self):
        vol = getattr(self.sound_manager, "master_volume", 1.0)
        try:
            vol = max(0.0, min(1.0, float(vol)))
        except (TypeError, ValueError):
            vol = 1.0
        self.volume_fill.setSx(max(0.0001, vol))
        self._set_text(self.volume_value, f"{int(round(vol * 100))}%")

    def _refresh_audio_status(self):
        ready = bool(getattr(self.sound_manager, "audio_ready", True)) and hasattr(self.sound_manager, "play_drum")
        if ready:
            self._set_text(self.audio_value, "READY")
            self.audio_value["text_fg"] = Vec4(0.3, 1.0, 0.5, 1.0)
        else:
            self._set_text(self.audio_value, "OFFLINE")
            self.audio_value["text_fg"] = Vec4(1.0, 0.35, 0.35, 1.0)

    def _adjust_volume(self, delta):
        sm = self.sound_manager
        if not hasattr(sm, "set_master_volume"):
            return
        cur = getattr(sm, "master_volume", 1.0)
        sm.set_master_volume(round(max(0.0, min(1.0, cur + delta)), 2))
        self._refresh_volume()

    def reset_session(self):
        """Clears hit counters, history and BPM (UI only; audio is untouched)."""
        self.beat_count = 0
        self.beat_times = []
        self.bpm = 0
        self.history = []
        self.last_hit_id = None
        self.last_hit_time = -999.0
        for pad in self.PADS:
            pid = pad["id"]
            self.pad_counts[pid] = 0
            self.pad_levels[pid] = 0.0
            parts = self.pad_parts[pid]
            parts["meter_fill"].setSx(0.0001)
            self._set_text(parts["count_lbl"], "0")
        self._set_text(self.feedback_display, "READY")
        self.feedback_display["text_fg"] = Vec4(self.CYAN[0], self.CYAN[1], self.CYAN[2], 1.0)
        self._refresh_stats()
        self._update_history()

    def _update_history(self):
        pads = {p["id"]: p for p in self.PADS}
        recent = list(reversed(self.history))
        for i, cell in enumerate(self._hist_cells):
            if i < len(recent):
                c = pads[recent[i]]["active_color"]
                cell.setColor(c[0], c[1], c[2], 1.0 - i * 0.08)
            else:
                cell.setColor(0.0, 0.0, 0.0, 0.0)

    # ====================================================
    # ANIMATION TASK (only does work for pads that were just hit)
    # ====================================================

    def _animate(self, task):
        if not self._alive:
            return task.done

        # Nothing to animate while the studio is hidden
        if not self._visible:
            return task.cont

        try:
            dt = ClockObject.getGlobalClock().getDt()
            now = time.time()

            for pad in self.PADS:
                self._animate_pad(pad, now, dt)

            for slot in self._slots.values():
                if slot["flash"] > 0.0:
                    slot["flash"] = max(0.0, slot["flash"] - dt * 4.5)
                    self._style_cursor(slot)

            self._animate_global(now)
        except Exception as e:
            pass
        return task.cont

    def _animate_pad(self, pad, now, dt):
        pid = pad["id"]
        p = self.pad_parts[pid]
        e = now - self.hit_timers.get(pid, -999.0)
        act = p["act"]
        fx = self.fx_enabled      # False = head colour + meters only

        # ---- meter decay ----
        lvl = self.pad_levels[pid]
        if lvl > 0.0:
            lvl = max(0.0, lvl - dt * 1.3)
            self.pad_levels[pid] = lvl
            p["meter_fill"].setSx(max(0.0001, lvl))

        if e < 0.60:
            p["active"] = True

            glow = max(0.0, 1.0 - e / 0.30) ** 1.4
            flash = max(0.0, 1.0 - e / 0.14)

            # head / cymbal + rim colour
            bc = _mix(p["body_base"], act, glow * 0.75)
            p["body"].setColorScale(bc[0], bc[1], bc[2], 1.0)
            rc = _mix(p["rim_base"], (1.0, 1.0, 1.0), glow * 0.6)
            p["rim"].setColorScale(rc[0], rc[1], rc[2], 1.0)

            # small physical motion, different per instrument
            motion = p["motion"]
            dx = 0.0
            dz = 0.0
            s = 1.0
            if fx:
                if motion == "shake":        # cymbals swing and settle
                    dx = 0.008 * math.sin(e * 42.0) * max(0.0, 1.0 - e / 0.55)
                    dz = -0.010 * glow
                elif motion == "hat":        # hi-hat clamps down
                    dz = -0.014 * glow
                elif motion == "kick":       # bass drum punches
                    s = 1.0 + 0.035 * glow
                else:                        # snare / tom: head presses in
                    dz = -0.008 * glow

            px = p["x"]
            pz = p["z"]
            for node, ox, oz, sx, sz in p["move"]:
                node.setPos(px + ox * s + dx, 0, pz + oz * s + dz)
                if motion == "kick":
                    node.setScale(sx * s, 1.0, sz * s)

            # soft halo
            if fx and glow > 0.02:
                if not p["halo_on"]:
                    p["halo"].show()
                    p["halo_on"] = True
                p["halo"].setColorScale(act[0], act[1], act[2], 0.55 * glow)
            elif p["halo_on"]:
                p["halo"].hide()
                p["halo_on"] = False

            # impact flash
            if fx and flash > 0.01:
                if not p["flash_on"]:
                    p["flash"].show()
                    p["flash_on"] = True
                fc = _mix(act, (1.0, 1.0, 1.0), 0.15)
                p["flash"].setColorScale(fc[0], fc[1], fc[2], flash * 0.50)
            elif p["flash_on"]:
                p["flash"].hide()
                p["flash_on"] = False

            # single shockwave ring
            q = e / 0.50
            if fx and 0.0 <= q < 1.0:
                if not p["shock_on"]:
                    p["shock"].show()
                    p["shock_on"] = True
                ease = 1.0 - (1.0 - q) ** 2
                grow = 1.0 + 0.45 * ease
                p["shock"].setScale(p["rx"] * grow, 1.0, p["rz"] * grow)
                p["shock"].setColorScale(act[0], act[1], act[2], (1.0 - q) ** 1.5 * 0.85)
            elif p["shock_on"]:
                p["shock"].hide()
                p["shock_on"] = False

            # left-panel row flash
            base = p["row_base"]
            rcol = _mix(base, act, glow * 0.9)
            p["row_card"].setColor(rcol[0], rcol[1], rcol[2], base[3])
            p["row_dot"].setColor(1.0, 1.0, 1.0, 0.25 + 0.75 * glow)

        elif p["active"]:
            self._set_pad_idle(p)

    def _animate_global(self, now):
        if not hasattr(self, "accent_bar") or self.accent_bar is None:
            return
        f = max(0.0, 1.0 - (now - self.last_hit_time) / 0.7)
        if not self.fx_enabled:
            f = 0.0
        try:
            if f > 0.0:
                tint = _mix(self.CYAN, self.last_color, min(1.0, f * 1.4))
                self.accent_bar.setColor(tint[0], tint[1], tint[2], 0.55 + 0.45 * f)
                self._accent_active = True
            elif self._accent_active:
                self.accent_bar.setColor(self.CYAN[0], self.CYAN[1], self.CYAN[2], 0.70)
                self._accent_active = False
        except Exception:
            pass

    def _set_pad_idle(self, p):
        """Return one pad to its resting look."""
        bb = p["body_base"]
        rb = p["rim_base"]
        p["body"].setColorScale(bb[0], bb[1], bb[2], 1.0)
        p["rim"].setColorScale(rb[0], rb[1], rb[2], 1.0)

        px = p["x"]
        pz = p["z"]
        for node, ox, oz, sx, sz in p["move"]:
            node.setPos(px + ox, 0, pz + oz)
            node.setScale(sx, 1.0, sz)

        p["halo"].hide()
        p["halo_on"] = False
        p["flash"].hide()
        p["flash_on"] = False
        p["shock"].hide()
        p["shock_on"] = False

        base = p["row_base"]
        p["row_card"].setColor(base[0], base[1], base[2], base[3])
        p["row_dot"].setColor(1.0, 1.0, 1.0, 0.25)
        p["active"] = False

    # ====================================================
    # HIT ZONES (exact shapes of the drawn instruments)
    # ====================================================

    def _build_hit_shapes(self):
        """Hit shapes use the same numbers that draw the instruments:
        ("e", cx, cz, rx, rz) = ellipse, ("r", x0, x1, z0, z1) = rectangle.
        A drum = head ellipse + bottom ellipse + the rectangle between them
        (exactly the visible shell). The hi-hat covers both cymbals."""
        self._shapes = {}
        self._margins = {}
        for pad in self.PADS:
            x, z = pad["pos"]
            rx, rz, depth = pad["rx"], pad["rz"], pad["depth"]
            kind = pad["kind"]
            if kind == "kick":
                shapes = [("e", x, z, rx, rz)]
                margin = self.HIT_MARGIN_DRUM
            elif kind in ("snare", "tom"):
                zb = z - depth - 0.014
                shapes = [("e", x, z, rx, rz), ("e", x, zb, rx, rz),
                          ("r", x - rx, x + rx, zb, z)]
                margin = self.HIT_MARGIN_DRUM
            elif kind == "hat":
                zb = z - 0.034
                shapes = [("e", x, z, rx, rz), ("e", x, zb, rx * 0.98, rz),
                          ("r", x - rx * 0.98, x + rx * 0.98, zb, z)]
                margin = self.HIT_MARGIN_CYMBAL
            else:
                zb = z - 0.014
                shapes = [("e", x, z, rx, rz), ("e", x, zb, rx, rz),
                          ("r", x - rx, x + rx, zb, z)]
                margin = self.HIT_MARGIN_CYMBAL
            self._shapes[pad["id"]] = shapes
            self._margins[pad["id"]] = margin

    def _inside(self, pid, x, z, extra=0.0):
        m = self._margins[pid] + extra
        for s in self._shapes[pid]:
            if s[0] == "e":
                nx = (x - s[1]) / (s[3] + m)
                nz = (z - s[2]) / (s[4] + m)
                if nx * nx + nz * nz <= 1.0:
                    return True
            else:
                if s[1] - m <= x <= s[2] + m and s[3] - m <= z <= s[4] + m:
                    return True
        return False

    def _pad_at(self, x, z, prefer=None):
        """Pad under the point. Overlaps go to the drum painted on top
        (later in DRAW_ORDER). If the point is in no pad, `prefer` (the pad
        that was highlighted a moment ago) is kept while the cursor is only
        just outside it, so the highlight doesn't flicker at the edge."""
        hit = None
        for pid in self.DRAW_ORDER:
            if self._inside(pid, x, z):
                hit = pid
        if hit is None and prefer is not None and self._inside(prefer, x, z, self.HOVER_STICKY):
            return prefer
        return hit

    def get_hit_zones(self):
        """[(pad_id, centre_x, centre_z, half_width, half_height), ...]:
        coarse bounding ellipses (informational). Real hit-testing uses the
        exact shapes through find_pad_at()."""
        zones = []
        for pad in self.PADS:
            cx, cz, hx, hz = pad["hit"]
            zones.append((pad["id"], cx, cz, hx, hz))
        return zones

    def find_pad_at(self, x, z):
        """Id of the drum under the aspect2d point (x, z), or None."""
        return self._pad_at(x, z)

    def recent_hit(self, window=0.35):
        """True if a drum was hit within the last `window` seconds. main.py
        uses this so one pinch can never both play a drum and press HOME."""
        return (time.time() - self.last_hit_time) < window

    # ====================================================
    # HAND SLOTS + CURSORS
    # ====================================================

    def _init_slots(self):
        left_c, right_c = self.LEFT_COLOR, self.RIGHT_COLOR
        if self.SWAP_HAND_COLORS:
            left_c, right_c = right_c, left_c
        self._slots = {}
        for key, col in (("L", left_c), ("R", right_c)):
            self._slots[key] = {
                "key": key, "color": col,
                "present": False, "last_seen": -999.0, "anchor": None,
                "pos": None, "hist": [],
                "pinched": False, "lock": True, "last_hit": -999.0,
                "hover": None, "flash": 0.0, "style_key": None,
                "root": None, "halo": None, "ring": None, "core": None,
                # Stage 3 (AIR mode)
                "rhist": [], "air_lock": None, "since": -999.0,
            }

    def _build_cursors(self):
        layer = self._layers["cursor"]
        for key, slot in self._slots.items():
            root = layer.attachNewNode("DrumCursor_" + key)
            halo = _disc_geom(1.0, 32, 0.6, 0.0)
            halo.reparentTo(root)
            halo.setScale(0.085, 1.0, 0.085)
            _make_additive(halo)
            ring = _ring_geom(0.80, 1.0, 40)
            ring.reparentTo(root)
            _make_additive(ring)
            core = _disc_geom(1.0, 16, 1.0, 1.0)
            core.reparentTo(root)
            root.hide()
            slot["root"] = root
            slot["halo"] = halo
            slot["ring"] = ring
            slot["core"] = core
            self._style_cursor(slot)

    def _style_cursor(self, slot):
        """Open = wide ring. Pinched = tight, brighter ring + bigger core.
        A short pop after a successful hit. Only touches nodes when the look
        actually changes."""
        pinched = slot["pinched"]
        fq = int(slot["flash"] * 5.0)
        key = (pinched, fq)
        if slot["style_key"] == key:
            return
        slot["style_key"] = key
        f = fq / 5.0
        c = slot["color"]
        if pinched:
            rc = _mix(c, (1.0, 1.0, 1.0), 0.45)
            ring_s, halo_a, core_s = 0.030, 0.85, 0.013
        else:
            rc = c
            ring_s, halo_a, core_s = 0.042, 0.45, 0.009
        ring_s *= 1.0 + 0.8 * f
        halo_a = min(1.0, halo_a + 0.5 * f)
        slot["ring"].setScale(ring_s, 1.0, ring_s)
        slot["ring"].setColorScale(rc[0], rc[1], rc[2], 1.0)
        slot["halo"].setColorScale(c[0], c[1], c[2], halo_a)
        slot["core"].setScale(core_s, 1.0, core_s)
        slot["core"].setColorScale(1.0, 1.0, 1.0, 0.95)

    def _reset_slots(self):
        for s in self._slots.values():
            s["present"] = False
            s["last_seen"] = -999.0
            s["anchor"] = None
            s["pos"] = None
            s["hist"] = []
            s["rhist"] = []
            s["air_lock"] = None
            s["ui_dwell_target"] = None
            s["ui_dwell_start"] = 0.0
            s["since"] = -999.0
            s["pinched"] = False
            s["lock"] = True          # must be seen open before it may hit
            s["hover"] = None
            s["flash"] = 0.0
            s["style_key"] = None
            if s["root"] is not None:
                s["root"].hide()
                self._style_cursor(s)
        self._hover_state = {}
        for p in self.pad_parts.values():
            p["hover"].hide()
            p["hover_on"] = False
        self._input_key = None
        self._refresh_input_status()

    def _reset_hand_states(self):
        """Called when the play mode changes or settings are reset: every hand
        must be seen open again before a pinch counts, and any AIR lock is
        cleared. Cursors stay where they are."""
        for s in self._slots.values():
            s["pinched"] = False
            s["lock"] = True
            s["air_lock"] = None
            s["style_key"] = None
            if s["root"] is not None:
                self._style_cursor(s)

    def _refresh_hover(self):
        desired = {}
        for slot in self._slots.values():
            if slot["present"] and slot["hover"] is not None:
                desired.setdefault(slot["hover"], []).append(slot)
        state = {}
        for pid, slots in desired.items():
            pinched = any(s["pinched"] for s in slots)
            if len(slots) == 1:
                col = slots[0]["color"]
            else:
                col = (0.95, 0.95, 1.0)
            state[pid] = (col, pinched)
        if state == self._hover_state:
            return
        self._hover_state = state
        for pad in self.PADS:
            pid = pad["id"]
            p = self.pad_parts[pid]
            entry = state.get(pid)
            if entry is not None:
                col, pinched = entry
                p["hover"].setColorScale(col[0], col[1], col[2], 0.90 if pinched else 0.55)
                if not p["hover_on"]:
                    p["hover"].show()
                    p["hover_on"] = True
            elif p["hover_on"]:
                p["hover"].hide()
                p["hover_on"] = False

    def _refresh_input_status(self):
        left = self._slots["L"]["present"] if self._slots else False
        right = self._slots["R"]["present"] if self._slots else False
        key = (left, right)
        if key == self._input_key:
            return
        self._input_key = key
        if left and right:
            text, col = "BOTH HANDS", (0.95, 0.95, 1.0)
        elif left:
            text, col = "LEFT HAND", self._slots["L"]["color"]
        elif right:
            text, col = "RIGHT HAND", self._slots["R"]["color"]
        else:
            text, col = "SHOW YOUR HANDS", self.GREY
        self._set_text(self.input_value, text)
        self.input_value["text_fg"] = Vec4(col[0], col[1], col[2], 1.0)

    # ====================================================
    # UPDATE — CALLED EACH FRAME FROM MAIN
    # ====================================================

    @staticmethod
    def _extract_landmarks(hands):
        """Landmark lists for up to two hands. Accepts the list main.py now
        passes, a single hand (old behaviour) or None."""
        if hands is None:
            return []
        seq = hands if isinstance(hands, (list, tuple)) else [hands]
        out = []
        for h in seq:
            lm = getattr(h, "landmark", None)
            if lm is None:
                continue
            try:
                if len(lm) >= 21:
                    out.append(lm)
            except TypeError:
                continue
            if len(out) == 2:
                break
        return out

    def _assign_hands(self, lms, now):
        """Give each hand a stable slot. No handedness labels exist, so:
        new hands -> by screen side; known hands -> nearest remembered spot
        (works even if the tracker reorders them or the hands cross)."""
        n = len(lms)
        if n == 0:
            return {}
        pts = [(lm[9].x, lm[9].y) for lm in lms]     # middle knuckle = stable palm point
        L, R = self._slots["L"], self._slots["R"]

        def mem(slot):
            if slot["anchor"] is not None and now - slot["last_seen"] <= self.HAND_MEMORY:
                return slot["anchor"]
            return None

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        mL, mR = mem(L), mem(R)
        if n == 2:
            if mL is not None and mR is not None:
                first_left = (dist(pts[0], mL) + dist(pts[1], mR)
                              <= dist(pts[0], mR) + dist(pts[1], mL))
            elif mL is not None:
                first_left = dist(pts[0], mL) <= dist(pts[1], mL)
            elif mR is not None:
                first_left = dist(pts[1], mR) <= dist(pts[0], mR)
            else:
                first_left = pts[0][0] <= pts[1][0]
            if first_left:
                return {"L": lms[0], "R": lms[1]}
            return {"L": lms[1], "R": lms[0]}

        p = pts[0]
        if mL is not None and mR is not None:
            key = "L" if dist(p, mL) <= dist(p, mR) else "R"
        elif mL is not None and dist(p, mL) < 0.40:
            key = "L"
        elif mR is not None and dist(p, mR) < 0.40:
            key = "R"
        else:
            key = "L" if p[0] < 0.5 else "R"
        return {key: lms[0]}

    def _pinch_ratio(self, lm):
        """Thumb-tip to index-tip distance relative to palm size. Palm size
        is the mean of palm width and palm length, which stays steadier than
        palm width alone when the hand turns."""
        fa = self.FRAME_ASPECT
        d = math.hypot((lm[4].x - lm[8].x) * fa, lm[4].y - lm[8].y)
        w = math.hypot((lm[5].x - lm[17].x) * fa, lm[5].y - lm[17].y)
        ln = math.hypot((lm[0].x - lm[9].x) * fa, lm[0].y - lm[9].y)
        scale = 0.5 * (w + ln)
        if scale < 0.02:
            return None
        return d / scale

    def update(self, hands):
        if self.LEGACY_POSE_MODE:
            if isinstance(hands, (list, tuple)):
                hands = hands[0] if hands else None
            self._update_legacy_pose(hands)
            return

        if not self._visible:
            return

        now = time.time()
        get_aspect = getattr(self.base, "getAspectRatio", None)
        aspect = get_aspect() if get_aspect is not None else 16.0 / 9.0

        lms = self._extract_landmarks(hands)
        assigned = self._assign_hands(lms, now)

        for key in ("L", "R"):
            slot = self._slots[key]
            lm = assigned.get(key)
            if lm is None:
                self._slot_lost(slot, now)
            else:
                self._slot_track(slot, lm, now, aspect)

        self._refresh_hover()
        self._refresh_input_status()

    def _slot_lost(self, slot, now):
        if slot["present"] and now - slot["last_seen"] > self.LOSS_GRACE:
            slot["present"] = False
            slot["pinched"] = False
            slot["lock"] = True
            slot["hover"] = None
            slot["pos"] = None
            slot["hist"] = []
            slot["rhist"] = []
            slot["air_lock"] = None
            slot["ui_dwell_target"] = None
            slot["ui_dwell_start"] = 0.0
            slot["root"].hide()
            self._style_cursor(slot)

    def _slot_track(self, slot, lm, now, aspect):
        if not slot["present"]:
            slot["present"] = True
            slot["pinched"] = False
            slot["lock"] = True      # a pinch already closed on arrival must not hit
            slot["pos"] = None
            slot["hist"] = []
            slot["rhist"] = []
            slot["air_lock"] = None
            slot["since"] = now      # AIR mode: no hit right after a hand appears
            slot["root"].show()
        slot["last_seen"] = now
        slot["anchor"] = (lm[9].x, lm[9].y)

        # index fingertip -> screen (same mapping as main.py's cursor)
        gain = self.CURSOR_GAIN
        rx = (lm[8].x - 0.5) * 2.0 * aspect * gain
        rz = (0.5 - lm[8].y) * 2.0 * gain

        # light adaptive smoothing: steady when still, responsive when moving
        pos = slot["pos"]
        if pos is None:
            x, z = rx, rz
        else:
            speed = math.hypot(rx - pos[0], rz - pos[1])
            if speed > 0.08:
                a = 0.92
            elif speed > 0.02:
                a = min(0.88, self.SMOOTH_MIN + speed * self.SMOOTH_GAIN * 0.4)
            else:
                a = self.SMOOTH_MIN
            x = pos[0] + (rx - pos[0]) * a
            z = pos[1] + (rz - pos[1]) * a
        slot["pos"] = (x, z)
        slot["root"].setPos(x, 0, z)

        hist = slot["hist"]
        hist.append((now, x, z))
        while hist and now - hist[0][0] > 0.5:
            hist.pop(0)

        # raw (unsmoothed) fingertip track: AIR mode measures taps on this,
        # because the smoothed cursor lags behind a quick tap
        rhist = slot["rhist"]
        rhist.append((now, rx, rz))
        while rhist and now - rhist[0][0] > 0.5:
            rhist.pop(0)

        slot["hover"] = self._pad_at(x, z, slot["hover"])

        # Hover Dwell selection for UI targets (works in AIR mode & PINCH mode)
        ui_target = self._ui_target_at(x, z)
        if ui_target is not None:
            t_id = id(ui_target)
            if slot.get("ui_dwell_target") != t_id:
                slot["ui_dwell_target"] = t_id
                slot["ui_dwell_start"] = now
            elif self.play_mode == "AIR" and now - slot.get("ui_dwell_start", now) >= 0.38:
                if now - self._last_ui_click >= self.UI_CLICK_COOLDOWN:
                    self._last_ui_click = now
                    slot["flash"] = 1.0
                    slot["style_key"] = None
                    if hasattr(self.sound_manager, "play_ui_click"):
                        self.sound_manager.play_ui_click()
                    ui_target["cmd"](*ui_target["args"])
                    slot["ui_dwell_start"] = now + 999.0
        else:
            slot["ui_dwell_target"] = None
            slot["ui_dwell_start"] = 0.0

        # pinch state machine (separate ON / OFF thresholds, own state per hand).
        # Runs in BOTH modes: PINCH mode plays drums with it, AIR mode only uses
        # it to press buttons.
        edge = False
        ratio = self._pinch_ratio(lm)
        if ratio is not None:
            # Smooth pinch ratio for instant, responsive triggering
            if slot.get("smooth_ratio") is None:
                slot["smooth_ratio"] = ratio
            else:
                slot["smooth_ratio"] = 0.70 * ratio + 0.30 * slot["smooth_ratio"]
            eff_ratio = slot["smooth_ratio"]

            if slot["pinched"]:
                if eff_ratio > self.PINCH_OFF:
                    slot["pinched"] = False
            elif eff_ratio < self.PINCH_ON:
                if not slot["lock"]:
                    slot["pinched"] = True
                    edge = True
            elif eff_ratio > self.PINCH_OFF:
                slot["lock"] = False

        if edge:
            # If cursor is over any UI target or in upper console area, prioritize UI button click
            if z > 0.65 or ui_target is not None:
                if not self._ui_click(slot, now):
                    if self.play_mode == "PINCH":
                        self._try_hit(slot, now)
            elif self.play_mode == "PINCH":
                if not self._try_hit(slot, now):
                    self._ui_click(slot, now)
            else:
                self._ui_click(slot, now)
        elif self.play_mode == "AIR":
            self._air_detect(slot, now, rx, rz)
        self._style_cursor(slot)

    def _try_hit(self, slot, now):
        """PINCH mode. Runs once per pinch (on the closing edge only).
        Returns True if a drum was played."""
        if now - slot["last_hit"] < self.HIT_COOLDOWN:
            return False
        pad_id = self._pick_target(slot, now)
        if pad_id is None:
            return False
        slot["last_hit"] = now
        slot["flash"] = 1.0 if self.fx_enabled else 0.0
        slot["style_key"] = None
        self._hit_pad(pad_id, now)
        return True

    def _pick_target(self, slot, now):
        """Closing the fingers nudges the index tip. If the hand was nearly
        still over the last ~100 ms, trust where the cursor WAS; otherwise
        use where it is now."""
        cur = slot["pos"]
        past = None
        for (t, px, pz) in reversed(slot["hist"]):
            if t <= now - self.LOOKBACK:
                past = (px, pz)
                break
        if past is not None and math.hypot(cur[0] - past[0], cur[1] - past[1]) < self.LOOKBACK_STILL:
            old = self._pad_at(past[0], past[1])
            if old is not None:
                return old
        return slot["hover"]

    # ---- Stage 3: AIR MODE ----

    def _air_detect(self, slot, now, rx, rz):
        """One hit per deliberate downward tap over a drum.

        A hit needs, inside the last AIR_WINDOW seconds, a downward travel of at
        least `dist` at a speed of at least `speed` (both from AIR_PROFILES),
        mostly vertical, while the fingertip is over a drum.

        After a hit the hand is locked to that drum. The lock opens when the
        fingertip leaves the drum, moves onto another drum, or rises `rise`
        above its lowest point since the hit. A finger resting inside a drum
        therefore never repeats, and a repeated tap (down, up, down) does."""
        prof = self.AIR_PROFILES[self.sensitivity]
        pad = self._pad_at(rx, rz, slot["hover"])

        lock = slot["air_lock"]
        if lock is not None:
            if pad != lock["pad"]:
                slot["air_lock"] = None
            elif rz < lock["low"]:
                lock["low"] = rz
            elif rz - lock["low"] >= prof["rise"]:
                slot["air_lock"] = None
            if slot["air_lock"] is not None:
                return

        ui_t = self._ui_target_at(rx, rz)
        if ui_t is not None:
            rh = slot["rhist"]
            for (t, px, pz) in rh:
                dt = now - t
                if dt > 0.25 or dt < self.AIR_MIN_DT:
                    continue
                down = pz - rz
                if down >= 0.025 and (down / dt) >= 0.22:
                    if now - self._last_ui_click >= self.UI_CLICK_COOLDOWN:
                        self._last_ui_click = now
                        slot["flash"] = 1.0
                        slot["style_key"] = None
                        if hasattr(self.sound_manager, "play_ui_click"):
                            self.sound_manager.play_ui_click()
                        ui_t["cmd"](*ui_t["args"])
                        return

        if pad is None:
            return
        if now - slot["last_hit"] < self.AIR_COOLDOWN:
            return
        if now - slot["since"] < self.AIR_ARRIVAL_GUARD:
            return

        # The look-back window grows when the app runs slowly, so a low frame
        # rate (long gaps between samples) can still see a tap.
        rh = slot["rhist"]
        n = len(rh)
        window = self.AIR_WINDOW
        if n >= 3:
            gap = (rh[-1][0] - rh[max(0, n - 4)][0]) / min(3, n - 1)
            window = min(0.35, max(window, 2.5 * gap))

        best_down = 0.0
        best_speed = 0.0
        for (t, px, pz) in rh:
            dt = now - t
            if dt > window:
                continue
            if dt < self.AIR_MIN_DT:
                break
            down = pz - rz                       # positive = fingertip moved down
            if down > best_down:
                best_down = down
            if down / dt > best_speed:
                best_speed = down / dt
            if down < prof["dist"]:
                continue
            if down / dt < prof["speed"]:
                continue
            if down < self.AIR_DOWN_DOMINANCE * abs(rx - px):
                continue
            slot["last_hit"] = now
            slot["flash"] = 1.0 if self.fx_enabled else 0.0
            slot["style_key"] = None
            slot["air_lock"] = {"pad": pad, "low": rz}
            if self.AIR_DEBUG:
                print("[AIR] HIT %s %s down=%.3f speed=%.2f" % (slot["key"], pad, down, down / dt))
            self._hit_pad(pad, now)
            return

        if self.AIR_DEBUG and best_down > 0.01 and now - slot.get("dbg", 0.0) > 0.15:
            slot["dbg"] = now
            print("[AIR] no hit %s %s down=%.3f (need %.3f) speed=%.2f (need %.2f) window=%.2fs"
                  % (slot["key"], pad, best_down, prof["dist"], best_speed, prof["speed"], window))

    # ---- Stage 3: pressing buttons with a pinch ----

    def _ui_point(self, slot, now):
        """Where the cursor was a moment ago if the hand was still (closing the
        fingers nudges the fingertip), otherwise where it is now."""
        cur = slot["pos"]
        for (t, px, pz) in reversed(slot["hist"]):
            if t <= now - self.LOOKBACK:
                if math.hypot(cur[0] - px, cur[1] - pz) < self.LOOKBACK_STILL:
                    return (px, pz)
                break
        return cur

    def _ui_target_at(self, x, z):
        if x is None or z is None:
            return None
        for t in self._ui_targets:
            margin_w = max(0.045, t["hw"] * 0.45)
            margin_h = max(0.038, t["hh"] * 0.85)
            if abs(x - t["x"]) <= (t["hw"] + margin_w) and abs(z - t["z"]) <= (t["hh"] + margin_h):
                return t
        return None

    def _ui_click(self, slot, now):
        """Pinch or tap edge over one of this module's buttons = a click on it."""
        if slot["pos"] is None or now - self._last_ui_click < self.UI_CLICK_COOLDOWN:
            return False
        pts = [self._ui_point(slot, now), slot["pos"]]
        target = None
        for (x, z) in pts:
            target = self._ui_target_at(x, z)
            if target is not None:
                break
        if target is not None:
            self._last_ui_click = now
            slot["flash"] = 1.0
            slot["style_key"] = None
            if hasattr(self.sound_manager, "play_ui_click"):
                self.sound_manager.play_ui_click()
            target["cmd"](*target["args"])
            return True
        return False

    # ---- Stage 1 behaviour, kept behind LEGACY_POSE_MODE ----

    def _update_legacy_pose(self, hand):
        if hand is None:
            self._reset_pads()
            return

        lm = hand.landmark

        index_up  = lm[8].y  < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up   = lm[16].y < lm[14].y
        pinky_up  = lm[20].y < lm[18].y
        thumb_up  = lm[4].x  < lm[3].x

        triggered_drum = None
        if pinky_up and not index_up and not middle_up and not ring_up:
            triggered_drum = "kick"
        elif index_up and not middle_up and not ring_up and not pinky_up:
            triggered_drum = "snare"
        elif middle_up and not ring_up and not pinky_up:
            triggered_drum = "hat"
        elif ring_up and not pinky_up and not index_up:
            triggered_drum = "tom"
        elif thumb_up and not index_up and not middle_up:
            triggered_drum = "crash"
        elif index_up and middle_up and ring_up and pinky_up:
            triggered_drum = "ride"
        else:
            x = lm[9].x
            for pad in self.PADS:
                z0, z1 = pad["zone"]
                if z0 <= x < z1:
                    triggered_drum = pad["id"]
                    break
            if triggered_drum is None:
                triggered_drum = "snare"

        now = time.time()
        if triggered_drum and (
            triggered_drum != self.last_drum or
            (now - self.last_time > self.cooldown)
        ):
            self._hit_pad(triggered_drum, now)

    def _on_mouse_click(self):
        """Allows direct clicking on any drum kit piece with the mouse."""
        if not self._visible:
            return
        mw = getattr(self.base, "mouseWatcherNode", None)
        if mw is None or not mw.hasMouse():
            return
        try:
            m = mw.getMouse()
            get_aspect = getattr(self.base, "getAspectRatio", None)
            aspect = get_aspect() if get_aspect is not None else 16.0 / 9.0
            mx = m.getX() * aspect
            mz = m.getY()
            pad = self._pad_at(mx, mz)
            if pad:
                self._hit_pad(pad, time.time())
        except Exception:
            pass

    def _hit_pad(self, drum_id, now):
        """Single funnel for every drum hit (AIR, PINCH, mouse and legacy)."""
        self.last_drum = drum_id
        self.last_time = now
        self.hit_timers[drum_id] = now

        # Play audio
        if hasattr(self.sound_manager, "play_drum"):
            try:
                self.sound_manager.play_drum(drum_id)
            except Exception as e:
                print(f"[Drums] Audio playback error for {drum_id}:", e)

        # Visual feedback
        try:
            pad_info = next((p for p in self.PADS if p["id"] == drum_id), None)
            if pad_info:
                self._on_visual_hit(pad_info, now)
        except Exception as e:
            print(f"[Drums] Visual feedback error for {drum_id}:", e)

        # Beat counting + BPM
        try:
            self.beat_count += 1
            self.beat_times.append(now)
            self.beat_times = [t for t in self.beat_times if now - t <= 10.0]
            if len(self.beat_times) >= 2:
                span = self.beat_times[-1] - self.beat_times[0]
                if span > 0:
                    self.bpm = int((len(self.beat_times) - 1) / span * 60)
            self._refresh_stats()
        except Exception:
            pass

    def _on_visual_hit(self, pad_info, now):
        pid = pad_info["id"]
        act = pad_info["active_color"][:3]

        self.pad_levels[pid] = 1.0
        self.pad_counts[pid] += 1
        self.last_hit_id = pid
        self.last_color = act
        self.last_hit_time = now

        self._set_text(self.feedback_display, pad_info["name"])
        self.feedback_display["text_fg"] = Vec4(act[0], act[1], act[2], 1.0)
        self._set_text(self.pad_parts[pid]["count_lbl"], str(self.pad_counts[pid]))

        self.history.append(pid)
        if len(self.history) > 8:
            self.history = self.history[-8:]
        self._update_history()

    def _reset_pads(self):
        # Pad visuals are returned to rest by the animation task, so there is
        # nothing to do here when the hand leaves the frame.
        return

    def show(self):
        self._visible = True
        self._reset_slots()      # hands start locked: no hit from a pinch carried in
        self.frame.show()
        if hasattr(self, 'drum_world'):
            self.drum_world.show()
        self._refresh_volume()
        self._refresh_audio_status()
        self._refresh_settings_ui()
        self._metro_lamp_key = None
        if self.metro_on:
            self._metro_restart()

    def hide(self):
        self._visible = False
        self.frame.hide()
        if hasattr(self, 'drum_world'):
            self.drum_world.hide()

        # Leave every pad in its resting state so nothing flashes on re-entry
        self.hit_timers.clear()
        for pad in self.PADS:
            pid = pad["id"]
            self.pad_levels[pid] = 0.0
            parts = self.pad_parts.get(pid)
            if parts:
                parts["meter_fill"].setSx(0.0001)
                self._set_pad_idle(parts)
        self.last_hit_time = -999.0
        self._reset_slots()
        self._reset_pads()

    def cleanup(self):
        self._alive = False
        try:
            if hasattr(self.base, "ignore"):
                self.base.ignore("mouse1")
        except Exception:
            pass
        try:
            self.base.taskMgr.remove("DrumsAnimation")
            self.base.taskMgr.remove("DrumsMetronome")
        except Exception:
            pass
        try:
            if hasattr(self, 'drum_world'):
                self.drum_world.removeNode()
        except Exception:
            pass
        for btn in getattr(self, "_buttons", []):
            try:
                btn.destroy()
            except Exception:
                pass
        self._buttons = []
        try:
            self.frame.removeNode()
        except Exception:
            pass