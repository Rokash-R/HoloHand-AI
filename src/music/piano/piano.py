
import time
from pathlib import Path

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton
)
from panda3d.core import TextNode, LineSegs


class Piano:

    WHITE = ["C", "D", "E", "F", "G", "A", "B", "C5"]

    BLACK = [
        ("C#", 0), ("D#", 1),
        ("F#", 3), ("G#", 4), ("A#", 5)
    ]

    CHORDS = {
        "C MAJOR": ["C", "E", "G"],
        "G MAJOR": ["G", "B", "D"],
        "A MINOR": ["A", "C", "E"],
        "F MAJOR": ["F", "A", "C"]
    }

    def __init__(self, base, sound_manager):

        self.base = base
        self.sound_manager = sound_manager
        self.active = False

        # Playing modes: "AIR_KEYBOARD" (default) or "PINCH"
        self.play_mode = "AIR_KEYBOARD"
        self.gesture_input_enabled = True

        # Per-hand tracking state (supports Hand 0 and Hand 1 independently)
        self.max_hands = 2
        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.candidate_times = [0.0, 0.0]
        self.pinch_downs = [False, False]
        self.last_actions = [0.0, 0.0]
        self.last_valid_targets = [None, None]

        # Timing and detection thresholds
        self.key_dwell_time = 0.025   # 25ms anti-jitter dwell for air-keyboard
        self.pinch_on = 0.32
        self.pinch_off = 0.45
        self.action_cooldown = 0.18

        self.pointer_nodes = []
        self.track_channel = None

        self.white_frames = {}
        self.black_frames = {}
        self.key_regions = []
        self.chord_regions = []

        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameSize=(-1.8, 1.8, -1, 1),
            frameColor=(0.008, 0.014, 0.03, 1),
            relief=None
        )

        self.header()
        self.keyboard()
        self.chord_panel()
        self.music_panel()

        self.status = self.label(
            "AIR-KEYBOARD: HOVER KEYS TO PLAY | [M] PINCH MODE | [SPACE] MUTE",
            0, -0.84, 0.026,
            (0.35, 1, 0.8, 1)
        )

        # Finger pointer appears above the keyboard.
        self.pointer_root = base.aspect2d.attachNewNode(
            "PianoFingerPointers"
        )
        self.pointer_root.setBin("fixed", 110)
        self.pointer_root.setDepthTest(False)
        self.pointer_root.setDepthWrite(False)

        self.hide()

    # -----------------------------------------
    # UI HELPERS
    # -----------------------------------------

    def label(self, text, x, z, scale, color):

        return DirectLabel(
            parent=self.frame,
            text=text,
            pos=(x, 0, z),
            scale=scale,
            text_fg=color,
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

    def button(self, text, x, z, callback):

        return DirectButton(
            parent=self.frame,
            text=text,
            pos=(x, 0, z),
            text_scale=0.036,
            text_fg=(0.8, 1, 1, 1),
            frameSize=(-0.24, 0.24, -0.065, 0.065),
            frameColor=(0.04, 0.15, 0.25, 1),
            command=callback
        )

    # -----------------------------------------
    # HEADER & CONTROLS
    # -----------------------------------------

    def header(self):

        self.label(
            "HOLOHAND AI - PIANO STUDIO",
            0, 0.88, 0.052,
            (0.2, 0.95, 1, 1)
        )

        self.mode_btn = self.button(
            "MODE: AIR-KEYBOARD",
            -0.38, 0.74,
            self.toggle_play_mode
        )

        self.input_btn = self.button(
            "INPUT: ACTIVE",
            0.38, 0.74,
            self.toggle_gesture_input
        )

        self.sub_label = self.label(
            "LIVE AIR-KEYBOARD  |  CHORDS  |  BACKING MUSIC",
            0, 0.65, 0.024,
            (0.65, 0.8, 1, 1)
        )

    def toggle_play_mode(self):

        if self.play_mode == "AIR_KEYBOARD":
            self.play_mode = "PINCH"
        else:
            self.play_mode = "AIR_KEYBOARD"

        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.update_mode_ui()

    def toggle_gesture_input(self):

        self.gesture_input_enabled = not self.gesture_input_enabled
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.update_mode_ui()

    def update_mode_ui(self):

        if hasattr(self, "mode_btn"):
            if self.play_mode == "AIR_KEYBOARD":
                self.mode_btn["text"] = "MODE: AIR-KEYBOARD"
                self.mode_btn["frameColor"] = (0.02, 0.28, 0.40, 1)
                self.mode_btn["text_fg"] = (0.3, 1.0, 1.0, 1)
            else:
                self.mode_btn["text"] = "MODE: PINCH"
                self.mode_btn["frameColor"] = (0.30, 0.15, 0.42, 1)
                self.mode_btn["text_fg"] = (1.0, 0.6, 1.0, 1)

        if hasattr(self, "input_btn"):
            if self.gesture_input_enabled:
                self.input_btn["text"] = "INPUT: ACTIVE"
                self.input_btn["frameColor"] = (0.04, 0.35, 0.22, 1)
                self.input_btn["text_fg"] = (0.4, 1.0, 0.6, 1)
            else:
                self.input_btn["text"] = "INPUT: MUTED"
                self.input_btn["frameColor"] = (0.38, 0.18, 0.05, 1)
                self.input_btn["text_fg"] = (1.0, 0.7, 0.3, 1)

        if self.play_mode == "AIR_KEYBOARD":
            self.status["text"] = "AIR-KEYBOARD: HOVER KEYS TO PLAY | [M] PINCH MODE | [SPACE] MUTE"
        else:
            self.status["text"] = "PINCH MODE: HOVER KEY AND PINCH TO PLAY | [M] AIR-KEYBOARD"

    # -----------------------------------------
    # CENTRAL KEYBOARD
    # -----------------------------------------

    def keyboard(self):

        DirectFrame(
            parent=self.frame,
            pos=(0, 0, -0.05),
            frameSize=(-0.95, 0.95, -0.46, 0.46),
            frameColor=(0.045, 0.055, 0.075, 1)
        )

        self.label(
            "HOLOHAND SYNTHESIZER",
            0, 0.26, 0.036,
            (0.8, 0.95, 1, 1)
        )

        start_x = -0.75
        width = 0.215

        for i, note in enumerate(self.WHITE):

            x = start_x + i * width

            frame = DirectFrame(
                parent=self.frame,
                pos=(x, 0, -0.19),
                frameSize=(
                    -0.102, 0.102,
                    -0.255, 0.255
                ),
                frameColor=(0.92, 0.95, 1, 1)
            )

            DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.20),
                scale=0.037,
                text_fg=(0.05, 0.08, 0.12, 1),
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.white_frames[note] = frame

            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.19,
                "w": 0.102,
                "h": 0.255,
                "black": False
            })

        for note, after in self.BLACK:

            x = start_x + after * width + width / 2

            frame = DirectFrame(
                parent=self.frame,
                pos=(x, 0, -0.065),
                frameSize=(
                    -0.066, 0.066,
                    -0.145, 0.145
                ),
                frameColor=(0.02, 0.025, 0.045, 1)
            )

            self.black_frames[note] = frame

            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.065,
                "w": 0.066,
                "h": 0.145,
                "black": True
            })

    # -----------------------------------------
    # CHORD PANEL
    # -----------------------------------------

    def chord_panel(self):

        self.label(
            "CHORD STUDIO",
            -1.35, 0.56, 0.037,
            (0.3, 1, 0.9, 1)
        )

        for i, chord in enumerate(self.CHORDS):

            z = 0.34 - i * 0.19

            self.button(
                chord,
                -1.35,
                z,
                lambda c=chord: self.play_chord(c)
            )

            self.chord_regions.append({
                "name": chord,
                "x": -1.35,
                "z": z,
                "w": 0.24,
                "h": 0.065
            })

    # -----------------------------------------
    # MUSIC PANEL
    # -----------------------------------------

    def music_panel(self):

        self.label(
            "MUSIC PLAYER",
            1.35, 0.56, 0.037,
            (0.3, 1, 0.9, 1)
        )

        self.button(
            "PLAY TRACK",
            1.35, 0.30,
            self.play_track
        )

        self.button(
            "STOP TRACK",
            1.35, 0.10,
            self.stop_track
        )

        self.label(
            "PLAY ALONG WITH MUSIC",
            1.35, -0.22, 0.023,
            (0.65, 0.8, 1, 1)
        )

    # -----------------------------------------
    # SOUND
    # -----------------------------------------

    def play_note(self, note):

        note_id = note.replace("#", "s")

        try:
            self.sound_manager.play_piano(note_id)
            self.status["text"] = "PLAYING: " + note
        except Exception as error:
            print("Piano sound error:", error)

    def play_chord(self, name):

        notes = self.CHORDS.get(name, [])

        for note in notes:
            self.play_note(note)

        self.status["text"] = (
            name + " : " + " + ".join(notes)
        )

    # -----------------------------------------
    # BACKING TRACK
    # -----------------------------------------

    def play_track(self):

        path = (
            Path(__file__).resolve().parents[3]
            / "assets"
            / "backing_track.wav"
        )

        if not path.exists():
            self.status["text"] = "BACKING TRACK NOT FOUND"
            return

        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self.stop_track()

            sound = pygame.mixer.Sound(str(path))
            self.track_channel = sound.play()

            self.status["text"] = "BACKING TRACK PLAYING"

        except Exception as error:
            print("Track error:", error)

    def stop_track(self):

        if self.track_channel is not None:
            self.track_channel.stop()
            self.track_channel = None

    # -----------------------------------------
    # HAND LANDMARK HELPERS
    # -----------------------------------------

    def landmarks(self, hand):

        if hand is None:
            return None

        if hasattr(hand, "landmark"):
            return hand.landmark

        if hasattr(hand, "landmarks"):
            return hand.landmarks

        if isinstance(hand, dict):
            return hand.get(
                "landmarks",
                hand.get("landmark")
            )

        return None

    def xy(self, lm):

        if hasattr(lm, "x"):
            return float(lm.x), float(lm.y)

        if isinstance(lm, dict):
            return float(lm["x"]), float(lm["y"])

        return float(lm[0]), float(lm[1])

    def distance(self, a, b):

        ax, ay = self.xy(a)
        bx, by = self.xy(b)

        return ((ax - bx)**2 + (ay - by)**2)**0.5

    def screen_point(self, lm):

        x, y = self.xy(lm)
        aspect = self.base.getAspectRatio()

        return (
            (x - 0.5) * 2 * aspect,
            (0.5 - y) * 2
        )

    # -----------------------------------------
    # VISIBLE FINGER POINTER
    # -----------------------------------------

    def draw_pointer(self, x, z, color, radius=0.04):

        lines = LineSegs()
        lines.setThickness(3)
        lines.setColor(*color)

        import math

        for i in range(25):

            angle = i * 2 * math.pi / 24

            px = x + radius * math.cos(angle)
            pz = z + radius * math.sin(angle)

            if i == 0:
                lines.moveTo(px, 0, pz)
            else:
                lines.drawTo(px, 0, pz)

        node = self.pointer_root.attachNewNode(
            lines.create()
        )

        self.pointer_nodes.append(node)

    def clear_pointers(self):

        for node in self.pointer_nodes:
            node.removeNode()

        self.pointer_nodes.clear()

    # -----------------------------------------
    # KEY HIGHLIGHT
    # -----------------------------------------

    def reset_keys(self):

        for frame in self.white_frames.values():
            frame["frameColor"] = (
                0.92, 0.95, 1, 1
            )

        for frame in self.black_frames.values():
            frame["frameColor"] = (
                0.02, 0.025, 0.045, 1
            )

    def find_target(self, x, z):

        # Chord buttons.
        for region in self.chord_regions:

            if (
                abs(x - region["x"]) <= region["w"]
                and abs(z - region["z"]) <= region["h"]
            ):
                return ("chord", region["name"])

        # Black keys first.
        for region in self.key_regions:

            if not region["black"]:
                continue

            if (
                abs(x - region["x"]) <= region["w"]
                and abs(z - region["z"]) <= region["h"]
            ):
                return ("note", region["note"])

        # White keys.
        for region in self.key_regions:

            if region["black"]:
                continue

            if (
                abs(x - region["x"]) <= region["w"]
                and abs(z - region["z"]) <= region["h"]
            ):
                return ("note", region["note"])

        return None

    def highlight_target(self, target, hand_idx=0):

        if target is None:
            return

        kind, name = target

        if kind == "chord":
            chord_notes = self.CHORDS.get(name, [])
            for note in chord_notes:
                self._apply_key_color(note, hand_idx)
            return

        if kind == "note":
            self._apply_key_color(name, hand_idx)

    def _apply_key_color(self, name, hand_idx=0):

        if hand_idx == 0:
            white_col = (0.25, 0.95, 1.0, 1)
            black_col = (0.65, 0.40, 1.0, 1)
        else:
            white_col = (1.0, 0.45, 0.85, 1)
            black_col = (0.90, 0.25, 0.70, 1)

        if name in self.white_frames:
            self.white_frames[name]["frameColor"] = white_col
        elif name in self.black_frames:
            self.black_frames[name]["frameColor"] = black_col

    # -----------------------------------------
    # HAND-CONTROLLED PIANO
    # -----------------------------------------

    def update(self, hands):

        if not self.active:
            return

        self.clear_pointers()
        self.reset_keys()

        if hands is None:
            hands_list = []
        elif isinstance(hands, (list, tuple)):
            hands_list = [h for h in hands if h is not None]
        else:
            hands_list = [hands]

        if not hands_list:
            self.cursors = [None, None]
            self.current_keys = [None, None]
            self.candidate_keys = [None, None]
            self.pinch_downs = [False, False]
            return

        now = time.monotonic()
        active_statuses = []

        processed_hands = []
        for hand in hands_list[:2]:
            lm = self.landmarks(hand)
            if lm is not None and len(lm) >= 21:
                processed_hands.append((hand, lm, lm[8].x))

        if len(processed_hands) == 2:
            processed_hands.sort(key=lambda item: item[2])

        colors = [
            (0.0, 1.0, 1.0, 1.0),
            (1.0, 0.3, 0.85, 1.0)
        ]

        for h_idx, (hand, lm, _) in enumerate(processed_hands):
            # Index finger controls selection.
            x, z = self.screen_point(lm[8])

            if self.cursors[h_idx] is None:
                self.cursors[h_idx] = (x, z)
            else:
                old_x, old_z = self.cursors[h_idx]
                alpha = 0.70
                self.cursors[h_idx] = (
                    old_x + (x - old_x) * alpha,
                    old_z + (z - old_z) * alpha
                )

            cx, cz = self.cursors[h_idx]
            self.draw_pointer(cx, cz, colors[h_idx], radius=0.038)

            target = self.find_target(cx, cz)

            if target is not None:
                self.highlight_target(target, h_idx)
                active_statuses.append(f"H{h_idx + 1}: {target[1]}")

            if self.play_mode == "AIR_KEYBOARD":
                if target is not None:
                    if target != self.current_keys[h_idx]:
                        if self.candidate_keys[h_idx] != target:
                            self.candidate_keys[h_idx] = target
                            self.candidate_times[h_idx] = now
                        elif now - self.candidate_times[h_idx] >= self.key_dwell_time:
                            self.current_keys[h_idx] = target
                            self.last_actions[h_idx] = now
                            if self.gesture_input_enabled:
                                kind, name = target
                                if kind == "note":
                                    self.play_note(name)
                                elif kind == "chord":
                                    self.play_chord(name)
                    else:
                        self.candidate_keys[h_idx] = target
                else:
                    self.candidate_keys[h_idx] = None
                    self.current_keys[h_idx] = None

            elif self.play_mode == "PINCH":
                if target is not None:
                    self.last_valid_targets[h_idx] = target

                scale_a = self.distance(lm[5], lm[17])
                scale_b = self.distance(lm[0], lm[9]) * 0.5
                palm_scale = max(scale_a, scale_b)

                if palm_scale >= 0.025:
                    pinch_distance = self.distance(lm[4], lm[8])
                    ratio = pinch_distance / palm_scale

                    if not self.pinch_downs[h_idx]:
                        if ratio < self.pinch_on:
                            self.pinch_downs[h_idx] = True
                            active_target = target or self.last_valid_targets[h_idx]
                            if (
                                active_target is not None
                                and now - self.last_actions[h_idx] >= self.action_cooldown
                            ):
                                if self.gesture_input_enabled:
                                    kind, name = active_target
                                    if kind == "note":
                                        self.play_note(name)
                                    elif kind == "chord":
                                        self.play_chord(name)
                                self.last_actions[h_idx] = now
                    elif ratio > self.pinch_off:
                        self.pinch_downs[h_idx] = False

        if active_statuses:
            status_text = "  |  ".join(active_statuses)
            if not self.gesture_input_enabled:
                status_text += " [MUTED - PRESS SPACE TO UNMUTE]"
            self.status["text"] = status_text
        elif not self.gesture_input_enabled:
            self.status["text"] = "GESTURE INPUT MUTED [PRESS SPACE TO UNMUTE]"

    # -----------------------------------------
    # SHOW / HIDE
    # -----------------------------------------

    def show(self):

        self.active = True
        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.pinch_downs = [False, False]

        self.base.accept("m", self.toggle_play_mode)
        self.base.accept("space", self.toggle_gesture_input)

        self.frame.show()
        self.pointer_root.show()
        self.update_mode_ui()

    def hide(self):

        self.active = False
        self.base.ignore("m")
        self.base.ignore("space")

        self.frame.hide()
        self.pointer_root.hide()

        self.clear_pointers()
        self.reset_keys()
        self.stop_track()

        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.pinch_downs = [False, False]

    def cleanup(self):

        self.hide()
        self.pointer_root.removeNode()
        self.frame.destroy()
