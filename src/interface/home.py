
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton
from panda3d.core import TextNode, Vec4


class Home:
    """Simple, static HoloHand AI home screen."""

    def __init__(self, base, on_mode_select=None):
        self.base = base
        self.on_mode_select = on_mode_select

        # Main transparent UI panel
        self.frame = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=(0.015, 0.025, 0.07, 0),
            frameSize=(-1.78, 1.78, -1.0, 1.0),
        )

        # Application title
        self.title = DirectLabel(
            parent=self.frame,
            text="HOLOHAND AI",
            text_fg=Vec4(0.25, 0.9, 1.0, 1),
            text_scale=0.11,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.48),
        )

        # Subtitle
        self.subtitle = DirectLabel(
            parent=self.frame,
            text="HAND GESTURE INTERACTION SYSTEM",
            text_fg=Vec4(0.75, 0.82, 0.92, 1),
            text_scale=0.032,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.32),
        )

        self.description = DirectLabel(
            parent=self.frame,
            text="Explore a new way to interact with your world.",
            text_fg=Vec4(0.65, 0.72, 0.84, 1),
            text_scale=0.027,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.18),
        )

        # Simple navigation buttons
        self.piano_button = self._make_button(
            "OPEN PIANO", -0.38, "PIANO"
        )

        self.drums_button = self._make_button(
            "OPEN DRUMS", 0.38, "DRUMS"
        )

        self.status = DirectLabel(
            parent=self.frame,
            text="READY TO EXPLORE",
            text_fg=Vec4(0.25, 0.85, 0.75, 1),
            text_scale=0.023,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.52),
        )

        self.footer = DirectLabel(
            parent=self.frame,
            text="CONTROL YOUR EXPERIENCE WITH HAND GESTURES",
            text_fg=Vec4(0.42, 0.5, 0.64, 1),
            text_scale=0.019,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.82),
        )

    def _make_button(self, label, x, mode):
        return DirectButton(
            parent=self.frame,
            text=label,
            text_scale=0.035,
            text_fg=Vec4(0.9, 0.98, 1, 1),
            frameColor=(
                (0.03, 0.25, 0.36, 1),
                (0.05, 0.4, 0.52, 1),
                (0.02, 0.18, 0.28, 1),
                (0.02, 0.18, 0.28, 1),
            ),
            frameSize=(-0.28, 0.28, -0.09, 0.09),
            relief=1,
            borderWidth=(0.008, 0.008),
            pos=(x, 0, -0.12),
            command=self._select_mode,
            extraArgs=[mode],
        )

    def _select_mode(self, mode):
        if self.on_mode_select:
            self.on_mode_select(mode)

    def update_telemetry(
        self, hand_detected, gesture, active_mode, confidence=1.0
    ):
        if hand_detected:
            hint = ""
            if gesture == "TWO FINGERS":
                hint = " -> SWITCHING TO PIANO"
            elif gesture == "CLOSED FIST":
                hint = " -> SWITCHING TO DRUMS"
            elif gesture == "OPEN PALM":
                hint = " (HOME CORE)"
            self.status["text"] = f"HAND TRACKED | GESTURE: {gesture}{hint}"
            self.status["text_fg"] = Vec4(0.2, 0.95, 0.7, 1)
        else:
            self.status["text"] = "READY TO EXPLORE — SHOW HAND TO CAMERA"
            self.status["text_fg"] = Vec4(0.25, 0.85, 0.75, 1)

    def show(self):
        self.frame.show()

    def hide(self):
        self.frame.hide()

    def cleanup(self):
        try:
            self.frame.destroy()
        except Exception:
            pass
