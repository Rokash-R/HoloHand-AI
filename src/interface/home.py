import math
import os

from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton
from direct.gui.OnscreenImage import OnscreenImage
from direct.task import Task

from panda3d.core import (
    TextNode,
    Vec4,
    TransparencyAttrib,
)


class Home:
    """
    HoloHand AI - Grand Holographic Home Interface
    Matches image design:
    - 3 distinct studio cards: PIANO STUDIO (Cyan), DRUMS STUDIO (Magenta/Purple), GESTURE FX STUDIO (Emerald/Teal)
    - [ENTER PIANO], [ENTER DRUMS], [ENTER GESTURE FX] buttons
    - Center console & bottom guidance banner
    - Interactive cursor hover and pinch-to-select
    """

    def __init__(self, base, on_mode_select=None):
        self.base = base
        self.on_mode_select = on_mode_select

        self.hovered_card = None
        self._prev_hovered = None
        self._anim_time = 0.0
        self.cards = {}
        self.card_data = {}

        aspect = self.base.getAspectRatio()

        self.frame = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=(0, 0, 0, 0),
            frameSize=(-aspect, aspect, -1, 1),
        )

        self.background = None
        self.background_image = None

        self._build_background()
        self._build_header()
        self._build_studio_cards()
        self._build_footer()

        self.base.taskMgr.add(
            self._animation_task,
            "HomeAnimationTask"
        )

    # ---------------------------------------------------------
    # BACKGROUND
    # ---------------------------------------------------------

    def _build_background(self):
        possible_paths = [
            os.path.join("assets", "home_studio_background.png"),
            os.path.join("src", "textures", "home_bg.jpg"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    self.background_image = OnscreenImage(
                        image=path,
                        parent=self.frame,
                        pos=(0, 0, 0),
                        scale=(self.base.getAspectRatio(), 1, 1),
                    )
                    self.background_image.setTransparency(TransparencyAttrib.MAlpha)
                    break
                except Exception as error:
                    print("Home background could not load:", error)

        if self.background_image is None:
            self.background = DirectFrame(
                parent=self.frame,
                frameColor=(0.012, 0.016, 0.032, 1),
                frameSize=(-self.base.getAspectRatio(), self.base.getAspectRatio(), -1, 1),
            )

    # ---------------------------------------------------------
    # HEADER (Matches Image 1)
    # ---------------------------------------------------------

    def _build_header(self):
        self.title = DirectLabel(
            parent=self.frame,
            text="HOLOHAND AI",
            text_fg=Vec4(0.85, 0.95, 1.0, 1),
            text_scale=0.088,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.74),
        )

        self.subtitle = DirectLabel(
            parent=self.frame,
            text="AI Spatial Music & Holographic Studio",
            text_fg=Vec4(0.40, 0.78, 0.95, 0.9),
            text_scale=0.026,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.64),
        )

    # ---------------------------------------------------------
    # STUDIO CARDS (Matches Image 1 exactly)
    # ---------------------------------------------------------

    def _build_studio_cards(self):
        # 3 Studio Hero Cards centered horizontally
        # Positions: Piano = -0.63, Drums = 0.0, Gesture FX = 0.63
        card_definitions = [
            {
                "name": "PIANO STUDIO",
                "btn_text": "[ ENTER PIANO ]",
                "mode": "PIANO",
                "position": (-0.63, 0, 0.04),
                "border_color": (0.0, 0.75, 1.0, 0.95),      # Neon Cyan
                "glow_color": (0.0, 0.55, 0.95, 0.35),
                "btn_color": (0.06, 0.28, 0.65, 0.95),
                "btn_hover": (0.12, 0.45, 0.92, 1.0),
            },
            {
                "name": "DRUMS STUDIO",
                "btn_text": "[ ENTER DRUMS ]",
                "mode": "DRUMS",
                "position": (0.0, 0, 0.04),
                "border_color": (0.75, 0.20, 0.85, 0.95),     # Vibrant Purple / Magenta
                "glow_color": (0.60, 0.15, 0.75, 0.35),
                "btn_color": (0.45, 0.12, 0.60, 0.95),
                "btn_hover": (0.65, 0.20, 0.85, 1.0),
            },
            {
                "name": "GESTURE FX STUDIO",
                "btn_text": "[ ENTER GESTURE FX ]",
                "mode": "FX",
                "position": (0.63, 0, 0.04),
                "border_color": (0.0, 0.85, 0.65, 0.95),      # Emerald / Teal
                "glow_color": (0.0, 0.65, 0.50, 0.35),
                "btn_color": (0.05, 0.38, 0.32, 0.95),
                "btn_hover": (0.08, 0.58, 0.48, 1.0),
            },
        ]

        self.card_data = {}
        for item in card_definitions:
            self.card_data[item["mode"]] = item
            self._create_studio_card(item)

    def _create_studio_card(self, item):
        name = item["name"]
        btn_text = item["btn_text"]
        mode = item["mode"]
        x, y, z = item["position"]
        border = item["border_color"]
        btn_c = item["btn_color"]

        # Outer glowing border card
        outer_border = DirectFrame(
            parent=self.frame,
            frameColor=border,
            frameSize=(-0.275, 0.275, -0.325, 0.325),
            pos=(x, y, z),
        )
        outer_border.setTransparency(TransparencyAttrib.MAlpha)

        # Inner dark translucent studio body
        card_inner = DirectFrame(
            parent=outer_border,
            frameColor=(0.02, 0.04, 0.08, 0.94),
            frameSize=(-0.267, 0.267, -0.317, 0.317),
            pos=(0, 0, 0),
        )
        card_inner.setTransparency(TransparencyAttrib.MAlpha)

        # Title
        title = DirectLabel(
            parent=card_inner,
            text=name,
            text_fg=Vec4(0.92, 0.97, 1.0, 1),
            text_scale=0.034,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.14),
        )

        # Divider line
        divider = DirectFrame(
            parent=card_inner,
            frameColor=(border[0], border[1], border[2], 0.35),
            frameSize=(-0.22, 0.22, -0.0015, 0.0015),
            pos=(0, 0, 0.04),
        )
        divider.setTransparency(TransparencyAttrib.MAlpha)

        # [ ENTER STUDIO ] action button
        button = DirectButton(
            parent=card_inner,
            text=btn_text,
            text_fg=Vec4(0.90, 0.98, 1.0, 1),
            text_scale=0.025,
            frameColor=btn_c,
            frameSize=(-0.21, 0.21, -0.055, 0.055),
            relief=1,
            borderWidth=(0.004, 0.004),
            pos=(0, 0, -0.14),
            command=self._select_mode,
            extraArgs=[mode],
        )
        button.setTransparency(TransparencyAttrib.MAlpha)

        self.cards[mode] = {
            "outer": outer_border,
            "inner": card_inner,
            "title": title,
            "divider": divider,
            "button": button,
            "data": item,
            "bounds": (-0.275, 0.275, -0.325, 0.325),
            "world_pos": (x, z),
        }

        # Mouse click support on the card body
        card_inner.bind("mouse1", self._select_mode, [mode])

    def _build_footer(self):
        # Bottom Banner matching Image 1: "Raise hand in front of camera or click any studio with mouse"
        self.banner_frame = DirectFrame(
            parent=self.frame,
            frameColor=(0.015, 0.06, 0.12, 0.85),
            frameSize=(-0.65, 0.65, -0.035, 0.035),
            pos=(0, 0, -0.72),
        )
        self.banner_frame.setTransparency(TransparencyAttrib.MAlpha)

        self.banner_text = DirectLabel(
            parent=self.banner_frame,
            text="Raise hand in front of camera or pinch to select any studio",
            text_fg=Vec4(0.35, 0.75, 0.95, 0.95),
            text_scale=0.020,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.007),
        )

    # ---------------------------------------------------------
    # STUDIO SELECTION & SOUND
    # ---------------------------------------------------------

    def _select_mode(self, mode):
        # Play selection sound if sound manager is available
        if hasattr(self.base, "sound_manager") and hasattr(self.base.sound_manager, "play_ui_click"):
            try:
                self.base.sound_manager.play_ui_click()
            except Exception:
                pass

        if self.on_mode_select:
            self.on_mode_select(mode)

    # ---------------------------------------------------------
    # HAND CURSOR HOVER & HIT TESTING
    # ---------------------------------------------------------

    def update_cursor_hover(self, cursor_pos):
        """
        Updates visual hover feedback based on the 2D cursor position (x, z).
        Returns the name of the hovered studio mode ('PIANO', 'DRUMS', 'FX') or None.
        """
        if cursor_pos is None:
            self.clear_hover()
            return None

        cx, cz = cursor_pos
        hovered = None

        for mode, card in self.cards.items():
            wx, wz = card["world_pos"]
            # Card half-width is 0.275, half-height is 0.325
            if abs(cx - wx) <= 0.285 and abs(cz - wz) <= 0.335:
                hovered = mode
                break

        self.set_hovered_card(hovered)
        return hovered

    def set_hovered_card(self, mode):
        if mode not in self.cards:
            mode = None

        if self.hovered_card != mode:
            # Play gentle audio tick when hovering over a new card
            if mode is not None and hasattr(self.base, "sound_manager") and hasattr(self.base.sound_manager, "play_ui_click"):
                try:
                    self.base.sound_manager.play_ui_click()
                except Exception:
                    pass

        self.hovered_card = mode

    def clear_hover(self):
        self.hovered_card = None
        for mode, card in self.cards.items():
            card["outer"].setScale(1.0)
            item = card["data"]
            orig_x, orig_y, orig_z = item["position"]
            card["outer"].setPos(orig_x, orig_y, orig_z)
            card["button"]["text"] = item["btn_text"]
            card["button"]["text_fg"] = Vec4(0.90, 0.98, 1.0, 1.0)

    # ---------------------------------------------------------
    # ANIMATION
    # ---------------------------------------------------------

    def _animation_task(self, task):
        self._anim_time = task.time

        for mode, card in self.cards.items():
            item = card["data"]
            border = item["border_color"]
            btn = card["button"]
            outer = card["outer"]
            inner = card["inner"]
            orig_x, orig_y, orig_z = item["position"]

            if mode == self.hovered_card:
                pulse = 0.12 * math.sin(self._anim_time * 6.5)
                # Slightly hover: smooth scale up and slight lift
                outer.setScale(1.035)
                outer.setPos(orig_x, orig_y, orig_z + 0.015)

                # Bright glowing border and button
                outer["frameColor"] = (
                    min(1.0, border[0] + 0.20 + pulse),
                    min(1.0, border[1] + 0.20 + pulse),
                    min(1.0, border[2] + 0.20 + pulse),
                    1.0
                )
                inner["frameColor"] = (0.04 + pulse * 0.5, 0.07 + pulse * 0.5, 0.14 + pulse * 0.5, 0.98)
                btn["frameColor"] = item["btn_hover"]
                btn["text"] = "[ PINCH TO ENTER ]"
                btn["text_fg"] = Vec4(0.25, 1.0, 0.85, 1.0)
            else:
                outer.setScale(1.0)
                outer.setPos(orig_x, orig_y, orig_z)
                outer["frameColor"] = border
                inner["frameColor"] = (0.02, 0.04, 0.08, 0.94)
                btn["frameColor"] = item["btn_color"]
                btn["text"] = item["btn_text"]
                btn["text_fg"] = Vec4(0.90, 0.98, 1.0, 1.0)

        # Dynamic guidance banner update on hover
        if hasattr(self, "banner_text") and self.banner_text:
            if self.hovered_card is not None and self.hovered_card in self.cards:
                h_name = self.cards[self.hovered_card]["data"]["name"]
                self.banner_text["text"] = f">> PINCH TO ENTER {h_name} <<"
                self.banner_text["text_fg"] = Vec4(0.15, 1.0, 0.75, 1.0)

        return Task.cont

    # ---------------------------------------------------------
    # TELEMETRY COMPATIBILITY
    # ---------------------------------------------------------

    def update_telemetry(self, hand_detected=False, gesture="UNKNOWN", active_mode="HOME", confidence=1.0):
        if hasattr(self, "banner_text") and self.banner_text:
            if self.hovered_card is not None and self.hovered_card in self.cards:
                h_name = self.cards[self.hovered_card]["data"]["name"]
                self.banner_text["text"] = f">> PINCH TO ENTER {h_name} <<"
                self.banner_text["text_fg"] = Vec4(0.15, 1.0, 0.75, 1.0)
            elif hand_detected:
                self.banner_text["text"] = f"Hand Active | Gesture: {gesture} | Hover over any card & Pinch to Enter"
                self.banner_text["text_fg"] = Vec4(0.20, 0.95, 0.70, 1.0)
            else:
                self.banner_text["text"] = "Raise hand in front of camera or pinch to select any studio"
                self.banner_text["text_fg"] = Vec4(0.35, 0.75, 0.95, 0.95)

    # ---------------------------------------------------------
    # SHOW / HIDE / CLEANUP
    # ---------------------------------------------------------

    def show(self):
        self.frame.show()

    def hide(self):
        self.frame.hide()

    def cleanup(self):
        try:
            self.base.taskMgr.remove("HomeAnimationTask")
        except Exception:
            pass

        if hasattr(self, "frame") and self.frame:
            self.frame.destroy()

        self.cards.clear()
