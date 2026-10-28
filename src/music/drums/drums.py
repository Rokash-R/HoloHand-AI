import math
import time
from direct.gui.DirectGui import DirectFrame, DirectLabel
from panda3d.core import TextNode, Vec4, LineSegs, NodePath, Point3


class Drums:
    """
    Premium Holographic Drum Matrix for HoloHand AI.

    Features:
      - 6 cyber drum pads: KICK, SNARE, HI-HAT, TOM, CRASH, RIDE
      - Per-finger extension detection (index/middle/ring/pinky/thumb)
      - Spatial X-zone fallback mapping when multiple fingers are up
      - Velocity-sensitive glow with shockwave pulse animation
      - 3D explosive ring burst animation on each hit
      - BPM counter and beat pattern display
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
            "zone": (0.0, 0.17)
        },
        {
            "id": "snare",
            "name": "SNARE",
            "emoji": "[*]",
            "color": (0.1, 0.55, 1.0, 0.88),
            "active_color": (0.4, 0.95, 1.0, 1.0),
            "finger": "Index",
            "finger_idx": 1,
            "zone": (0.17, 0.34)
        },
        {
            "id": "hat",
            "name": "HI-HAT",
            "emoji": "[^]",
            "color": (0.85, 0.75, 0.05, 0.88),
            "active_color": (1.0, 0.95, 0.4, 1.0),
            "finger": "Middle",
            "finger_idx": 2,
            "zone": (0.34, 0.51)
        },
        {
            "id": "tom",
            "name": "TOM",
            "emoji": "[#]",
            "color": (0.05, 0.80, 0.35, 0.88),
            "active_color": (0.3, 1.0, 0.6, 1.0),
            "finger": "Ring",
            "finger_idx": 3,
            "zone": (0.51, 0.68)
        },
        {
            "id": "crash",
            "name": "CRASH",
            "emoji": "[!]",
            "color": (1.0, 0.45, 0.1, 0.88),
            "active_color": (1.0, 0.75, 0.3, 1.0),
            "finger": "Thumb",
            "finger_idx": 0,
            "zone": (0.68, 0.84)
        },
        {
            "id": "ride",
            "name": "RIDE",
            "emoji": "[+]",
            "color": (0.1, 0.75, 0.85, 0.88),
            "active_color": (0.4, 1.0, 0.95, 1.0),
            "finger": "All",
            "finger_idx": -1,
            "zone": (0.84, 1.00)
        },
    ]

    # Map finger index -> which drum to prioritize
    FINGER_DRUM = {
        1: "snare",   # index
        2: "hat",     # middle
        3: "tom",     # ring
        4: "kick",    # pinky
        0: "crash",   # thumb
    }

    def __init__(self, base, sound_manager):
        self.base = base
        self.sound_manager = sound_manager
        self._alive = True

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

        # Shockwave animation state
        self.shockwave_pad = None
        self.shockwave_phase = 0.0

        # 3D World
        self._build_drum_3d_world()

        # 2D HUD
        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0),
            frameSize=(-1.77, 1.77, -1.0, 1.0),
            parent=self.base.aspect2d
        )

        self._build_header()
        self._build_feedback()
        self._build_pads()
        self._build_info_bar()

        self.base.taskMgr.add(self._animate, "DrumsAnimation")
        self.hide()

    # ====================================================
    # 3D DRUM WORLD
    # ====================================================

    def _build_drum_3d_world(self):
        self.drum_world = NodePath("DrumWorld")
        self.drum_world.reparentTo(self.base.render)

        self.drum_rings = []
        configs = [
            (2.2, (0.8, 0.2, 0.9, 0.45), 3.0, (0, 30, 0)),
            (3.0, (0.1, 0.7, 1.0, 0.35), 2.0, (-20, 0, 0)),
            (1.4, (1.0, 0.5, 0.1, 0.50), 2.5, (10, -15, 0)),
        ]
        for radius, color, thick, tilt in configs:
            ring = self._make_ring(radius, color, thick)
            ring.reparentTo(self.drum_world)
            ring.setPos(0, 3.5, 0.5)
            ring.setHpr(*tilt)
            self.drum_rings.append(ring)

        # Grid floor
        lines = LineSegs("DrumGrid")
        lines.setThickness(1.0)
        lines.setColor(0.4, 0.1, 0.5, 0.2)
        for i in range(13):
            v = -3.0 + i * 0.5
            lines.moveTo(Point3(-3.5, 4.0, v))
            lines.drawTo(Point3(3.5, 4.0, v))
            lines.moveTo(Point3(v, 4.0, -3.5))
            lines.drawTo(Point3(v, 4.0, 3.5))
        geom = lines.create()
        self.drum_world.attachNewNode(geom)

    def _make_ring(self, radius, color, thickness, segments=64):
        lines = LineSegs()
        lines.setThickness(thickness)
        lines.setColor(*color)
        for i in range(segments + 1):
            a = (i / segments) * math.pi * 2
            x, z = math.cos(a) * radius, math.sin(a) * radius
            if i == 0:
                lines.moveTo(Point3(x, 0, z))
            else:
                lines.drawTo(Point3(x, 0, z))
        return NodePath(lines.create())

    # ====================================================
    # HUD COMPONENTS
    # ====================================================

    def _build_header(self):
        self.title_banner = DirectFrame(
            parent=self.frame,
            frameColor=(0.04, 0.01, 0.09, 0.90),
            frameSize=(-0.85, 0.85, -0.075, 0.075),
            pos=(0, 0, 0.875)
        )
        self.title = DirectLabel(
            parent=self.title_banner,
            text="[+]  H O L O   D R U M   M A T R I X  [+]",
            scale=0.048,
            text_fg=Vec4(0.9, 0.4, 1.0, 1.0),
            text_align=TextNode.ACenter,
            relief=None,
            pos=(0, 0, 0.015)
        )
        self.instruction = DirectLabel(
            parent=self.title_banner,
            text="EXTEND FINGERS OR HOVER ZONES  |  6 PADS  |  VELOCITY SENSITIVE",
            scale=0.020,
            text_fg=Vec4(0.75, 0.6, 0.9, 0.85),
            text_align=TextNode.ACenter,
            relief=None,
            pos=(0, 0, -0.040)
        )

    def _build_feedback(self):
        self.feedback_display = DirectLabel(
            parent=self.frame,
            text="*  READY  --  POSITION HAND IN DRUM FIELD",
            scale=0.036,
            text_fg=Vec4(0.8, 0.5, 1.0, 1.0),
            text_align=TextNode.ACenter,
            relief=None,
            pos=(0, 0, 0.56)
        )
        self.bpm_display = DirectLabel(
            parent=self.frame,
            text="BPM: ---  |  BEATS: 0",
            scale=0.025,
            text_fg=Vec4(0.5, 0.75, 1.0, 0.75),
            text_align=TextNode.ACenter,
            relief=None,
            pos=(0, 0, 0.50)
        )

    def _build_pads(self):
        self.pad_frames = []
        self.pad_icon_labels = []
        self.pad_name_labels = []
        self.pad_finger_labels = []

        n = len(self.PADS)
        pad_w = 0.26
        pad_h = 0.48
        gap = 0.025
        total_w = n * pad_w + (n - 1) * gap
        start_x = -total_w / 2.0 + pad_w / 2.0

        for i, pad in enumerate(self.PADS):
            px = start_x + i * (pad_w + gap)
            py = -0.15

            frame = DirectFrame(
                parent=self.frame,
                frameColor=pad["color"],
                frameSize=(-pad_w / 2.0, pad_w / 2.0, -pad_h / 2.0, pad_h / 2.0),
                pos=(px, 0, py)
            )
            icon_lbl = DirectLabel(
                parent=frame,
                text=pad["emoji"],
                scale=0.085,
                text_fg=Vec4(1, 1, 1, 0.9),
                text_align=TextNode.ACenter,
                relief=None,
                pos=(0, 0, 0.08)
            )
            name_lbl = DirectLabel(
                parent=frame,
                text=pad["name"],
                scale=0.036,
                text_fg=Vec4(1, 1, 1, 1),
                text_align=TextNode.ACenter,
                relief=None,
                pos=(0, 0, -0.05)
            )
            finger_lbl = DirectLabel(
                parent=frame,
                text=f"[{pad['finger']}]",
                scale=0.022,
                text_fg=Vec4(0.9, 0.9, 0.9, 0.78),
                text_align=TextNode.ACenter,
                relief=None,
                pos=(0, 0, -0.16)
            )
            self.pad_frames.append(frame)
            self.pad_icon_labels.append(icon_lbl)
            self.pad_name_labels.append(name_lbl)
            self.pad_finger_labels.append(finger_lbl)

    def _build_info_bar(self):
        self.info_bar = DirectFrame(
            parent=self.frame,
            frameColor=(0.04, 0.01, 0.08, 0.80),
            frameSize=(-0.95, 0.95, -0.045, 0.045),
            pos=(0, 0, -0.84)
        )
        self.info_label = DirectLabel(
            parent=self.info_bar,
            text="[ H ] HOME  |  [ P ] PIANO  |  [FIST] = DRUMS  |  FINGER EXTENDS TRIGGER PADS",
            scale=0.022,
            text_fg=Vec4(0.6, 0.5, 0.9, 0.8),
            text_align=TextNode.ACenter,
            relief=None,
            pos=(0, 0, -0.010)
        )

    # ====================================================
    # ANIMATION TASK
    # ====================================================

    def _animate(self, task):
        if not self._alive:
            return task.done

        dt = globalClock.getDt()  # noqa
        self.pulse_phase = (self.pulse_phase + dt * 3.5) % (math.pi * 2)

        # Rotate drum rings
        if hasattr(self, 'drum_world') and not self.drum_world.isEmpty():
            if len(self.drum_rings) >= 3:
                self.drum_rings[0].setH(self.drum_rings[0].getH() + dt * 30.0)
                self.drum_rings[1].setH(self.drum_rings[1].getH() - dt * 20.0)
                self.drum_rings[2].setH(self.drum_rings[2].getH() + dt * 48.0)
                self.drum_rings[2].setR(self.drum_rings[2].getR() + dt * 12.0)

        # Fade pad glows
        now = time.time()
        for i, pad in enumerate(self.PADS):
            elapsed = now - self.hit_timers.get(pad["id"], -999)
            if elapsed < 0.35:
                glow = max(0.0, 1.0 - elapsed / 0.35)
                ac = pad["active_color"]
                bc = pad["color"]
                f = self.pad_frames[i]
                f["frameColor"] = (
                    bc[0] + (ac[0] - bc[0]) * glow,
                    bc[1] + (ac[1] - bc[1]) * glow,
                    bc[2] + (ac[2] - bc[2]) * glow,
                    bc[3] + (ac[3] - bc[3]) * glow
                )
                # Scale pulse on hit
                scale_boost = 1.0 + 0.06 * glow
                f.setScale(scale_boost)
            else:
                self.pad_frames[i]["frameColor"] = pad["color"]
                self.pad_frames[i].setScale(1.0)

        return task.cont

    # ====================================================
    # UPDATE — CALLED EACH FRAME FROM MAIN
    # ====================================================

    def update(self, hand):
        if hand is None:
            self._reset_pads()
            return

        lm = hand.landmark

        # ---- Finger extension detection ----
        # For each finger, check if tip is above pip (Y is inverted)
        index_up  = lm[8].y  < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up   = lm[16].y < lm[14].y
        pinky_up  = lm[20].y < lm[18].y
        thumb_up  = lm[4].x  < lm[3].x  # Thumb: check X (relative to hand side)

        fingers_up = {
            "index": index_up,
            "middle": middle_up,
            "ring": ring_up,
            "pinky": pinky_up,
            "thumb": thumb_up,
        }

        triggered_drum = None

        # Priority-based finger → drum assignment
        # Single finger gestures
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
            # All four up = RIDE
            triggered_drum = "ride"
        else:
            # Spatial X-zone fallback
            x = lm[9].x  # hand center (middle knuckle)
            for pad in self.PADS:
                z0, z1 = pad["zone"]
                if z0 <= x < z1:
                    triggered_drum = pad["id"]
                    break
            if triggered_drum is None:
                triggered_drum = "snare"  # default

        now = time.time()
        if triggered_drum and (
            triggered_drum != self.last_drum or
            (now - self.last_time > self.cooldown)
        ):
            self._hit_pad(triggered_drum, now)

    def _hit_pad(self, drum_id, now):
        self.last_drum = drum_id
        self.last_time = now
        self.hit_timers[drum_id] = now

        # Play audio
        if hasattr(self.sound_manager, "play_drum"):
            self.sound_manager.play_drum(drum_id)

        # Find pad display info
        pad_info = next((p for p in self.PADS if p["id"] == drum_id), None)
        if pad_info:
            name = pad_info["name"]
            emoji = pad_info["emoji"]
            self.feedback_display["text"] = f"{emoji}  HIT:  [ {name} ]  {emoji}"
            self.feedback_display["text_fg"] = Vec4(1.0, 0.5, 0.9, 1.0)

        # Beat counting + BPM
        self.beat_count += 1
        self.beat_times.append(now)
        self.beat_times = [t for t in self.beat_times if now - t <= 10.0]
        if len(self.beat_times) >= 2:
            span = self.beat_times[-1] - self.beat_times[0]
            if span > 0:
                self.bpm = int((len(self.beat_times) - 1) / span * 60)
        self.bpm_display["text"] = f"BPM: {self.bpm}  |  BEATS: {self.beat_count}"

    def _reset_pads(self):
        now = time.time()
        for i, pad in enumerate(self.PADS):
            elapsed = now - self.hit_timers.get(pad["id"], -999)
            if elapsed > 0.35:
                self.pad_frames[i]["frameColor"] = pad["color"]
                self.pad_frames[i].setScale(1.0)

    def show(self):
        self.frame.show()
        if hasattr(self, 'drum_world'):
            self.drum_world.show()

    def hide(self):
        self.frame.hide()
        if hasattr(self, 'drum_world'):
            self.drum_world.hide()
        self._reset_pads()

    def cleanup(self):
        self._alive = False
        try:
            self.base.taskMgr.remove("DrumsAnimation")
        except Exception:
            pass
        try:
            if hasattr(self, 'drum_world'):
                self.drum_world.removeNode()
        except Exception:
            pass
        try:
            self.frame.destroy()
        except Exception:
            pass