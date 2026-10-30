from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton
from panda3d.core import TextNode, Vec4


class Home:
    """Premium dark‑theme home screen with four module cards."""

    def __init__(self, base, on_mode_select=None):
        self.base = base
        self.on_mode_select = on_mode_select

        # Main transparent UI panel (covers whole screen)
        self.frame = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=(0.015, 0.025, 0.07, 0),
            frameSize=(-1.78, 1.78, -1.0, 1.0),
        )

        # Branding
        self.title = DirectLabel(
            parent=self.frame,
            text="HOLOHAND AI",
            text_fg=Vec4(0.0, 0.8, 1.0, 1),
            text_scale=0.12,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.45),
        )
        self.subtitle = DirectLabel(
            parent=self.frame,
            text="Touchless Interactive Desktop",
            text_fg=Vec4(0.6, 0.8, 0.95, 1),
            text_scale=0.035,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.35),
        )

        # Central welcome description
        self.welcome = DirectLabel(
            parent=self.frame,
            text="Select a module to begin",
            text_fg=Vec4(0.7, 0.85, 1.0, 1),
            text_scale=0.027,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.25),
        )

        # Module cards (DirectButton) – forward mode via callback.
        self.card_buttons = {}
        self._make_card("PIANO STUDIO", "PIANO", -0.45, 0.25)
        self._make_card("DRUMS STUDIO", "DRUMS", 0.45, 0.25)
        self._make_card("HOLOLAB – COMING SOON", "HOLOLAB", -0.45, -0.25)
        self._make_card("AIR CONTROL – COMING SOON", "AIR", 0.45, -0.25)

        # Status footer (hand‑tracking telemetry)
        self.status = DirectLabel(
            parent=self.frame,
            text="READY TO EXPLORE",
            text_fg=Vec4(0.25, 0.85, 0.75, 1),
            text_scale=0.023,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.55),
        )
        self.footer = DirectLabel(
            parent=self.frame,
            text="CONTROL YOUR EXPERIENCE WITH HAND GESTURES",
            text_fg=Vec4(0.42, 0.5, 0.64, 1),
            text_scale=0.019,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.78),
        )

    def _make_card(self, label, mode, x, z):
        """Create a module card button.
        label – displayed text,
        mode – identifier sent to on_mode_select,
        x, z – position in aspect2d coordinates.
        """
        button = DirectButton(
            parent=self.frame,
            text=label,
            text_scale=0.032,
            text_fg=Vec4(0.9, 0.98, 1.0, 1),
            frameSize=(-0.35, 0.35, -0.15, 0.15),
            frameColor=(0.015, 0.12, 0.20, 0.92),
            relief=1,
            borderWidth=(0.008, 0.008),
            pos=(x, 0, z),
            command=self._select_mode,
            extraArgs=[mode],
        )
        button.setTransparency(True)
        self.card_buttons[mode] = button
        return button

    def _select_mode(self, mode):
        # Forward selection to the main app.
        if self.on_mode_select:
            self.on_mode_select(mode)

    def update_telemetry(self, hand_detected, gesture, active_mode, confidence=1.0):
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
