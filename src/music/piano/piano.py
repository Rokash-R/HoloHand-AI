import os
import time
import math
import wave
from pathlib import Path
import numpy as np

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DGG
)
from panda3d.core import TextNode, LineSegs, Vec4, TransparencyAttrib


class Piano:
    """
    HoloHand AI - Professional Cyber Stage Synthesizer Workstation.

    Complete Upgrade:
      - 1:1 Visual Match with Reference Workstation Design (Image 2)
      - Left Panel: HOME button, Major/Minor Tabs, 7 Rich Color Chord Pads, Chord Progression
      - Center Panel: Controls Bar (Mode, Octave 2-6, Sustain, Volume, Reverb, Note Display),
                      Real-time Audio Visualizer Screen, 6 Synth Patches (Piano, E.Piano, Organ,
                      Strings, Pad, Synth), Hardware Knobs, Visual Performance Mode,
                      Realistic Ivory/Ebony Keys (Z-Order Fixed), Bottom Dock (Piano, Drums, Home)
      - Right Panel: SETTINGS button (with modal overlay), 8 Distinct Rich Musical Tracks,
                     Transport Row (Play, Pause, Stop, Mute), Track Volume Slider,
                     Track Progress Display, Professional Recording System
      - Gesture Controls: Adaptive mouse-like cursor tracking, Blue (Left) & Pink (Right) glowing
                          fingertip pointers, selection ripple feedback, full button hit-testing.
    """

    WHITE = ["C", "D", "E", "F", "G", "A", "B", "C5"]

    BLACK = [
        ("C#", 0), ("D#", 1),
        ("F#", 3), ("G#", 4), ("A#", 5)
    ]

    MAJOR_CHORDS = {
        "C MAJOR": (["C", "E", "G"], "C - E - G", (0.06, 0.44, 0.72, 1.0)),
        "G MAJOR": (["G", "B", "D"], "G - B - D", (0.85, 0.52, 0.08, 1.0)),
        "D MAJOR": (["D", "Fs", "A"], "D - F# - A", (0.12, 0.60, 0.32, 1.0)),
        "F MAJOR": (["F", "A", "C5"], "F - A - C", (0.80, 0.18, 0.22, 1.0)),
        "A MAJOR": (["A", "Cs", "E"], "A - C# - E", (0.55, 0.18, 0.75, 1.0)),
        "E MAJOR": (["E", "Gs", "B"], "E - G# - B", (0.72, 0.40, 0.15, 1.0)),
        "B MAJOR": (["B", "Ds", "Fs"], "B - D# - F#", (0.08, 0.60, 0.70, 1.0))
    }

    MINOR_CHORDS = {
        "C MINOR": (["C", "Ds", "G"], "C - Eb - G", (0.06, 0.44, 0.72, 1.0)),
        "G MINOR": (["G", "As", "D"], "G - Bb - D", (0.85, 0.52, 0.08, 1.0)),
        "D MINOR": (["D", "F", "A"], "D - F - A", (0.12, 0.60, 0.32, 1.0)),
        "F MINOR": (["F", "Gs", "C5"], "F - Ab - C", (0.80, 0.18, 0.22, 1.0)),
        "A MINOR": (["A", "C5", "E"], "A - C - E", (0.55, 0.18, 0.75, 1.0)),
        "E MINOR": (["E", "G", "B"], "E - G - B", (0.72, 0.40, 0.15, 1.0)),
        "B MINOR": (["B", "D", "Fs"], "B - D - F#", (0.08, 0.60, 0.70, 1.0))
    }

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
        self.piano_volume = 0.85
        self.track_volume = 0.80
        self.is_muted = False
        self.prev_track_vol = 0.80

        # Visual Performance Mode
        self.visual_fx_enabled = True
        self.active_beams = []

        # Chord tab state: "MAJOR" or "MINOR"
        self.active_chord_tab = "MAJOR"
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

        # Backing track audio state
        self.active_track_idx = 0
        self.track_channel = None
        self.track_sound = None
        self.track_paused = False
        self.track_start_time = 0.0
        self.track_pause_time = 0.0
        self.track_total_duration = 8.0
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
        self.interactive_regions = []

        # Master workstation chassis frame (Deep dark background)
        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameSize=(-1.78, 1.78, -1.0, 1.0),
            frameColor=(0.02, 0.025, 0.035, 1.0),
            relief=DGG.FLAT
        )
        self.frame.setBin("fixed", 1)

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

        # Load initial backing track
        self._load_active_track()

        self.hide()

    # ========================================================
    # CENTER SYNTHESIZER CONSOLE (MATCHING IMAGE 2 HARDWARE)
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

        # Speaker grille louvers on left and right
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

        # Center embossed branding plate
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

        # ── 2. Top Hardware Control Strip ──
        self.controls_strip = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.51),
            frameSize=(-0.94, 0.94, -0.080, 0.080),
            frameColor=(0.035, 0.045, 0.065, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.controls_strip.setBin("fixed", 5)

        # PLAY MODE Segmented Switch
        DirectLabel(
            parent=self.controls_strip,
            text="PLAY MODE",
            pos=(-0.68, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.mode_air_btn = DirectButton(
            parent=self.controls_strip,
            text="AIR KEYBOARD",
            pos=(-0.77, 0, -0.015),
            text_scale=0.022,
            text_fg=(0.95, 1.0, 1.0, 1),
            frameSize=(-0.105, 0.105, -0.038, 0.038),
            frameColor=(0.08, 0.48, 0.78, 1),
            relief=DGG.FLAT,
            command=lambda: self.set_play_mode("AIR_KEYBOARD")
        )

        self.mode_pinch_btn = DirectButton(
            parent=self.controls_strip,
            text="PINCH MODE",
            pos=(-0.56, 0, -0.015),
            text_scale=0.022,
            text_fg=(0.60, 0.70, 0.80, 1),
            frameSize=(-0.095, 0.095, -0.038, 0.038),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=lambda: self.set_play_mode("PINCH")
        )

        self._register_target("action", "mode_air", -0.77, 0.51 - 0.015 + 0.16, 0.105, 0.038, self.mode_air_btn)
        self._register_target("action", "mode_pinch", -0.56, 0.51 - 0.015 + 0.16, 0.095, 0.038, self.mode_pinch_btn)

        # OCTAVE Controller: [ - ] 4 [ + ]
        DirectLabel(
            parent=self.controls_strip,
            text="OCTAVE",
            pos=(-0.32, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.octave_down_btn = DirectButton(
            parent=self.controls_strip,
            text="-",
            pos=(-0.40, 0, -0.015),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.035, 0.035, -0.035, 0.035),
            frameColor=(0.10, 0.14, 0.20, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_octave(-1)
        )

        self.octave_display = DirectLabel(
            parent=self.controls_strip,
            text=str(self.current_octave),
            pos=(-0.32, 0, -0.024),
            scale=0.032,
            text_fg=(0.85, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.06, 0.08, 0.12, 1),
            frameSize=(-0.040, 0.040, -0.035, 0.035)
        )

        self.octave_up_btn = DirectButton(
            parent=self.controls_strip,
            text="+",
            pos=(-0.24, 0, -0.015),
            text_scale=0.030,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.035, 0.035, -0.035, 0.035),
            frameColor=(0.10, 0.14, 0.20, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_octave(+1)
        )

        self._register_target("action", "octave_down", -0.40, 0.51 - 0.015 + 0.16, 0.035, 0.035, self.octave_down_btn)
        self._register_target("action", "octave_up", -0.24, 0.51 - 0.015 + 0.16, 0.035, 0.035, self.octave_up_btn)

        # SUSTAIN Switch: [ ON ] (Vibrant Green Pill Switch)
        DirectLabel(
            parent=self.controls_strip,
            text="SUSTAIN",
            pos=(-0.08, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.sustain_btn = DirectButton(
            parent=self.controls_strip,
            text="ON",
            pos=(-0.08, 0, -0.015),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.085, 0.085, -0.036, 0.036),
            frameColor=(0.12, 0.72, 0.32, 1),
            relief=DGG.FLAT,
            command=self.toggle_sustain
        )
        self._register_target("action", "toggle_sustain", -0.08, 0.51 - 0.015 + 0.16, 0.085, 0.036, self.sustain_btn)

        # VOLUME Display with LED Level Bars
        DirectLabel(
            parent=self.controls_strip,
            text="VOLUME",
            pos=(0.14, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_strip_label = DirectLabel(
            parent=self.controls_strip,
            text="||||||||  85%",
            pos=(0.14, 0, -0.022),
            scale=0.022,
            text_fg=(0.20, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.08, 0.10, 0.14, 1),
            frameSize=(-0.095, 0.095, -0.034, 0.034)
        )

        # REVERB Switch: [ OFF / ON ]
        DirectLabel(
            parent=self.controls_strip,
            text="REVERB",
            pos=(0.38, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.reverb_btn = DirectButton(
            parent=self.controls_strip,
            text="OFF",
            pos=(0.38, 0, -0.015),
            text_scale=0.026,
            text_fg=(0.70, 0.75, 0.85, 1),
            frameSize=(-0.085, 0.085, -0.036, 0.036),
            frameColor=(0.12, 0.14, 0.20, 1),
            relief=DGG.FLAT,
            command=self.toggle_reverb
        )
        self._register_target("action", "toggle_reverb", 0.38, 0.51 - 0.015 + 0.16, 0.085, 0.036, self.reverb_btn)

        # CURRENT NOTE Large Readout Box (Displays e.g. C4, F#4)
        DirectLabel(
            parent=self.controls_strip,
            text="CURRENT NOTE",
            pos=(0.68, 0, 0.050),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.current_note_frame = DirectFrame(
            parent=self.controls_strip,
            pos=(0.68, 0, -0.015),
            frameSize=(-0.12, 0.12, -0.038, 0.038),
            frameColor=(0.05, 0.08, 0.14, 1),
            relief=DGG.SUNKEN,
            borderWidth=(0.003, 0.003)
        )

        self.current_note_label = DirectLabel(
            parent=self.current_note_frame,
            text="C4",
            pos=(0, 0, -0.016),
            scale=0.046,
            text_fg=(0.20, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── 3. Middle Hardware Synth Console (Wheels, LCD Display & Controls) ──
        self.rack_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.29),
            frameSize=(-0.94, 0.94, -0.125, 0.125),
            frameColor=(0.06, 0.07, 0.09, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.rack_frame.setBin("fixed", 5)

        # Dual Pitch & Mod Wheels
        DirectFrame(
            parent=self.rack_frame,
            pos=(-0.84, 0, 0.01),
            frameSize=(-0.038, 0.038, -0.085, 0.085),
            frameColor=(0.14, 0.15, 0.18, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004)
        )
        DirectLabel(
            parent=self.rack_frame,
            text="PITCH",
            pos=(-0.84, 0, -0.105),
            scale=0.018,
            text_fg=(0.55, 0.60, 0.65, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectFrame(
            parent=self.rack_frame,
            pos=(-0.73, 0, 0.01),
            frameSize=(-0.038, 0.038, -0.085, 0.085),
            frameColor=(0.14, 0.15, 0.18, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004)
        )
        DirectLabel(
            parent=self.rack_frame,
            text="MOD",
            pos=(-0.73, 0, -0.105),
            scale=0.018,
            text_fg=(0.55, 0.60, 0.65, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Center Blue LCD Spectrum & Waveform Screen
        self.lcd_screen = DirectFrame(
            parent=self.rack_frame,
            pos=(-0.03, 0, 0.015),
            frameSize=(-0.24, 0.24, -0.088, 0.088),
            frameColor=(0.01, 0.08, 0.16, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )

        # Real-time animated audio spectrum display
        self.spectrum_label = DirectLabel(
            parent=self.lcd_screen,
            text="| | || ||| |||| ||||| |||| ||| || | |",
            pos=(0, 0, -0.015),
            scale=0.024,
            text_fg=(0.25, 0.90, 1.0, 0.95),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # 6 Sound Patch Selectors directly under LCD screen
        self.patch_buttons = {}
        for p_idx, pname in enumerate(self.SYNTH_PATCHES):
            is_active = (pname == self.current_patch)
            p_col = (0.10, 0.50, 0.85, 1) if is_active else (0.10, 0.12, 0.16, 1)
            p_fg = (1.0, 1.0, 1.0, 1) if is_active else (0.65, 0.70, 0.78, 1)
            px = -0.205 + p_idx * 0.070
            pz = -0.088
            btn = DirectButton(
                parent=self.rack_frame,
                text=pname,
                pos=(px, 0, pz),
                text_scale=0.016,
                text_fg=p_fg,
                frameSize=(-0.032, 0.032, -0.018, 0.018),
                frameColor=p_col,
                relief=DGG.FLAT,
                command=lambda p=pname: self.set_synth_patch(p)
            )
            self.patch_buttons[pname] = btn
            self._register_target("patch", pname, px, 0.29 + pz + 0.16, 0.032, 0.018, btn)

        # Rotary Synth Knobs on Right (CUTOFF, RESONANCE, RELEASE)
        knobs = [
            ("CUTOFF", 0.32),
            ("RESONANCE", 0.50),
            ("RELEASE", 0.68)
        ]
        for kname, kpos_x in knobs:
            DirectFrame(
                parent=self.rack_frame,
                pos=(kpos_x, 0, 0.025),
                frameSize=(-0.042, 0.042, -0.042, 0.042),
                frameColor=(0.14, 0.16, 0.20, 1.0),
                relief=DGG.RAISED,
                borderWidth=(0.004, 0.004)
            )
            DirectLabel(
                parent=self.rack_frame,
                text=kname,
                pos=(kpos_x, 0, -0.042),
                scale=0.016,
                text_fg=(0.60, 0.65, 0.70, 1),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

        # VISUAL PERFORMANCE Mode Toggle Button
        self.vfx_btn = DirectButton(
            parent=self.rack_frame,
            text="VISUAL FX",
            pos=(0.83, 0, 0.03),
            text_scale=0.016,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.040, 0.040, -0.020, 0.020),
            frameColor=(0.10, 0.65, 0.40, 1),
            relief=DGG.FLAT,
            command=self.toggle_visual_fx
        )
        self._register_target("action", "toggle_vfx", 0.83, 0.29 + 0.03 + 0.16, 0.040, 0.020, self.vfx_btn)

        # Speed / Sensitivity Button
        self.speed_btn = DirectButton(
            parent=self.rack_frame,
            text="NORMAL",
            pos=(0.83, 0, -0.03),
            text_scale=0.016,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.040, 0.040, -0.020, 0.020),
            frameColor=(0.70, 0.45, 0.08, 1),
            relief=DGG.FLAT,
            command=self.toggle_speed_mode
        )
        self._register_target("action", "toggle_speed", 0.83, 0.29 - 0.03 + 0.16, 0.040, 0.020, self.speed_btn)

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

        # Red felt damper strip at top of keybed (authentic physical piano detail)
        DirectFrame(
            parent=self.keybed_frame,
            pos=(0, 0, 0.365),
            frameSize=(-0.91, 0.91, -0.012, 0.012),
            frameColor=(0.75, 0.08, 0.12, 1.0)
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

            # Beveled Bottom Lip
            bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.342),
                frameSize=(-0.104, 0.104, -0.010, 0.010),
                frameColor=(0.82, 0.80, 0.76, 1.0)
            )
            bevel.setBin("fixed", 21)

            # Note Label
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.250),
                scale=0.046,
                text_fg=(0.10, 0.12, 0.16, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 22)

            self.white_frames[note] = frame

            world_z = -0.28 + z_pos + 0.16
            self._register_target("note", note, x, world_z, 0.108, 0.355, frame, is_black=False)

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

            # Top highlight
            top_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, 0.175),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.32, 0.34, 0.38, 1.0)
            )
            top_bevel.setBin("fixed", 36)

            # Bottom lip
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

            world_z = -0.28 + z_pos + 0.16
            self._register_target("note", note, x, world_z, 0.065, 0.190, frame, is_black=True)

        # ----------------------------------------------------
        # 3. BOTTOM NAVIGATION DOCK (PIANO, DRUMS, HOME)
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

        # PIANO Button (Active with glowing border)
        self.dock_piano = DirectButton(
            parent=self.bottom_dock,
            text="PIANO",
            pos=(-0.34, 0, -0.012),
            text_scale=0.026,
            text_fg=(0.30, 0.95, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.40, 0.65, 1),
            relief=DGG.FLAT
        )

        # DRUMS Button (Navigates to Drums mode)
        self.dock_drums = DirectButton(
            parent=self.bottom_dock,
            text="DRUMS",
            pos=(0.0, 0, -0.012),
            text_scale=0.026,
            text_fg=(0.75, 0.80, 0.88, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=lambda: self.base.set_mode("DRUMS")
        )

        # HOME Button (Navigates to Home mode)
        self.dock_home = DirectButton(
            parent=self.bottom_dock,
            text="HOME",
            pos=(0.34, 0, -0.012),
            text_scale=0.026,
            text_fg=(0.75, 0.80, 0.88, 1),
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=lambda: self.base.set_mode("HOME")
        )

        self._register_target("action", "nav_drums", 0.0, -0.74 - 0.012 + 0.16, 0.14, 0.045, self.dock_drums)
        self._register_target("action", "nav_home", 0.34, -0.74 - 0.012 + 0.16, 0.14, 0.045, self.dock_home)

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

        # Top HOME Button in Left Panel (Matching Image 2)
        self.panel_home_btn = DirectButton(
            parent=self.chord_dock,
            text="HOME",
            pos=(-0.20, 0, 0.62),
            text_scale=0.024,
            text_fg=(0.85, 0.95, 1.0, 1),
            frameSize=(-0.11, 0.11, -0.032, 0.032),
            frameColor=(0.12, 0.16, 0.24, 1),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004),
            command=lambda: self.base.set_mode("HOME")
        )
        self._register_target("action", "nav_home", -1.35 - 0.20, -0.02 + 0.62, 0.11, 0.032, self.panel_home_btn)

        # Header Title
        DirectLabel(
            parent=self.chord_dock,
            text="CHORD STUDIO",
            pos=(0.10, 0, 0.61),
            scale=0.034,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Sub-tabs: [ MAJOR ] and [ MINOR ] with functional switching
        self.tab_major = DirectButton(
            parent=self.chord_dock,
            text="MAJOR",
            pos=(-0.16, 0, 0.54),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT,
            command=lambda: self.switch_chord_tab("MAJOR")
        )

        self.tab_minor = DirectButton(
            parent=self.chord_dock,
            text="MINOR",
            pos=(0.16, 0, 0.54),
            text_scale=0.024,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT,
            command=lambda: self.switch_chord_tab("MINOR")
        )

        self._register_target("action", "tab_major", -1.35 - 0.16, -0.02 + 0.54, 0.14, 0.030, self.tab_major)
        self._register_target("action", "tab_minor", -1.35 + 0.16, -0.02 + 0.54, 0.14, 0.030, self.tab_minor)

        # Container for 7 Chord Buttons
        self.chord_buttons_container = DirectFrame(
            parent=self.chord_dock,
            pos=(0, 0, 0),
            frameColor=(0, 0, 0, 0)
        )

        self._render_chord_pads()

        # Bottom Progression Section
        DirectLabel(
            parent=self.chord_dock,
            text="CHORD PROGRESSION",
            pos=(-0.30, 0, -0.37),
            scale=0.020,
            text_fg=(0.60, 0.68, 0.75, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.chord_dock,
            text="<  C - G - Am - F  >",
            pos=(0, 0, -0.44),
            scale=0.026,
            text_fg=(0.85, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.08, 0.10, 0.14, 1),
            frameSize=(-0.33, 0.33, -0.035, 0.035)
        )

        self.prog_btn = DirectButton(
            parent=self.chord_dock,
            text="> PLAY PROGRESSION",
            pos=(0, 0, -0.54),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.33, 0.33, -0.042, 0.042),
            frameColor=(0.10, 0.60, 0.30, 1),
            relief=DGG.FLAT,
            command=self.step_chord_progression
        )
        self._register_target("progression", "step", -1.35, -0.02 - 0.54, 0.33, 0.042, self.prog_btn)

    def _render_chord_pads(self):
        """
        Dynamically builds the 7 chord buttons based on active tab (MAJOR or MINOR).
        """
        for child in self.chord_buttons_container.getChildren():
            child.removeNode()

        # Remove existing chord targets from interactive regions
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
                command=lambda c=name: self.play_chord(c)
            )

            DirectLabel(
                parent=btn,
                text=name.title(),
                pos=(-0.30, 0, 0.010),
                scale=0.028,
                text_fg=(1.0, 1.0, 1.0, 1),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=btn,
                text=notes_str,
                pos=(-0.30, 0, -0.025),
                scale=0.020,
                text_fg=(0.85, 0.92, 1.0, 0.90),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=btn,
                text=">",
                pos=(0.28, 0, -0.012),
                scale=0.028,
                text_fg=(1.0, 1.0, 1.0, 0.8),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.chord_buttons[name] = btn

            world_z = -0.02 + z
            self._register_target("chord", name, -1.35, world_z, 0.33, 0.046, btn)

    def switch_chord_tab(self, tab):

        self.active_chord_tab = tab
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

        self._render_chord_pads()

    # ========================================================
    # RIGHT PANEL — MUSIC STUDIO (TRACKS, MUTE & RECORDER)
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

        # Top SETTINGS Button in Right Panel (Matching Image 2)
        self.panel_settings_btn = DirectButton(
            parent=self.music_dock,
            text="SETTINGS",
            pos=(-0.16, 0, 0.62),
            text_scale=0.022,
            text_fg=(0.85, 0.95, 1.0, 1),
            frameSize=(-0.12, 0.12, -0.032, 0.032),
            frameColor=(0.14, 0.18, 0.26, 1),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004),
            command=self.open_settings
        )
        self._register_target("action", "open_settings", 1.35 - 0.16, -0.02 + 0.62, 0.12, 0.032, self.panel_settings_btn)

        # Header Title
        DirectLabel(
            parent=self.music_dock,
            text="MUSIC STUDIO",
            pos=(0.14, 0, 0.61),
            scale=0.034,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Sub-tabs: [ TRACKS ] and [ CUSTOM ]
        self.tab_tracks = DirectButton(
            parent=self.music_dock,
            text="TRACKS",
            pos=(-0.16, 0, 0.54),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT
        )

        self.tab_custom = DirectButton(
            parent=self.music_dock,
            text="CUSTOM",
            pos=(0.16, 0, 0.54),
            text_scale=0.024,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.030, 0.030),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT
        )

        # ── 8 Authentic Backing Tracks List ──
        track_start_z = 0.45
        track_step_z = 0.052

        for i, (tname, fname, bpm) in enumerate(self.TRACK_FILES):
            z = track_start_z - i * track_step_z
            is_active = (i == self.active_track_idx)

            bg_col = (0.10, 0.24, 0.38, 1.0) if is_active else (0.08, 0.09, 0.12, 1.0)
            fg_col = (0.25, 0.92, 1.0, 1.0) if is_active else (0.82, 0.86, 0.92, 1.0)

            tbtn = DirectButton(
                parent=self.music_dock,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.023, 0.023),
                frameColor=bg_col,
                relief=DGG.FLAT,
                command=lambda idx=i: self.select_track(idx)
            )

            tlbl = DirectLabel(
                parent=tbtn,
                text=f"{tname}  [{bpm} BPM]",
                pos=(-0.30, 0, -0.008),
                scale=0.020,
                text_fg=fg_col,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            DirectLabel(
                parent=tbtn,
                text=">",
                pos=(0.28, 0, -0.008),
                scale=0.024,
                text_fg=fg_col,
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.track_buttons.append((tbtn, tlbl))

            world_z = -0.02 + z
            self._register_target("track", i, 1.35, world_z, 0.33, 0.023, tbtn)

        # ── Transport Controls Row: PLAY, PAUSE, STOP, MUTE ──
        self.track_play_btn = DirectButton(
            parent=self.music_dock,
            text="> PLAY",
            pos=(-0.25, 0, -0.03),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.034, 0.034),
            frameColor=(0.10, 0.60, 0.30, 1),
            relief=DGG.FLAT,
            command=self.play_track
        )

        self.track_pause_btn = DirectButton(
            parent=self.music_dock,
            text="|| PAUSE",
            pos=(-0.08, 0, -0.03),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.034, 0.034),
            frameColor=(0.75, 0.52, 0.08, 1),
            relief=DGG.FLAT,
            command=self.pause_track
        )

        self.track_stop_btn = DirectButton(
            parent=self.music_dock,
            text="# STOP",
            pos=(0.09, 0, -0.03),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.034, 0.034),
            frameColor=(0.75, 0.15, 0.18, 1),
            relief=DGG.FLAT,
            command=self.stop_track
        )

        self.track_mute_btn = DirectButton(
            parent=self.music_dock,
            text="MUTE",
            pos=(0.26, 0, -0.03),
            text_scale=0.022,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.075, 0.075, -0.034, 0.034),
            frameColor=(0.20, 0.22, 0.28, 1),
            relief=DGG.FLAT,
            command=self.toggle_mute
        )

        self._register_target("action", "play_track", 1.35 - 0.25, -0.02 - 0.03, 0.075, 0.034, self.track_play_btn)
        self._register_target("action", "pause_track", 1.35 - 0.08, -0.02 - 0.03, 0.075, 0.034, self.track_pause_btn)
        self._register_target("action", "stop_track", 1.35 + 0.09, -0.02 - 0.03, 0.075, 0.034, self.track_stop_btn)
        self._register_target("action", "toggle_mute", 1.35 + 0.26, -0.02 - 0.03, 0.075, 0.034, self.track_mute_btn)

        # ── TRACK VOLUME Slider & Progress Indicator ──
        DirectLabel(
            parent=self.music_dock,
            text="TRACK VOLUME",
            pos=(-0.30, 0, -0.11),
            scale=0.020,
            text_fg=(0.60, 0.68, 0.75, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.track_progress_label = DirectLabel(
            parent=self.music_dock,
            text="00:00 / 08:00",
            pos=(0.30, 0, -0.11),
            scale=0.018,
            text_fg=(0.35, 0.85, 1.0, 1),
            text_align=TextNode.ARight,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_down_btn = DirectButton(
            parent=self.music_dock,
            text="-",
            pos=(-0.25, 0, -0.16),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.028, 0.028),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_track_volume(-0.10)
        )

        self.vol_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||    ]  80%",
            pos=(0.02, 0, -0.165),
            scale=0.022,
            text_fg=(0.20, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_up_btn = DirectButton(
            parent=self.music_dock,
            text="+",
            pos=(0.28, 0, -0.16),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.028, 0.028),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_track_volume(+0.10)
        )

        self._register_target("action", "vol_down", 1.35 - 0.25, -0.02 - 0.16, 0.05, 0.028, self.vol_down_btn)
        self._register_target("action", "vol_up", 1.35 + 0.28, -0.02 - 0.16, 0.05, 0.028, self.vol_up_btn)

        # ── RECORDING Studio Controls ──
        DirectLabel(
            parent=self.music_dock,
            text="* RECORDING",
            pos=(-0.30, 0, -0.24),
            scale=0.020,
            text_fg=(0.85, 0.35, 0.40, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.record_btn = DirectButton(
            parent=self.music_dock,
            text="* RECORD",
            pos=(-0.16, 0, -0.30),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.038, 0.038),
            frameColor=(0.75, 0.12, 0.15, 1),
            relief=DGG.FLAT,
            command=self.toggle_recording
        )

        self.rec_stop_btn = DirectButton(
            parent=self.music_dock,
            text="# STOP",
            pos=(0.16, 0, -0.30),
            text_scale=0.026,
            text_fg=(0.80, 0.85, 0.90, 1),
            frameSize=(-0.14, 0.14, -0.038, 0.038),
            frameColor=(0.16, 0.18, 0.22, 1),
            relief=DGG.FLAT,
            command=self.stop_recording
        )

        self._register_target("action", "toggle_record", 1.35 - 0.16, -0.02 - 0.30, 0.14, 0.038, self.record_btn)
        self._register_target("action", "stop_record", 1.35 + 0.16, -0.02 - 0.30, 0.14, 0.038, self.rec_stop_btn)

        # Recording Status Timer & Dynamic VU Meter
        self.rec_status_label = DirectLabel(
            parent=self.music_dock,
            text="00:00",
            pos=(-0.24, 0, -0.39),
            scale=0.028,
            text_fg=(0.80, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.rec_vu_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||||]",
            pos=(0.10, 0, -0.39),
            scale=0.024,
            text_fg=(0.20, 0.90, 0.40, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # SAVE RECORDING Button
        self.save_rec_btn = DirectButton(
            parent=self.music_dock,
            text="SAVE RECORDING",
            pos=(0, 0, -0.51),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.33, 0.33, -0.042, 0.042),
            frameColor=(0.10, 0.42, 0.70, 1),
            relief=DGG.FLAT,
            command=self.save_and_export_recording
        )
        self._register_target("action", "save_record", 1.35, -0.02 - 0.51, 0.33, 0.042, self.save_rec_btn)

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

        # Header
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

        # Setting 1: Gesture Sensitivity
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

        # Setting 2: Master Volume
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

        # Setting 3: Visual Performance FX
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

        # Setting 4: Audio Reverb Acoustics
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

        # Close Settings Button
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
    # SOUND, PATCH, OCTAVE, CHORD & SUSTAIN PLAYBACK
    # ========================================================

    def play_note(self, note):

        note_id = note.replace("#", "s")

        try:
            channel = self.sound_manager.play_piano(
                note_id,
                octave=self.current_octave,
                patch=self.current_patch,
                reverb=self.reverb_on
            )

            # Apply damper cutoff if sustain is OFF
            if not self.sustain_on and channel is not None:
                channel.fadeout(260)

            now = time.monotonic()
            self.key_press_timers[note] = now
            self.vu_level = min(1.0, self.vu_level + 0.65)
            self._trigger_spectrum_peak()

            # Display played note with exact octave
            note_display = f"{note}{self.current_octave}"
            self.current_display_note = note_display
            self.current_note_label["text"] = note_display

            # Trigger Visual Performance Beam Effect
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

    def set_synth_patch(self, patch):

        self.current_patch = patch
        for pname, btn in self.patch_buttons.items():
            if pname == patch:
                btn["frameColor"] = (0.10, 0.50, 0.85, 1)
                btn["text_fg"] = (1.0, 1.0, 1.0, 1)
            else:
                btn["frameColor"] = (0.10, 0.12, 0.16, 1)
                btn["text_fg"] = (0.65, 0.70, 0.78, 1)

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
    # BACKING TRACK ENGINE (8 AUTHENTIC DISTINCT BEATS)
    # ========================================================

    def _load_active_track(self):

        tname, fname, bpm = self.TRACK_FILES[self.active_track_idx]
        self.track_name = tname

        project_root = Path(__file__).resolve().parents[3]
        track_path = project_root / "assets" / fname

        if not track_path.exists():
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.track_sound = pygame.mixer.Sound(str(track_path))
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

        for i, (tbtn, tlbl) in enumerate(self.track_buttons):
            if i == idx:
                tbtn["frameColor"] = (0.10, 0.24, 0.38, 1.0)
                tlbl["text_fg"] = (0.25, 0.92, 1.0, 1.0)
            else:
                tbtn["frameColor"] = (0.08, 0.09, 0.12, 1.0)
                tlbl["text_fg"] = (0.82, 0.86, 0.92, 1.0)

        if was_playing:
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
            self.track_channel = self.track_sound.play(loops=-1)
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
        else:
            self.track_mute_btn["text"] = "MUTE"
            self.track_mute_btn["frameColor"] = (0.20, 0.22, 0.28, 1)
            if self.track_channel is not None:
                self.track_channel.set_volume(self.track_volume * self.sound_manager.master_volume)

    def adjust_track_volume(self, delta):

        self.track_volume = max(0.0, min(1.0, self.track_volume + delta))
        if self.track_channel is not None and not self.is_muted:
            self.track_channel.set_volume(self.track_volume * self.sound_manager.master_volume)
        pct = int(self.track_volume * 100)
        bars_count = int(self.track_volume * 14)
        bars_str = "|" * bars_count + " " * (14 - bars_count)
        self.vol_label["text"] = f"[{bars_str}]  {pct}%"
        self.vol_strip_label["text"] = f"{'|'*int(self.track_volume*8)}  {pct}%"

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
    # INTERACTIVE TARGET SYSTEM (ALL STUDIO BUTTONS & KEYS)
    # ========================================================

    def _register_target(self, kind, ident, x, z, w, h, widget, is_black=False):

        self.interactive_regions.append({
            "kind": kind,
            "ident": ident,
            "x": x,
            "z": z,
            "w": w,
            "h": h,
            "widget": widget,
            "black": is_black
        })

    def find_target(self, x, z):
        """
        Priority collision: Black keys first, then on-screen buttons, then white keys.
        """
        # If settings modal is open, only check settings buttons
        if self.settings_open:
            if abs(x) <= 0.25 and abs(z - (-0.40)) <= 0.046:
                return ("action", "close_settings")
            return None

        # 1. Black keys
        for reg in self.interactive_regions:
            if reg["kind"] == "note" and reg["black"]:
                if abs(x - reg["x"]) <= reg["w"] and abs(z - reg["z"]) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        # 2. Controls, Chords, Navigation & Studio buttons
        for reg in self.interactive_regions:
            if reg["kind"] != "note":
                if abs(x - reg["x"]) <= reg["w"] and abs(z - reg["z"]) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        # 3. White keys
        for reg in self.interactive_regions:
            if reg["kind"] == "note" and not reg["black"]:
                if abs(x - reg["x"]) <= reg["w"] and abs(z - reg["z"]) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        return None

    def execute_target_action(self, kind, ident, hand_idx=0):

        # Visual feedback: Ripple animation at cursor location
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
            elif ident == "open_settings":
                self.open_settings()
            elif ident == "close_settings":
                self.close_settings()
            elif ident == "nav_drums":
                self.base.set_mode("DRUMS")
            elif ident == "nav_home":
                self.base.set_mode("HOME")

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

        self.speed_btn["text"] = self.speed_mode
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

        # Concentric glowing rings
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

        # Center crosshair dot
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
            self.active_beams.append({
                "x": reg["x"],
                "z": reg["z"] + reg["h"],
                "height": 0.02,
                "max_height": 0.35,
                "color": self.key_press_colors.get(note, (0.2, 0.85, 1.0, 1.0)),
                "alpha": 1.0
            })

    def clear_pointers(self):

        for node in self.pointer_nodes:
            node.removeNode()
        self.pointer_nodes.clear()

        # Update ripples & beams
        for child in self.fx_root.getChildren():
            child.removeNode()

        # Draw active ripples
        now = time.monotonic()
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

        # Draw active visual performance beams
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

        # White keys
        for note, frame in self.white_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = self.key_press_colors.get(note, (0.35, 0.88, 1.0, 1.0))
            else:
                frame["frameColor"] = (0.97, 0.96, 0.93, 1.0)

        # Black keys
        for note, frame in self.black_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = self.key_press_colors.get(note, (1.0, 0.35, 0.85, 1.0))
            else:
                frame["frameColor"] = (0.12, 0.12, 0.14, 1.0)

        # Chord buttons reset to their original palette
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

        # Pre-process up to 2 hands (Left = Cyan/Blue, Right = Magenta/Pink)
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
            # Index fingertip point
            raw_x, raw_z = self.screen_point(lm[8])

            # Adaptive mouse-like velocity filter (fast = low latency, slow = steady precision)
            if self.cursors[h_idx] is None:
                self.cursors[h_idx] = (raw_x, raw_z)
                self.cursor_velocities[h_idx] = 0.0
            else:
                old_x, old_z = self.cursors[h_idx]
                dist = math.hypot(raw_x - old_x, raw_z - old_z)
                self.cursor_velocities[h_idx] = dist

                # Scale smoothing dynamically based on movement speed
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

        # Decay VU level
        self.vu_level = max(0.0, self.vu_level - 0.04)
        bars_count = int(self.vu_level * 16)
        bars_str = "|" * bars_count + " " * (16 - bars_count)
        self.rec_vu_label["text"] = f"[{bars_str}]"

        # Decay Real-time Audio Spectrum Bands & Update LCD Display
        spectrum_chars = [" ", ".", ":", "|", "||", "|||", "||||", "|||||"]
        spec_text = []
        for i in range(len(self.spectrum_bands)):
            # If backing track is playing, add rhythmic energy
            if self.track_channel and not self.track_paused:
                self.spectrum_bands[i] = max(self.spectrum_bands[i], np.random.uniform(0.15, 0.65))
            else:
                self.spectrum_bands[i] = max(0.0, self.spectrum_bands[i] - 0.06)

            idx = min(len(spectrum_chars) - 1, int(self.spectrum_bands[i] * len(spectrum_chars)))
            spec_text.append(spectrum_chars[idx])

        self.spectrum_label["text"] = " ".join(spec_text)

        # Track playback elapsed time
        if self.track_channel and not self.track_paused:
            elapsed = time.monotonic() - self.track_start_time
            cur_sec = int(elapsed % self.track_total_duration)
            tot_sec = int(self.track_total_duration)
            self.track_progress_label["text"] = f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}"

        # Recording timer
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
        self.pointer_root.removeNode()
        self.fx_root.removeNode()
        self.frame.destroy()
