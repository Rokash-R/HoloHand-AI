import math
import os
import random
import time
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton
from direct.showbase.ShowBaseGlobal import globalClock
from panda3d.core import (
    NodePath,
    Vec4,
    Point3,
    TransparencyAttrib,
    GeomVertexFormat,
    GeomVertexData,
    GeomVertexWriter,
    Geom,
    GeomTriangles,
    GeomNode,
    Texture,
    TexturePool,
    BillboardEffect,
    LineSegs,
    TextNode,
    CardMaker
)


def create_quad_mesh(texture, width=0.15, height=0.15):
    """Creates a 2-sided textured planar quad."""
    format_data = GeomVertexFormat.getV3n3c4t2()
    vdata = GeomVertexData("quad", format_data, GeomVertexData.UHDynamic)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color = GeomVertexWriter(vdata, "color")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    w2 = width * 0.5
    h2 = height * 0.5

    corners = [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    for (vx, vz), (u, v) in zip(corners, uvs):
        vertex.addData3(vx, 0.0, vz)
        normal.addData3(0.0, -1.0, 0.0)
        color.addData4(1.0, 1.0, 1.0, 1.0)
        texcoord.addData2(u, v)

    geom = Geom(vdata)
    tris = GeomTriangles(GeomVertexData.UHDynamic)
    tris.addVertices(0, 1, 2)
    tris.addVertices(0, 2, 3)
    tris.closePrimitive()
    geom.addPrimitive(tris)

    node = GeomNode("quad_node")
    node.addGeom(geom)
    np = NodePath(node)
    np.setTexture(texture, 1)
    np.setTransparency(TransparencyAttrib.MAlpha)
    np.setEffect(BillboardEffect.makePointEye())
    return np


class GestureFx:
    """
    Gesture FX Studio - Authentic Interactive Holographic Visual Synthesis Studio
    Directly modeled after the futuristic holographic studio design.
    """

    AVAILABLE_EFFECTS = ["ALL", "ROSE & PETALS", "GLOW TRAIL", "ENERGY WAVES"]

    def __init__(self, base):
        self.base = base
        self.active = False

        # Configuration & Parameters
        self.current_effect_mode = "ALL"
        self.intensity = 1.0
        self.max_particles = 180

        # State tracking
        self.primary_hand_world_pos = Point3(0, 0, 0)
        self.has_active_hand = False
        self.last_emission_time = 0.0
        self.last_burst_time = 0.0
        self.burst_cooldown = 0.8
        self.prev_pinch_state = False
        self.last_ui_action_time = 0.0
        self.ui_action_cooldown = 0.5

        # Load authentic textures
        tex_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "textures"))
        from panda3d.core import Filename
        fn_rose = Filename.fromOsSpecific(os.path.join(tex_dir, "rose_glow.png"))
        fn_petal = Filename.fromOsSpecific(os.path.join(tex_dir, "petal_glow.png"))
        fn_gold = Filename.fromOsSpecific(os.path.join(tex_dir, "gold_spark.png"))
        fn_bg = Filename.fromOsSpecific(os.path.join(tex_dir, "gesture_fx_bg.jpg"))

        self.tex_rose = TexturePool.loadTexture(fn_rose)
        self.tex_petal = TexturePool.loadTexture(fn_petal)
        self.tex_gold = TexturePool.loadTexture(fn_gold)
        self.tex_bg = TexturePool.loadTexture(fn_bg)

        # Particles container
        self.particles = []

        # Root Scene Graph Node in 3D render
        self.fx_root = self.base.render.attachNewNode("GestureFXRoot")
        self.fx_root.setTransparency(TransparencyAttrib.MAlpha)
        self.fx_root.setLightOff()

        # Build UI
        self._build_ui()
        self.hide()

    def _build_ui(self):
        """Constructs high-res futuristic studio interface matching model image."""
        self.ui_root = self.base.aspect2d.attachNewNode("GestureFXUI")
        self.ui_root.setBin("fixed", 40)
        self.ui_root.setDepthTest(False)
        self.ui_root.setDepthWrite(False)

        # Colorful vivid background — no image file
        aspect = self.base.getAspectRatio()
        cm = CardMaker("GestureFXBG")
        cm.setFrame(-aspect, aspect, -1.0, 1.0)
        self.bg_card = self.ui_root.attachNewNode(cm.generate())
        self.bg_card.setBin("background", 5)
        # Deep indigo-purple background for holographic FX look
        self.bg_card.setColor(0, 0, 0, 0)
        self.bg_card.setTransparency(TransparencyAttrib.MAlpha)

        # Side Architectural Studio Flanks (Left & Right ONLY, leaving center completely clear)
        self._build_side_studio_flanks()

        # Top Header Bar - Increased font sizes
        self.header_frame = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.015, 0.04, 0.10, 0.90),
            frameSize=(-1.68, 1.68, -0.075, 0.075),
            pos=(0, 0, 0.88)
        )
        self.header_frame.setTransparency(TransparencyAttrib.MAlpha)

        # Cyan Neon Accent Line on top of header
        DirectFrame(
            parent=self.header_frame,
            frameColor=(0.0, 0.85, 1.0, 0.95),
            frameSize=(-1.67, 1.67, 0.070, 0.075),
            pos=(0, 0, 0)
        )

        # Return Home button in header top-left (matches Image 3)
        self.btn_home = DirectButton(
            parent=self.header_frame,
            text="< RETURN HOME",
            text_scale=0.026,
            text_fg=Vec4(0.85, 0.95, 1.0, 1),
            text_pos=(0, -0.008),
            frameSize=(-0.15, 0.15, -0.040, 0.040),
            frameColor=(0.04, 0.16, 0.32, 0.92),
            relief=1,
            borderWidth=(0.003, 0.003),
            pos=(-1.45, 0, -0.005),
            command=self._on_home_clicked
        )
        self.btn_home.setTransparency(TransparencyAttrib.MAlpha)

        self.title_label = DirectLabel(
            parent=self.header_frame,
            text="GESTURE FX STUDIO",
            text_fg=Vec4(0.0, 0.95, 1.0, 1),
            text_scale=0.062,
            frameColor=(0, 0, 0, 0),
            pos=(-0.85, 0, -0.020)
        )

        self.subtitle_label = DirectLabel(
            parent=self.header_frame,
            text="HOLOGRAPHIC LIGHT & FLORAL GESTURE SYNTHESIS",
            text_fg=Vec4(0.70, 0.90, 1.0, 0.95),
            text_scale=0.032,
            frameColor=(0, 0, 0, 0),
            pos=(-0.05, 0, -0.016)
        )

        # Left Controls Panel (Effect mode selector + Intensity)
        self.panel_left = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.012, 0.04, 0.09, 0.86),
            frameSize=(-0.35, 0.35, -0.42, 0.42),
            relief=1,
            borderWidth=(0.006, 0.006),
            pos=(-1.28, 0, 0.12)
        )
        self.panel_left.setTransparency(TransparencyAttrib.MAlpha)

        # Top cyan border of left panel
        DirectFrame(
            parent=self.panel_left,
            frameColor=(0.0, 0.85, 1.0, 0.95),
            frameSize=(-0.345, 0.345, 0.412, 0.418),
            pos=(0, 0, 0)
        )

        DirectLabel(
            parent=self.panel_left,
            text="EFFECT SELECT",
            text_fg=Vec4(0.15, 0.90, 1.0, 1),
            text_scale=0.036, # Increased font size
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.33)
        )

        self.mode_buttons = {}
        self.mode_btn_bounds = {}
        modes = [
            ("ALL EFFECTS", "ALL"),
            ("ROSE & PETALS", "ROSE & PETALS"),
            ("GLOW TRAIL", "GLOW TRAIL"),
            ("ENERGY WAVES", "ENERGY WAVES")
        ]
        btn_y = 0.22
        for label, mode_key in modes:
            btn = DirectButton(
                parent=self.panel_left,
                text=label,
                text_scale=0.030,
                text_fg=Vec4(0.9, 0.98, 1.0, 1),
                text_pos=(0, -0.010),
                frameSize=(-0.29, 0.29, -0.045, 0.045),
                frameColor=(0.05, 0.18, 0.32, 0.92),
                relief=1,
                borderWidth=(0.003, 0.003),
                pos=(0, 0, btn_y),
                command=self.set_effect_mode,
                extraArgs=[mode_key]
            )
            btn.setTransparency(TransparencyAttrib.MAlpha)
            self.mode_buttons[mode_key] = btn
            # Calculate absolute aspect2d bounds for hand hover/pinch detection
            # panel_left is at x=-1.28, z=0.12. Button pos is (0, 0, btn_y) relative to panel
            center_x = -1.28
            center_z = 0.12 + btn_y
            self.mode_btn_bounds[mode_key] = {
                "center_x": center_x,
                "center_z": center_z,
                "half_w": 0.4,
                "half_h": 0.08
            }
            btn_y -= 0.095

        # Intensity control
        DirectLabel(
            parent=self.panel_left,
            text="INTENSITY",
            text_fg=Vec4(0.15, 0.90, 1.0, 1),
            text_scale=0.032, # Increased font size
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.19)
        )

        self.lbl_intensity = DirectLabel(
            parent=self.panel_left,
            text="NORMAL (1.0x)",
            text_fg=Vec4(1.0, 0.92, 0.35, 1),
            text_scale=0.028, # Increased font size
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.25)
        )

        btn_dec = DirectButton(
            parent=self.panel_left,
            text="-",
            text_scale=0.045, # Larger button text
            text_fg=Vec4(1, 1, 1, 1),
            text_pos=(0, -0.012),
            frameSize=(-0.075, 0.075, -0.04, 0.04),
            frameColor=(0.06, 0.24, 0.40, 0.9),
            relief=1,
            pos=(-0.14, 0, -0.33),
            command=self._adjust_intensity,
            extraArgs=[-0.25]
        )
        btn_dec.setTransparency(TransparencyAttrib.MAlpha)
        self.btn_dec = btn_dec

        btn_inc = DirectButton(
            parent=self.panel_left,
            text="+",
            text_scale=0.045,
            text_fg=Vec4(1, 1, 1, 1),
            text_pos=(0, -0.012),
            frameSize=(-0.075, 0.075, -0.04, 0.04),
            frameColor=(0.06, 0.24, 0.40, 0.9),
            relief=1,
            pos=(0.14, 0, -0.33),
            command=self._adjust_intensity,
            extraArgs=[0.25]
        )
        btn_inc.setTransparency(TransparencyAttrib.MAlpha)
        self.btn_inc = btn_inc

        self.intensity_btn_bounds = {
            "dec": {
                "center_x": -1.28 - 0.14,
                "center_z": 0.12 - 0.33,
                "half_w": 0.09,
                "half_h": 0.05
            },
            "inc": {
                "center_x": -1.28 + 0.14,
                "center_z": 0.12 - 0.33,
                "half_w": 0.09,
                "half_h": 0.05
            }
        }

        # Right Gesture Guide Panel - Increased font sizes
        self.panel_right = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.012, 0.04, 0.09, 0.86),
            frameSize=(-0.35, 0.35, -0.42, 0.42),
            relief=1,
            borderWidth=(0.006, 0.006),
            pos=(1.28, 0, 0.12)
        )
        self.panel_right.setTransparency(TransparencyAttrib.MAlpha)

        DirectFrame(
            parent=self.panel_right,
            frameColor=(0.0, 0.85, 1.0, 0.95),
            frameSize=(-0.345, 0.345, 0.412, 0.418),
            pos=(0, 0, 0)
        )

        DirectLabel(
            parent=self.panel_right,
            text="GESTURE CONTROLS",
            text_fg=Vec4(0.15, 0.90, 1.0, 1),
            text_scale=0.036, # Increased font size
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.33)
        )

        guide_texts = [
            ("HAND PINCH", "Hover button & Pinch to select"),
            ("MOUSE CLICK", "Click buttons directly with mouse"),
            ("PINCH & MOVE", "Stream trails in movement direction"),
            ("PINCH BURST", "Pinch in center for visual burst"),
        ]
        gy = 0.22
        for title, desc in guide_texts:
            DirectLabel(
                parent=self.panel_right,
                text=title,
                text_fg=Vec4(0.25, 0.95, 0.85, 1),
                text_scale=0.028,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.30, 0, gy)
            )
            DirectLabel(
                parent=self.panel_right,
                text=desc,
                text_fg=Vec4(0.75, 0.88, 1.0, 0.90),
                text_scale=0.024,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                pos=(-0.30, 0, gy - 0.042)
            )
            gy -= 0.105

        # Telemetry Pill at Bottom
        self.status_pill = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.015, 0.06, 0.14, 0.88),
            frameSize=(-1.25, 1.25, -0.05, 0.05),
            relief=1,
            borderWidth=(0.005, 0.005),
            pos=(0, 0, -0.88)
        )
        self.status_pill.setTransparency(TransparencyAttrib.MAlpha)

        self.lbl_telemetry = DirectLabel(
            parent=self.status_pill,
            text="GESTURE FX READY - SHOW HAND TO EMIT HOLOGRAPHIC PETALS & LIGHT",
            text_fg=Vec4(0.2, 0.95, 0.85, 1),
            text_scale=0.030,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.010)
        )

        self._build_pointer()
        self._refresh_ui_highlight()

    def _build_pointer(self):
        self.pointer_node = self.ui_root.attachNewNode("GestureFXPointer")
        self.pointer_node.setBin("fixed", 65)
        self.pointer_node.setDepthTest(False)
        self.pointer_node.setDepthWrite(False)

        # Outer glowing ring
        segs = LineSegs("pointer_ring")
        segs.setThickness(2.8)
        segs.setColor(0.0, 0.95, 1.0, 0.90)
        for i in range(33):
            th = (i / 32.0) * 2.0 * math.pi
            segs.drawTo(0.034 * math.cos(th), 0.0, 0.034 * math.sin(th))
        self.pointer_ring = self.pointer_node.attachNewNode(segs.create())

        # Inner bright core
        dot = LineSegs("pointer_dot")
        dot.setThickness(5.5)
        dot.setColor(1.0, 0.95, 0.40, 1.0)
        dot.drawTo(0, 0, 0)
        self.pointer_dot = self.pointer_node.attachNewNode(dot.create())

        self.pointer_node.hide()

    def _build_side_studio_flanks(self):
        """Constructs rich acoustic diffuser towers on Left and Right wings ONLY,
        preserving the entire center stage as clean dark space for holographic interaction."""
        aspect = self.base.getAspectRatio()

        # Left Studio Wing Frame
        left_flank = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.012, 0.025, 0.06, 0.92),
            frameSize=(-aspect, -0.92, -1.0, 1.0),
        )
        left_flank.setBin("background", 6)

        for i in range(5):
            sx = -aspect + 0.04 + i * 0.065
            if sx + 0.035 < -0.92:
                DirectFrame(
                    parent=left_flank,
                    frameColor=(0.22, 0.15, 0.09, 0.85),
                    frameSize=(sx, sx + 0.035, -0.95, 0.95),
                )

        # Left Vertical Cyan LED Divider
        DirectFrame(
            parent=left_flank,
            frameColor=(0.0, 0.85, 1.0, 0.80),
            frameSize=(-0.925, -0.920, -1.0, 1.0),
        )

        # Right Studio Wing Frame
        right_flank = DirectFrame(
            parent=self.ui_root,
            frameColor=(0.012, 0.025, 0.06, 0.92),
            frameSize=(0.92, aspect, -1.0, 1.0),
        )
        right_flank.setBin("background", 6)

        for i in range(5):
            sx = 0.92 + 0.04 + i * 0.065
            if sx + 0.035 < aspect:
                DirectFrame(
                    parent=right_flank,
                    frameColor=(0.22, 0.15, 0.09, 0.85),
                    frameSize=(sx, sx + 0.035, -0.95, 0.95),
                )

        # Right Vertical Cyan LED Divider
        DirectFrame(
            parent=right_flank,
            frameColor=(0.0, 0.85, 1.0, 0.80),
            frameSize=(0.920, 0.925, -1.0, 1.0),
        )

    def _on_home_clicked(self):
        if hasattr(self.base, "set_mode"):
            self.base.set_mode("HOME")

    def set_effect_mode(self, mode):
        self.current_effect_mode = mode
        self._refresh_ui_highlight()
        # Clean existing particles so user immediately sees only the selected effect
        self._clear_all_particles()

    def _refresh_ui_highlight(self, hovered_key=None):
        for mode_key, btn in self.mode_buttons.items():
            if mode_key == self.current_effect_mode:
                btn["frameColor"] = (0.05, 0.55, 0.95, 0.98)
                btn["text_fg"] = Vec4(1, 1, 1, 1)
            elif mode_key == hovered_key:
                btn["frameColor"] = (0.08, 0.38, 0.65, 0.98)
                btn["text_fg"] = Vec4(0.10, 1.0, 0.85, 1)
            else:
                btn["frameColor"] = (0.05, 0.18, 0.32, 0.92)
                btn["text_fg"] = Vec4(0.80, 0.92, 1.0, 0.85)

        if hasattr(self, "btn_dec") and hasattr(self, "btn_inc"):
            self.btn_dec["frameColor"] = (0.12, 0.45, 0.70, 1.0) if hovered_key == "dec" else (0.06, 0.24, 0.40, 0.9)
            self.btn_inc["frameColor"] = (0.12, 0.45, 0.70, 1.0) if hovered_key == "inc" else (0.06, 0.24, 0.40, 0.9)

    def click_at_cursor(self, cursor_position):
        """Select effect mode based on cursor position, used by click actions.
        Returns True if a UI element was activated.
        """
        if cursor_position is None:
            return False
        cursor_x, cursor_z = cursor_position
        # Return Home button
        if abs(cursor_x - (-1.45)) <= 0.22 and abs(cursor_z - 0.88) <= 0.08:
            self._on_home_clicked()
            return True
        # Mode buttons
        for mode_key, bounds in self.mode_btn_bounds.items():
            if abs(cursor_x - bounds["center_x"]) <= bounds["half_w"] and abs(cursor_z - bounds["center_z"]) <= bounds["half_h"]:
                self.set_effect_mode(mode_key)
                self.lbl_telemetry["text"] = f"GESTURE SELECTED: {mode_key}"
                self.lbl_telemetry["text_fg"] = Vec4(0.2, 1.0, 0.7, 1)
                return True
        # Intensity buttons
        if hasattr(self, "intensity_btn_bounds"):
            dec = self.intensity_btn_bounds["dec"]
            inc = self.intensity_btn_bounds["inc"]
            if abs(cursor_x - dec["center_x"]) <= dec["half_w"] and abs(cursor_z - dec["center_z"]) <= dec["half_h"]:
                self._adjust_intensity(-0.25)
                return True
            elif abs(cursor_x - inc["center_x"]) <= inc["half_w"] and abs(cursor_z - inc["center_z"]) <= inc["half_h"]:
                self._adjust_intensity(0.25)
                return True
        return False
    def _adjust_intensity(self, delta):
        """Adjust the intensity multiplier and update the intensity label."""
        self.intensity = max(0.5, min(2.5, self.intensity + delta))
        if self.intensity <= 0.6:
            text = f"LOW ({self.intensity:.1f}x)"
        elif self.intensity <= 1.2:
            text = f"NORMAL ({self.intensity:.1f}x)"
        elif self.intensity <= 1.8:
            text = f"HIGH ({self.intensity:.1f}x)"
        else:
            text = f"BURST ({self.intensity:.1f}x)"
        self.lbl_intensity["text"] = text

    # ========================================================
    # ACTIVATION & LIFECYCLE
    # ========================================================

    def show(self):
        self.active = True
        self.ui_root.show()
        self.fx_root.show()
        if not self.base.taskMgr.hasTaskNamed("GestureFXAnimationTask"):
            self.base.taskMgr.add(self._animate_task, "GestureFXAnimationTask")

    def hide(self):
        self.active = False
        self.ui_root.hide()
        self.fx_root.hide()
        if hasattr(self, "pointer_node"):
            self.pointer_node.hide()
        self.cursor_pos = None
        self.smooth_tip_world = None
        self.prev_hand_world_pos = None
        self._hover_target = None
        self._hover_start_time = 0.0
        if self.base.taskMgr.hasTaskNamed("GestureFXAnimationTask"):
            self.base.taskMgr.remove("GestureFXAnimationTask")
        self._clear_all_particles()

    def _clear_all_particles(self):
        for p in self.particles:
            try:
                node = p.get("node")
                if node and not node.isEmpty():
                    node.removeNode()
            except Exception:
                pass
        self.particles.clear()

    def cleanup(self):
        self.hide()
        try:
            self.ui_root.removeNode()
            self.fx_root.removeNode()
        except Exception:
            pass

    # ========================================================
    # COORDINATE CONVERSION (Exact alignment with hand skeleton)
    # ========================================================

    def _landmark_to_aspect2d(self, lm):
        """Maps MediaPipe landmarks directly to 2D aspect2d coordinates."""
        aspect = self.base.getAspectRatio()
        if hasattr(lm, "x"):
            lx, ly = lm.x, lm.y
        elif isinstance(lm, dict):
            lx, ly = lm.get("x", 0.5), lm.get("y", 0.5)
        else:
            lx, ly = lm[0], lm[1]
        ax = (lx - 0.5) * 2.0 * aspect
        az = (0.5 - ly) * 2.0
        return ax, az

    def _landmark_to_screen_world(self, lm):
        """Maps MediaPipe landmarks accurately to 3D space matching hand model."""
        aspect = self.base.getAspectRatio()
        if hasattr(lm, "x"):
            lx, ly = lm.x, lm.y
        elif isinstance(lm, dict):
            lx, ly = lm.get("x", 0.5), lm.get("y", 0.5)
        else:
            lx, ly = lm[0], lm[1]

        # In HandModel: sx = (x - 0.5) * 2 * aspect, sz = (0.5 - y) * 2
        # Camera is at (0, -12, 0.4). In front of camera at Y=-6.0:
        # 1 unit at Y=-6.0 corresponds closely to aspect2d!
        sx = (lx - 0.5) * 2.0 * aspect * 3.5
        sz = (0.5 - ly) * 2.0 * 2.8
        sy = 0.0
        return Point3(sx, sy, sz)

    # ========================================================
    # PARTICLE GENERATION (UPWARD ROSE PETALS & GOLDEN PARTICLES)
    # ========================================================

    def _spawn_petal(self, pos, vel=None, scale=0.24, life=2.4):
        """
        Spawns a glowing rose petal that flows naturally in the movement direction.
        """
        node = create_quad_mesh(self.tex_petal, width=scale, height=scale * 1.35)
        node.reparentTo(self.fx_root)
        pos_pt = Point3(pos[0], pos[1], pos[2])
        node.setPos(pos_pt)

        if vel is None:
            upward_speed = random.uniform(0.45, 1.10)
            vel_pt = Point3(random.uniform(-0.18, 0.18), 0.0, upward_speed)
        else:
            vel_pt = Point3(vel[0], vel[1], vel[2])

        p = {
            "node": node,
            "pos": pos_pt,
            "vel": vel_pt,
            "life": life,
            "max_life": life,
            "scale": scale,
            "type": "petal",
            "rot": random.uniform(0, 360),
            "rot_vel": random.uniform(-45, 45),
            "base_color": Vec4(1.0, 0.45, 0.70, 0.98)
        }
        self.particles.append(p)

    def _spawn_gold_spark(self, pos, vel, scale=0.22, life=1.2):
        """Spawns brilliant, rich golden glowing spark particles."""
        node = create_quad_mesh(self.tex_gold, width=scale, height=scale)
        node.reparentTo(self.fx_root)
        pos_pt = Point3(pos[0], pos[1], pos[2])
        vel_pt = Point3(vel[0], vel[1], vel[2])
        node.setPos(pos_pt)

        p = {
            "node": node,
            "pos": pos_pt,
            "vel": vel_pt,
            "life": life,
            "max_life": life,
            "scale": scale,
            "type": "glow",
            "rot": 0.0,
            "rot_vel": 0.0,
            "base_color": Vec4(1.0, 0.88, 0.16, 1.0) # Rich Luminous Gold
        }
        self.particles.append(p)

    def _spawn_energy_wave(self, center_pos, max_radius=2.5, life=1.6):
        """
        Creates an expanding glowing energy ring wave radiating from hand.
        """
        segs = LineSegs("energy_wave")
        segs.setThickness(3.2)
        segs.setColor(0.75, 0.25, 0.95, 0.90) # Magenta / Violet energy ring matching model image

        points = 64
        r = 0.05
        for i in range(points + 1):
            theta = (i / float(points)) * 2.0 * math.pi
            segs.drawTo(r * math.cos(theta), 0.0, r * math.sin(theta))

        node = NodePath(segs.create())
        node.reparentTo(self.fx_root)
        pos_pt = Point3(center_pos[0], center_pos[1], center_pos[2])
        node.setPos(pos_pt)
        node.setTransparency(TransparencyAttrib.MAlpha)

        p = {
            "node": node,
            "pos": pos_pt,
            "vel": Point3(0, 0, 0),
            "life": life,
            "max_life": life,
            "scale": 1.0,
            "radius": r,
            "max_radius": max_radius,
            "type": "wave",
            "base_color": Vec4(0.85, 0.35, 1.0, 0.92)
        }
        self.particles.append(p)

    def trigger_screen_burst(self, origin_pos=None):
        """
        Triggers an explosion tailored strictly to the selected effect mode.
        """
        if not self.active:
            return

        now = time.monotonic()
        if now - self.last_burst_time < self.burst_cooldown:
            return
        self.last_burst_time = now

        if origin_pos is None:
            origin_pos = self.primary_hand_world_pos

        mode = self.current_effect_mode
        self.lbl_telemetry["text"] = f"✦ {mode} BURST ACTIVATED! ✦"
        self.lbl_telemetry["text_fg"] = Vec4(1.0, 0.95, 0.35, 1)

        # 1. Energy Waves Mode Burst
        if mode in ("ALL", "ENERGY WAVES"):
            self._spawn_energy_wave(origin_pos, max_radius=5.5 * self.intensity, life=1.8)
            self._spawn_energy_wave(origin_pos, max_radius=3.8 * self.intensity, life=1.4)
            self._spawn_energy_wave(origin_pos, max_radius=2.2 * self.intensity, life=1.1)

        # 2. Rose & Petals Mode Burst (Only glowing petals, NO full rose)
        if mode in ("ALL", "ROSE & PETALS"):
            # Medium number of petals, slightly faster outward velocity for a richer burst
            petal_count = int(40 * self.intensity)
            for _ in range(petal_count):
                scatter_pos = Point3(
                    origin_pos[0] + random.uniform(-0.35, 0.35),
                    origin_pos[1],
                    origin_pos[2] + random.uniform(-0.15, 0.25)
                )
                scatter_vel = Point3(
                    random.uniform(-0.5, 0.5) * 1.3,
                    0.0,
                    random.uniform(0.6, 1.4) * 1.3
                )
                self._spawn_petal(scatter_pos, vel=scatter_vel, scale=random.uniform(0.24, 0.36) * self.intensity, life=random.uniform(2.2, 3.2))

        # 3. Glow Trail Mode Burst (Rich luminous golden sparks)
        if mode in ("ALL", "GLOW TRAIL"):
            spark_count = int(42 * self.intensity)
            for i in range(spark_count):
                angle = (i / float(spark_count)) * 2.0 * math.pi + random.uniform(-0.15, 0.15)
                speed = random.uniform(2.2, 5.0)
                vel = Point3(math.cos(angle) * speed, 0.0, math.sin(angle) * speed)
                scale = random.uniform(0.20, 0.32) * self.intensity
                life = random.uniform(1.0, 1.8)
                self._spawn_gold_spark(origin_pos, vel, scale=scale, life=life)

    # ========================================================
    # MAIN PER-FRAME UPDATE (DETECTS HAND & EMITS UPWARD)
    # ========================================================

    def update(self, hands):
        if not self.active:
            return

        now = time.monotonic()

        if not hands or len(hands) == 0:
            self.has_active_hand = False
            self.lbl_telemetry["text"] = "SEARCHING FOR HAND — SHOW HAND IN FRONT OF SENSOR"
            self.lbl_telemetry["text_fg"] = Vec4(0.40, 0.70, 0.90, 0.85)
            self.prev_hand_world_pos = None
            self.cursor_pos = None
            self.smooth_tip_world = None
            if hasattr(self, "pointer_node"):
                self.pointer_node.hide()
            self._refresh_ui_highlight(None)
            return

        self.has_active_hand = True
        primary = hands[0]
        landmarks = None
        if hasattr(primary, "landmark"):
            landmarks = primary.landmark
        elif hasattr(primary, "landmarks"):
            landmarks = primary.landmarks
        elif isinstance(primary, dict):
            landmarks = primary.get("landmarks", primary.get("landmark"))

        if not landmarks or len(landmarks) < 21:
            return

        # Landmark 8 = index fingertip, 4 = thumb tip, 9 = middle MCP
        raw_cx, raw_cz = self._landmark_to_aspect2d(landmarks[8])
        raw_tip = self._landmark_to_screen_world(landmarks[8])
        thumb_tip_world = self._landmark_to_screen_world(landmarks[4])
        palm_world = self._landmark_to_screen_world(landmarks[9])

        # Smooth 2D cursor for rock-steady button targeting
        if not hasattr(self, "cursor_pos") or self.cursor_pos is None:
            self.cursor_pos = (raw_cx, raw_cz)
        else:
            cdist = math.hypot(raw_cx - self.cursor_pos[0], raw_cz - self.cursor_pos[1])
            calpha = min(0.68, max(0.18, 0.22 + cdist * 2.8))
            self.cursor_pos = (
                self.cursor_pos[0] + (raw_cx - self.cursor_pos[0]) * calpha,
                self.cursor_pos[1] + (raw_cz - self.cursor_pos[1]) * calpha
            )
        cursor_x, cursor_z = self.cursor_pos
        if hasattr(self, "pointer_node"):
            self.pointer_node.setPos(cursor_x, 0, cursor_z)
            self.pointer_node.show()

        # Smooth 3D fingertip position for fluid particle emissions
        if not hasattr(self, "smooth_tip_world") or self.smooth_tip_world is None:
            self.smooth_tip_world = Point3(raw_tip)
        else:
            wdist = (raw_tip - self.smooth_tip_world).length()
            walpha = min(0.68, max(0.18, 0.22 + wdist * 1.8))
            self.smooth_tip_world = Point3(
                self.smooth_tip_world[0] + (raw_tip[0] - self.smooth_tip_world[0]) * walpha,
                self.smooth_tip_world[1] + (raw_tip[1] - self.smooth_tip_world[1]) * walpha,
                self.smooth_tip_world[2] + (raw_tip[2] - self.smooth_tip_world[2]) * walpha
            )
        index_tip_world = self.smooth_tip_world
        self.primary_hand_world_pos = index_tip_world

        # Track hand movement vector for directional particle emission
        if not hasattr(self, "prev_hand_world_pos") or self.prev_hand_world_pos is None:
            self.prev_hand_world_pos = Point3(index_tip_world)
            hand_move_dir = Point3(0, 0, 0.5)
        else:
            delta = index_tip_world - self.prev_hand_world_pos
            self.prev_hand_world_pos = Point3(index_tip_world)
            # Smooth directional tracking — gentle multiplier for natural flow
            if delta.length() > 0.01:
                # Blend with previous direction for smoothness
                if not hasattr(self, "_smooth_dir"):
                    self._smooth_dir = Point3(0, 0, 0.5)
                raw_dir = delta * 6.0
                blend = 0.35  # Lower = smoother (more lag), Higher = more responsive
                self._smooth_dir = Point3(
                    self._smooth_dir[0] * (1.0 - blend) + raw_dir[0] * blend,
                    0.0,
                    self._smooth_dir[2] * (1.0 - blend) + raw_dir[2] * blend
                )
                hand_move_dir = self._smooth_dir
            else:
                # Hand is still — gentle upward drift
                if hasattr(self, "_smooth_dir"):
                    self._smooth_dir = Point3(
                        self._smooth_dir[0] * 0.92,
                        0.0,
                        self._smooth_dir[2] * 0.92 + 0.04
                    )
                    hand_move_dir = self._smooth_dir
                else:
                    hand_move_dir = Point3(0, 0, 0.5)

        # Scale-invariant and 3D distance pinch detection
        fa = self.base.getAspectRatio()
        pinch_d = math.hypot((landmarks[4].x - landmarks[8].x) * fa, landmarks[4].y - landmarks[8].y)
        palm_w = math.hypot((landmarks[5].x - landmarks[17].x) * fa, landmarks[5].y - landmarks[17].y)
        palm_len = math.hypot((landmarks[0].x - landmarks[9].x) * fa, landmarks[0].y - landmarks[9].y)
        palm_scale = max(0.025, 0.5 * (palm_w + palm_len))
        ratio = pinch_d / palm_scale
        pinch_dist = (index_tip_world - thumb_tip_world).length()
        is_pinching = (pinch_dist < 0.55) or (ratio < 0.38)
        pinch_edge = is_pinching and not self.prev_pinch_state

        # Check button hover with generous margin
        hovered_key = None
        for mode_key, bounds in self.mode_btn_bounds.items():
            if abs(cursor_x - bounds["center_x"]) <= (bounds["half_w"] + 0.05) and abs(cursor_z - bounds["center_z"]) <= (bounds["half_h"] + 0.035):
                hovered_key = mode_key
                break

        if hovered_key is None and hasattr(self, "intensity_btn_bounds"):
            dec = self.intensity_btn_bounds["dec"]
            inc = self.intensity_btn_bounds["inc"]
            if abs(cursor_x - dec["center_x"]) <= (dec["half_w"] + 0.035) and abs(cursor_z - dec["center_z"]) <= (dec["half_h"] + 0.035):
                hovered_key = "dec"
            elif abs(cursor_x - inc["center_x"]) <= (inc["half_w"] + 0.035) and abs(cursor_z - inc["center_z"]) <= (inc["half_h"] + 0.035):
                hovered_key = "inc"

        # Update hover visual highlighting
        self._refresh_ui_highlight(hovered_key)

        handled_ui_click = False

        # Selection: works by Hover Dwell (0.38s) OR Pinch
        if hovered_key is not None:
            if getattr(self, "_hover_target", None) != hovered_key:
                self._hover_target = hovered_key
                self._hover_start_time = now
            else:
                dwell_time = now - getattr(self, "_hover_start_time", now)
                can_click = (now - self.last_ui_action_time >= self.ui_action_cooldown)
                if (dwell_time >= 0.38 or pinch_edge) and can_click:
                    self.last_ui_action_time = now
                    handled_ui_click = True
                    self._hover_start_time = now + 999.0  # require leaving before re-triggering

                    if hovered_key in self.mode_buttons:
                        self.set_effect_mode(hovered_key)
                        self.lbl_telemetry["text"] = f"✦ GESTURE SELECTED: {hovered_key} ✦"
                        self.lbl_telemetry["text_fg"] = Vec4(0.0, 1.0, 0.85, 1)
                    elif hovered_key == "dec":
                        self._adjust_intensity(-0.25)
                    elif hovered_key == "inc":
                        self._adjust_intensity(0.25)

                    if hasattr(self.base, "sound_manager") and hasattr(self.base.sound_manager, "play_ui_click"):
                        self.base.sound_manager.play_ui_click()
        else:
            self._hover_target = None
            self._hover_start_time = 0.0

        if pinch_edge and not handled_ui_click and (now - self.last_ui_action_time >= 0.3):
            # Screen burst when pinching in center stage
            self.trigger_screen_burst(origin_pos=index_tip_world)

        self.prev_pinch_state = is_pinching

        if not is_pinching and not handled_ui_click:
            self.lbl_telemetry["text"] = f"ACTIVE: {self.current_effect_mode} | PINCH & MOVE TO STREAM TRAILS"
            self.lbl_telemetry["text_fg"] = Vec4(0.25, 0.95, 0.85, 1)

        # If user is currently pinching & moving hand, stream directional visuals!
        if is_pinching and not handled_ui_click:
            mode = self.current_effect_mode
            # Gold sparks follow hand direction smoothly
            spark_vel = Point3(
                hand_move_dir[0] + random.uniform(-0.10, 0.10),
                0.0,
                hand_move_dir[2] + random.uniform(-0.10, 0.10)
            )
            self._spawn_gold_spark(index_tip_world, spark_vel, scale=0.26 * self.intensity, life=1.3)

            if mode in ("ALL", "ROSE & PETALS"):
                petal_vel = Point3(
                    hand_move_dir[0] * 0.8 + random.uniform(-0.08, 0.08),
                    0.0,
                    hand_move_dir[2] * 0.8 + random.uniform(0.15, 0.40)
                )
                self._spawn_petal(index_tip_world, vel=petal_vel, scale=0.28 * self.intensity, life=2.4)

        # Controlled continuous emission
        rate_interval = 0.055 / max(0.5, self.intensity)
        if now - self.last_emission_time >= rate_interval:
            self.last_emission_time = now

            if len(self.particles) < self.max_particles:
                mode = self.current_effect_mode

                # 1. Upward Floating Rose Petals (NO full rose)
                if mode in ("ALL", "ROSE & PETALS"):
                    petal_vel = Point3(
                        hand_move_dir[0] * 0.4 + random.uniform(-0.08, 0.08),
                        0.0,
                        hand_move_dir[2] * 0.4 + random.uniform(0.30, 0.65)
                    )
                    self._spawn_petal(index_tip_world, vel=petal_vel, scale=0.24 * self.intensity, life=2.4)

                # 2. Glowing Golden Sparks & Trails (Higher density and brightness)
                if mode in ("ALL", "GLOW TRAIL"):
                    trail_vel = Point3(
                        hand_move_dir[0] * 0.45 + random.uniform(-0.08, 0.08),
                        0.0,
                        hand_move_dir[2] * 0.45 + random.uniform(0.18, 0.50)
                    )
                    self._spawn_gold_spark(index_tip_world, trail_vel, scale=0.22 * self.intensity, life=1.2)
                    if random.random() < 0.50:
                        palm_vel = Point3(
                            hand_move_dir[0] * 0.35 + random.uniform(-0.06, 0.06),
                            0.0,
                            hand_move_dir[2] * 0.35 + random.uniform(0.12, 0.35)
                        )
                        self._spawn_gold_spark(palm_world, palm_vel, scale=0.18 * self.intensity, life=1.0)

                # 3. Expanding Energy Rings
                if mode in ("ALL", "ENERGY WAVES"):
                    if random.random() < (0.16 * self.intensity):
                        self._spawn_energy_wave(palm_world, max_radius=2.2 * self.intensity, life=1.5)

    # ========================================================
    # ANIMATION TASK
    # ========================================================

    def _animate_task(self, task):
        if not self.active:
            return task.cont

        dt = globalClock.getDt()
        if dt > 0.1:
            dt = 0.033

        alive_particles = []

        for p in self.particles:
            p["life"] -= dt

            if p["life"] <= 0.0:
                node = p.get("node")
                if node and not node.isEmpty():
                    node.removeNode()
                continue

            node = p.get("node")
            if not node or node.isEmpty():
                continue

            norm_life = p["life"] / p["max_life"]
            ptype = p["type"]

            if ptype == "rose":
                bloom_factor = min(1.0, (1.0 - norm_life) * 3.2)
                cur_scale = p["scale"] * (0.35 + 0.65 * bloom_factor)
                node.setScale(cur_scale)

                p["pos"] += p["vel"] * dt
                node.setPos(p["pos"])
                node.setR(node.getR() + p["rot_vel"] * dt)

                alpha = norm_life ** 1.3
                bc = p["base_color"]
                node.setColorScale(bc[0], bc[1], bc[2], bc[3] * alpha)

            elif ptype == "petal":
                # Sway horizontally as it flows UPWARDS
                sway = math.sin(p["life"] * 6.5 + p["rot"]) * 0.25
                p["vel"].setX(p["vel"].getX() + sway * dt)
                p["pos"] += p["vel"] * dt
                node.setPos(p["pos"])
                node.setR(node.getR() + p["rot_vel"] * dt)

                alpha = norm_life ** 1.1
                bc = p["base_color"]
                node.setColorScale(bc[0], bc[1], bc[2], bc[3] * alpha)

            elif ptype == "glow":
                p["pos"] += p["vel"] * dt
                node.setPos(p["pos"])

                pulse = 0.85 + 0.15 * math.sin(p["life"] * 18.0)
                node.setScale(p["scale"] * pulse * norm_life)

                alpha = norm_life ** 0.8
                bc = p["base_color"]
                node.setColorScale(bc[0], bc[1], bc[2], bc[3] * alpha)

            elif ptype == "wave":
                growth = 1.0 - norm_life
                cur_radius = p["max_radius"] * (growth ** 0.72)
                node.setScale(cur_radius / 0.05)

                alpha = (norm_life ** 1.6) * 0.90
                bc = p["base_color"]
                node.setColorScale(bc[0], bc[1], bc[2], bc[3] * alpha)

            alive_particles.append(p)

        self.particles = alive_particles
        return task.cont
