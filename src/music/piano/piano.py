import os
import time
import math
import wave
from pathlib import Path
import numpy as np

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DGG
)
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, LineSegs, Vec4, TransparencyAttrib


class Piano:
    """
    HoloHand AI - Professional Cyber Stage Synthesizer Workstation.

    Complete Upgrade:
      - 1:1 Visual Match with Reference Workstation Design (Image 2)
      - Large, high-contrast, bold font sizes across all keyboards and controls
      - Left Panel: HOME button, Major/Minor Tabs, 7 Rich Color Chord Pads, Chord Progression
      - Center Console:
          * Top: PLAY MODE (Air-Keyboard / Pinch), OCTAVE 2-6 with [-] and [+], SUSTAIN (ON/OFF),
                 REVERB (ON/OFF), VOLUME %, CURRENT NOTE (Large Box)
          * Below (Main Keyboard Settings Bay):
              - Left: SOUND PATCHES (PIANO, E.PIANO, ORGAN, STRINGS, PAD, SYNTH) with large buttons
              - Center: Blue LCD Spectrum Analyzer Screen (real-time reactive audio display)
              - Right: KEYBOARD SETTINGS (Piano Volume [-]/[+], Speed Toggle, Visual FX Toggle)
          * Piano Keyboard: 8 Ivory White Keys + 5 Ebony Black Keys (Z-Order 35, Drop Shadows, Bevels)
          * Bottom Navigation Dock: PIANO, DRUMS, HOME
      - Right Panel: SETTINGS button, 8 Distinct Musical Tracks at full 26,000 peak volume,
                     Transport Row (Play, Pause, Stop, Mute), Track Volume Slider, Progress Timer,
                     Performance Recording Studio
      - Gesture Tracking: Adaptive mouse-like velocity smoothing, Blue (Left) & Pink (Right) glowing
                          fingertip pointers, selection ripple feedback, full button hit-testing.
    """

    WHITE = ["C", "D", "E", "F", "G", "A", "B", "C5"]

    BLACK = [
        ("C#", 0), ("D#", 1),
        ("F#", 3), ("G#", 4), ("A#", 5)
    ]

    # C Major Family Chords (Diatonic Triads: I, ii, iii, IV, V, vi, vii°)
    MAJOR_CHORDS = {
        "C MAJOR": (["C", "E", "G"], "C - E - G (I)", (0.06, 0.46, 0.76, 1.0)),
        "D MINOR": (["D", "F", "A"], "D - F - A (ii)", (0.12, 0.55, 0.42, 1.0)),
        "E MINOR": (["E", "G", "B"], "E - G - B (iii)", (0.72, 0.42, 0.15, 1.0)),
        "F MAJOR": (["F", "A", "C5"], "F - A - C (IV)", (0.80, 0.20, 0.24, 1.0)),
        "G MAJOR": (["G", "B", "D"], "G - B - D (V)", (0.85, 0.55, 0.08, 1.0)),
        "A MINOR": (["A", "C5", "E"], "A - C - E (vi)", (0.55, 0.22, 0.75, 1.0)),
        "B DIM": (["B", "D", "F"], "B - D - F (vii°)", (0.08, 0.60, 0.70, 1.0))
    }

    # Parallel & Relative Minor Family Chords
    MINOR_CHORDS = {
        "A MINOR": (["A", "C5", "E"], "A - C - E (i)", (0.55, 0.22, 0.75, 1.0)),
        "D MINOR": (["D", "F", "A"], "D - F - A (iv)", (0.12, 0.55, 0.42, 1.0)),
        "E MINOR": (["E", "G", "B"], "E - G - B (v)", (0.72, 0.42, 0.15, 1.0)),
        "F MAJOR": (["F", "A", "C5"], "F - A - C (VI)", (0.80, 0.20, 0.24, 1.0)),
        "G MAJOR": (["G", "B", "D"], "G - B - D (VII)", (0.85, 0.55, 0.08, 1.0)),
        "C MAJOR": (["C", "E", "G"], "C - E - G (III)", (0.06, 0.46, 0.76, 1.0)),
        "C MINOR": (["C", "Ds", "G"], "C - Eb - G (i)", (0.20, 0.40, 0.65, 1.0))
    }

    # Standard Diatonic Progressions in C Major and A Minor Families
    MAJOR_PROGRESSIONS = [
        ("POP HIT (I - V - vi - IV)", ["C MAJOR", "G MAJOR", "A MINOR", "F MAJOR"]),
        ("DOO-WOP (I - vi - IV - V)", ["C MAJOR", "A MINOR", "F MAJOR", "G MAJOR"]),
        ("JAZZ CADENCE (ii - V - I)", ["D MINOR", "G MAJOR", "C MAJOR", "A MINOR"]),
        ("CANON (I - V - vi - iii - IV)", ["C MAJOR", "G MAJOR", "A MINOR", "E MINOR", "F MAJOR", "C MAJOR"]),
        ("CLASSIC (I - IV - V - I)", ["C MAJOR", "F MAJOR", "G MAJOR", "C MAJOR"])
    ]

    MINOR_PROGRESSIONS = [
        ("DARK POP (i - VI - III - VII)", ["A MINOR", "F MAJOR", "C MAJOR", "G MAJOR"]),
        ("BALLAD (i - iv - v - i)", ["A MINOR", "D MINOR", "E MINOR", "A MINOR"]),
        ("ANDALUSIAN (i - VII - VI - V)", ["A MINOR", "G MAJOR", "F MAJOR", "E MINOR"]),
        ("EPIC CINEMATIC", ["C MINOR", "G MAJOR", "A MINOR", "F MAJOR"])
    ]

    CHORD_PROGRESSION = [
        "C MAJOR", "G MAJOR", "A MINOR", "F MAJOR"
    ]

    TRACK_FILES = [
        ("Pop Beat", "pop_beat.wav", 120),
        ("Ballad (Vocal)", "ballad_beat.wav", 72),
        ("Acoustic Beat", "acoustic_beat.wav", 95),
        ("Electronic Beat", "electronic_beat.wav", 128),
        ("Hip Hop", "hiphop_beat.wav", 90),
        ("Rock Beat", "rock_beat.wav", 116),
        ("Chill Ambient", "chill_beat.wav", 78),
        ("Entertainer", "entertainer_beat.wav", 100)
    ]

    SYNTH_PATCHES = ["PIANO", "E.PIANO", "ORGAN", "STRINGS", "PAD", "SYNTH"]

    def __init__(self, base, sound_manager):

        self.base = base
        self.sound_manager = sound_manager
        self.active = False

        # Playing modes: "AIR_KEYBOARD" (default hover-to-play) or "PINCH"
        self.play_mode = "AIR_KEYBOARD"
        self.gesture_input_enabled = True

        # Octave control: 2 to 6 (default 4)
        self.current_octave = 4

        # Sound parameters
        self.current_patch = "PIANO"
        self.sustain_on = True
        self.reverb_on = False
        self.piano_volume = 0.90
        self.track_volume = 1.00
        self.is_muted = False
        self.prev_track_vol = 1.00

        # Piano Volume Fade In / Fade Out animation state
        self.fade_state = "IDLE"  # "IDLE", "FADING_OUT", "FADING_IN"
        self.target_fade_volume = 0.90
        self._last_telemetry_time = time.monotonic()

        # Visual Performance Mode
        self.visual_fx_enabled = True
        self.active_beams = []

        # Chord tab state: "MAJOR" or "MINOR"
        self.active_chord_tab = "MAJOR"
        self.progression_idx = 0
        self.progression_step = 0

        # Speed / Sensitivity: "NORMAL" (85ms), "RELAXED" (130ms), "FAST" (45ms)
        self.speed_mode = "NORMAL"
        self.key_dwell_time = 0.085
        self.base_smoothing = 0.42

        # Per-hand tracking state (Hand 0: Left/Blue, Hand 1: Right/Pink)
        self.max_hands = 2
        self.cursors = [None, None]
        self.cursor_velocities = [0.0, 0.0]
        self.current_targets = [None, None]
        self.candidate_targets = [None, None]
        self.candidate_times = [0.0, 0.0]
        self.pinch_downs = [False, False]
        self.last_actions = [0.0, 0.0]
        self.last_valid_targets = [None, None]

        # Pinch detection thresholds
        self.pinch_on = 0.32
        self.pinch_off = 0.45
        self.action_cooldown = 0.16

        # Key press visual illumination timers & colors
        self.key_press_timers = {}
        self.key_press_colors = {}
        self.button_ripples = []

        # Backing track audio state & customizable tempo per track
        self.active_track_idx = 0
        self.track_bpms = [bpm for _, _, bpm in self.TRACK_FILES]
        self.default_track_bpms = list(self.track_bpms)
        self.raw_sound_data = {}
        self.track_channel = None
        self.track_sound = None
        self.track_paused = False
        self.track_start_time = 0.0
        self.track_total_duration = 8.0

        # Music Studio tab state: "TRACKS" or "CUSTOM"
        self.active_music_tab = "TRACKS"
        self.custom_track_buttons = []
        self.active_custom_path = None
        self.track_name = self.TRACK_FILES[0][0]

        # Performance recording state
        self.is_recording = False
        self.record_start_time = 0.0
        self.recorded_events = []
        self.last_exported_file = None

        # VU Meter & visualizer state
        self.vu_level = 0.0
        self.spectrum_bands = [0.0] * 12
        self.current_display_note = "READY"

        # Settings overlay state
        self.settings_open = False

        # Interactive UI target regions for hand gestures
        self.pointer_nodes = []
        self.white_frames = {}
        self.black_frames = {}
        self.chord_buttons = {}
        self.track_buttons = []
        self.patch_buttons = {}
        self.interactive_regions = []

        # Master workstation chassis frame (Deep dark background)
        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameSize=(-1.78, 1.78, -1.0, 1.0),
            frameColor=(0.02, 0.025, 0.035, 1.0),
            relief=DGG.FLAT
        )
        self.frame.setBin("fixed", 1)

        # Colorful hand-crafted acoustic studio art backdrop
        backdrop_path = "assets/studio_background.png"
        if os.path.exists(backdrop_path):
            self.backdrop = OnscreenImage(
                image=backdrop_path,
                pos=(0, 0, 0),
                scale=(1.78, 1, 1.0),
                parent=self.frame
            )
            self.backdrop.setBin("fixed", 2)
            self.backdrop.setDepthTest(False)
            self.backdrop.setDepthWrite(False)

        # Build all workstation sections
        self._build_center_console()
        self._build_keyboard()
        self._build_chord_studio()
        self._build_music_studio()
        self._build_settings_modal()

        # High priority pointer root (always top)
        self.pointer_root = base.aspect2d.attachNewNode("PianoFingerPointers")
        self.pointer_root.setBin("fixed", 120)
        self.pointer_root.setDepthTest(False)
        self.pointer_root.setDepthWrite(False)

        # Visual Performance effect root
        self.fx_root = base.aspect2d.attachNewNode("PianoVisualFX")
        self.fx_root.setBin("fixed", 110)

        # Pre-load initial backing track
        self._load_active_track()

        self.hide()

    def _navigate_to(self, mode_name):
        """Safely navigate to another screen mode in HoloHand."""
        if hasattr(self.base, 'set_mode'):
            self.base.set_mode(mode_name)
        elif hasattr(self.base, 'app') and hasattr(self.base.app, 'set_mode'):
            self.base.app.set_mode(mode_name)
        else:
            print(f"[Piano] Mode navigation: {mode_name}")

    # ========================================================
    # CENTER SYNTHESIZER CONSOLE (ALL CONTROLS PROMINENTLY ARRANGED)
    # ========================================================

    def _build_center_console(self):

        # Main synthesizer chassis body (spans -0.96 to 0.96)
        self.synth_body = DirectFrame(
            parent=self.frame,
            pos=(0, 0, 0.16),
            frameSize=(-0.96, 0.96, -0.86, 0.78),
            frameColor=(0.05, 0.06, 0.085, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.008, 0.008)
        )
        self.synth_body.setBin("fixed", 3)

        # ── 1. Top Header Plate with Textured Speaker Louvers ──
        self.header_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.68),
            frameSize=(-0.94, 0.94, -0.075, 0.075),
            frameColor=(0.03, 0.035, 0.05, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.header_frame.setBin("fixed", 5)

        for s in range(5):
            DirectFrame(
                parent=self.header_frame,
                pos=(-0.65, 0, 0.035 - s * 0.018),
                frameSize=(-0.22, 0.22, -0.003, 0.003),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )
            DirectFrame(
                parent=self.header_frame,
                pos=(0.65, 0, 0.035 - s * 0.018),
                frameSize=(-0.22, 0.22, -0.003, 0.003),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )

        DirectLabel(
            parent=self.header_frame,
            text="HOLOHAND  AI",
            pos=(0, 0, 0.012),
            scale=0.048,
            text_fg=(0.92, 0.96, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.header_frame,
            text="MUSIC STUDIO",
            pos=(0, 0, -0.038),
            scale=0.024,
            text_fg=(0.35, 0.70, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── 2. Top Hardware Control Strip (Play Mode, Octave, Sustain, Reverb, Note) ──
        self.controls_strip = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.52),
            frameSize=(-0.94, 0.94, -0.075, 0.075),
            frameColor=(0.035, 0.045, 0.065, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.controls_strip.setBin("fixed", 5)

        # PLAY MODE Selector
        DirectLabel(
            parent=self.controls_strip,
            text="PLAY MODE",
            pos=(-0.68, 0, 0.045),
            scale=0.032,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.mode_air_btn = DirectButton(
            parent=self.controls_strip,
            text="AIR KEYBOARD",
            pos=(-0.77, 0, -0.016),
            text_scale=0.028,
            text_fg=(0.95, 1.0, 1.0, 1),
            frameSize=(-0.11, 0.11, -0.038, 0.038),
            frameColor=(0.08, 0.48, 0.78, 1),
            relief=DGG.FLAT,
            command=self.set_play_mode,
            extraArgs=["AIR_KEYBOARD"]
        )

        self.mode_pinch_btn = DirectButton(
            parent=self.controls_strip,
            text="PINCH MODE",
            pos=(-0.56, 0, -0.016),
            text_scale=0.028,
            text_fg=(0.70, 0.80, 0.90, 1),
            frameSize=(-0.10, 0.10, -0.038, 0.038),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=self.set_play_mode,
            extraArgs=["PINCH"]
        )

        self._register_widget_target("action", "mode_air", self.mode_air_btn, 0.11, 0.038)
        self._register_widget_target("action", "mode_pinch", self.mode_pinch_btn, 0.10, 0.038)

        # OCTAVE Controller with Big Clear Buttons: [ - ]  4  [ + ]
        DirectLabel(
            parent=self.controls_strip,
            text="OCTAVE",
            pos=(-0.32, 0, 0.045),
            scale=0.030,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.octave_down_btn = DirectButton(
            parent=self.controls_strip,
            text="-",
            pos=(-0.40, 0, -0.016),
            text_scale=0.042,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.038, 0.038, -0.038, 0.038),
            frameColor=(0.12, 0.16, 0.24, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.adjust_octave,
            extraArgs=[-1]
        )

        self.octave_display = DirectLabel(
            parent=self.controls_strip,
            text=str(self.current_octave),
            pos=(-0.32, 0, -0.026),
            scale=0.046,
            text_fg=(0.20, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.06, 0.08, 0.12, 1),
            frameSize=(-0.042, 0.042, -0.038, 0.038)
        )

        self.octave_up_btn = DirectButton(
            parent=self.controls_strip,
            text="+",
            pos=(-0.24, 0, -0.016),
            text_scale=0.042,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.038, 0.038, -0.038, 0.038),
            frameColor=(0.12, 0.16, 0.24, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.adjust_octave,
            extraArgs=[+1]
        )

        self._register_widget_target("action", "octave_down", self.octave_down_btn, 0.038, 0.038)
        self._register_widget_target("action", "octave_up", self.octave_up_btn, 0.038, 0.038)

        # SUSTAIN Switch: [ ON ] / [ OFF ]
        DirectLabel(
            parent=self.controls_strip,
            text="SUSTAIN",
            pos=(-0.08, 0, 0.045),
            scale=0.030,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.sustain_btn = DirectButton(
            parent=self.controls_strip,
            text="ON",
            pos=(-0.08, 0, -0.016),
            text_scale=0.034,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.088, 0.088, -0.038, 0.038),
            frameColor=(0.12, 0.72, 0.32, 1),
            relief=DGG.FLAT,
            command=self.toggle_sustain
        )
        self._register_widget_target("action", "toggle_sustain", self.sustain_btn, 0.088, 0.038)

        # REVERB Switch: [ OFF / ON ]
        DirectLabel(
            parent=self.controls_strip,
            text="REVERB",
            pos=(0.14, 0, 0.045),
            scale=0.030,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.reverb_btn = DirectButton(
            parent=self.controls_strip,
            text="OFF",
            pos=(0.14, 0, -0.016),
            text_scale=0.032,
            text_fg=(0.70, 0.75, 0.85, 1),
            frameSize=(-0.085, 0.085, -0.038, 0.038),
            frameColor=(0.12, 0.14, 0.20, 1),
            relief=DGG.FLAT,
            command=self.toggle_reverb
        )
        self._register_widget_target("action", "toggle_reverb", self.reverb_btn, 0.085, 0.038)

        # CURRENT NOTE Large High-Contrast Display
        DirectLabel(
            parent=self.controls_strip,
            text="CURRENT NOTE",
            pos=(0.55, 0, 0.045),
            scale=0.030,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.current_note_frame = DirectFrame(
            parent=self.controls_strip,
            pos=(0.55, 0, -0.016),
            frameSize=(-0.16, 0.16, -0.040, 0.040),
            frameColor=(0.05, 0.08, 0.14, 1),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )

        self.current_note_label = DirectLabel(
            parent=self.current_note_frame,
            text="C4",
            pos=(0, 0, -0.018),
            scale=0.054,
            text_fg=(0.20, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── 3. Middle Hardware Rack — Main Keyboard Settings & Sound Bay ──
        self.rack_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.31),
            frameSize=(-0.94, 0.94, -0.120, 0.120),
            frameColor=(0.06, 0.07, 0.09, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.rack_frame.setBin("fixed", 5)

        # ── CLUSTER A: SOUND PATCHES (Left side, 2 Rows of 3 Big Buttons) ──
        DirectLabel(
            parent=self.rack_frame,
            text="SOUND PATCH",
            pos=(-0.65, 0, 0.078),
            scale=0.028,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        patch_row1 = [("PIANO", -0.82), ("E.PIANO", -0.65), ("ORGAN", -0.48)]
        patch_row2 = [("STRINGS", -0.82), ("PAD", -0.65), ("SYNTH", -0.48)]

        for pname, px in patch_row1:
            is_active = (pname == self.current_patch)
            col = (0.10, 0.52, 0.88, 1) if is_active else (0.10, 0.12, 0.18, 1)
            btn = DirectButton(
                parent=self.rack_frame,
                text=pname,
                pos=(px, 0, 0.028),
                text_scale=0.026,
                text_fg=(1.0, 1.0, 1.0, 1),
                frameSize=(-0.080, 0.080, -0.025, 0.025),
                frameColor=col,
                relief=DGG.FLAT,
                command=self.set_synth_patch,
                extraArgs=[pname]
            )
            self.patch_buttons[pname] = btn
            self._register_widget_target("patch", pname, btn, 0.080, 0.025)

        for pname, px in patch_row2:
            is_active = (pname == self.current_patch)
            col = (0.10, 0.52, 0.88, 1) if is_active else (0.10, 0.12, 0.18, 1)
            btn = DirectButton(
                parent=self.rack_frame,
                text=pname,
                pos=(px, 0, -0.038),
                text_scale=0.026,
                text_fg=(1.0, 1.0, 1.0, 1),
                frameSize=(-0.080, 0.080, -0.025, 0.025),
                frameColor=col,
                relief=DGG.FLAT,
                command=self.set_synth_patch,
                extraArgs=[pname]
            )
            self.patch_buttons[pname] = btn
            self._register_widget_target("patch", pname, btn, 0.080, 0.025)

        # ── CLUSTER B: Blue LCD Spectrum Analyzer Screen (Center) ──
        self.lcd_screen = DirectFrame(
            parent=self.rack_frame,
            pos=(-0.05, 0, 0.00),
            frameSize=(-0.24, 0.24, -0.095, 0.095),
            frameColor=(0.01, 0.08, 0.16, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )

        DirectLabel(
            parent=self.lcd_screen,
            text="SYNTH SPECTRUM ANALYZER",
            pos=(0, 0, 0.065),
            scale=0.022,
            text_fg=(0.35, 0.75, 1.0, 0.8),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.spectrum_label = DirectLabel(
            parent=self.lcd_screen,
            text="| | || ||| |||| ||||| |||| ||| || | |",
            pos=(0, 0, -0.010),
            scale=0.030,
            text_fg=(0.25, 0.92, 1.0, 0.95),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.lcd_status_label = DirectLabel(
            parent=self.lcd_screen,
            text="PATCH: PIANO  |  OCT: 4",
            pos=(0, 0, -0.070),
            scale=0.022,
            text_fg=(0.35, 0.85, 0.60, 0.9),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── CLUSTER C: MAIN KEYBOARD SETTINGS (Right side, Volume, Speed, Visual FX) ──
        DirectLabel(
            parent=self.rack_frame,
            text="KEYBOARD SETTINGS",
            pos=(0.55, 0, 0.078),
            scale=0.028,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Row 1: Piano Volume [-]  90%  [+]  [FADE OUT]
        self.piano_vol_down = DirectButton(
            parent=self.rack_frame,
            text="-",
            pos=(0.30, 0, 0.028),
            text_scale=0.036,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.032, 0.032, -0.024, 0.024),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.adjust_piano_volume,
            extraArgs=[-0.10]
        )

        self.piano_vol_label = DirectLabel(
            parent=self.rack_frame,
            text="VOL: 90%",
            pos=(0.44, 0, 0.020),
            scale=0.026,
            text_fg=(0.25, 0.92, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.06, 0.08, 0.12, 1),
            frameSize=(-0.085, 0.085, -0.024, 0.024)
        )

        self.piano_vol_up = DirectButton(
            parent=self.rack_frame,
            text="+",
            pos=(0.58, 0, 0.028),
            text_scale=0.036,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.032, 0.032, -0.024, 0.024),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.adjust_piano_volume,
            extraArgs=[+0.10]
        )

        self.fade_btn = DirectButton(
            parent=self.rack_frame,
            text="FADE OUT",
            pos=(0.74, 0, 0.028),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.070, 0.070, -0.024, 0.024),
            frameColor=(0.65, 0.22, 0.22, 1),
            relief=DGG.FLAT,
            command=self.toggle_piano_fade
        )

        self._register_widget_target("action", "pvol_down", self.piano_vol_down, 0.032, 0.024)
        self._register_widget_target("action", "pvol_up", self.piano_vol_up, 0.032, 0.024)
        self._register_widget_target("action", "toggle_fade", self.fade_btn, 0.070, 0.024)

        # Row 2: Speed Toggle and Visual FX Toggle
        self.speed_btn = DirectButton(
            parent=self.rack_frame,
            text=f"SPEED: {self.speed_mode}",
            pos=(0.40, 0, -0.038),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.095, 0.095, -0.024, 0.024),
            frameColor=(0.70, 0.45, 0.08, 1),
            relief=DGG.FLAT,
            command=self.toggle_speed_mode
        )

        self.vfx_btn = DirectButton(
            parent=self.rack_frame,
            text="VISUAL FX",
            pos=(0.64, 0, -0.038),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.095, 0.095, -0.024, 0.024),
            frameColor=(0.10, 0.65, 0.40, 1),
            relief=DGG.FLAT,
            command=self.toggle_visual_fx
        )

        self._register_widget_target("action", "toggle_speed", self.speed_btn, 0.095, 0.024)
        self._register_widget_target("action", "toggle_vfx", self.vfx_btn, 0.095, 0.024)

    # ========================================================
    # MAIN REALISTIC PIANO KEYBOARD & BOTTOM DOCK
    # ========================================================

    def _build_keyboard(self):

        # Main keybed tray recessed into synthesizer chassis
        self.keybed_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, -0.28),
            frameSize=(-0.93, 0.93, -0.38, 0.38),
            frameColor=(0.025, 0.028, 0.038, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.006, 0.006)
        )
        self.keybed_frame.setBin("fixed", 5)
        self.keybed_frame.setDepthWrite(False)
        self.keybed_frame.setDepthTest(False)

        # Red felt damper strip at top of keybed
        DirectFrame(
            parent=self.keybed_frame,
            pos=(0, 0, 0.365),
            frameSize=(-0.91, 0.91, -0.012, 0.012),
            frameColor=(0.75, 0.08, 0.12, 1.0)
        )

        # Red felt damper strip & gold accent rim at bottom of keybed (mirroring top)
        DirectFrame(
            parent=self.keybed_frame,
            pos=(0, 0, -0.365),
            frameSize=(-0.91, 0.91, -0.010, 0.010),
            frameColor=(0.75, 0.08, 0.12, 1.0)
        )
        DirectFrame(
            parent=self.keybed_frame,
            pos=(0, 0, -0.375),
            frameSize=(-0.91, 0.91, -0.003, 0.003),
            frameColor=(0.85, 0.70, 0.25, 0.90)
        )

        start_x = -0.7875
        width = 0.225

        # ----------------------------------------------------
        # 1. WHITE KEYS (8 keys: C, D, E, F, G, A, B, C5)
        # ----------------------------------------------------
        for i, note in enumerate(self.WHITE):

            x = start_x + i * width
            z_pos = -0.02

            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.108, 0.108, -0.355, 0.355),
                frameColor=(0.97, 0.96, 0.93, 1.0),
                relief=DGG.RAISED,
                borderWidth=(0.004, 0.004)
            )
            frame.setBin("fixed", 20)
            frame.setDepthWrite(False)
            frame.setDepthTest(False)

            bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.342),
                frameSize=(-0.104, 0.104, -0.010, 0.010),
                frameColor=(0.82, 0.80, 0.76, 1.0)
            )
            bevel.setBin("fixed", 21)

            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.250),
                scale=0.048,
                text_fg=(0.10, 0.12, 0.16, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 22)

            self.white_frames[note] = frame
            self._register_widget_target("note", note, frame, 0.108, 0.355, is_black=False)

        # ----------------------------------------------------
        # 2. BLACK KEYS (5 keys: C#, D#, F#, G#, A#)
        # ----------------------------------------------------
        for note, after in self.BLACK:

            x = start_x + after * width + width / 2.0
            z_pos = 0.150

            shadow = DirectFrame(
                parent=self.keybed_frame,
                pos=(x + 0.008, 0, z_pos - 0.010),
                frameSize=(-0.068, 0.068, -0.195, 0.195),
                frameColor=(0.0, 0.0, 0.0, 0.6)
            )
            shadow.setBin("fixed", 32)
            shadow.setDepthWrite(False)
            shadow.setDepthTest(False)

            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.065, 0.065, -0.190, 0.190),
                frameColor=(0.12, 0.12, 0.14, 1.0),
                relief=DGG.RAISED,
                borderWidth=(0.004, 0.004)
            )
            frame.setBin("fixed", 35)
            frame.setDepthWrite(False)
            frame.setDepthTest(False)

            top_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, 0.175),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.32, 0.34, 0.38, 1.0)
            )
            top_bevel.setBin("fixed", 36)

            bot_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.178),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.20, 0.22, 0.26, 1.0)
            )
            bot_bevel.setBin("fixed", 36)

            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.115),
                scale=0.034,
                text_fg=(0.82, 0.85, 0.90, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 37)

            self.black_frames[note] = frame
            self._register_widget_target("note", note, frame, 0.065, 0.190, is_black=True)

        # ----------------------------------------------------
        # 3. BOTTOM NAVIGATION DOCK (PIANO, DRUMS, HOME) & LOWER CHASSIS DECORATION
        # ----------------------------------------------------
        self.bottom_dock = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, -0.74),
            frameSize=(-0.52, 0.52, -0.065, 0.065),
            frameColor=(0.03, 0.035, 0.05, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.bottom_dock.setBin("fixed", 5)

        self.dock_piano = DirectButton(
            parent=self.bottom_dock,
            text="PIANO",
            pos=(-0.34, 0, -0.012),
            text_scale=0.032,
            text_fg=(0.30, 0.95, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.40, 0.65, 1),
            relief=DGG.FLAT
        )

        self.dock_drums = DirectButton(
            parent=self.bottom_dock,
            text="DRUMS",
            pos=(0.0, 0, -0.012),
            text_scale=0.032,
            text_fg=(0.75, 0.80, 0.88, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=self._navigate_to,
            extraArgs=["DRUMS"]
        )

        self.dock_home = DirectButton(
            parent=self.bottom_dock,
            text="HOME",
            pos=(0.34, 0, -0.012),
            text_scale=0.032,
            text_fg=(0.75, 0.80, 0.88, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=self._navigate_to,
            extraArgs=["HOME"]
        )

        self._register_widget_target("action", "nav_drums", self.dock_drums, 0.14, 0.045)
        self._register_widget_target("action", "nav_home", self.dock_home, 0.14, 0.045)

        # ── Lower Acoustic Speaker Louvers (Mirroring the Top Header Louvers) ──
        # Left Bottom Speaker Panel
        self.bottom_louver_left = DirectFrame(
            parent=self.synth_body,
            pos=(-0.73, 0, -0.74),
            frameSize=(-0.19, 0.19, -0.065, 0.065),
            frameColor=(0.03, 0.035, 0.05, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.bottom_louver_left.setBin("fixed", 5)
        for s in range(5):
            DirectFrame(
                parent=self.bottom_louver_left,
                pos=(0, 0, 0.035 - s * 0.018),
                frameSize=(-0.16, 0.16, -0.003, 0.003),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )

        # Right Bottom Speaker Panel
        self.bottom_louver_right = DirectFrame(
            parent=self.synth_body,
            pos=(0.73, 0, -0.74),
            frameSize=(-0.19, 0.19, -0.065, 0.065),
            frameColor=(0.03, 0.035, 0.05, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.bottom_louver_right.setBin("fixed", 5)
        for s in range(5):
            DirectFrame(
                parent=self.bottom_louver_right,
                pos=(0, 0, 0.035 - s * 0.018),
                frameSize=(-0.16, 0.16, -0.003, 0.003),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )

        # Bottom Chassis Trim Runners (Lower Edge Accent)
        DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, -0.835),
            frameSize=(-0.94, 0.94, -0.005, 0.005),
            frameColor=(0.10, 0.45, 0.75, 0.90)
        )
        DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, -0.846),
            frameSize=(-0.94, 0.94, -0.003, 0.003),
            frameColor=(0.85, 0.70, 0.25, 0.90)
        )

    # ========================================================
    # LEFT PANEL — CHORD STUDIO (WITH HOME BUTTON & MAJOR/MINOR)
    # ========================================================

    def _build_chord_studio(self):

        self.chord_dock = DirectFrame(
            parent=self.frame,
            pos=(-1.35, 0, -0.02),
            frameSize=(-0.36, 0.36, -0.68, 0.68),
            frameColor=(0.07, 0.08, 0.11, 0.98),
            relief=DGG.RAISED,
            borderWidth=(0.006, 0.006)
        )
        self.chord_dock.setBin("fixed", 5)

        # Top HOME Button
        self.panel_home_btn = DirectButton(
            parent=self.chord_dock,
            text="HOME",
            pos=(-0.20, 0, 0.62),
            text_scale=0.028,
            text_fg=(0.85, 0.95, 1.0, 1),
            frameSize=(-0.11, 0.11, -0.032, 0.032),
            frameColor=(0.12, 0.16, 0.24, 1),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004),
            command=self._navigate_to,
            extraArgs=["HOME"]
        )
        self._register_widget_target("action", "nav_home", self.panel_home_btn, 0.11, 0.032)

        DirectLabel(
            parent=self.chord_dock,
            text="CHORD STUDIO",
            pos=(0.10, 0, 0.61),
            scale=0.038,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Tabs: [ MAJOR ] and [ MINOR ]
        self.tab_major = DirectButton(
            parent=self.chord_dock,
            text="MAJOR",
            pos=(-0.16, 0, 0.54),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT,
            command=self.switch_chord_tab,
            extraArgs=["MAJOR"]
        )

        self.tab_minor = DirectButton(
            parent=self.chord_dock,
            text="MINOR",
            pos=(0.16, 0, 0.54),
            text_scale=0.028,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT,
            command=self.switch_chord_tab,
            extraArgs=["MINOR"]
        )

        self._register_widget_target("action", "tab_major", self.tab_major, 0.14, 0.030)
        self._register_widget_target("action", "tab_minor", self.tab_minor, 0.14, 0.030)

        self.chord_buttons_container = DirectFrame(
            parent=self.chord_dock,
            pos=(0, 0, 0),
            frameColor=(0, 0, 0, 0)
        )

        self._render_chord_pads()

        # Progression Section with Interactive Family Switchers [<] [>]
        DirectLabel(
            parent=self.chord_dock,
            text="CHORD PROGRESSION",
            pos=(-0.30, 0, -0.37),
            scale=0.026,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.prog_prev_btn = DirectButton(
            parent=self.chord_dock,
            text="<",
            pos=(-0.29, 0, -0.44),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.035, 0.035, -0.035, 0.035),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.cycle_progression,
            extraArgs=[-1]
        )

        self.prog_display_label = DirectLabel(
            parent=self.chord_dock,
            text="C - G - Am - F",
            pos=(0.01, 0, -0.44),
            scale=0.025,
            text_fg=(0.85, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.08, 0.10, 0.14, 1),
            frameSize=(-0.24, 0.24, -0.035, 0.035)
        )

        self.prog_next_btn = DirectButton(
            parent=self.chord_dock,
            text=">",
            pos=(0.29, 0, -0.44),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.035, 0.035, -0.035, 0.035),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.003, 0.003),
            command=self.cycle_progression,
            extraArgs=[+1]
        )

        self._register_widget_target("action", "prog_prev", self.prog_prev_btn, 0.035, 0.035)
        self._register_widget_target("action", "prog_next", self.prog_next_btn, 0.035, 0.035)

        self.prog_btn = DirectButton(
            parent=self.chord_dock,
            text="> PLAY PROGRESSION",
            pos=(0, 0, -0.54),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.33, 0.33, -0.042, 0.042),
            frameColor=(0.10, 0.60, 0.30, 1),
            relief=DGG.FLAT,
            command=self.step_chord_progression
        )
        self._register_widget_target("progression", "step", self.prog_btn, 0.33, 0.042)

    def _render_chord_pads(self):

        for child in self.chord_buttons_container.getChildren():
            child.removeNode()

        self.interactive_regions = [r for r in self.interactive_regions if r["kind"] != "chord"]
        self.chord_buttons.clear()

        chord_dict = self.MAJOR_CHORDS if self.active_chord_tab == "MAJOR" else self.MINOR_CHORDS

        start_z = 0.44
        step_z = 0.108

        for i, (name, (notes, notes_str, col)) in enumerate(chord_dict.items()):
            z = start_z - i * step_z

            btn = DirectButton(
                parent=self.chord_buttons_container,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.046, 0.046),
                frameColor=col,
                relief=DGG.FLAT,
                command=self.play_chord,
                extraArgs=[name]
            )

            DirectLabel(
                parent=btn,
                text=name.title(),
                pos=(-0.30, 0, 0.010),
                scale=0.032,
                text_fg=(1.0, 1.0, 1.0, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=btn,
                text=notes_str,
                pos=(-0.30, 0, -0.025),
                scale=0.024,
                text_fg=(0.85, 0.92, 1.0, 0.90),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=btn,
                text=">",
                pos=(0.28, 0, -0.012),
                scale=0.032,
                text_fg=(1.0, 1.0, 1.0, 0.8),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.chord_buttons[name] = btn
            self._register_widget_target("chord", name, btn, 0.33, 0.046)

    def cycle_progression(self, delta):
        progs = self.MAJOR_PROGRESSIONS if self.active_chord_tab == "MAJOR" else self.MINOR_PROGRESSIONS
        self.progression_idx = (self.progression_idx + delta) % len(progs)
        self.progression_step = 0
        pname, chords = progs[self.progression_idx]
        self.CHORD_PROGRESSION = chords

        short_names = " - ".join([c.replace(" MAJOR", "").replace(" MINOR", "m").replace(" DIM", "°") for c in chords])
        if hasattr(self, "prog_display_label"):
            self.prog_display_label["text"] = short_names
        if hasattr(self, "prog_btn"):
            first_c = chords[0].replace(" MAJOR", "").replace(" MINOR", "m").replace(" DIM", "°")
            self.prog_btn["text"] = f"> PLAY: {first_c}"

    def switch_chord_tab(self, tab):

        self.active_chord_tab = tab
        self.progression_idx = 0
        self.progression_step = 0
        if tab == "MAJOR":
            self.tab_major["frameColor"] = (0.08, 0.52, 0.85, 1)
            self.tab_major["text_fg"] = (1.0, 1.0, 1.0, 1)
            self.tab_minor["frameColor"] = (0.12, 0.14, 0.18, 1)
            self.tab_minor["text_fg"] = (0.60, 0.65, 0.72, 1)
        else:
            self.tab_major["frameColor"] = (0.12, 0.14, 0.18, 1)
            self.tab_major["text_fg"] = (0.60, 0.65, 0.72, 1)
            self.tab_minor["frameColor"] = (0.75, 0.40, 0.10, 1)
            self.tab_minor["text_fg"] = (1.0, 1.0, 1.0, 1)

        progs = self.MAJOR_PROGRESSIONS if tab == "MAJOR" else self.MINOR_PROGRESSIONS
        pname, chords = progs[0]
        self.CHORD_PROGRESSION = chords
        short_names = " - ".join([c.replace(" MAJOR", "").replace(" MINOR", "m").replace(" DIM", "°") for c in chords])
        if hasattr(self, "prog_display_label"):
            self.prog_display_label["text"] = short_names
        if hasattr(self, "prog_btn"):
            first_c = chords[0].replace(" MAJOR", "").replace(" MINOR", "m").replace(" DIM", "°")
            self.prog_btn["text"] = f"> PLAY: {first_c}"

        self._render_chord_pads()

    # ========================================================
    # RIGHT PANEL — MUSIC STUDIO (8 FULL-VOLUME TRACKS)
    # ========================================================

    def _build_music_studio(self):

        self.music_dock = DirectFrame(
            parent=self.frame,
            pos=(1.35, 0, -0.02),
            frameSize=(-0.36, 0.36, -0.68, 0.68),
            frameColor=(0.07, 0.08, 0.11, 0.98),
            relief=DGG.RAISED,
            borderWidth=(0.006, 0.006)
        )
        self.music_dock.setBin("fixed", 5)

        # Top SETTINGS Button
        self.panel_settings_btn = DirectButton(
            parent=self.music_dock,
            text="SETTINGS",
            pos=(-0.16, 0, 0.62),
            text_scale=0.028,
            text_fg=(0.85, 0.95, 1.0, 1),
            frameSize=(-0.12, 0.12, -0.032, 0.032),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004),
            command=self.open_settings
        )
        self._register_widget_target("action", "open_settings", self.panel_settings_btn, 0.12, 0.032)

        DirectLabel(
            parent=self.music_dock,
            text="MUSIC STUDIO",
            pos=(0.14, 0, 0.61),
            scale=0.038,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Tabs: [ TRACKS ] and [ CUSTOM ]
        self.tab_tracks = DirectButton(
            parent=self.music_dock,
            text="TRACKS",
            pos=(-0.16, 0, 0.54),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT,
            command=self.switch_music_tab,
            extraArgs=["TRACKS"]
        )

        self.tab_custom = DirectButton(
            parent=self.music_dock,
            text="CUSTOM",
            pos=(0.16, 0, 0.54),
            text_scale=0.028,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT,
            command=self.switch_music_tab,
            extraArgs=["CUSTOM"]
        )

        self._register_widget_target("action", "tab_music_tracks", self.tab_tracks, 0.14, 0.030)
        self._register_widget_target("action", "tab_music_custom", self.tab_custom, 0.14, 0.030)

        # ── Tracks List Container ──
        self.tracks_list_frame = DirectFrame(
            parent=self.music_dock,
            pos=(0, 0, 0),
            frameColor=(0, 0, 0, 0)
        )

        # ── Custom Recordings List Container ──
        self.custom_list_frame = DirectFrame(
            parent=self.music_dock,
            pos=(0, 0, 0),
            frameColor=(0, 0, 0, 0)
        )
        self.custom_list_frame.hide()

        # ── 8 Authentic Backing Tracks List ──
        track_start_z = 0.46
        track_step_z = 0.048

        for i, (tname, fname, default_bpm) in enumerate(self.TRACK_FILES):
            z = track_start_z - i * track_step_z
            is_active = (i == self.active_track_idx)

            bg_col = (0.10, 0.24, 0.38, 1.0) if is_active else (0.08, 0.09, 0.12, 1.0)
            fg_col = (0.25, 0.92, 1.0, 1.0) if is_active else (0.82, 0.86, 0.92, 1.0)

            tbtn = DirectButton(
                parent=self.tracks_list_frame,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.022, 0.022),
                frameColor=bg_col,
                relief=DGG.FLAT,
                command=self.select_track,
                extraArgs=[i]
            )

            tlbl = DirectLabel(
                parent=tbtn,
                text=f"{tname}  [{self.track_bpms[i]} BPM]",
                pos=(-0.30, 0, -0.007),
                scale=0.024,
                text_fg=fg_col,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=tbtn,
                text=">",
                pos=(0.28, 0, -0.007),
                scale=0.026,
                text_fg=fg_col,
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.track_buttons.append((tbtn, tlbl))
            self._register_widget_target("track", i, tbtn, 0.33, 0.022)

        # ── TEMPO ADJUSTMENT BAR for All Beats: [-5] 120 BPM [+5] [RST] ──
        self.tempo_frame = DirectFrame(
            parent=self.music_dock,
            pos=(0, 0, 0.052),
            frameSize=(-0.33, 0.33, -0.024, 0.024),
            frameColor=(0.04, 0.06, 0.10, 1),
            relief=DGG.SUNKEN,
            borderWidth=(0.003, 0.003)
        )

        DirectLabel(
            parent=self.tempo_frame,
            text="BEAT TEMPO",
            pos=(-0.23, 0, -0.008),
            scale=0.022,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.tempo_down_btn = DirectButton(
            parent=self.tempo_frame,
            text="[-5]",
            pos=(-0.05, 0, 0.0),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.032, 0.032, -0.018, 0.018),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.002, 0.002),
            command=self.adjust_beat_tempo,
            extraArgs=[-5]
        )

        self.tempo_display = DirectLabel(
            parent=self.tempo_frame,
            text=f"{self.track_bpms[self.active_track_idx]} BPM",
            pos=(0.07, 0, -0.008),
            scale=0.024,
            text_fg=(0.25, 0.92, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.06, 0.08, 0.12, 1),
            frameSize=(-0.052, 0.052, -0.018, 0.018)
        )

        self.tempo_up_btn = DirectButton(
            parent=self.tempo_frame,
            text="[+5]",
            pos=(0.19, 0, 0.0),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.032, 0.032, -0.018, 0.018),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.002, 0.002),
            command=self.adjust_beat_tempo,
            extraArgs=[+5]
        )

        self.tempo_reset_btn = DirectButton(
            parent=self.tempo_frame,
            text="RST",
            pos=(0.27, 0, 0.0),
            text_scale=0.018,
            text_fg=(0.85, 0.90, 1.0, 1),
            frameSize=(-0.024, 0.024, -0.018, 0.018),
            frameColor=(0.24, 0.18, 0.12, 1),
            relief=DGG.FLAT,
            command=self.reset_beat_tempo
        )

        self._register_widget_target("action", "tempo_down", self.tempo_down_btn, 0.032, 0.018)
        self._register_widget_target("action", "tempo_up", self.tempo_up_btn, 0.032, 0.018)
        self._register_widget_target("action", "tempo_reset", self.tempo_reset_btn, 0.024, 0.018)

        # ── Transport Controls Row: PLAY, PAUSE, STOP, MUTE ──
        self.track_play_btn = DirectButton(
            parent=self.music_dock,
            text="> PLAY",
            pos=(-0.25, 0, -0.025),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.032, 0.032),
            frameColor=(0.10, 0.60, 0.30, 1),
            relief=DGG.FLAT,
            command=self.play_track
        )

        self.track_pause_btn = DirectButton(
            parent=self.music_dock,
            text="|| PAUSE",
            pos=(-0.08, 0, -0.025),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.032, 0.032),
            frameColor=(0.75, 0.52, 0.08, 1),
            relief=DGG.FLAT,
            command=self.pause_track
        )

        self.track_stop_btn = DirectButton(
            parent=self.music_dock,
            text="# STOP",
            pos=(0.09, 0, -0.025),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.032, 0.032),
            frameColor=(0.75, 0.15, 0.18, 1),
            relief=DGG.FLAT,
            command=self.stop_track
        )

        self.track_mute_btn = DirectButton(
            parent=self.music_dock,
            text="MUTE",
            pos=(0.26, 0, -0.025),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.032, 0.032),
            frameColor=(0.20, 0.22, 0.28, 1),
            relief=DGG.FLAT,
            command=self.toggle_mute
        )

        self._register_widget_target("action", "play_track", self.track_play_btn, 0.075, 0.032)
        self._register_widget_target("action", "pause_track", self.track_pause_btn, 0.075, 0.032)
        self._register_widget_target("action", "stop_track", self.track_stop_btn, 0.075, 0.032)
        self._register_widget_target("action", "toggle_mute", self.track_mute_btn, 0.075, 0.032)

        # ── TRACK VOLUME Slider & Progress Indicator ──
        DirectLabel(
            parent=self.music_dock,
            text="TRACK VOLUME",
            pos=(-0.30, 0, -0.095),
            scale=0.026,
            text_fg=(0.75, 0.85, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.track_progress_label = DirectLabel(
            parent=self.music_dock,
            text="00:00 / 08:00",
            pos=(0.30, 0, -0.095),
            scale=0.024,
            text_fg=(0.35, 0.85, 1.0, 1),
            text_align=TextNode.ARight,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_down_btn = DirectButton(
            parent=self.music_dock,
            text="-",
            pos=(-0.25, 0, -0.145),
            text_scale=0.036,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.026, 0.026),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=self.adjust_track_volume,
            extraArgs=[-0.10]
        )

        self.vol_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||||]  100%",
            pos=(0.02, 0, -0.150),
            scale=0.026,
            text_fg=(0.20, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_up_btn = DirectButton(
            parent=self.music_dock,
            text="+",
            pos=(0.28, 0, -0.145),
            text_scale=0.036,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.026, 0.026),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=self.adjust_track_volume,
            extraArgs=[+0.10]
        )

        self._register_widget_target("action", "vol_down", self.vol_down_btn, 0.05, 0.026)
        self._register_widget_target("action", "vol_up", self.vol_up_btn, 0.05, 0.026)

        # ── RECORDING Studio Controls ──
        DirectLabel(
            parent=self.music_dock,
            text="* RECORDING",
            pos=(-0.30, 0, -0.215),
            scale=0.026,
            text_fg=(0.95, 0.40, 0.45, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.record_btn = DirectButton(
            parent=self.music_dock,
            text="* RECORD",
            pos=(-0.16, 0, -0.275),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.035, 0.035),
            frameColor=(0.75, 0.12, 0.15, 1),
            relief=DGG.FLAT,
            command=self.toggle_recording
        )

        self.rec_stop_btn = DirectButton(
            parent=self.music_dock,
            text="# STOP",
            pos=(0.16, 0, -0.275),
            text_scale=0.030,
            text_fg=(0.80, 0.85, 0.90, 1),
            frameSize=(-0.14, 0.14, -0.035, 0.035),
            frameColor=(0.16, 0.18, 0.22, 1),
            relief=DGG.FLAT,
            command=self.stop_recording
        )

        self._register_widget_target("action", "toggle_record", self.record_btn, 0.14, 0.035)
        self._register_widget_target("action", "stop_record", self.rec_stop_btn, 0.14, 0.035)

        # Recording Status Timer & Dynamic VU Meter
        self.rec_status_label = DirectLabel(
            parent=self.music_dock,
            text="00:00",
            pos=(-0.24, 0, -0.355),
            scale=0.034,
            text_fg=(0.80, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.rec_vu_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||||]",
            pos=(0.10, 0, -0.355),
            scale=0.030,
            text_fg=(0.20, 0.90, 0.40, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # SAVE RECORDING Button
        self.save_rec_btn = DirectButton(
            parent=self.music_dock,
            text="SAVE RECORDING",
            pos=(0, 0, -0.465),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.33, 0.33, -0.040, 0.040),
            frameColor=(0.10, 0.42, 0.70, 1),
            relief=DGG.FLAT,
            command=self.save_and_export_recording
        )
        self._register_widget_target("action", "save_record", self.save_rec_btn, 0.33, 0.040)

    # ========================================================
    # SETTINGS MODAL DIALOG
    # ========================================================

    def _build_settings_modal(self):

        self.settings_frame = DirectFrame(
            parent=self.frame,
            pos=(0, 0, 0),
            frameSize=(-0.65, 0.65, -0.55, 0.55),
            frameColor=(0.06, 0.08, 0.12, 0.98),
            relief=DGG.RAISED,
            borderWidth=(0.008, 0.008)
        )
        self.settings_frame.setBin("fixed", 90)

        DirectLabel(
            parent=self.settings_frame,
            text="STUDIO SETTINGS & CALIBRATION",
            pos=(0, 0, 0.45),
            scale=0.038,
            text_fg=(0.30, 0.90, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.settings_frame,
            text="Gesture Tracking Sensitivity:",
            pos=(-0.55, 0, 0.32),
            scale=0.026,
            text_fg=(0.85, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.cfg_speed_btn = DirectButton(
            parent=self.settings_frame,
            text=f"SPEED: {self.speed_mode}",
            pos=(0.30, 0, 0.32),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.16, 0.16, -0.036, 0.036),
            frameColor=(0.12, 0.45, 0.75, 1),
            relief=DGG.FLAT,
            command=self.toggle_speed_mode
        )

        DirectLabel(
            parent=self.settings_frame,
            text="Master System Volume:",
            pos=(-0.55, 0, 0.18),
            scale=0.026,
            text_fg=(0.85, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.cfg_vol_btn = DirectButton(
            parent=self.settings_frame,
            text="100%",
            pos=(0.30, 0, 0.18),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.16, 0.16, -0.036, 0.036),
            frameColor=(0.10, 0.55, 0.30, 1),
            relief=DGG.FLAT,
            command=self._cycle_master_volume
        )

        DirectLabel(
            parent=self.settings_frame,
            text="Visual Performance Effects:",
            pos=(-0.55, 0, 0.04),
            scale=0.026,
            text_fg=(0.85, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.cfg_vfx_btn = DirectButton(
            parent=self.settings_frame,
            text="ENABLED" if self.visual_fx_enabled else "DISABLED",
            pos=(0.30, 0, 0.04),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.16, 0.16, -0.036, 0.036),
            frameColor=(0.10, 0.60, 0.40, 1) if self.visual_fx_enabled else (0.45, 0.20, 0.20, 1),
            relief=DGG.FLAT,
            command=self.toggle_visual_fx
        )

        DirectLabel(
            parent=self.settings_frame,
            text="Concert Hall Reverb Tail:",
            pos=(-0.55, 0, -0.10),
            scale=0.026,
            text_fg=(0.85, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.cfg_rev_btn = DirectButton(
            parent=self.settings_frame,
            text="ON" if self.reverb_on else "OFF",
            pos=(0.30, 0, -0.10),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.16, 0.16, -0.036, 0.036),
            frameColor=(0.55, 0.25, 0.75, 1) if self.reverb_on else (0.20, 0.22, 0.28, 1),
            relief=DGG.FLAT,
            command=self.toggle_reverb
        )

        self.close_settings_btn = DirectButton(
            parent=self.settings_frame,
            text="CLOSE SETTINGS",
            pos=(0, 0, -0.40),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.25, 0.25, -0.046, 0.046),
            frameColor=(0.10, 0.48, 0.78, 1),
            relief=DGG.FLAT,
            command=self.close_settings
        )

        self.settings_frame.hide()

    def open_settings(self):
        self.settings_open = True
        self.settings_frame.show()

    def close_settings(self):
        self.settings_open = False
        self.settings_frame.hide()

    def _cycle_master_volume(self):
        vols = [1.0, 0.75, 0.50, 0.25]
        cur = self.sound_manager.master_volume
        nxt = 1.0
        for v in vols:
            if v < cur - 0.05:
                nxt = v
                break
        self.sound_manager.set_master_volume(nxt)
        pct = int(nxt * 100)
        self.cfg_vol_btn["text"] = f"{pct}%"

    # ========================================================
    # INTERACTIVE TARGET SYSTEM (EXACT ABSOLUTE COORDINATES)
    # ========================================================

    def _register_widget_target(self, kind, ident, widget, w, h, is_black=False):
        """
        Uses widget.getPos(base.aspect2d) to ensure 100% collision precision.
        """
        self.interactive_regions.append({
            "kind": kind,
            "ident": ident,
            "widget": widget,
            "w": w,
            "h": h,
            "black": is_black
        })

    def find_target(self, x, z):
        """
        Finds interactive target matching cursor (x, z).
        """
        if self.settings_open:
            if abs(x) <= 0.25 and abs(z - (-0.40)) <= 0.046:
                return ("action", "close_settings")
            return None

        # 1. Black keys priority
        for reg in self.interactive_regions:
            if reg["kind"] == "note" and reg["black"]:
                wpos = reg["widget"].getPos(self.base.aspect2d)
                if abs(x - wpos.getX()) <= reg["w"] and abs(z - wpos.getZ()) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        # 2. Controls, Buttons, Chords & Patches
        for reg in self.interactive_regions:
            if reg["kind"] != "note":
                wpos = reg["widget"].getPos(self.base.aspect2d)
                if abs(x - wpos.getX()) <= reg["w"] and abs(z - wpos.getZ()) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        # 3. White keys
        for reg in self.interactive_regions:
            if reg["kind"] == "note" and not reg["black"]:
                wpos = reg["widget"].getPos(self.base.aspect2d)
                if abs(x - wpos.getX()) <= reg["w"] and abs(z - wpos.getZ()) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        return None

    def execute_target_action(self, kind, ident, hand_idx=0):

        cx, cz = self.cursors[hand_idx] if self.cursors[hand_idx] else (0, 0)
        col = (0.0, 0.85, 1.0, 1.0) if hand_idx == 0 else (1.0, 0.35, 0.85, 1.0)
        self._spawn_selection_ripple(cx, cz, col)

        if kind == "note":
            self.key_press_colors[ident] = col
            self.play_note(ident)
        elif kind == "chord":
            self.play_chord(ident)
        elif kind == "progression":
            self.step_chord_progression()
        elif kind == "track":
            self.select_track(ident)
            self.play_track()
        elif kind == "custom_track":
            self.select_custom_recording(ident)
        elif kind == "patch":
            self.set_synth_patch(ident)
        elif kind == "action":
            if ident == "mode_air":
                self.set_play_mode("AIR_KEYBOARD")
            elif ident == "mode_pinch":
                self.set_play_mode("PINCH")
            elif ident == "octave_down":
                self.adjust_octave(-1)
            elif ident == "octave_up":
                self.adjust_octave(+1)
            elif ident == "toggle_sustain":
                self.toggle_sustain()
            elif ident == "toggle_reverb":
                self.toggle_reverb()
            elif ident == "toggle_vfx":
                self.toggle_visual_fx()
            elif ident == "toggle_speed":
                self.toggle_speed_mode()
            elif ident == "pvol_down":
                self.adjust_piano_volume(-0.10)
            elif ident == "pvol_up":
                self.adjust_piano_volume(+0.10)
            elif ident == "toggle_fade":
                self.toggle_piano_fade()
            elif ident == "play_track":
                self.play_track()
            elif ident == "pause_track":
                self.pause_track()
            elif ident == "stop_track":
                self.stop_track()
            elif ident == "toggle_mute":
                self.toggle_mute()
            elif ident == "vol_down":
                self.adjust_track_volume(-0.10)
            elif ident == "vol_up":
                self.adjust_track_volume(+0.10)
            elif ident == "toggle_record":
                self.toggle_recording()
            elif ident == "stop_record":
                self.stop_recording()
            elif ident == "save_record":
                self.save_and_export_recording()
            elif ident == "tab_major":
                self.switch_chord_tab("MAJOR")
            elif ident == "tab_minor":
                self.switch_chord_tab("MINOR")
            elif ident == "prog_prev":
                self.cycle_progression(-1)
            elif ident == "prog_next":
                self.cycle_progression(+1)
            elif ident == "tab_music_tracks":
                self.switch_music_tab("TRACKS")
            elif ident == "tab_music_custom":
                self.switch_music_tab("CUSTOM")
            elif ident == "tempo_down":
                self.adjust_beat_tempo(-5)
            elif ident == "tempo_up":
                self.adjust_beat_tempo(+5)
            elif ident == "tempo_reset":
                self.reset_beat_tempo()
            elif ident == "open_settings":
                self.open_settings()
            elif ident == "close_settings":
                self.close_settings()
            elif ident == "nav_drums":
                self._navigate_to("DRUMS")
            elif ident == "nav_home":
                self._navigate_to("HOME")

    # ========================================================
    # SOUND, PATCH, OCTAVE, CHORD & SUSTAIN PLAYBACK
    # ========================================================

    def play_note(self, note):

        note_id = note.replace("#", "s")

        try:
            channel = None
            if not self.is_muted and self.piano_volume > 0.001:
                channel = self.sound_manager.play_piano(
                    note_id,
                    octave=self.current_octave,
                    patch=self.current_patch,
                    reverb=self.reverb_on
                )

                if not self.sustain_on and channel is not None:
                    channel.fadeout(260)

            now = time.monotonic()
            self.key_press_timers[note] = now
            self.vu_level = min(1.0, self.vu_level + 0.65)
            self._trigger_spectrum_peak()

            note_display = f"{note}{self.current_octave}"
            self.current_display_note = note_display
            self.current_note_label["text"] = note_display

            if self.visual_fx_enabled:
                self._spawn_visual_beam(note)

            self.record_event("note", note)

        except Exception as error:
            print("Piano sound error:", error)

    def play_chord(self, name):

        chord_dict = self.MAJOR_CHORDS if self.active_chord_tab == "MAJOR" else self.MINOR_CHORDS
        if name in chord_dict:
            notes, _, _ = chord_dict[name]
        else:
            notes = ["C", "E", "G"]

        for note in notes:
            self.play_note(note)

        self.record_event("chord", name)
        self.vu_level = 1.0
        self._trigger_spectrum_peak()
        self.current_note_label["text"] = name[:5]

    def step_chord_progression(self):

        name = self.CHORD_PROGRESSION[self.progression_step]
        self.play_chord(name)

        self.progression_step = (self.progression_step + 1) % len(self.CHORD_PROGRESSION)
        next_name = self.CHORD_PROGRESSION[self.progression_step]
        self.prog_btn["text"] = f"> NEXT: {next_name[:5]}"

    def adjust_octave(self, delta):

        self.current_octave = max(2, min(6, self.current_octave + delta))
        self.octave_display["text"] = str(self.current_octave)
        self.lcd_status_label["text"] = f"PATCH: {self.current_patch}  |  OCT: {self.current_octave}"

    def set_synth_patch(self, patch):

        self.current_patch = patch
        for pname, btn in self.patch_buttons.items():
            if pname == patch:
                btn["frameColor"] = (0.10, 0.52, 0.88, 1)
                btn["text_fg"] = (1.0, 1.0, 1.0, 1)
            else:
                btn["frameColor"] = (0.10, 0.12, 0.18, 1)
                btn["text_fg"] = (0.65, 0.70, 0.78, 1)

        self.lcd_status_label["text"] = f"PATCH: {self.current_patch}  |  OCT: {self.current_octave}"

    def adjust_piano_volume(self, delta):

        self.piano_volume = max(0.0, min(1.0, self.piano_volume + delta))
        self.sound_manager.set_piano_volume(self.piano_volume)
        pct = int(self.piano_volume * 100)
        self.piano_vol_label["text"] = f"VOL: {pct}%"
        self.fade_state = "IDLE"
        if hasattr(self, "fade_btn"):
            self.fade_btn["text"] = "FADE OUT"
            self.fade_btn["frameColor"] = (0.20, 0.22, 0.28, 1)

    def toggle_piano_fade(self):
        """Smoothly ramps piano sound down to 0% (FADE OUT) or back to target (FADE IN)."""
        if self.fade_state in ("IDLE", "FADING_IN"):
            if self.piano_volume > 0.05:
                self.target_fade_volume = self.piano_volume
            self.fade_state = "FADING_OUT"
            if hasattr(self, "fade_btn"):
                self.fade_btn["text"] = "FADING..."
                self.fade_btn["frameColor"] = (0.85, 0.45, 0.15, 1)
        else: # "MUTED" or "FADING_OUT"
            self.fade_state = "FADING_IN"
            if hasattr(self, "fade_btn"):
                self.fade_btn["text"] = "FADING..."
                self.fade_btn["frameColor"] = (0.15, 0.65, 0.35, 1)

    def toggle_sustain(self):

        self.sustain_on = not self.sustain_on
        if self.sustain_on:
            self.sustain_btn["text"] = "ON"
            self.sustain_btn["frameColor"] = (0.12, 0.72, 0.32, 1)
        else:
            self.sustain_btn["text"] = "OFF"
            self.sustain_btn["frameColor"] = (0.35, 0.38, 0.42, 1)

    def toggle_reverb(self):

        self.reverb_on = not self.reverb_on
        if self.reverb_on:
            self.reverb_btn["text"] = "ON"
            self.reverb_btn["frameColor"] = (0.60, 0.25, 0.85, 1)
            self.reverb_btn["text_fg"] = (1.0, 1.0, 1.0, 1)
        else:
            self.reverb_btn["text"] = "OFF"
            self.reverb_btn["frameColor"] = (0.12, 0.14, 0.20, 1)
            self.reverb_btn["text_fg"] = (0.70, 0.75, 0.85, 1)
        if hasattr(self, "cfg_rev_btn"):
            self.cfg_rev_btn["text"] = "ON" if self.reverb_on else "OFF"
            self.cfg_rev_btn["frameColor"] = (0.55, 0.25, 0.75, 1) if self.reverb_on else (0.20, 0.22, 0.28, 1)

    def toggle_visual_fx(self):

        self.visual_fx_enabled = not self.visual_fx_enabled
        if self.visual_fx_enabled:
            self.vfx_btn["frameColor"] = (0.10, 0.65, 0.40, 1)
        else:
            self.vfx_btn["frameColor"] = (0.45, 0.20, 0.20, 1)
        if hasattr(self, "cfg_vfx_btn"):
            self.cfg_vfx_btn["text"] = "ENABLED" if self.visual_fx_enabled else "DISABLED"
            self.cfg_vfx_btn["frameColor"] = (0.10, 0.60, 0.40, 1) if self.visual_fx_enabled else (0.45, 0.20, 0.20, 1)

    # ========================================================
    # BACKING TRACK ENGINE (FULL-VOLUME AUTHENTIC BEATS & CUSTOM RECORDINGS)
    # ========================================================

    def _load_active_track(self):

        tname, fname, default_bpm = self.TRACK_FILES[self.active_track_idx]
        self.track_name = tname

        project_root = Path(__file__).resolve().parents[3]
        track_path = project_root / "assets" / fname

        if not track_path.exists():
            print("Track path not found:", track_path)
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            cur_bpm = self.track_bpms[self.active_track_idx]

            # Cache raw array for fast dynamic tempo shifts
            if fname not in self.raw_sound_data:
                orig_snd = pygame.mixer.Sound(str(track_path))
                raw_arr = pygame.sndarray.array(orig_snd)
                self.raw_sound_data[fname] = raw_arr

            raw_arr = self.raw_sound_data[fname]

            if cur_bpm == default_bpm:
                self.track_sound = pygame.mixer.Sound(str(track_path))
            else:
                # Dynamic resampling: scale playback length by ratio of bpms
                speed_factor = float(cur_bpm) / float(default_bpm)
                orig_len = len(raw_arr)
                new_len = max(100, int(orig_len / speed_factor))
                orig_x = np.linspace(0, 1, orig_len)
                new_x = np.linspace(0, 1, new_len)
                resampled = np.zeros((new_len, raw_arr.shape[1]), dtype=raw_arr.dtype)
                for ch in range(raw_arr.shape[1]):
                    resampled[:, ch] = np.interp(new_x, orig_x, raw_arr[:, ch]).astype(raw_arr.dtype)
                self.track_sound = pygame.sndarray.make_sound(resampled)

            self.track_total_duration = self.track_sound.get_length()
        except Exception as error:
            print("Backing track load error:", error)

    def select_track(self, idx):

        if idx < 0 or idx >= len(self.TRACK_FILES):
            return

        was_playing = (self.track_channel is not None and not self.track_paused)
        self.stop_track()

        self.active_track_idx = idx
        self._load_active_track()

        if hasattr(self, "tempo_display"):
            self.tempo_display["text"] = f"{self.track_bpms[idx]} BPM"

        for i, (tbtn, tlbl) in enumerate(self.track_buttons):
            if i == idx:
                tbtn["frameColor"] = (0.10, 0.24, 0.38, 1.0)
                tlbl["text_fg"] = (0.25, 0.92, 1.0, 1.0)
            else:
                tbtn["frameColor"] = (0.08, 0.09, 0.12, 1.0)
                tlbl["text_fg"] = (0.82, 0.86, 0.92, 1.0)

        if was_playing:
            self.play_track()

    def adjust_beat_tempo(self, delta):
        idx = self.active_track_idx
        cur_bpm = self.track_bpms[idx]
        new_bpm = max(50, min(220, cur_bpm + delta))
        if new_bpm == cur_bpm:
            return

        self.track_bpms[idx] = new_bpm
        if hasattr(self, "tempo_display"):
            self.tempo_display["text"] = f"{new_bpm} BPM"

        tname, _, _ = self.TRACK_FILES[idx]
        if idx < len(self.track_buttons):
            _, tlbl = self.track_buttons[idx]
            tlbl["text"] = f"{tname}  [{new_bpm} BPM]"

        was_playing = (self.track_channel is not None and not self.track_paused)
        if was_playing:
            self.stop_track()
            self._load_active_track()
            self.play_track()
        else:
            self._load_active_track()

    def reset_beat_tempo(self):
        idx = self.active_track_idx
        default_bpm = self.default_track_bpms[idx]
        delta = default_bpm - self.track_bpms[idx]
        if delta != 0:
            self.adjust_beat_tempo(delta)

    def switch_music_tab(self, tab):
        if tab in ("TRACKS", "BEATS"):
            self.active_music_tab = "TRACKS"
            self.tab_tracks["frameColor"] = (0.08, 0.52, 0.85, 1)
            self.tab_tracks["text_fg"] = (1.0, 1.0, 1.0, 1)
            self.tab_custom["frameColor"] = (0.12, 0.14, 0.18, 1)
            self.tab_custom["text_fg"] = (0.60, 0.65, 0.72, 1)
            self.tracks_list_frame.show()
            self.tempo_frame.show()
            self.custom_list_frame.hide()
        else: # "CUSTOM"
            self.active_music_tab = "CUSTOM"
            self.tab_tracks["frameColor"] = (0.12, 0.14, 0.18, 1)
            self.tab_tracks["text_fg"] = (0.60, 0.65, 0.72, 1)
            self.tab_custom["frameColor"] = (0.75, 0.40, 0.10, 1)
            self.tab_custom["text_fg"] = (1.0, 1.0, 1.0, 1)
            self.tracks_list_frame.hide()
            self.tempo_frame.hide()
            self.custom_list_frame.show()
            self._render_custom_recordings()

    def _render_custom_recordings(self):
        self.interactive_regions = [r for r in self.interactive_regions if r["kind"] != "custom_track"]
        for child in list(self.custom_list_frame.getChildren()):
            child.removeNode()

        self.custom_track_buttons = []
        self.custom_recordings_list = []

        project_root = Path(__file__).resolve().parents[3]
        rec_dir = project_root / "recordings"

        rec_files = []
        if rec_dir.exists():
            rec_files = sorted(list(rec_dir.glob("*.wav")), key=lambda p: p.stat().st_mtime, reverse=True)

        if not rec_files:
            DirectLabel(
                parent=self.custom_list_frame,
                text="NO RECORDINGS YET\n\nHit * RECORD below to capture\nyour live piano performances!",
                pos=(0, 0, 0.35),
                scale=0.024,
                text_fg=(0.70, 0.75, 0.85, 1),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            return

        rec_start_z = 0.46
        rec_step_z = 0.054
        max_show = min(7, len(rec_files))

        for i in range(max_show):
            rf = rec_files[i]
            self.custom_recordings_list.append(rf)
            z = rec_start_z - i * rec_step_z
            is_active = (str(rf) == self.active_custom_path)

            bg_col = (0.12, 0.35, 0.22, 1.0) if is_active else (0.08, 0.09, 0.12, 1.0)
            fg_col = (0.35, 0.95, 0.65, 1.0) if is_active else (0.82, 0.86, 0.92, 1.0)

            # File info
            mtime = time.strftime("%m/%d %H:%M", time.localtime(rf.stat().st_mtime))
            approx_dur = max(1, int(rf.stat().st_size / 176400))
            dur_str = f"{approx_dur//60:02d}:{approx_dur%60:02d}"
            display_title = f"{rf.stem[:17]} [{dur_str}]"

            cbtn = DirectButton(
                parent=self.custom_list_frame,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.022, 0.022),
                frameColor=bg_col,
                relief=DGG.FLAT,
                command=self.select_custom_recording,
                extraArgs=[i]
            )

            clbl = DirectLabel(
                parent=cbtn,
                text=display_title,
                pos=(-0.31, 0, -0.007),
                scale=0.022,
                text_fg=fg_col,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=cbtn,
                text=">",
                pos=(0.29, 0, -0.007),
                scale=0.026,
                text_fg=fg_col,
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.custom_track_buttons.append((cbtn, clbl, rf))
            self._register_widget_target("custom_track", i, cbtn, 0.33, 0.022)

    def select_custom_recording(self, idx):
        if not hasattr(self, "custom_recordings_list") or idx < 0 or idx >= len(self.custom_recordings_list):
            return

        rf = self.custom_recordings_list[idx]
        self.active_custom_path = str(rf)
        self.track_name = rf.stem[:17]

        self.stop_track()

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.track_sound = pygame.mixer.Sound(str(rf))
            self.track_total_duration = self.track_sound.get_length()
        except Exception as error:
            print("Custom recording load error:", error)
            return

        for i, (cbtn, clbl, _) in enumerate(self.custom_track_buttons):
            if i == idx:
                cbtn["frameColor"] = (0.12, 0.35, 0.22, 1.0)
                clbl["text_fg"] = (0.35, 0.95, 0.65, 1.0)
            else:
                cbtn["frameColor"] = (0.08, 0.09, 0.12, 1.0)
                clbl["text_fg"] = (0.82, 0.86, 0.92, 1.0)

        self.play_track()

    def play_track(self):

        if self.track_sound is None:
            self._load_active_track()

        if self.track_sound is None:
            return

        try:
            if self.track_channel is not None and self.track_paused:
                self.track_channel.unpause()
                self.track_paused = False
                self.track_play_btn["frameColor"] = (0.12, 0.72, 0.35, 1)
                return

            self.stop_track()
            loops = 0 if self.active_music_tab == "CUSTOM" else -1
            self.track_channel = self.track_sound.play(loops=loops)
            if self.track_channel:
                vol = 0.0 if self.is_muted else (self.track_volume * self.sound_manager.master_volume)
                self.track_channel.set_volume(vol)
            self.track_paused = False
            self.track_start_time = time.monotonic()
            self.track_play_btn["frameColor"] = (0.12, 0.72, 0.35, 1)

            if self.is_recording:
                self.recorded_events.append((time.monotonic() - self.record_start_time, "backing", self.track_volume))

        except Exception as error:
            print("Track play error:", error)

    def pause_track(self):

        if self.track_channel is not None:
            if not self.track_paused:
                self.track_channel.pause()
                self.track_paused = True
                self.track_play_btn["frameColor"] = (0.10, 0.60, 0.30, 1)
            else:
                self.track_channel.unpause()
                self.track_paused = False
                self.track_play_btn["frameColor"] = (0.12, 0.72, 0.35, 1)

    def stop_track(self):

        if self.track_channel is not None:
            self.track_channel.stop()
            self.track_channel = None
        self.track_paused = False
        self.track_play_btn["frameColor"] = (0.10, 0.60, 0.30, 1)
        self.track_progress_label["text"] = "00:00 / 08:00"

    def toggle_mute(self):

        self.is_muted = not self.is_muted
        if self.is_muted:
            self.track_mute_btn["text"] = "MUTED"
            self.track_mute_btn["frameColor"] = (0.75, 0.15, 0.18, 1)
            if self.track_channel is not None:
                self.track_channel.set_volume(0.0)
            self.sound_manager.set_piano_volume(0.0)
        else:
            self.track_mute_btn["text"] = "MUTE"
            self.track_mute_btn["frameColor"] = (0.20, 0.22, 0.28, 1)
            if self.track_channel is not None:
                self.track_channel.set_volume(self.track_volume * self.sound_manager.master_volume)
            self.sound_manager.set_piano_volume(self.piano_volume)

    def adjust_track_volume(self, delta):

        self.track_volume = max(0.0, min(1.0, self.track_volume + delta))
        if self.track_channel is not None and not self.is_muted:
            self.track_channel.set_volume(self.track_volume * self.sound_manager.master_volume)
        pct = int(self.track_volume * 100)
        bars_count = int(self.track_volume * 14)
        bars_str = "|" * bars_count + " " * (14 - bars_count)
        self.vol_label["text"] = f"[{bars_str}]  {pct}%"

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

        self.record_btn["text"] = "# STOP"
        self.record_btn["frameColor"] = (0.85, 0.10, 0.10, 1)
        self.rec_status_label["text"] = "00:00"
        self.rec_status_label["text_fg"] = (1.0, 0.35, 0.35, 1)
        self.save_rec_btn["text"] = "SAVE RECORDING"

    def stop_recording(self):

        if not self.is_recording:
            return

        self.is_recording = False
        self.record_btn["text"] = "* RECORD"
        self.record_btn["frameColor"] = (0.75, 0.12, 0.15, 1)
        self.rec_status_label["text_fg"] = (0.35, 0.95, 0.65, 1)

    def save_and_export_recording(self):

        if not self.recorded_events:
            self.save_rec_btn["text"] = "NO AUDIO RECORDED"
            return

        duration = max(1.0, time.monotonic() - self.record_start_time if self.is_recording else 5.0)
        if self.is_recording:
            self.stop_recording()

        out_path = self.export_recording(duration)
        if out_path:
            self.save_rec_btn["text"] = "SAVED TO recordings/"
            if self.active_music_tab == "CUSTOM":
                self._render_custom_recordings()

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
        src_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        for offset, ev_type, name in self.recorded_events:
            start_idx = int(offset * sample_rate)
            if start_idx >= total_samples:
                continue

            if ev_type == "note":
                safe = name.replace("#", "s")
                freq = self.sound_manager.NOTE_BASE_FREQS.get(safe, 440.0)
                samples = self.sound_manager._synthesize_instrument_sample(
                    freq, patch=self.current_patch, reverb=self.reverb_on, duration=1.6
                )
                end_idx = min(total_samples, start_idx + len(samples))
                count = end_idx - start_idx
                master[start_idx:end_idx] += samples[:count]

            elif ev_type == "chord":
                chord_dict = self.MAJOR_CHORDS if self.active_chord_tab == "MAJOR" else self.MINOR_CHORDS
                notes, _, _ = chord_dict.get(name, (["C", "E", "G"], "", None))
                for n in notes:
                    safe = n.replace("#", "s")
                    freq = self.sound_manager.NOTE_BASE_FREQS.get(safe, 440.0)
                    samples = self.sound_manager._synthesize_instrument_sample(
                        freq, patch=self.current_patch, reverb=self.reverb_on, duration=1.6
                    )
                    end_idx = min(total_samples, start_idx + len(samples))
                    count = end_idx - start_idx
                    master[start_idx:end_idx] += samples[:count]

            elif ev_type == "backing":
                vol = name
                _, backing_file, _ = self.TRACK_FILES[self.active_track_idx]
                track_path = os.path.join(src_folder, "..", "assets", backing_file)
                if os.path.isfile(track_path):
                    with wave.open(track_path, "rb") as wf:
                        n_frames = wf.getnframes()
                        raw = wf.readframes(n_frames)
                        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, 2)
                        cur_idx = start_idx
                        while cur_idx < total_samples:
                            rem = total_samples - cur_idx
                            take = min(rem, len(arr))
                            master[cur_idx:cur_idx+take] += arr[:take] * vol
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
        filename = f"holohand_studio_{timestamp_str}.wav"
        out_path = os.path.join(rec_dir, filename)

        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(master_int16.tobytes())

        print(f"Recorded performance exported to: {out_path}")
        return out_path

    # ========================================================
    # PLAY MODE & SENSITIVITY CONTROLS
    # ========================================================

    def set_play_mode(self, mode):

        self.play_mode = mode
        if mode == "AIR_KEYBOARD":
            self.mode_air_btn["frameColor"] = (0.08, 0.48, 0.78, 1)
            self.mode_air_btn["text_fg"] = (0.95, 1.0, 1.0, 1)
            self.mode_pinch_btn["frameColor"] = (0.08, 0.10, 0.15, 1)
            self.mode_pinch_btn["text_fg"] = (0.60, 0.70, 0.80, 1)
        else:
            self.mode_air_btn["frameColor"] = (0.08, 0.10, 0.15, 1)
            self.mode_air_btn["text_fg"] = (0.60, 0.70, 0.80, 1)
            self.mode_pinch_btn["frameColor"] = (0.50, 0.15, 0.65, 1)
            self.mode_pinch_btn["text_fg"] = (1.0, 0.85, 1.0, 1)

        self.current_targets = [None, None]
        self.candidate_targets = [None, None]

    def toggle_play_mode(self):

        if self.play_mode == "AIR_KEYBOARD":
            self.set_play_mode("PINCH")
        else:
            self.set_play_mode("AIR_KEYBOARD")

    def toggle_speed_mode(self):

        if self.speed_mode == "NORMAL":
            self.speed_mode = "RELAXED"
            self.key_dwell_time = 0.130
            self.base_smoothing = 0.30
        elif self.speed_mode == "RELAXED":
            self.speed_mode = "FAST"
            self.key_dwell_time = 0.045
            self.base_smoothing = 0.60
        else:
            self.speed_mode = "NORMAL"
            self.key_dwell_time = 0.085
            self.base_smoothing = 0.42

        self.speed_btn["text"] = f"SPEED: {self.speed_mode}"
        if hasattr(self, "cfg_speed_btn"):
            self.cfg_speed_btn["text"] = f"SPEED: {self.speed_mode}"

        self.current_targets = [None, None]
        self.candidate_targets = [None, None]

    # ========================================================
    # NATURAL HAND TRACKING & POINTER OVERLAYS
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

    def draw_pointer(self, x, z, color, radius=0.038):

        lines = LineSegs()
        lines.setThickness(3)
        lines.setColor(*color)

        for r_factor in (1.0, 0.45):
            r = radius * r_factor
            for i in range(25):
                angle = i * 2.0 * math.pi / 24.0
                px = x + r * math.cos(angle)
                pz = z + r * math.sin(angle)
                if i == 0:
                    lines.moveTo(px, 0, pz)
                else:
                    lines.drawTo(px, 0, pz)

        lines.moveTo(x - 0.012, 0, z)
        lines.drawTo(x + 0.012, 0, z)
        lines.moveTo(x, 0, z - 0.012)
        lines.drawTo(x, 0, z + 0.012)

        node = self.pointer_root.attachNewNode(lines.create())
        self.pointer_nodes.append(node)

    def _spawn_selection_ripple(self, x, z, color):

        self.button_ripples.append({
            "x": x,
            "z": z,
            "color": color,
            "radius": 0.02,
            "max_radius": 0.08,
            "alpha": 1.0
        })

    def _spawn_visual_beam(self, note):

        reg = next((r for r in self.interactive_regions if r["kind"] == "note" and r["ident"] == note), None)
        if reg:
            wpos = reg["widget"].getPos(self.base.aspect2d)
            self.active_beams.append({
                "x": wpos.getX(),
                "z": wpos.getZ() + reg["h"],
                "height": 0.02,
                "max_height": 0.35,
                "color": self.key_press_colors.get(note, (0.2, 0.85, 1.0, 1.0)),
                "alpha": 1.0
            })

    def clear_pointers(self):

        for node in self.pointer_nodes:
            node.removeNode()
        self.pointer_nodes.clear()

        for child in self.fx_root.getChildren():
            child.removeNode()

        alive_ripples = []
        for rip in self.button_ripples:
            rip["radius"] += 0.012
            rip["alpha"] -= 0.15
            if rip["alpha"] > 0:
                lines = LineSegs()
                lines.setThickness(2)
                r, g, b, _ = rip["color"]
                lines.setColor(r, g, b, rip["alpha"])
                for i in range(17):
                    a = i * 2.0 * math.pi / 16.0
                    px = rip["x"] + rip["radius"] * math.cos(a)
                    pz = rip["z"] + rip["radius"] * math.sin(a)
                    if i == 0: lines.moveTo(px, 0, pz)
                    else: lines.drawTo(px, 0, pz)
                self.fx_root.attachNewNode(lines.create())
                alive_ripples.append(rip)
        self.button_ripples = alive_ripples

        alive_beams = []
        for beam in self.active_beams:
            beam["height"] += 0.035
            beam["alpha"] -= 0.08
            if beam["alpha"] > 0 and beam["height"] < beam["max_height"]:
                lines = LineSegs()
                lines.setThickness(4)
                r, g, b, _ = beam["color"]
                lines.setColor(r, g, b, beam["alpha"])
                lines.moveTo(beam["x"], 0, beam["z"])
                lines.drawTo(beam["x"], 0, beam["z"] + beam["height"])
                self.fx_root.attachNewNode(lines.create())
                alive_beams.append(beam)
        self.active_beams = alive_beams

    # ========================================================
    # VISUAL KEY ILLUMINATION & TARGET HIGHLIGHTS
    # ========================================================

    def reset_keys(self):

        now = time.monotonic()

        for note, frame in self.white_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = self.key_press_colors.get(note, (0.35, 0.88, 1.0, 1.0))
            else:
                frame["frameColor"] = (0.97, 0.96, 0.93, 1.0)

        for note, frame in self.black_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = self.key_press_colors.get(note, (1.0, 0.35, 0.85, 1.0))
            else:
                frame["frameColor"] = (0.12, 0.12, 0.14, 1.0)

        chord_dict = self.MAJOR_CHORDS if self.active_chord_tab == "MAJOR" else self.MINOR_CHORDS
        for name, btn in self.chord_buttons.items():
            if name in chord_dict:
                _, _, col = chord_dict[name]
                btn["frameColor"] = col

    def highlight_target(self, target, hand_idx=0):

        if target is None:
            return

        kind, ident = target
        col = (0.30, 0.90, 1.0, 1.0) if hand_idx == 0 else (1.0, 0.35, 0.85, 1.0)

        if kind == "chord":
            if ident in self.chord_buttons:
                self.chord_buttons[ident]["frameColor"] = (0.20, 0.75, 1.0, 1)
            chord_dict = self.MAJOR_CHORDS if self.active_chord_tab == "MAJOR" else self.MINOR_CHORDS
            if ident in chord_dict:
                notes, _, _ = chord_dict[ident]
                for note in notes:
                    self._apply_key_highlight(note, col)
            return

        if kind == "note":
            self._apply_key_highlight(ident, col)

    def _apply_key_highlight(self, name, col):

        if name in self.white_frames:
            self.white_frames[name]["frameColor"] = col
        elif name in self.black_frames:
            self.black_frames[name]["frameColor"] = col

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
            self.current_targets = [None, None]
            self.candidate_targets = [None, None]
            self.pinch_downs = [False, False]
            return

        processed_hands = []
        for hand in hands_list[:2]:
            lm = self.landmarks(hand)
            if lm is not None and len(lm) >= 21:
                processed_hands.append((hand, lm, lm[8].x))

        if len(processed_hands) == 2:
            processed_hands.sort(key=lambda item: item[2])

        hand_colors = [
            (0.0, 0.85, 1.0, 1.0),   # Left Hand: Electric Blue
            (1.0, 0.30, 0.85, 1.0)   # Right Hand: Vivid Pink
        ]

        for h_idx, (hand, lm, _) in enumerate(processed_hands):
            raw_x, raw_z = self.screen_point(lm[8])

            if self.cursors[h_idx] is None:
                self.cursors[h_idx] = (raw_x, raw_z)
                self.cursor_velocities[h_idx] = 0.0
            else:
                old_x, old_z = self.cursors[h_idx]
                dist = math.hypot(raw_x - old_x, raw_z - old_z)
                self.cursor_velocities[h_idx] = dist

                adaptive_alpha = min(0.85, max(self.base_smoothing, self.base_smoothing + dist * 3.5))
                self.cursors[h_idx] = (
                    old_x + (raw_x - old_x) * adaptive_alpha,
                    old_z + (raw_z - old_z) * adaptive_alpha
                )

            cx, cz = self.cursors[h_idx]
            self.draw_pointer(cx, cz, hand_colors[h_idx], radius=0.038)

            target = self.find_target(cx, cz)

            if target is not None:
                self.highlight_target(target, h_idx)

            # ------------------------------------
            # MODE A: AIR-KEYBOARD MODE (DEFAULT HOVER-TO-PLAY)
            # ------------------------------------
            if self.play_mode == "AIR_KEYBOARD":
                if target is not None:
                    if target != self.current_targets[h_idx]:
                        if self.candidate_targets[h_idx] != target:
                            self.candidate_targets[h_idx] = target
                            self.candidate_times[h_idx] = now
                        elif now - self.candidate_times[h_idx] >= self.key_dwell_time:
                            self.current_targets[h_idx] = target
                            self.last_actions[h_idx] = now
                            if self.gesture_input_enabled:
                                kind, ident = target
                                self.execute_target_action(kind, ident, h_idx)
                    else:
                        self.candidate_targets[h_idx] = target
                else:
                    self.candidate_targets[h_idx] = None
                    self.current_targets[h_idx] = None

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
                                    kind, ident = active_target
                                    self.execute_target_action(kind, ident, h_idx)
                                self.last_actions[h_idx] = now
                    elif ratio > self.pinch_off:
                        self.pinch_downs[h_idx] = False

    def _trigger_spectrum_peak(self):

        for i in range(len(self.spectrum_bands)):
            self.spectrum_bands[i] = min(1.0, self.spectrum_bands[i] + np.random.uniform(0.4, 0.9))

    def _update_telemetry(self, now):

        # Smooth Piano Fade In / Fade Out animation
        dt = min(0.1, max(0.001, now - getattr(self, "_last_telemetry_time", now)))
        self._last_telemetry_time = now

        if self.fade_state == "FADING_OUT":
            self.piano_volume = max(0.0, self.piano_volume - dt * 0.75)
            self.sound_manager.set_piano_volume(self.piano_volume)
            pct = int(self.piano_volume * 100)
            self.piano_vol_label["text"] = f"VOL: {pct}%"
            if self.piano_volume <= 0.001:
                self.fade_state = "MUTED"
                if hasattr(self, "fade_btn"):
                    self.fade_btn["text"] = "FADE IN"
                    self.fade_btn["frameColor"] = (0.75, 0.15, 0.18, 1)
        elif self.fade_state == "FADING_IN":
            target = getattr(self, "target_fade_volume", 0.90)
            self.piano_volume = min(target, self.piano_volume + dt * 0.75)
            self.sound_manager.set_piano_volume(self.piano_volume)
            pct = int(self.piano_volume * 100)
            self.piano_vol_label["text"] = f"VOL: {pct}%"
            if self.piano_volume >= target - 0.001:
                self.fade_state = "IDLE"
                if hasattr(self, "fade_btn"):
                    self.fade_btn["text"] = "FADE OUT"
                    self.fade_btn["frameColor"] = (0.20, 0.22, 0.28, 1)

        self.vu_level = max(0.0, self.vu_level - 0.04)
        bars_count = int(self.vu_level * 16)
        bars_str = "|" * bars_count + " " * (16 - bars_count)
        self.rec_vu_label["text"] = f"[{bars_str}]"

        spectrum_chars = [" ", ".", ":", "|", "||", "|||", "||||", "|||||"]
        spec_text = []
        for i in range(len(self.spectrum_bands)):
            if self.track_channel and not self.track_paused:
                self.spectrum_bands[i] = max(self.spectrum_bands[i], np.random.uniform(0.20, 0.70))
            else:
                self.spectrum_bands[i] = max(0.0, self.spectrum_bands[i] - 0.06)

            idx = min(len(spectrum_chars) - 1, int(self.spectrum_bands[i] * len(spectrum_chars)))
            spec_text.append(spectrum_chars[idx])

        self.spectrum_label["text"] = " ".join(spec_text)

        if self.track_channel and not self.track_paused:
            elapsed = time.monotonic() - self.track_start_time
            cur_sec = int(elapsed % max(1.0, self.track_total_duration))
            tot_sec = int(max(1.0, self.track_total_duration))
            self.track_progress_label["text"] = f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}"

        if self.is_recording:
            elapsed = int(now - self.record_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.rec_status_label["text"] = f"{mins:02d}:{secs:02d}"

    # ========================================================
    # SHOW / HIDE / CLEANUP
    # ========================================================

    def show(self):

        self.active = True
        self.cursors = [None, None]
        self.current_targets = [None, None]
        self.candidate_targets = [None, None]
        self.pinch_downs = [False, False]

        if hasattr(self.base, "win") and self.base.win:
            self.base.win.setClearColor(Vec4(0.02, 0.025, 0.035, 1.0))

        # Hotkeys
        self.base.accept("m", self.toggle_play_mode)
        self.base.accept("r", self.toggle_recording)
        self.base.accept("t", self.play_track)
        self.base.accept("s", self.stop_track)
        self.base.accept("u", self.toggle_sustain)
        self.base.accept("f", self.toggle_piano_fade)
        self.base.accept("=", lambda: self.adjust_track_volume(+0.10))
        self.base.accept("+", lambda: self.adjust_track_volume(+0.10))
        self.base.accept("-", lambda: self.adjust_track_volume(-0.10))
        self.base.accept("n", self.step_chord_progression)
        self.base.accept("[", lambda: self.adjust_octave(-1))
        self.base.accept("]", lambda: self.adjust_octave(+1))

        self.frame.show()
        self.pointer_root.show()
        self.fx_root.show()

    def hide(self):

        self.active = False

        self.base.ignore("m")
        self.base.ignore("r")
        self.base.ignore("t")
        self.base.ignore("s")
        self.base.ignore("u")
        self.base.ignore("f")
        self.base.ignore("=")
        self.base.ignore("+")
        self.base.ignore("-")
        self.base.ignore("n")
        self.base.ignore("[")
        self.base.ignore("]")

        self.frame.hide()
        self.pointer_root.hide()
        self.fx_root.hide()

        self.clear_pointers()
        self.reset_keys()
        self.stop_track()

        if self.is_recording:
            self.stop_recording()

        self.cursors = [None, None]
        self.current_targets = [None, None]
        self.candidate_targets = [None, None]
        self.pinch_downs = [False, False]

    def cleanup(self):

        self.hide()

    def _navigate_to(self, mode_name):
        """Safely navigate to another screen mode in HoloHand."""
        if hasattr(self.base, 'set_mode'):
            self.base.set_mode(mode_name)
        elif hasattr(self.base, 'app') and hasattr(self.base.app, 'set_mode'):
            self.base.app.set_mode(mode_name)
        else:
            print(f"[Piano] Mode navigation: {mode_name}")
        self.pointer_root.removeNode()
        self.fx_root.removeNode()
        self.frame.destroy()
