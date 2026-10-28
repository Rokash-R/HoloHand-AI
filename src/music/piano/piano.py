import os
import time
import math
import wave
from pathlib import Path
import numpy as np

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton
)
from panda3d.core import TextNode, LineSegs, Vec4


class Piano:
    """
    HoloHand AI - Professional Cyber Stage Synthesizer Workstation.

    Upgrades:
      - High-visibility 3D Black Keys with bright cyan neon bevels & fixed Z-order
      - Large, bold, readable font sizes across all keyboards, buttons, and readouts
      - Vibrant, colorful cyber stage aesthetic (cyan, purple, emerald, gold, coral)
      - Controllable hand gesture speed (Normal 85ms, Relaxed 130ms, Fast 45ms)
      - Silky smooth 0.45 cursor smoothing for jitter-free, effortless control
      - Dual Playing Modes: Air-Keyboard (default) & Pinch-to-Play
      - Two-hand independent polyphonic playing (Cyan & Neon Pink pointers)
      - 6 Color-Coded Chord Pads + 4-Step Pop Progression Stepper
      - Backing Track Player (Play, Pause, Stop, Volume)
      - Studio Performance Recorder: Auto-mixes and exports clean 16-bit WAV to recordings/
    """

    WHITE = ["C", "D", "E", "F", "G", "A", "B", "C5"]

    BLACK = [
        ("C#", 0), ("D#", 1),
        ("F#", 3), ("G#", 4), ("A#", 5)
    ]

    CHORDS = {
        "C MAJOR": ["C", "E", "G"],
        "G MAJOR": ["G", "B", "D"],
        "A MINOR": ["A", "C5", "E"],
        "F MAJOR": ["F", "A", "C5"],
        "D MINOR": ["D", "F", "A"],
        "E MINOR": ["E", "G", "B"]
    }

    CHORD_PROGRESSION = [
        "C MAJOR", "G MAJOR", "A MINOR", "F MAJOR"
    ]

    CHORD_COLORS = {
        "C MAJOR": (0.05, 0.38, 0.55, 1.0),   # Electric Cyan
        "G MAJOR": (0.50, 0.38, 0.06, 1.0),   # Golden Amber
        "A MINOR": (0.42, 0.10, 0.52, 1.0),   # Neon Purple
        "F MAJOR": (0.06, 0.42, 0.22, 1.0),   # Emerald Green
        "D MINOR": (0.50, 0.14, 0.18, 1.0),   # Crimson Coral
        "E MINOR": (0.14, 0.25, 0.60, 1.0)    # Royal Cobalt
    }

    def __init__(self, base, sound_manager):

        self.base = base
        self.sound_manager = sound_manager
        self.active = False

        # Playing modes: "AIR_KEYBOARD" (default) or "PINCH"
        self.play_mode = "AIR_KEYBOARD"
        self.gesture_input_enabled = True

        # Speed / Sensitivity: "NORMAL" (85ms), "RELAXED" (130ms), "FAST" (45ms)
        self.speed_mode = "NORMAL"
        self.key_dwell_time = 0.085
        self.smoothing_alpha = 0.45

        # Per-hand tracking state (supports Hand 0 and Hand 1 independently)
        self.max_hands = 2
        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.candidate_times = [0.0, 0.0]
        self.pinch_downs = [False, False]
        self.last_actions = [0.0, 0.0]
        self.last_valid_targets = [None, None]

        # Pinch detection thresholds
        self.pinch_on = 0.32
        self.pinch_off = 0.45
        self.action_cooldown = 0.15

        # Key press visual illumination timers
        self.key_press_timers = {}

        # Chord progression state
        self.progression_step = 0

        # Backing track audio state
        self.track_channel = None
        self.track_sound = None
        self.track_volume = 0.80
        self.track_paused = False
        self.track_name = "DEMO BEAT 1 (120 BPM)"

        # Performance recording state
        self.is_recording = False
        self.record_start_time = 0.0
        self.recorded_events = []
        self.last_exported_file = None

        # VU Meter state
        self.vu_level = 0.0
        self.last_played_item = "NONE"

        # Pointers and UI references
        self.pointer_nodes = []
        self.white_frames = {}
        self.black_frames = {}
        self.chord_buttons = {}
        self.key_regions = []
        self.chord_regions = []

        # Master workstation chassis frame (Rich Cyber Sapphire Theme)
        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameSize=(-1.78, 1.78, -1.0, 1.0),
            frameColor=(0.015, 0.022, 0.040, 1.0),
            relief=None
        )

        # Build workstation sections
        self._build_top_deck()
        self._build_keyboard()
        self._build_chord_studio()
        self._build_music_studio()
        self._build_bottom_status()

        # High priority pointer root
        self.pointer_root = base.aspect2d.attachNewNode("PianoFingerPointers")
        self.pointer_root.setBin("fixed", 120)
        self.pointer_root.setDepthTest(False)
        self.pointer_root.setDepthWrite(False)

        # Load demo backing track
        self._init_backing_track()

        self.hide()

    # ========================================================
    # TOP SYNTHESIZER CONTROL DECK
    # ========================================================

    def _build_top_deck(self):

        # Main deck chassis banner
        self.deck_banner = DirectFrame(
            parent=self.frame,
            pos=(0, 0, 0.77),
            frameSize=(-1.74, 1.74, -0.20, 0.20),
            frameColor=(0.025, 0.038, 0.065, 0.98)
        )

        # Top illuminated neon border trim
        DirectFrame(
            parent=self.deck_banner,
            pos=(0, 0, 0.192),
            frameSize=(-1.73, 1.73, -0.005, 0.005),
            frameColor=(0.0, 0.85, 1.0, 1.0)
        )

        # Header branding
        DirectLabel(
            parent=self.deck_banner,
            text="HOLOHAND AI  //  PRO SYNTHESIZER",
            pos=(-1.65, 0, 0.11),
            scale=0.048,
            text_fg=(0.2, 0.95, 1.0, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.deck_banner,
            text="MULTI-HAND AIR-KEYBOARD  |  CHORD MATRIX  |  STUDIO WORKSTATION",
            pos=(-1.65, 0, 0.048),
            scale=0.024,
            text_fg=(0.7, 0.85, 1.0, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Quick Control Buttons on Left Deck
        self.mode_btn = DirectButton(
            parent=self.deck_banner,
            text="MODE: AIR-KEYBOARD",
            pos=(-1.35, 0, -0.08),
            text_scale=0.032,
            text_fg=(0.2, 1.0, 1.0, 1),
            frameSize=(-0.25, 0.25, -0.055, 0.055),
            frameColor=(0.04, 0.32, 0.48, 1),
            command=self.toggle_play_mode
        )

        self.input_btn = DirectButton(
            parent=self.deck_banner,
            text="INPUT: ACTIVE",
            pos=(-0.82, 0, -0.08),
            text_scale=0.032,
            text_fg=(0.3, 1.0, 0.6, 1),
            frameSize=(-0.22, 0.22, -0.055, 0.055),
            frameColor=(0.05, 0.42, 0.24, 1),
            command=self.toggle_gesture_input
        )

        self.speed_btn = DirectButton(
            parent=self.deck_banner,
            text="SPEED: NORMAL",
            pos=(-0.34, 0, -0.08),
            text_scale=0.032,
            text_fg=(1.0, 0.95, 0.3, 1),
            frameSize=(-0.21, 0.21, -0.055, 0.055),
            frameColor=(0.48, 0.35, 0.05, 1),
            command=self.toggle_speed_mode
        )

        # Central LED display readout box (High-Contrast Cyber Display)
        self.led_box = DirectFrame(
            parent=self.deck_banner,
            pos=(0.88, 0, 0.00),
            frameSize=(-0.78, 0.78, -0.17, 0.17),
            frameColor=(0.006, 0.018, 0.035, 0.98)
        )

        # Glowing cyan border on LED screen
        DirectFrame(
            parent=self.led_box,
            pos=(0, 0, 0.165),
            frameSize=(-0.77, 0.77, -0.004, 0.004),
            frameColor=(0.1, 0.8, 1.0, 0.8)
        )

        # Large high-contrast LED readouts
        self.led_line1 = DirectLabel(
            parent=self.led_box,
            text="MODE: AIR-KEYBOARD  |  INPUT: ACTIVE  |  OCTAVE: C4 - C5",
            pos=(-0.73, 0, 0.095),
            scale=0.029,
            text_fg=(0.2, 1.0, 0.9, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line2 = DirectLabel(
            parent=self.led_box,
            text="NOTE: READY  |  POLYPHONY: 32-CH  |  CLOCK: 44.1 kHz",
            pos=(-0.73, 0, 0.030),
            scale=0.029,
            text_fg=(0.3, 1.0, 0.5, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line3 = DirectLabel(
            parent=self.led_box,
            text="TRACKING: WAITING  |  VU [||||||||        ]",
            pos=(-0.73, 0, -0.038),
            scale=0.029,
            text_fg=(1.0, 0.85, 0.25, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line4 = DirectLabel(
            parent=self.led_box,
            text="REC: IDLE  |  TRACK: STOPPED",
            pos=(-0.73, 0, -0.105),
            scale=0.027,
            text_fg=(1.0, 0.5, 0.85, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

    # ========================================================
    # MAIN KEYBOARD (WITH VISIBLE 3D BLACK KEYS)
    # ========================================================

    def _build_keyboard(self):

        # Outer metallic keyboard bed with cyan edge accent
        self.keybed_frame = DirectFrame(
            parent=self.frame,
            pos=(0, 0, -0.22),
            frameSize=(-0.98, 0.98, -0.32, 0.32),
            frameColor=(0.028, 0.040, 0.070, 1.0)
        )

        # Neon cyan border outline on keybed
        DirectFrame(
            parent=self.keybed_frame,
            pos=(0, 0, 0.315),
            frameSize=(-0.97, 0.97, -0.005, 0.005),
            frameColor=(0.0, 0.9, 1.0, 1.0)
        )

        DirectLabel(
            parent=self.keybed_frame,
            text="STAGE SYNTHESIZER KEYBED  //  OCTAVE 4  [C4 - C5]",
            pos=(0, 0, 0.26),
            scale=0.030,
            text_fg=(0.4, 0.92, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        start_x = -0.7525
        width = 0.215

        # ----------------------------------------------------
        # 1. WHITE KEYS (8 keys: C, D, E, F, G, A, B, C5)
        # ----------------------------------------------------
        for i, note in enumerate(self.WHITE):

            x = start_x + i * width
            z_pos = -0.04

            # White key body (Bin: fixed 20)
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.103, 0.103, -0.245, 0.245),
                frameColor=(0.95, 0.97, 1.0, 1.0)
            )
            frame.setBin("fixed", 20)

            # Beveled bottom lip
            bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.235),
                frameSize=(-0.098, 0.098, -0.008, 0.008),
                frameColor=(0.75, 0.82, 0.90, 1.0)
            )
            bevel.setBin("fixed", 21)

            # Large, bold, high-contrast note label
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.180),
                scale=0.052,
                text_fg=(0.05, 0.08, 0.16, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 22)

            self.white_frames[note] = frame

            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.26, # world-space z
                "w": 0.103,
                "h": 0.245,
                "black": False
            })

        # ----------------------------------------------------
        # 2. BLACK KEYS (5 keys: C#, D#, F#, G#, A#)
        # Higher Bin (fixed 35) ensures they are ALWAYS ON TOP!
        # ----------------------------------------------------
        for note, after in self.BLACK:

            x = start_x + after * width + width / 2.0
            z_pos = 0.075

            # Outer Drop-Shadow frame
            shadow = DirectFrame(
                parent=self.keybed_frame,
                pos=(x + 0.006, 0, z_pos - 0.008),
                frameSize=(-0.066, 0.066, -0.142, 0.142),
                frameColor=(0.0, 0.0, 0.0, 0.6)
            )
            shadow.setBin("fixed", 32)

            # High-visibility black key body (rich charcoal ebony)
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.064, 0.064, -0.138, 0.138),
                frameColor=(0.08, 0.10, 0.15, 1.0)
            )
            frame.setBin("fixed", 35)

            # Luminous cyan neon bevel trim along top edge
            top_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, 0.126),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.0, 0.85, 1.0, 1.0)
            )
            top_bevel.setBin("fixed", 36)

            # Bottom highlight lip
            bot_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.128),
                frameSize=(-0.058, 0.058, -0.006, 0.006),
                frameColor=(0.18, 0.35, 0.50, 1.0)
            )
            bot_bevel.setBin("fixed", 36)

            # Sharp, bright electric cyan label
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.085),
                scale=0.038,
                text_fg=(0.35, 0.95, 1.0, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 37)

            self.black_frames[note] = frame

            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.145, # world-space z
                "w": 0.064,
                "h": 0.138,
                "black": True
            })

    # ========================================================
    # LEFT PANEL — COLORFUL CHORD STUDIO
    # ========================================================

    def _build_chord_studio(self):

        self.chord_panel_frame = DirectFrame(
            parent=self.frame,
            pos=(-1.38, 0, -0.18),
            frameSize=(-0.35, 0.35, -0.42, 0.42),
            frameColor=(0.022, 0.030, 0.052, 0.98)
        )

        # Neon cyan top trim
        DirectFrame(
            parent=self.chord_panel_frame,
            pos=(0, 0, 0.415),
            frameSize=(-0.34, 0.34, -0.004, 0.004),
            frameColor=(0.1, 0.85, 1.0, 1.0)
        )

        DirectLabel(
            parent=self.chord_panel_frame,
            text="CHORD STUDIO",
            pos=(0, 0, 0.35),
            scale=0.042,
            text_fg=(0.3, 1.0, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # 6 Color-Coded Chord Pads with large fonts
        chord_list = [
            ("C MAJOR", "C - E - G"),
            ("G MAJOR", "G - B - D"),
            ("A MINOR", "A - C - E"),
            ("F MAJOR", "F - A - C"),
            ("D MINOR", "D - F - A"),
            ("E MINOR", "E - G - B")
        ]

        start_z = 0.25
        step_z = 0.088

        for i, (name, notes_str) in enumerate(chord_list):
            z = start_z - i * step_z
            col = self.CHORD_COLORS.get(name, (0.04, 0.20, 0.35, 1))

            btn = DirectButton(
                parent=self.chord_panel_frame,
                text=f"{name} [{notes_str}]",
                pos=(0, 0, z),
                text_scale=0.028,
                text_fg=(1.0, 1.0, 1.0, 1),
                frameSize=(-0.32, 0.32, -0.038, 0.038),
                frameColor=col,
                command=lambda c=name: self.play_chord(c)
            )

            self.chord_buttons[name] = btn

            self.chord_regions.append({
                "name": name,
                "x": -1.38,
                "z": -0.18 + z,
                "w": 0.32,
                "h": 0.038
            })

        # Progression Stepper
        DirectLabel(
            parent=self.chord_panel_frame,
            text="PROGRESSION: C -> G -> Am -> F",
            pos=(0, 0, -0.28),
            scale=0.026,
            text_fg=(1.0, 0.85, 0.3, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.prog_btn = DirectButton(
            parent=self.chord_panel_frame,
            text="[ > PLAY NEXT CHORD: C MAJ ]",
            pos=(0, 0, -0.36),
            text_scale=0.030,
            text_fg=(1.0, 0.98, 0.4, 1),
            frameSize=(-0.32, 0.32, -0.046, 0.046),
            frameColor=(0.55, 0.40, 0.06, 1),
            command=self.step_chord_progression
        )

    # ========================================================
    # RIGHT PANEL — COLORFUL MUSIC STUDIO
    # ========================================================

    def _build_music_studio(self):

        self.music_panel_frame = DirectFrame(
            parent=self.frame,
            pos=(1.38, 0, -0.18),
            frameSize=(-0.35, 0.35, -0.42, 0.42),
            frameColor=(0.022, 0.030, 0.052, 0.98)
        )

        # Neon pink top trim
        DirectFrame(
            parent=self.music_panel_frame,
            pos=(0, 0, 0.415),
            frameSize=(-0.34, 0.34, -0.004, 0.004),
            frameColor=(1.0, 0.3, 0.85, 1.0)
        )

        DirectLabel(
            parent=self.music_panel_frame,
            text="MUSIC STUDIO",
            pos=(0, 0, 0.35),
            scale=0.042,
            text_fg=(1.0, 0.4, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Track name
        self.track_name_label = DirectLabel(
            parent=self.music_panel_frame,
            text=self.track_name,
            pos=(0, 0, 0.28),
            scale=0.028,
            text_fg=(0.4, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Backing track buttons
        self.track_play_btn = DirectButton(
            parent=self.music_panel_frame,
            text="PLAY TRACK",
            pos=(-0.16, 0, 0.20),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.15, 0.15, -0.040, 0.040),
            frameColor=(0.08, 0.52, 0.24, 1),
            command=self.play_track
        )

        self.track_pause_btn = DirectButton(
            parent=self.music_panel_frame,
            text="PAUSE",
            pos=(0.16, 0, 0.20),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.040, 0.040),
            frameColor=(0.58, 0.45, 0.06, 1),
            command=self.pause_track
        )

        self.track_stop_btn = DirectButton(
            parent=self.music_panel_frame,
            text="STOP TRACK",
            pos=(0, 0, 0.11),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.31, 0.31, -0.038, 0.038),
            frameColor=(0.55, 0.12, 0.12, 1),
            command=self.stop_track
        )

        # Volume controls
        self.vol_down_btn = DirectButton(
            parent=self.music_panel_frame,
            text="VOL -",
            pos=(-0.21, 0, 0.02),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.09, 0.09, -0.035, 0.035),
            frameColor=(0.08, 0.32, 0.55, 1),
            command=lambda: self.adjust_volume(-0.10)
        )

        self.vol_label = DirectLabel(
            parent=self.music_panel_frame,
            text="VOL: 80%",
            pos=(0, 0, 0.02),
            scale=0.028,
            text_fg=(0.3, 1.0, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_up_btn = DirectButton(
            parent=self.music_panel_frame,
            text="VOL +",
            pos=(0.21, 0, 0.02),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.09, 0.09, -0.035, 0.035),
            frameColor=(0.08, 0.32, 0.55, 1),
            command=lambda: self.adjust_volume(+0.10)
        )

        # Performance recording section (Glowing Cherry Red)
        self.record_btn = DirectButton(
            parent=self.music_panel_frame,
            text="[ * RECORD ]",
            pos=(0, 0, -0.11),
            text_scale=0.032,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.31, 0.31, -0.046, 0.046),
            frameColor=(0.72, 0.08, 0.08, 1),
            command=self.toggle_recording
        )

        self.rec_status_label = DirectLabel(
            parent=self.music_panel_frame,
            text="RECORDER IDLE",
            pos=(0, 0, -0.21),
            scale=0.028,
            text_fg=(0.7, 0.88, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.rec_file_label = DirectLabel(
            parent=self.music_panel_frame,
            text="WAV EXPORT: recordings/",
            pos=(0, 0, -0.28),
            scale=0.022,
            text_fg=(0.5, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.music_panel_frame,
            text="HOTKEYS: [R] REC | [T] TRACK | [SPACE] MUTE",
            pos=(0, 0, -0.37),
            scale=0.022,
            text_fg=(0.6, 0.75, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

    # ========================================================
    # BOTTOM STATUS BAR
    # ========================================================

    def _build_bottom_status(self):

        self.status = DirectLabel(
            parent=self.frame,
            text="AIR-KEYBOARD READY  |  HOVER OVER KEYS TO PLAY  |  [M] PINCH MODE",
            pos=(0, 0, -0.66),
            scale=0.034,
            text_fg=(0.35, 1.0, 0.90, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

    # ========================================================
    # BACKING TRACK ENGINE
    # ========================================================

    def _init_backing_track(self):

        project_root = Path(__file__).resolve().parents[3]
        track_path = project_root / "assets" / "backing_track.wav"

        if not track_path.exists():
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.track_sound = pygame.mixer.Sound(str(track_path))
        except Exception as error:
            print("Backing track load error:", error)

    def play_track(self):

        if self.track_sound is None:
            self._init_backing_track()

        if self.track_sound is None:
            self.status["text"] = "BACKING TRACK NOT FOUND IN assets/"
            return

        try:
            if self.track_channel is not None and self.track_paused:
                self.track_channel.unpause()
                self.track_paused = False
                self.track_play_btn["frameColor"] = (0.08, 0.65, 0.30, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PLAYING"
                return

            self.stop_track()
            self.track_channel = self.track_sound.play(loops=-1)
            if self.track_channel:
                self.track_channel.set_volume(self.track_volume)
            self.track_paused = False
            self.track_play_btn["frameColor"] = (0.08, 0.65, 0.30, 1)
            self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PLAYING"

            if self.is_recording:
                self.recorded_events.append((time.monotonic() - self.record_start_time, "backing", self.track_volume))

        except Exception as error:
            print("Track play error:", error)

    def pause_track(self):

        if self.track_channel is not None:
            if not self.track_paused:
                self.track_channel.pause()
                self.track_paused = True
                self.track_play_btn["frameColor"] = (0.08, 0.52, 0.24, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PAUSED"
            else:
                self.track_channel.unpause()
                self.track_paused = False
                self.track_play_btn["frameColor"] = (0.08, 0.65, 0.30, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PLAYING"

    def stop_track(self):

        if self.track_channel is not None:
            self.track_channel.stop()
            self.track_channel = None
        self.track_paused = False
        self.track_play_btn["frameColor"] = (0.08, 0.52, 0.24, 1)
        self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: STOPPED"

    def adjust_volume(self, delta):

        self.track_volume = max(0.0, min(1.0, self.track_volume + delta))
        if self.track_channel is not None:
            self.track_channel.set_volume(self.track_volume)
        pct = int(self.track_volume * 100)
        self.vol_label["text"] = f"VOL: {pct}%"

    # ========================================================
    # PERFORMANCE RECORDER
    # ========================================================

    def toggle_recording(self):

        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):

        self.is_recording = True
        self.record_start_time = time.monotonic()
        self.recorded_events = []

        if self.track_channel and self.track_channel.get_busy() and not self.track_paused:
            self.recorded_events.append((0.0, "backing", self.track_volume))

        self.record_btn["text"] = "[ # STOP REC ]"
        self.record_btn["frameColor"] = (0.85, 0.10, 0.10, 1)
        self.rec_status_label["text"] = "[* REC] 00:00 (0 notes)"
        self.rec_status_label["text_fg"] = (1.0, 0.3, 0.3, 1)
        self.led_line4["text"] = f"REC: RECORDING...  |  TRACK: {'PLAYING' if self.track_channel and not self.track_paused else 'STOPPED'}"

    def stop_recording(self):

        if not self.is_recording:
            return

        self.is_recording = False
        duration = time.monotonic() - self.record_start_time

        self.record_btn["text"] = "[ * RECORD ]"
        self.record_btn["frameColor"] = (0.72, 0.08, 0.08, 1)
        self.rec_status_label["text"] = f"SAVED ({len(self.recorded_events)} events)"
        self.rec_status_label["text_fg"] = (0.3, 1.0, 0.6, 1)
        self.led_line4["text"] = f"REC: SAVED  |  TRACK: {'PLAYING' if self.track_channel and not self.track_paused else 'STOPPED'}"

        saved_path = self.export_recording(duration)
        if saved_path:
            filename = os.path.basename(saved_path)
            self.rec_file_label["text"] = f"SAVED: {filename}"
            self.status["text"] = f"RECORDING SAVED TO recordings/{filename}"

    def record_event(self, event_type, name):

        if self.is_recording:
            offset = time.monotonic() - self.record_start_time
            self.recorded_events.append((offset, event_type, name))

    def export_recording(self, total_duration):

        if not self.recorded_events:
            return None

        total_duration = max(1.0, total_duration)
        sample_rate = 44100
        total_samples = int(sample_rate * (total_duration + 1.2))

        master = np.zeros((total_samples, 2), dtype=np.float32)

        sound_cache = {}
        src_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        def get_wav_samples(filename):
            if filename in sound_cache:
                return sound_cache[filename]
            path = os.path.join(src_folder, filename)
            if not os.path.isfile(path):
                path = os.path.join(src_folder, "..", "assets", filename)
            if not os.path.isfile(path):
                return None
            try:
                with wave.open(path, "rb") as wf:
                    n_channels = wf.getnchannels()
                    n_frames = wf.getnframes()
                    raw = wf.readframes(n_frames)
                    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                    if n_channels == 1:
                        arr = np.column_stack((arr, arr))
                    elif n_channels == 2:
                        arr = arr.reshape(-1, 2)
                    sound_cache[filename] = arr
                    return arr
            except Exception as e:
                print(f"Error loading {filename} for export:", e)
                return None

        for offset, ev_type, name in self.recorded_events:
            start_idx = int(offset * sample_rate)
            if start_idx >= total_samples:
                continue

            if ev_type == "note":
                safe = name.replace("#", "s")
                fname = f"holohand_{safe}4.wav"
                samples = get_wav_samples(fname)
                if samples is not None:
                    end_idx = min(total_samples, start_idx + len(samples))
                    count = end_idx - start_idx
                    master[start_idx:end_idx] += samples[:count]

            elif ev_type == "chord":
                notes = self.CHORDS.get(name, [])
                for n in notes:
                    safe = n.replace("#", "s")
                    fname = f"holohand_{safe}4.wav"
                    samples = get_wav_samples(fname)
                    if samples is not None:
                        end_idx = min(total_samples, start_idx + len(samples))
                        count = end_idx - start_idx
                        master[start_idx:end_idx] += samples[:count]

            elif ev_type == "backing":
                vol = name
                backing_samples = get_wav_samples("backing_track.wav")
                if backing_samples is not None:
                    cur_idx = start_idx
                    while cur_idx < total_samples:
                        rem = total_samples - cur_idx
                        take = min(rem, len(backing_samples))
                        master[cur_idx:cur_idx+take] += backing_samples[:take] * vol
                        cur_idx += take

        max_peak = np.max(np.abs(master))
        if max_peak > 32767:
            master = master * (32000.0 / max_peak)
        elif max_peak > 0:
            master = master * (28000.0 / max(max_peak, 28000.0))

        master_int16 = np.clip(master, -32767, 32767).astype(np.int16)

        rec_dir = os.path.join(src_folder, "..", "recordings")
        os.makedirs(rec_dir, exist_ok=True)
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"holohand_piano_{timestamp_str}.wav"
        out_path = os.path.join(rec_dir, filename)

        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(master_int16.tobytes())

        print(f"Recorded performance exported to: {out_path}")
        return out_path

    # ========================================================
    # SOUND & CHORD PLAYBACK
    # ========================================================

    def play_note(self, note):

        note_id = note.replace("#", "s")

        try:
            self.sound_manager.play_piano(note_id)
            now = time.monotonic()
            self.key_press_timers[note] = now
            self.vu_level = min(1.0, self.vu_level + 0.65)
            self.last_played_item = f"NOTE: {note}"

            self.record_event("note", note)
            self.led_line2["text"] = f"NOTE: {note}  |  POLYPHONY: 32-CH  |  CLOCK: 44.1 kHz"
            self.status["text"] = f"PLAYING NOTE: {note}"

        except Exception as error:
            print("Piano sound error:", error)

    def play_chord(self, name):

        notes = self.CHORDS.get(name, [])
        now = time.monotonic()

        for note in notes:
            self.play_note(note)
            self.key_press_timers[note] = now

        self.record_event("chord", name)
        self.vu_level = 1.0
        self.last_played_item = f"CHORD: {name}"

        chord_str = " + ".join(notes)
        self.led_line2["text"] = f"CHORD: {name} [{chord_str}]"
        self.status["text"] = f"PLAYING CHORD: {name}  [{chord_str}]"

    def step_chord_progression(self):

        name = self.CHORD_PROGRESSION[self.progression_step]
        self.play_chord(name)

        self.progression_step = (self.progression_step + 1) % len(self.CHORD_PROGRESSION)
        next_name = self.CHORD_PROGRESSION[self.progression_step]

        self.prog_btn["text"] = f"[ > NEXT CHORD: {next_name[:5]} ]"

    # ========================================================
    # PLAY MODE, INPUT & SPEED TOGGLES
    # ========================================================

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

    def toggle_speed_mode(self):

        if self.speed_mode == "NORMAL":
            self.speed_mode = "RELAXED"
            self.key_dwell_time = 0.130
            self.smoothing_alpha = 0.35
        elif self.speed_mode == "RELAXED":
            self.speed_mode = "FAST"
            self.key_dwell_time = 0.045
            self.smoothing_alpha = 0.65
        else:
            self.speed_mode = "NORMAL"
            self.key_dwell_time = 0.085
            self.smoothing_alpha = 0.45

        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.update_mode_ui()

    def update_mode_ui(self):

        if hasattr(self, "mode_btn"):
            if self.play_mode == "AIR_KEYBOARD":
                self.mode_btn["text"] = "MODE: AIR-KEYBOARD"
                self.mode_btn["frameColor"] = (0.04, 0.32, 0.48, 1)
                self.mode_btn["text_fg"] = (0.2, 1.0, 1.0, 1)
            else:
                self.mode_btn["text"] = "MODE: PINCH"
                self.mode_btn["frameColor"] = (0.42, 0.12, 0.52, 1)
                self.mode_btn["text_fg"] = (1.0, 0.7, 1.0, 1)

        if hasattr(self, "input_btn"):
            if self.gesture_input_enabled:
                self.input_btn["text"] = "INPUT: ACTIVE"
                self.input_btn["frameColor"] = (0.05, 0.42, 0.24, 1)
                self.input_btn["text_fg"] = (0.3, 1.0, 0.6, 1)
            else:
                self.input_btn["text"] = "INPUT: MUTED"
                self.input_btn["frameColor"] = (0.50, 0.22, 0.05, 1)
                self.input_btn["text_fg"] = (1.0, 0.75, 0.3, 1)

        if hasattr(self, "speed_btn"):
            self.speed_btn["text"] = f"SPEED: {self.speed_mode}"

        input_str = "ACTIVE" if self.gesture_input_enabled else "MUTED"
        self.led_line1["text"] = f"MODE: {self.play_mode}  |  INPUT: {input_str}  |  OCTAVE: C4 - C5"

        if self.play_mode == "AIR_KEYBOARD":
            self.status["text"] = f"AIR-KEYBOARD [{self.speed_mode}]: HOVER TO PLAY | [M] PINCH | [SPACE] MUTE"
        else:
            self.status["text"] = "PINCH MODE: HOVER KEY AND PINCH TO PLAY | [M] AIR-KEYBOARD"

    # ========================================================
    # HAND LANDMARK HELPERS
    # ========================================================

    def landmarks(self, hand):

        if hand is None:
            return None

        if hasattr(hand, "landmark"):
            return hand.landmark

        if hasattr(hand, "landmarks"):
            return hand.landmarks

        if isinstance(hand, dict):
            return hand.get("landmarks", hand.get("landmark"))

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
            (x - 0.5) * 2.0 * aspect,
            (0.5 - y) * 2.0
        )

    # ========================================================
    # FINGERTIP POINTER DRAWING
    # ========================================================

    def draw_pointer(self, x, z, color, radius=0.038):

        lines = LineSegs()
        lines.setThickness(3)
        lines.setColor(*color)

        for i in range(25):
            angle = i * 2.0 * math.pi / 24.0
            px = x + radius * math.cos(angle)
            pz = z + radius * math.sin(angle)
            if i == 0:
                lines.moveTo(px, 0, pz)
            else:
                lines.drawTo(px, 0, pz)

        # Crosshair center dot
        lines.moveTo(x - 0.010, 0, z)
        lines.drawTo(x + 0.010, 0, z)
        lines.moveTo(x, 0, z - 0.010)
        lines.drawTo(x, 0, z + 0.010)

        node = self.pointer_root.attachNewNode(lines.create())
        self.pointer_nodes.append(node)

    def clear_pointers(self):

        for node in self.pointer_nodes:
            node.removeNode()

        self.pointer_nodes.clear()

    # ========================================================
    # TARGET COLLISION & KEY HIGHLIGHTING
    # ========================================================

    def reset_keys(self):

        now = time.monotonic()

        # White keys
        for note, frame in self.white_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.20:
                # Brilliant Electric Cyan/Blue pressed flash
                frame["frameColor"] = (0.40, 0.95, 1.0, 1.0)
            else:
                frame["frameColor"] = (0.95, 0.97, 1.0, 1.0)

        # Black keys
        for note, frame in self.black_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.20:
                # Glowing Neon Magenta/Violet pressed flash
                frame["frameColor"] = (0.95, 0.45, 1.0, 1.0)
            else:
                frame["frameColor"] = (0.08, 0.10, 0.15, 1.0)

        # Chord buttons reset to their original palette
        for name, btn in self.chord_buttons.items():
            col = self.CHORD_COLORS.get(name, (0.04, 0.20, 0.35, 1))
            btn["frameColor"] = col

    def find_target(self, x, z):

        # Chord buttons (left panel)
        for region in self.chord_regions:
            if abs(x - region["x"]) <= region["w"] and abs(z - region["z"]) <= region["h"]:
                return ("chord", region["name"])

        # Black keys first (strict hit priority over white keys)
        for region in self.key_regions:
            if not region["black"]:
                continue
            if abs(x - region["x"]) <= region["w"] and abs(z - region["z"]) <= region["h"]:
                return ("note", region["note"])

        # White keys
        for region in self.key_regions:
            if region["black"]:
                continue
            if abs(x - region["x"]) <= region["w"] and abs(z - region["z"]) <= region["h"]:
                return ("note", region["note"])

        return None

    def highlight_target(self, target, hand_idx=0):

        if target is None:
            return

        kind, name = target

        if kind == "chord":
            if name in self.chord_buttons:
                self.chord_buttons[name]["frameColor"] = (0.12, 0.65, 0.95, 1)
            chord_notes = self.CHORDS.get(name, [])
            for note in chord_notes:
                self._apply_key_highlight(note, hand_idx)
            return

        if kind == "note":
            self._apply_key_highlight(name, hand_idx)

    def _apply_key_highlight(self, name, hand_idx=0):

        if hand_idx == 0:
            white_col = (0.30, 0.95, 1.0, 1.0)  # Bright Cyan
            black_col = (0.75, 0.40, 1.0, 1.0)  # Vivid Violet
        else:
            white_col = (1.0, 0.50, 0.88, 1.0)  # Radiant Pink
            black_col = (1.0, 0.25, 0.75, 1.0)  # Hot Magenta

        if name in self.white_frames:
            self.white_frames[name]["frameColor"] = white_col
        elif name in self.black_frames:
            self.black_frames[name]["frameColor"] = black_col

    # ========================================================
    # MAIN UPDATE LOOP
    # ========================================================

    def update(self, hands):

        if not self.active:
            return

        self.clear_pointers()
        self.reset_keys()

        now = time.monotonic()
        self._update_telemetry(now)

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
            self.led_line3["text"] = f"TRACKING: WAITING FOR HANDS  |  VU {self._vu_bar()}"
            return

        # Pre-process up to 2 hands
        processed_hands = []
        for hand in hands_list[:2]:
            lm = self.landmarks(hand)
            if lm is not None and len(lm) >= 21:
                processed_hands.append((hand, lm, lm[8].x))

        if len(processed_hands) == 2:
            processed_hands.sort(key=lambda item: item[2])

        hand_colors = [
            (0.0, 1.0, 1.0, 1.0),   # Hand 0: Electric Cyan
            (1.0, 0.3, 0.85, 1.0)   # Hand 1: Neon Magenta/Pink
        ]

        active_statuses = []

        for h_idx, (hand, lm, _) in enumerate(processed_hands):
            # Index fingertip
            x, z = self.screen_point(lm[8])

            if self.cursors[h_idx] is None:
                self.cursors[h_idx] = (x, z)
            else:
                old_x, old_z = self.cursors[h_idx]
                alpha = self.smoothing_alpha
                self.cursors[h_idx] = (
                    old_x + (x - old_x) * alpha,
                    old_z + (z - old_z) * alpha
                )

            cx, cz = self.cursors[h_idx]
            self.draw_pointer(cx, cz, hand_colors[h_idx], radius=0.038)

            target = self.find_target(cx, cz)

            if target is not None:
                self.highlight_target(target, h_idx)
                active_statuses.append(f"H{h_idx + 1}: {target[1]}")

            # ------------------------------------
            # MODE A: AIR-KEYBOARD MODE (DEFAULT)
            # ------------------------------------
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

            # ------------------------------------
            # MODE B: PINCH-TO-PLAY MODE
            # ------------------------------------
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

        # Status text update
        h_count = len(processed_hands)
        h_str = f"{h_count} HAND{'S' if h_count > 1 else ''}"
        self.led_line3["text"] = f"TRACKING: {h_str} ACTIVE  |  VU {self._vu_bar()}"

        if active_statuses:
            status_text = "  |  ".join(active_statuses)
            if not self.gesture_input_enabled:
                status_text += " [MUTED - PRESS SPACE TO UNMUTE]"
            self.status["text"] = status_text
        elif not self.gesture_input_enabled:
            self.status["text"] = "GESTURE INPUT MUTED [PRESS SPACE TO UNMUTE]"

    def _update_telemetry(self, now):

        # Decay VU meter
        self.vu_level = max(0.0, self.vu_level - 0.04)

        # Update recording status timer
        if self.is_recording:
            elapsed = int(now - self.record_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            count = len(self.recorded_events)
            self.rec_status_label["text"] = f"[* REC] {mins:02d}:{secs:02d} ({count} notes)"

    def _vu_bar(self):

        bars = int(self.vu_level * 10)
        return "[" + ("|" * bars) + (" " * (10 - bars)) + "]"

    # ========================================================
    # SHOW / HIDE / CLEANUP
    # ========================================================

    def show(self):

        self.active = True
        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.pinch_downs = [False, False]

        # Keyboard hotkeys
        self.base.accept("m", self.toggle_play_mode)
        self.base.accept("space", self.toggle_gesture_input)
        self.base.accept("r", self.toggle_recording)
        self.base.accept("t", self.play_track)
        self.base.accept("s", self.stop_track)
        self.base.accept("=", lambda: self.adjust_volume(+0.10))
        self.base.accept("+", lambda: self.adjust_volume(+0.10))
        self.base.accept("-", lambda: self.adjust_volume(-0.10))
        self.base.accept("n", self.step_chord_progression)

        self.frame.show()
        self.pointer_root.show()
        self.update_mode_ui()

    def hide(self):

        self.active = False

        self.base.ignore("m")
        self.base.ignore("space")
        self.base.ignore("r")
        self.base.ignore("t")
        self.base.ignore("s")
        self.base.ignore("=")
        self.base.ignore("+")
        self.base.ignore("-")
        self.base.ignore("n")

        self.frame.hide()
        self.pointer_root.hide()

        self.clear_pointers()
        self.reset_keys()
        self.stop_track()

        if self.is_recording:
            self.stop_recording()

        self.cursors = [None, None]
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.pinch_downs = [False, False]

    def cleanup(self):

        self.hide()
        self.pointer_root.removeNode()
        self.frame.destroy()
