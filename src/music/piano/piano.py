import os
import time
import math
import wave
from pathlib import Path
import numpy as np

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton
)
from panda3d.core import TextNode, LineSegs, Vec4, TransparencyAttrib


class Piano:
    """
    HoloHand AI - Professional Digital Synthesizer Workstation.

    Features:
      - Air-Keyboard mode (natural horizontal hover-to-play with zero-repetition dwell)
      - Pinch-to-Play mode (intentional pinch trigger with palm-scale hysteresis)
      - Play / Pause Gesture Input control (silent practice / reposition mode)
      - Two-hand independent polyphonic playing (Cyan & Pink fingertip pointers)
      - Realistic Stage Synthesizer keyboard layout with ivory/obsidian keys & press glow
      - Chord Studio: 6 polyphonic chords (C, G, Am, F, Dm, Em) + progression stepper
      - Music Studio: Backing track audio player (Play, Pause, Stop, Volume)
      - Performance Recorder: Capture live performance & export to WAV in recordings/
      - Real-time LED digital readout & dynamic audio VU meter
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

        # Key press visual illumination timers: note_name -> hit_timestamp
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
        self.recorded_events = []      # list of (timestamp_offset, event_type, data)
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
        self.action_regions = []

        # Master workstation chassis frame
        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameSize=(-1.78, 1.78, -1.0, 1.0),
            frameColor=(0.012, 0.016, 0.026, 1),
            relief=None
        )

        # Build workstation panels
        self._build_top_deck()
        self._build_keyboard()
        self._build_chord_studio()
        self._build_music_studio()
        self._build_bottom_status()

        # Pointer root attached with high priority
        self.pointer_root = base.aspect2d.attachNewNode("PianoFingerPointers")
        self.pointer_root.setBin("fixed", 115)
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
            frameSize=(-1.72, 1.72, -0.19, 0.19),
            frameColor=(0.02, 0.03, 0.05, 0.95)
        )

        # Header branding
        self.title_label = DirectLabel(
            parent=self.deck_banner,
            text="HOLOHAND AI  //  PRO SYNTHESIZER WORKSTATION",
            pos=(-0.85, 0, 0.11),
            scale=0.038,
            text_fg=(0.3, 0.95, 1.0, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.subtitle_label = DirectLabel(
            parent=self.deck_banner,
            text="MULTI-HAND AIR-KEYBOARD  |  CHORD MATRIX  |  STUDIO RECORDER",
            pos=(-0.85, 0, 0.055),
            scale=0.020,
            text_fg=(0.55, 0.75, 0.90, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Central LED display readout box
        self.led_box = DirectFrame(
            parent=self.deck_banner,
            pos=(0.32, 0, 0.01),
            frameSize=(-0.58, 0.58, -0.14, 0.14),
            frameColor=(0.005, 0.015, 0.025, 0.98)
        )

        # LED readouts
        self.led_line1 = DirectLabel(
            parent=self.led_box,
            text="MODE: AIR-KEYBOARD  |  INPUT: ACTIVE  |  OCTAVE: C4 - C5",
            pos=(-0.54, 0, 0.075),
            scale=0.022,
            text_fg=(0.3, 1.0, 0.85, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line2 = DirectLabel(
            parent=self.led_box,
            text="NOTE: READY  |  POLYPHONY: 32-CH  |  CLOCK: 44.1 kHz",
            pos=(-0.54, 0, 0.015),
            scale=0.022,
            text_fg=(0.6, 0.88, 1.0, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line3 = DirectLabel(
            parent=self.led_box,
            text="TRACKING: WAITING  |  VU [||||            ]",
            pos=(-0.54, 0, -0.045),
            scale=0.022,
            text_fg=(1.0, 0.85, 0.3, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.led_line4 = DirectLabel(
            parent=self.led_box,
            text="REC: IDLE  |  TRACK: STOPPED",
            pos=(-0.54, 0, -0.100),
            scale=0.019,
            text_fg=(0.55, 0.70, 0.85, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Quick mode toggle buttons on deck
        self.mode_btn = self._make_deck_button(
            "MODE: AIR-KEYBOARD",
            -0.55, -0.065,
            self.toggle_play_mode,
            width=0.22,
            bg_col=(0.02, 0.25, 0.38, 1),
            fg_col=(0.3, 1.0, 1.0, 1)
        )

        self.input_btn = self._make_deck_button(
            "INPUT: ACTIVE",
            -0.18, -0.065,
            self.toggle_gesture_input,
            width=0.18,
            bg_col=(0.04, 0.32, 0.20, 1),
            fg_col=(0.4, 1.0, 0.6, 1)
        )

    def _make_deck_button(self, text, x, z, callback, width=0.20, bg_col=None, fg_col=None):

        bg = bg_col or (0.03, 0.15, 0.25, 1)
        fg = fg_col or (0.8, 1, 1, 1)

        btn = DirectButton(
            parent=self.deck_banner,
            text=text,
            pos=(x, 0, z),
            text_scale=0.030,
            text_fg=fg,
            frameSize=(-width, width, -0.050, 0.050),
            frameColor=bg,
            command=callback
        )
        return btn

    # ========================================================
    # MAIN KEYBOARD
    # ========================================================

    def _build_keyboard(self):

        # Outer metallic keyboard bed
        self.keybed_frame = DirectFrame(
            parent=self.frame,
            pos=(0, 0, -0.20),
            frameSize=(-0.98, 0.98, -0.32, 0.32),
            frameColor=(0.025, 0.032, 0.045, 1)
        )

        # Keyboard bed accent header
        DirectLabel(
            parent=self.keybed_frame,
            text="OCTAVE 4  //  13-KEY CHROMATIC KEYBED  [C4 - C5]",
            pos=(0, 0, 0.26),
            scale=0.024,
            text_fg=(0.4, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        start_x = -0.7525
        width = 0.215

        # 1. White keys (8 keys: C, D, E, F, G, A, B, C5)
        for i, note in enumerate(self.WHITE):

            x = start_x + i * width
            z_pos = -0.04

            # White key body
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.103, 0.103, -0.245, 0.245),
                frameColor=(0.94, 0.96, 1.0, 1)
            )

            # Key bevel lip
            DirectFrame(
                parent=frame,
                pos=(0, 0, -0.235),
                frameSize=(-0.098, 0.098, -0.008, 0.008),
                frameColor=(0.75, 0.80, 0.88, 1)
            )

            # Note label centered at bottom of key
            DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.190),
                scale=0.038,
                text_fg=(0.05, 0.08, 0.15, 1),
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.white_frames[note] = frame

            # Register region for collision detection
            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.24, # world-space z
                "w": 0.103,
                "h": 0.245,
                "black": False
            })

        # 2. Black keys (5 keys: C#, D#, F#, G#, A#)
        for note, after in self.BLACK:

            x = start_x + after * width + width / 2.0
            z_pos = 0.080

            # Black key body (raised and higher bin)
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.062, 0.062, -0.135, 0.135),
                frameColor=(0.015, 0.018, 0.030, 1)
            )
            frame.setBin("fixed", 65)

            # Top highlight bevel
            bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, 0.125),
                frameSize=(-0.056, 0.056, -0.006, 0.006),
                frameColor=(0.15, 0.25, 0.35, 1)
            )
            bevel.setBin("fixed", 66)

            # Sharp note label
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.095),
                scale=0.026,
                text_fg=(0.4, 0.9, 1.0, 1),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 67)

            self.black_frames[note] = frame

            self.key_regions.append({
                "note": note,
                "x": x,
                "z": -0.120, # world-space z
                "w": 0.062,
                "h": 0.135,
                "black": True
            })

    # ========================================================
    # LEFT PANEL — CHORD STUDIO
    # ========================================================

    def _build_chord_studio(self):

        self.chord_panel_frame = DirectFrame(
            parent=self.frame,
            pos=(-1.38, 0, -0.08),
            frameSize=(-0.35, 0.35, -0.52, 0.52),
            frameColor=(0.02, 0.025, 0.04, 0.95)
        )

        DirectLabel(
            parent=self.chord_panel_frame,
            text="CHORD STUDIO",
            pos=(0, 0, 0.45),
            scale=0.036,
            text_fg=(0.3, 1.0, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.chord_panel_frame,
            text="POLYPHONIC CHORD PADS",
            pos=(0, 0, 0.39),
            scale=0.018,
            text_fg=(0.6, 0.75, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # 6 Chord Pads
        chord_list = [
            ("C MAJOR", "C - E - G"),
            ("G MAJOR", "G - B - D"),
            ("A MINOR", "A - C - E"),
            ("F MAJOR", "F - A - C"),
            ("D MINOR", "D - F - A"),
            ("E MINOR", "E - G - B")
        ]

        start_z = 0.30
        step_z = 0.10

        for i, (name, notes_str) in enumerate(chord_list):
            z = start_z - i * step_z

            btn = DirectButton(
                parent=self.chord_panel_frame,
                text=f"{name} [{notes_str}]",
                pos=(0, 0, z),
                text_scale=0.024,
                text_fg=(0.85, 0.98, 1.0, 1),
                frameSize=(-0.32, 0.32, -0.040, 0.040),
                frameColor=(0.04, 0.16, 0.28, 1),
                command=lambda c=name: self.play_chord(c)
            )

            self.chord_buttons[name] = btn

            # Register region for hand targeting
            self.chord_regions.append({
                "name": name,
                "x": -1.38,
                "z": -0.08 + z,
                "w": 0.32,
                "h": 0.040
            })

        # Chord Progression Stepper
        DirectLabel(
            parent=self.chord_panel_frame,
            text="PROGRESSION PLAYER",
            pos=(0, 0, -0.32),
            scale=0.022,
            text_fg=(0.95, 0.75, 0.25, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.progression_label = DirectLabel(
            parent=self.chord_panel_frame,
            text="C -> G -> Am -> F",
            pos=(0, 0, -0.37),
            scale=0.020,
            text_fg=(0.6, 0.9, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.prog_btn = DirectButton(
            parent=self.chord_panel_frame,
            text="[ > NEXT CHORD: C MAJ ]",
            pos=(0, 0, -0.45),
            text_scale=0.025,
            text_fg=(1.0, 0.95, 0.4, 1),
            frameSize=(-0.30, 0.30, -0.045, 0.045),
            frameColor=(0.25, 0.15, 0.03, 1),
            command=self.step_chord_progression
        )

    # ========================================================
    # RIGHT PANEL — MUSIC STUDIO & RECORDER
    # ========================================================

    def _build_music_studio(self):

        self.music_panel_frame = DirectFrame(
            parent=self.frame,
            pos=(1.38, 0, -0.08),
            frameSize=(-0.35, 0.35, -0.52, 0.52),
            frameColor=(0.02, 0.025, 0.04, 0.95)
        )

        DirectLabel(
            parent=self.music_panel_frame,
            text="MUSIC STUDIO",
            pos=(0, 0, 0.45),
            scale=0.036,
            text_fg=(0.3, 1.0, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Backing track section
        self.track_name_label = DirectLabel(
            parent=self.music_panel_frame,
            text=self.track_name,
            pos=(0, 0, 0.39),
            scale=0.021,
            text_fg=(0.7, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.track_play_btn = DirectButton(
            parent=self.music_panel_frame,
            text="PLAY TRACK",
            pos=(-0.16, 0, 0.30),
            text_scale=0.026,
            text_fg=(0.4, 1.0, 0.6, 1),
            frameSize=(-0.14, 0.14, -0.042, 0.042),
            frameColor=(0.03, 0.28, 0.15, 1),
            command=self.play_track
        )

        self.track_pause_btn = DirectButton(
            parent=self.music_panel_frame,
            text="PAUSE",
            pos=(0.16, 0, 0.30),
            text_scale=0.026,
            text_fg=(1.0, 0.85, 0.3, 1),
            frameSize=(-0.14, 0.14, -0.042, 0.042),
            frameColor=(0.30, 0.22, 0.03, 1),
            command=self.pause_track
        )

        self.track_stop_btn = DirectButton(
            parent=self.music_panel_frame,
            text="STOP TRACK",
            pos=(0, 0, 0.20),
            text_scale=0.026,
            text_fg=(1.0, 0.4, 0.4, 1),
            frameSize=(-0.30, 0.30, -0.040, 0.040),
            frameColor=(0.30, 0.08, 0.08, 1),
            command=self.stop_track
        )

        # Volume controls
        self.vol_down_btn = DirectButton(
            parent=self.music_panel_frame,
            text="VOL -",
            pos=(-0.20, 0, 0.10),
            text_scale=0.024,
            text_fg=(0.8, 0.95, 1.0, 1),
            frameSize=(-0.09, 0.09, -0.035, 0.035),
            frameColor=(0.04, 0.15, 0.25, 1),
            command=lambda: self.adjust_volume(-0.10)
        )

        self.vol_label = DirectLabel(
            parent=self.music_panel_frame,
            text="VOL: 80%",
            pos=(0, 0, 0.10),
            scale=0.022,
            text_fg=(0.7, 0.9, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_up_btn = DirectButton(
            parent=self.music_panel_frame,
            text="VOL +",
            pos=(0.20, 0, 0.10),
            text_scale=0.024,
            text_fg=(0.8, 0.95, 1.0, 1),
            frameSize=(-0.09, 0.09, -0.035, 0.035),
            frameColor=(0.04, 0.15, 0.25, 1),
            command=lambda: self.adjust_volume(+0.10)
        )

        # Divider line
        DirectLabel(
            parent=self.music_panel_frame,
            text="----------------------------------",
            pos=(0, 0, 0.02),
            scale=0.022,
            text_fg=(0.25, 0.4, 0.55, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Performance recording section
        DirectLabel(
            parent=self.music_panel_frame,
            text="STUDIO RECORDER",
            pos=(0, 0, -0.05),
            scale=0.032,
            text_fg=(1.0, 0.45, 0.45, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.record_btn = DirectButton(
            parent=self.music_panel_frame,
            text="[ * RECORD ]",
            pos=(0, 0, -0.15),
            text_scale=0.030,
            text_fg=(1.0, 0.35, 0.35, 1),
            frameSize=(-0.30, 0.30, -0.048, 0.048),
            frameColor=(0.35, 0.05, 0.05, 1),
            command=self.toggle_recording
        )

        self.rec_status_label = DirectLabel(
            parent=self.music_panel_frame,
            text="RECORDER IDLE",
            pos=(0, 0, -0.25),
            scale=0.022,
            text_fg=(0.6, 0.8, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.rec_file_label = DirectLabel(
            parent=self.music_panel_frame,
            text="WAV EXPORT: recordings/",
            pos=(0, 0, -0.32),
            scale=0.017,
            text_fg=(0.4, 0.7, 0.9, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Shortcut hints
        DirectLabel(
            parent=self.music_panel_frame,
            text="HOTKEYS: [R] REC | [T] TRACK | [SPACE] MUTE",
            pos=(0, 0, -0.45),
            scale=0.017,
            text_fg=(0.45, 0.6, 0.75, 1),
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
            scale=0.025,
            text_fg=(0.35, 1.0, 0.85, 1),
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
                self.track_play_btn["text_fg"] = (0.3, 1.0, 0.5, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PLAYING"
                return

            self.stop_track()
            # Loop indefinitely (-1)
            self.track_channel = self.track_sound.play(loops=-1)
            if self.track_channel:
                self.track_channel.set_volume(self.track_volume)
            self.track_paused = False
            self.track_play_btn["text_fg"] = (0.3, 1.0, 0.5, 1)
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
                self.track_play_btn["text_fg"] = (0.7, 0.9, 1.0, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PAUSED"
            else:
                self.track_channel.unpause()
                self.track_paused = False
                self.track_play_btn["text_fg"] = (0.3, 1.0, 0.5, 1)
                self.led_line4["text"] = f"REC: {'RECORDING' if self.is_recording else 'IDLE'}  |  TRACK: PLAYING"

    def stop_track(self):

        if self.track_channel is not None:
            self.track_channel.stop()
            self.track_channel = None
        self.track_paused = False
        self.track_play_btn["text_fg"] = (0.4, 1.0, 0.6, 1)
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

        # If backing track is currently playing, record its start
        if self.track_channel and self.track_channel.get_busy() and not self.track_paused:
            self.recorded_events.append((0.0, "backing", self.track_volume))

        self.record_btn["text"] = "[ # STOP REC ]"
        self.record_btn["frameColor"] = (0.65, 0.08, 0.08, 1)
        self.record_btn["text_fg"] = (1.0, 1.0, 1.0, 1)
        self.rec_status_label["text"] = "[* REC] 00:00 (0 notes)"
        self.rec_status_label["text_fg"] = (1.0, 0.3, 0.3, 1)
        self.led_line4["text"] = f"REC: RECORDING...  |  TRACK: {'PLAYING' if self.track_channel and not self.track_paused else 'STOPPED'}"

    def stop_recording(self):

        if not self.is_recording:
            return

        self.is_recording = False
        duration = time.monotonic() - self.record_start_time

        self.record_btn["text"] = "[ * RECORD ]"
        self.record_btn["frameColor"] = (0.35, 0.05, 0.05, 1)
        self.record_btn["text_fg"] = (1.0, 0.35, 0.35, 1)
        self.rec_status_label["text"] = f"SAVED ({len(self.recorded_events)} events)"
        self.rec_status_label["text_fg"] = (0.4, 1.0, 0.6, 1)
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

        # 32-bit float stereo mixing buffer
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

        # Mix all timestamped events
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

        # Peak normalization and soft-limiting
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
        self.progression_label["text"] = f"STEP {self.progression_step + 1}/4: {name} -> NEXT: {next_name}"

    # ========================================================
    # PLAY MODE & INPUT TOGGLES
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

        input_str = "ACTIVE" if self.gesture_input_enabled else "MUTED"
        self.led_line1["text"] = f"MODE: {self.play_mode}  |  INPUT: {input_str}  |  OCTAVE: C4 - C5"

        if self.play_mode == "AIR_KEYBOARD":
            self.status["text"] = "AIR-KEYBOARD: HOVER KEYS TO PLAY | [M] PINCH MODE | [SPACE] MUTE"
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

        # Decay resting white keys unless recently struck
        for note, frame in self.white_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.18:
                # Electric blue pressed illumination
                frame["frameColor"] = (0.50, 0.96, 1.0, 1)
            else:
                frame["frameColor"] = (0.94, 0.96, 1.0, 1)

        # Decay resting black keys unless recently struck
        for note, frame in self.black_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.18:
                # Vivid purple pressed illumination
                frame["frameColor"] = (0.90, 0.50, 1.0, 1)
            else:
                frame["frameColor"] = (0.015, 0.018, 0.030, 1)

        # Decay chord buttons
        for btn in self.chord_buttons.values():
            btn["frameColor"] = (0.04, 0.16, 0.28, 1)

    def find_target(self, x, z):

        # Chord buttons (left panel)
        for region in self.chord_regions:
            if abs(x - region["x"]) <= region["w"] and abs(z - region["z"]) <= region["h"]:
                return ("chord", region["name"])

        # Black keys first (hierarchical priority)
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
                self.chord_buttons[name]["frameColor"] = (0.08, 0.35, 0.55, 1)
            chord_notes = self.CHORDS.get(name, [])
            for note in chord_notes:
                self._apply_key_highlight(note, hand_idx)
            return

        if kind == "note":
            self._apply_key_highlight(name, hand_idx)

    def _apply_key_highlight(self, name, hand_idx=0):

        if hand_idx == 0:
            white_col = (0.25, 0.95, 1.0, 1)  # Cyan
            black_col = (0.65, 0.40, 1.0, 1)  # Violet
        else:
            white_col = (1.0, 0.45, 0.85, 1)  # Pink
            black_col = (0.90, 0.25, 0.70, 1)  # Magenta

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

        # Update dynamic VU meter & recording timer in UI
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

        # Sort hands horizontally (Hand 0 left, Hand 1 right)
        if len(processed_hands) == 2:
            processed_hands.sort(key=lambda item: item[2])

        hand_colors = [
            (0.0, 1.0, 1.0, 1.0),   # Hand 0: Electric Cyan
            (1.0, 0.3, 0.85, 1.0)   # Hand 1: Neon Magenta/Pink
        ]

        active_statuses = []

        for h_idx, (hand, lm, _) in enumerate(processed_hands):
            # Index fingertip (landmark 8)
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
