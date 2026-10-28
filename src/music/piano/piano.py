import os
import time
import math
import wave
from pathlib import Path
import numpy as np

from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DGG
)
from panda3d.core import TextNode, LineSegs, Vec4


class Piano:
    """
    HoloHand AI - Professional Cyber Stage Synthesizer Workstation.
    Matches the premium reference hardware synthesizer interface:
      - 8 ivory white keys + 5 ebony black keys with flawless Z-order visibility
      - Realistic hardware console: speaker louvers, metallic badges, synth knobs
      - Left dock: 7 warm, vibrant chord buttons (C, G, D, F, A, E, B) + progression stepper
      - Right dock: 8 authentic backing tracks (Pop, Ballad, Acoustic, Electronic, Hip Hop, Rock, Chill, Entertainer)
      - Integrated Gesture Targeting for ALL studio controls (play, pause, record, volume, sustain)
      - Sustain pedal control (ON = rich 1.6s natural decay, OFF = crisp staccato damper)
      - Dual Playing Modes: Air-Keyboard (default hover-to-play) & Pinch-to-Play
      - Two-hand independent polyphonic playing (Cyan & Magenta pointers)
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
        "E MINOR": ["E", "G", "B"],
        "B MAJOR": ["B", "Ds", "Fs"]
    }

    CHORD_PROGRESSION = [
        "C MAJOR", "G MAJOR", "A MINOR", "F MAJOR"
    ]

    # Rich, warm, physical hardware color palette (matching reference)
    CHORD_COLORS = {
        "C MAJOR": (0.06, 0.44, 0.72, 1.0),   # Deep Marine Cyan-Blue
        "G MAJOR": (0.85, 0.52, 0.08, 1.0),   # Warm Amber Golden
        "D MINOR": (0.12, 0.60, 0.32, 1.0),   # Vibrant Emerald Jade
        "F MAJOR": (0.80, 0.18, 0.22, 1.0),   # Crimson Coral Red
        "A MINOR": (0.55, 0.18, 0.75, 1.0),   # Royal Violet Purple
        "E MINOR": (0.72, 0.40, 0.15, 1.0),   # Warm Cocoa Ochre
        "B MAJOR": (0.08, 0.60, 0.70, 1.0)    # Radiant Cyan Cobalt
    }

    TRACK_FILES = [
        ("Pop Beat", "pop_beat.wav"),
        ("Ballad (Vocal)", "ballad_beat.wav"),
        ("Acoustic Beat", "acoustic_beat.wav"),
        ("Electronic Beat", "electronic_beat.wav"),
        ("Hip Hop", "hiphop_beat.wav"),
        ("Rock Beat", "rock_beat.wav"),
        ("Chill Ambient", "chill_beat.wav"),
        ("Entertainer", "entertainer_beat.wav")
    ]

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

        # Sustain feature (True = long decay, False = staccato)
        self.sustain_on = True

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
        self.action_cooldown = 0.18

        # Key press visual illumination timers
        self.key_press_timers = {}

        # Chord progression state
        self.progression_step = 0

        # Backing track audio state
        self.active_track_idx = 0
        self.track_channel = None
        self.track_sound = None
        self.track_volume = 0.80
        self.track_paused = False
        self.track_name = self.TRACK_FILES[0][0]

        # Performance recording state
        self.is_recording = False
        self.record_start_time = 0.0
        self.recorded_events = []
        self.last_exported_file = None

        # VU Meter state
        self.vu_level = 0.0
        self.current_display_note = "READY"

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

        # Build workstation sections
        self._build_center_console()
        self._build_keyboard()
        self._build_chord_studio()
        self._build_music_studio()

        # High priority pointer root (always top)
        self.pointer_root = base.aspect2d.attachNewNode("PianoFingerPointers")
        self.pointer_root.setBin("fixed", 120)
        self.pointer_root.setDepthTest(False)
        self.pointer_root.setDepthWrite(False)

        # Load initial backing track
        self._load_active_track()

        self.hide()

    # ========================================================
    # CENTER SYNTHESIZER CONSOLE (MATCHING REFERENCE HARDWARE)
    # ========================================================

    def _build_center_console(self):

        # Main synthesizer chassis body (spans -0.96 to 0.96)
        self.synth_body = DirectFrame(
            parent=self.frame,
            pos=(0, 0, 0.22),
            frameSize=(-0.96, 0.96, -0.78, 0.72),
            frameColor=(0.05, 0.06, 0.085, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.008, 0.008)
        )
        self.synth_body.setBin("fixed", 3)

        # ── 1. Top Header Plate with Speaker Louvers ──
        self.header_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.62),
            frameSize=(-0.94, 0.94, -0.08, 0.08),
            frameColor=(0.03, 0.035, 0.05, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.header_frame.setBin("fixed", 5)

        # Left speaker grille slats
        for s in range(5):
            DirectFrame(
                parent=self.header_frame,
                pos=(-0.65, 0, 0.04 - s * 0.02),
                frameSize=(-0.22, 0.22, -0.004, 0.004),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )

        # Right speaker grille slats
        for s in range(5):
            DirectFrame(
                parent=self.header_frame,
                pos=(0.65, 0, 0.04 - s * 0.02),
                frameSize=(-0.22, 0.22, -0.004, 0.004),
                frameColor=(0.015, 0.02, 0.03, 1.0)
            )

        # Center embossed branding plate
        DirectLabel(
            parent=self.header_frame,
            text="HOLOHAND  AI",
            pos=(0, 0, 0.015),
            scale=0.048,
            text_fg=(0.90, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.header_frame,
            text="MUSIC STUDIO",
            pos=(0, 0, -0.040),
            scale=0.024,
            text_fg=(0.35, 0.65, 0.85, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── 2. Top Hardware Control Strip ──
        self.controls_strip = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.44),
            frameSize=(-0.94, 0.94, -0.085, 0.085),
            frameColor=(0.035, 0.045, 0.065, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.controls_strip.setBin("fixed", 5)

        # PLAY MODE Segmented Switch
        DirectLabel(
            parent=self.controls_strip,
            text="PLAY MODE",
            pos=(-0.68, 0, 0.052),
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
            text_scale=0.024,
            text_fg=(0.95, 1.0, 1.0, 1),
            frameSize=(-0.11, 0.11, -0.040, 0.040),
            frameColor=(0.08, 0.48, 0.78, 1),
            relief=DGG.FLAT,
            command=lambda: self.set_play_mode("AIR_KEYBOARD")
        )

        self.mode_pinch_btn = DirectButton(
            parent=self.controls_strip,
            text="PINCH MODE",
            pos=(-0.55, 0, -0.015),
            text_scale=0.024,
            text_fg=(0.60, 0.70, 0.80, 1),
            frameSize=(-0.10, 0.10, -0.040, 0.040),
            frameColor=(0.08, 0.10, 0.15, 1),
            relief=DGG.FLAT,
            command=lambda: self.set_play_mode("PINCH")
        )

        self._register_target("action", "mode_air", -0.77, 0.44 - 0.015 + 0.22, 0.11, 0.040, self.mode_air_btn)
        self._register_target("action", "mode_pinch", -0.55, 0.44 - 0.015 + 0.22, 0.10, 0.040, self.mode_pinch_btn)

        # OCTAVE Controller: [ - ] 4 [ + ]
        DirectLabel(
            parent=self.controls_strip,
            text="OCTAVE",
            pos=(-0.30, 0, 0.052),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectFrame(
            parent=self.controls_strip,
            pos=(-0.30, 0, -0.015),
            frameSize=(-0.10, 0.10, -0.038, 0.038),
            frameColor=(0.08, 0.10, 0.14, 1),
            relief=DGG.FLAT
        )

        DirectLabel(
            parent=self.controls_strip,
            text="<  4  >",
            pos=(-0.30, 0, -0.025),
            scale=0.030,
            text_fg=(0.85, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # SUSTAIN Switch: [ ON ] (Vibrant Pill Switch)
        DirectLabel(
            parent=self.controls_strip,
            text="SUSTAIN",
            pos=(-0.08, 0, 0.052),
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
            frameSize=(-0.09, 0.09, -0.038, 0.038),
            frameColor=(0.12, 0.72, 0.32, 1),
            relief=DGG.FLAT,
            command=self.toggle_sustain
        )
        self._register_target("action", "toggle_sustain", -0.08, 0.44 - 0.015 + 0.22, 0.09, 0.038, self.sustain_btn)

        # VOLUME Display / Knob with LED Bar
        DirectLabel(
            parent=self.controls_strip,
            text="VOLUME",
            pos=(0.14, 0, 0.052),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_strip_label = DirectLabel(
            parent=self.controls_strip,
            text="||||||||  80%",
            pos=(0.14, 0, -0.025),
            scale=0.024,
            text_fg=(0.20, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.08, 0.10, 0.14, 1),
            frameSize=(-0.10, 0.10, -0.035, 0.035)
        )

        # REVERB Display
        DirectLabel(
            parent=self.controls_strip,
            text="REVERB",
            pos=(0.38, 0, 0.052),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectLabel(
            parent=self.controls_strip,
            text="|||||  HALL",
            pos=(0.38, 0, -0.025),
            scale=0.024,
            text_fg=(0.75, 0.45, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0.08, 0.10, 0.14, 1),
            frameSize=(-0.10, 0.10, -0.035, 0.035)
        )

        # CURRENT NOTE Large Readout Box
        DirectLabel(
            parent=self.controls_strip,
            text="CURRENT NOTE",
            pos=(0.68, 0, 0.052),
            scale=0.020,
            text_fg=(0.55, 0.65, 0.75, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.current_note_frame = DirectFrame(
            parent=self.controls_strip,
            pos=(0.68, 0, -0.015),
            frameSize=(-0.12, 0.12, -0.040, 0.040),
            frameColor=(0.05, 0.08, 0.14, 1),
            relief=DGG.SUNKEN,
            borderWidth=(0.003, 0.003)
        )

        self.current_note_label = DirectLabel(
            parent=self.current_note_frame,
            text="C4",
            pos=(0, 0, -0.016),
            scale=0.045,
            text_fg=(0.20, 0.95, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # ── 3. Middle Hardware Synth Console (Wheels, LCD Display & Controls) ──
        self.rack_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, 0.20),
            frameSize=(-0.94, 0.94, -0.13, 0.13),
            frameColor=(0.06, 0.07, 0.09, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )
        self.rack_frame.setBin("fixed", 5)

        # Dual Pitch & Mod Wheels
        DirectFrame(
            parent=self.rack_frame,
            pos=(-0.84, 0, 0.01),
            frameSize=(-0.038, 0.038, -0.09, 0.09),
            frameColor=(0.14, 0.15, 0.18, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004)
        )
        DirectLabel(
            parent=self.rack_frame,
            text="PITCH",
            pos=(-0.84, 0, -0.11),
            scale=0.018,
            text_fg=(0.55, 0.60, 0.65, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        DirectFrame(
            parent=self.rack_frame,
            pos=(-0.73, 0, 0.01),
            frameSize=(-0.038, 0.038, -0.09, 0.09),
            frameColor=(0.14, 0.15, 0.18, 1.0),
            relief=DGG.RAISED,
            borderWidth=(0.004, 0.004)
        )
        DirectLabel(
            parent=self.rack_frame,
            text="MOD",
            pos=(-0.73, 0, -0.11),
            scale=0.018,
            text_fg=(0.55, 0.60, 0.65, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Patch Buttons Row Centered Directly Under LCD Screen
        patches = ["PIANO", "E.PIANO", "ORGAN", "STRINGS", "PAD", "SYNTH"]
        for p_idx, pname in enumerate(patches):
            p_col = (0.10, 0.45, 0.75, 1) if p_idx == 0 else (0.11, 0.13, 0.17, 1)
            p_fg = (1.0, 1.0, 1.0, 1) if p_idx == 0 else (0.65, 0.70, 0.78, 1)
            DirectButton(
                parent=self.rack_frame,
                text=pname,
                pos=(-0.205 + p_idx * 0.070, 0, -0.088),
                text_scale=0.016,
                text_fg=p_fg,
                frameSize=(-0.032, 0.032, -0.018, 0.018),
                frameColor=p_col,
                relief=DGG.FLAT
            )

        # Center Blue LCD Spectrum Waveform Screen
        self.lcd_screen = DirectFrame(
            parent=self.rack_frame,
            pos=(-0.03, 0, 0.01),
            frameSize=(-0.24, 0.24, -0.095, 0.095),
            frameColor=(0.01, 0.08, 0.16, 1.0),
            relief=DGG.SUNKEN,
            borderWidth=(0.004, 0.004)
        )

        # Audio Waveform Line Graphic
        self.vu_bars_text = DirectLabel(
            parent=self.lcd_screen,
            text="| | || ||| |||| ||||| |||| ||| || | |",
            pos=(0, 0, -0.015),
            scale=0.022,
            text_fg=(0.25, 0.85, 1.0, 0.9),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

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
                frameSize=(-0.045, 0.045, -0.045, 0.045),
                frameColor=(0.14, 0.16, 0.20, 1.0),
                relief=DGG.RAISED,
                borderWidth=(0.004, 0.004)
            )
            DirectLabel(
                parent=self.rack_frame,
                text=kname,
                pos=(kpos_x, 0, -0.045),
                scale=0.017,
                text_fg=(0.60, 0.65, 0.70, 1),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

        # Sound Control Quick Buttons
        DirectButton(
            parent=self.rack_frame,
            text="CHORUS",
            pos=(0.83, 0, 0.04),
            text_scale=0.017,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.040, 0.040, -0.020, 0.020),
            frameColor=(0.72, 0.40, 0.08, 1),
            relief=DGG.FLAT
        )
        DirectButton(
            parent=self.rack_frame,
            text="DELAY",
            pos=(0.83, 0, -0.02),
            text_scale=0.017,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.040, 0.040, -0.020, 0.020),
            frameColor=(0.12, 0.50, 0.85, 1),
            relief=DGG.FLAT
        )

    # ========================================================
    # MAIN REALISTIC PIANO KEYBOARD (Z-ORDER & VISIBILITY FIX)
    # ========================================================

    def _build_keyboard(self):

        # Main keybed tray recessed into synthesizer chassis
        self.keybed_frame = DirectFrame(
            parent=self.synth_body,
            pos=(0, 0, -0.34),
            frameSize=(-0.93, 0.93, -0.39, 0.39),
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
            pos=(0, 0, 0.375),
            frameSize=(-0.91, 0.91, -0.012, 0.012),
            frameColor=(0.75, 0.08, 0.12, 1.0)
        )

        start_x = -0.7875
        width = 0.225

        # ----------------------------------------------------
        # 1. WHITE KEYS (8 keys: C, D, E, F, G, A, B, C5)
        # High-quality ivory white keys, bin 20
        # ----------------------------------------------------
        for i, note in enumerate(self.WHITE):

            x = start_x + i * width
            z_pos = -0.02

            # Ivory White Key Body
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.108, 0.108, -0.365, 0.365),
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
                pos=(0, 0, -0.352),
                frameSize=(-0.104, 0.104, -0.010, 0.010),
                frameColor=(0.82, 0.80, 0.76, 1.0)
            )
            bevel.setBin("fixed", 21)

            # Note Label (Clear, high contrast, positioned near bottom)
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.260),
                scale=0.046,
                text_fg=(0.10, 0.12, 0.16, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 22)

            self.white_frames[note] = frame

            # World-space target coordinates for hand cursor hit testing
            world_z = -0.34 + z_pos + 0.22
            self._register_target("note", note, x, world_z, 0.108, 0.365, frame, is_black=False)

        # ----------------------------------------------------
        # 2. BLACK KEYS (5 keys: C#, D#, F#, G#, A#)
        # Ebony Black Keys, Bin 35 — GUARANTEED ON TOP OF WHITE KEYS
        # ----------------------------------------------------
        for note, after in self.BLACK:

            x = start_x + after * width + width / 2.0
            z_pos = 0.155

            # Drop-shadow beneath black key
            shadow = DirectFrame(
                parent=self.keybed_frame,
                pos=(x + 0.008, 0, z_pos - 0.010),
                frameSize=(-0.068, 0.068, -0.205, 0.205),
                frameColor=(0.0, 0.0, 0.0, 0.6)
            )
            shadow.setBin("fixed", 32)
            shadow.setDepthWrite(False)
            shadow.setDepthTest(False)

            # Ebony Black Key Body
            frame = DirectFrame(
                parent=self.keybed_frame,
                pos=(x, 0, z_pos),
                frameSize=(-0.065, 0.065, -0.200, 0.200),
                frameColor=(0.12, 0.12, 0.14, 1.0),
                relief=DGG.RAISED,
                borderWidth=(0.004, 0.004)
            )
            frame.setBin("fixed", 35)
            frame.setDepthWrite(False)
            frame.setDepthTest(False)

            # Top bevel highlight
            top_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, 0.185),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.32, 0.34, 0.38, 1.0)
            )
            top_bevel.setBin("fixed", 36)

            # Bottom highlight lip
            bot_bevel = DirectFrame(
                parent=frame,
                pos=(0, 0, -0.188),
                frameSize=(-0.058, 0.058, -0.008, 0.008),
                frameColor=(0.20, 0.22, 0.26, 1.0)
            )
            bot_bevel.setBin("fixed", 36)

            # Crisp Sharp Label
            lbl = DirectLabel(
                parent=frame,
                text=note,
                pos=(0, 0, -0.120),
                scale=0.034,
                text_fg=(0.82, 0.85, 0.90, 1.0),
                frameColor=(0, 0, 0, 0),
                relief=None
            )
            lbl.setBin("fixed", 37)

            self.black_frames[note] = frame

            world_z = -0.34 + z_pos + 0.22
            self._register_target("note", note, x, world_z, 0.065, 0.200, frame, is_black=True)

    # ========================================================
    # LEFT PANEL — CHORD STUDIO (VIBRANT WARM DOCK)
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

        # Header Title
        DirectLabel(
            parent=self.chord_dock,
            text="CHORD STUDIO",
            pos=(0, 0, 0.60),
            scale=0.038,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Sub-tabs: [ MAJOR ] (active) and [ MINOR ]
        self.tab_major = DirectButton(
            parent=self.chord_dock,
            text="MAJOR",
            pos=(-0.16, 0, 0.53),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.032, 0.032),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT
        )
        self.tab_minor = DirectButton(
            parent=self.chord_dock,
            text="MINOR",
            pos=(0.16, 0, 0.53),
            text_scale=0.024,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.032, 0.032),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT
        )

        # 7 Warm, Richly Colored Chord Buttons
        chord_list = [
            ("C MAJOR", "C - E - G"),
            ("G MAJOR", "G - B - D"),
            ("D MINOR", "D - F - A"),
            ("F MAJOR", "F - A - C"),
            ("A MINOR", "A - C - E"),
            ("E MINOR", "E - G - B"),
            ("B MAJOR", "B - D# - F#")
        ]

        start_z = 0.43
        step_z = 0.108

        for i, (name, notes_str) in enumerate(chord_list):
            z = start_z - i * step_z
            col = self.CHORD_COLORS.get(name, (0.15, 0.40, 0.65, 1))

            # Outer button frame
            btn = DirectButton(
                parent=self.chord_dock,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.046, 0.046),
                frameColor=col,
                relief=DGG.FLAT,
                command=lambda c=name: self.play_chord(c)
            )

            # Left chord name label
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

            # Sub-notes label
            DirectLabel(
                parent=btn,
                text=notes_str,
                pos=(-0.30, 0, -0.025),
                scale=0.020,
                text_fg=(0.85, 0.90, 0.95, 0.85),
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            # Right chevron icon >
            DirectLabel(
                parent=btn,
                text=">",
                pos=(0.28, 0, -0.012),
                scale=0.030,
                text_fg=(1.0, 1.0, 1.0, 0.8),
                text_align=TextNode.ACenter,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            self.chord_buttons[name] = btn

            world_z = -0.02 + z
            self._register_target("chord", name, -1.35, world_z, 0.33, 0.046, btn)

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

    # ========================================================
    # RIGHT PANEL — MUSIC STUDIO (TRACKS & RECORDER DOCK)
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

        # Header Title
        DirectLabel(
            parent=self.music_dock,
            text="MUSIC STUDIO",
            pos=(0, 0, 0.60),
            scale=0.038,
            text_fg=(0.95, 0.95, 0.98, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        # Sub-tabs: [ TRACKS ] (active) and [ CUSTOM ]
        self.tab_tracks = DirectButton(
            parent=self.music_dock,
            text="TRACKS",
            pos=(-0.16, 0, 0.53),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.14, 0.14, -0.032, 0.032),
            frameColor=(0.08, 0.52, 0.85, 1),
            relief=DGG.FLAT
        )
        self.tab_custom = DirectButton(
            parent=self.music_dock,
            text="CUSTOM",
            pos=(0.16, 0, 0.53),
            text_scale=0.024,
            text_fg=(0.60, 0.65, 0.72, 1),
            frameSize=(-0.14, 0.14, -0.032, 0.032),
            frameColor=(0.12, 0.14, 0.18, 1),
            relief=DGG.FLAT
        )

        # ── 8 Authentic Backing Tracks List ──
        track_start_z = 0.44
        track_step_z = 0.052

        for i, (tname, fname) in enumerate(self.TRACK_FILES):
            z = track_start_z - i * track_step_z
            is_active = (i == self.active_track_idx)

            bg_col = (0.10, 0.22, 0.35, 1.0) if is_active else (0.08, 0.09, 0.12, 1.0)
            fg_col = (0.25, 0.90, 1.0, 1.0) if is_active else (0.80, 0.85, 0.90, 1.0)

            tbtn = DirectButton(
                parent=self.music_dock,
                text="",
                pos=(0, 0, z),
                frameSize=(-0.33, 0.33, -0.023, 0.023),
                frameColor=bg_col,
                relief=DGG.FLAT,
                command=lambda idx=i: self.select_track(idx)
            )

            # Track name label
            tlbl = DirectLabel(
                parent=tbtn,
                text=tname,
                pos=(-0.30, 0, -0.008),
                scale=0.022,
                text_fg=fg_col,
                text_align=TextNode.ALeft,
                frameColor=(0, 0, 0, 0),
                relief=None
            )

            # Play triangle >
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

        # ── Transport Controls: PLAY, PAUSE, STOP ──
        self.track_play_btn = DirectButton(
            parent=self.music_dock,
            text="> PLAY",
            pos=(-0.22, 0, -0.04),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.10, 0.10, -0.035, 0.035),
            frameColor=(0.10, 0.60, 0.30, 1),
            relief=DGG.FLAT,
            command=self.play_track
        )

        self.track_pause_btn = DirectButton(
            parent=self.music_dock,
            text="|| PAUSE",
            pos=(0.0, 0, -0.04),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.10, 0.10, -0.035, 0.035),
            frameColor=(0.75, 0.52, 0.08, 1),
            relief=DGG.FLAT,
            command=self.pause_track
        )

        self.track_stop_btn = DirectButton(
            parent=self.music_dock,
            text="# STOP",
            pos=(0.22, 0, -0.04),
            text_scale=0.024,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.10, 0.10, -0.035, 0.035),
            frameColor=(0.75, 0.15, 0.18, 1),
            relief=DGG.FLAT,
            command=self.stop_track
        )

        self._register_target("action", "play_track", 1.35 - 0.22, -0.02 - 0.04, 0.10, 0.035, self.track_play_btn)
        self._register_target("action", "pause_track", 1.35, -0.02 - 0.04, 0.10, 0.035, self.track_pause_btn)
        self._register_target("action", "stop_track", 1.35 + 0.22, -0.02 - 0.04, 0.10, 0.035, self.track_stop_btn)

        # ── TRACK VOLUME Slider ──
        DirectLabel(
            parent=self.music_dock,
            text="TRACK VOLUME",
            pos=(-0.30, 0, -0.12),
            scale=0.020,
            text_fg=(0.60, 0.68, 0.75, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_down_btn = DirectButton(
            parent=self.music_dock,
            text="-",
            pos=(-0.25, 0, -0.17),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.028, 0.028),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_volume(-0.10)
        )

        self.vol_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||    ]  80%",
            pos=(0.02, 0, -0.175),
            scale=0.022,
            text_fg=(0.20, 0.85, 1.0, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.vol_up_btn = DirectButton(
            parent=self.music_dock,
            text="+",
            pos=(0.28, 0, -0.17),
            text_scale=0.028,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.05, 0.05, -0.028, 0.028),
            frameColor=(0.12, 0.16, 0.22, 1),
            relief=DGG.FLAT,
            command=lambda: self.adjust_volume(+0.10)
        )

        self._register_target("action", "vol_down", 1.35 - 0.25, -0.02 - 0.17, 0.05, 0.028, self.vol_down_btn)
        self._register_target("action", "vol_up", 1.35 + 0.28, -0.02 - 0.17, 0.05, 0.028, self.vol_up_btn)

        # ── RECORDING Studio Controls ──
        DirectLabel(
            parent=self.music_dock,
            text="* RECORDING",
            pos=(-0.30, 0, -0.25),
            scale=0.020,
            text_fg=(0.85, 0.35, 0.40, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.record_btn = DirectButton(
            parent=self.music_dock,
            text="* RECORD",
            pos=(-0.16, 0, -0.31),
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
            pos=(0.16, 0, -0.31),
            text_scale=0.026,
            text_fg=(0.80, 0.85, 0.90, 1),
            frameSize=(-0.14, 0.14, -0.038, 0.038),
            frameColor=(0.16, 0.18, 0.22, 1),
            relief=DGG.FLAT,
            command=self.stop_recording
        )

        self._register_target("action", "toggle_record", 1.35 - 0.16, -0.02 - 0.31, 0.14, 0.038, self.record_btn)
        self._register_target("action", "stop_record", 1.35 + 0.16, -0.02 - 0.31, 0.14, 0.038, self.rec_stop_btn)

        # Recording Status Timer & VU Meter
        self.rec_status_label = DirectLabel(
            parent=self.music_dock,
            text="00:00",
            pos=(-0.24, 0, -0.40),
            scale=0.028,
            text_fg=(0.80, 0.90, 0.95, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None
        )

        self.rec_vu_label = DirectLabel(
            parent=self.music_dock,
            text="[||||||||||||||||]",
            pos=(0.10, 0, -0.40),
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
            pos=(0, 0, -0.52),
            text_scale=0.026,
            text_fg=(1.0, 1.0, 1.0, 1),
            frameSize=(-0.33, 0.33, -0.042, 0.042),
            frameColor=(0.10, 0.42, 0.70, 1),
            relief=DGG.FLAT,
            command=self.save_and_export_recording
        )
        self._register_target("action", "save_record", 1.35, -0.02 - 0.52, 0.33, 0.042, self.save_rec_btn)

    # ========================================================
    # INTERACTIVE TARGET SYSTEM (HAND GESTURE HIT-TESTING)
    # ========================================================

    def _register_target(self, kind, ident, x, z, w, h, widget, is_black=False):
        """
        Unified registry ensuring hand pointers can interact with
        keys, chords, and studio controls.
        """
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
        Collision detection: returns (kind, ident) matching (x, z).
        Priority: Black keys first, then controls/chords, then white keys.
        """
        # 1. Black keys priority
        for reg in self.interactive_regions:
            if reg["kind"] == "note" and reg["black"]:
                if abs(x - reg["x"]) <= reg["w"] and abs(z - reg["z"]) <= reg["h"]:
                    return (reg["kind"], reg["ident"])

        # 2. Studio buttons, chords & controls
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

    def execute_target_action(self, kind, ident):
        """
        Executes the action corresponding to a selected target.
        """
        if kind == "note":
            self.play_note(ident)
        elif kind == "chord":
            self.play_chord(ident)
        elif kind == "progression":
            self.step_chord_progression()
        elif kind == "track":
            self.select_track(ident)
            self.play_track()
        elif kind == "action":
            if ident == "mode_air":
                self.set_play_mode("AIR_KEYBOARD")
            elif ident == "mode_pinch":
                self.set_play_mode("PINCH")
            elif ident == "toggle_sustain":
                self.toggle_sustain()
            elif ident == "play_track":
                self.play_track()
            elif ident == "pause_track":
                self.pause_track()
            elif ident == "stop_track":
                self.stop_track()
            elif ident == "vol_down":
                self.adjust_volume(-0.10)
            elif ident == "vol_up":
                self.adjust_volume(+0.10)
            elif ident == "toggle_record":
                self.toggle_recording()
            elif ident == "stop_record":
                self.stop_recording()
            elif ident == "save_record":
                self.save_and_export_recording()

    # ========================================================
    # SOUND, CHORD & SUSTAIN PLAYBACK
    # ========================================================

    def play_note(self, note):

        note_id = note.replace("#", "s")

        try:
            channel = self.sound_manager.play_piano(note_id)

            # Sustain behavior: If sustain is OFF, apply short damper cutoff
            if not self.sustain_on and channel is not None:
                channel.fadeout(260)

            now = time.monotonic()
            self.key_press_timers[note] = now
            self.vu_level = min(1.0, self.vu_level + 0.65)
            self.current_display_note = note

            self.current_note_label["text"] = note
            self.record_event("note", note)

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
        self.current_note_label["text"] = name[:5]

    def step_chord_progression(self):

        name = self.CHORD_PROGRESSION[self.progression_step]
        self.play_chord(name)

        self.progression_step = (self.progression_step + 1) % len(self.CHORD_PROGRESSION)
        next_name = self.CHORD_PROGRESSION[self.progression_step]
        self.prog_btn["text"] = f"> NEXT: {next_name[:5]}"

    def toggle_sustain(self):

        self.sustain_on = not self.sustain_on
        if self.sustain_on:
            self.sustain_btn["text"] = "ON"
            self.sustain_btn["frameColor"] = (0.12, 0.72, 0.32, 1)
        else:
            self.sustain_btn["text"] = "OFF"
            self.sustain_btn["frameColor"] = (0.35, 0.38, 0.42, 1)

    # ========================================================
    # BACKING TRACK ENGINE (8 REAL TRACKS)
    # ========================================================

    def _load_active_track(self):

        tname, fname = self.TRACK_FILES[self.active_track_idx]
        self.track_name = tname

        project_root = Path(__file__).resolve().parents[3]
        track_path = project_root / "assets" / fname

        if not track_path.exists():
            print("Backing track not found:", track_path)
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.track_sound = pygame.mixer.Sound(str(track_path))
        except Exception as error:
            print("Backing track load error:", error)

    def select_track(self, idx):

        if idx < 0 or idx >= len(self.TRACK_FILES):
            return

        was_playing = (self.track_channel is not None and not self.track_paused)
        self.stop_track()

        self.active_track_idx = idx
        self._load_active_track()

        # Update track buttons visual selection
        for i, (tbtn, tlbl) in enumerate(self.track_buttons):
            if i == idx:
                tbtn["frameColor"] = (0.10, 0.22, 0.35, 1.0)
                tlbl["text_fg"] = (0.25, 0.90, 1.0, 1.0)
            else:
                tbtn["frameColor"] = (0.08, 0.09, 0.12, 1.0)
                tlbl["text_fg"] = (0.80, 0.85, 0.90, 1.0)

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
                self.track_channel.set_volume(self.track_volume)
            self.track_paused = False
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

    def adjust_volume(self, delta):

        self.track_volume = max(0.0, min(1.0, self.track_volume + delta))
        if self.track_channel is not None:
            self.track_channel.set_volume(self.track_volume)
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

    def stop_recording(self):

        if not self.is_recording:
            return

        self.is_recording = False
        self.record_btn["text"] = "* RECORD"
        self.record_btn["frameColor"] = (0.75, 0.12, 0.15, 1)
        self.rec_status_label["text_fg"] = (0.35, 0.95, 0.65, 1)

    def save_and_export_recording(self):

        if not self.recorded_events:
            return

        duration = max(1.0, time.monotonic() - self.record_start_time if self.is_recording else 5.0)
        if self.is_recording:
            self.stop_recording()

        self.export_recording(duration)

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
                _, backing_file = self.TRACK_FILES[self.active_track_idx]
                backing_samples = get_wav_samples(backing_file)
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
        filename = f"holohand_studio_{timestamp_str}.wav"
        out_path = os.path.join(rec_dir, filename)

        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(master_int16.tobytes())

        print(f"Recorded performance exported to: {out_path}")
        self.save_rec_btn["text"] = "SAVED TO recordings/"
        return out_path

    # ========================================================
    # PLAY MODE & INPUT CONTROLS
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

        self.current_keys = [None, None]
        self.candidate_keys = [None, None]

    def toggle_play_mode(self):

        if self.play_mode == "AIR_KEYBOARD":
            self.set_play_mode("PINCH")
        else:
            self.set_play_mode("AIR_KEYBOARD")

    def toggle_gesture_input(self):

        self.gesture_input_enabled = not self.gesture_input_enabled
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]

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

    # ========================================================
    # HAND TRACKING & SCREEN COORDINATES
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

        # Crosshair center indicator
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
    # VISUAL ILLUMINATION & HIGHLIGHTING
    # ========================================================

    def reset_keys(self):

        now = time.monotonic()

        # White keys
        for note, frame in self.white_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = (0.35, 0.88, 1.0, 1.0)  # Brilliant Cyan pressed glow
            else:
                frame["frameColor"] = (0.97, 0.96, 0.93, 1.0)

        # Black keys
        for note, frame in self.black_frames.items():
            timer = self.key_press_timers.get(note, 0.0)
            if now - timer < 0.22:
                frame["frameColor"] = (1.0, 0.35, 0.85, 1.0)  # Neon Magenta pressed glow
            else:
                frame["frameColor"] = (0.12, 0.12, 0.14, 1.0)

        # Chord buttons reset to their original palette
        for name, btn in self.chord_buttons.items():
            col = self.CHORD_COLORS.get(name, (0.15, 0.40, 0.65, 1))
            btn["frameColor"] = col

    def highlight_target(self, target, hand_idx=0):

        if target is None:
            return

        kind, ident = target

        if kind == "chord":
            if ident in self.chord_buttons:
                self.chord_buttons[ident]["frameColor"] = (0.20, 0.75, 1.0, 1)
            chord_notes = self.CHORDS.get(ident, [])
            for note in chord_notes:
                self._apply_key_highlight(note, hand_idx)
            return

        if kind == "note":
            self._apply_key_highlight(ident, hand_idx)

    def _apply_key_highlight(self, name, hand_idx=0):

        if hand_idx == 0:
            white_col = (0.30, 0.95, 1.0, 1.0)  # Cyan Hover
            black_col = (0.65, 0.35, 0.95, 1.0)
        else:
            white_col = (1.0, 0.50, 0.88, 1.0)  # Magenta Hover
            black_col = (1.0, 0.25, 0.75, 1.0)

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
            return

        # Pre-process up to 2 hands (Left and Right sorted horizontally)
        processed_hands = []
        for hand in hands_list[:2]:
            lm = self.landmarks(hand)
            if lm is not None and len(lm) >= 21:
                processed_hands.append((hand, lm, lm[8].x))

        if len(processed_hands) == 2:
            processed_hands.sort(key=lambda item: item[2])

        hand_colors = [
            (0.0, 1.0, 1.0, 1.0),   # Hand 0: Electric Cyan
            (1.0, 0.3, 0.85, 1.0)   # Hand 1: Neon Magenta
        ]

        for h_idx, (hand, lm, _) in enumerate(processed_hands):
            # Index fingertip point
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
                                kind, ident = target
                                self.execute_target_action(kind, ident)
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
                                    kind, ident = active_target
                                    self.execute_target_action(kind, ident)
                                self.last_actions[h_idx] = now
                    elif ratio > self.pinch_off:
                        self.pinch_downs[h_idx] = False

    def _update_telemetry(self, now):

        # Decay VU level
        self.vu_level = max(0.0, self.vu_level - 0.04)
        bars_count = int(self.vu_level * 16)
        bars_str = "|" * bars_count + " " * (16 - bars_count)
        self.rec_vu_label["text"] = f"[{bars_str}]"

        # Update recording status timer
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
        self.current_keys = [None, None]
        self.candidate_keys = [None, None]
        self.pinch_downs = [False, False]

        # Force window clear color to matching deep dark background
        if hasattr(self.base, "win") and self.base.win:
            self.base.win.setClearColor(Vec4(0.02, 0.025, 0.035, 1.0))

        # Hotkeys
        self.base.accept("m", self.toggle_play_mode)
        self.base.accept("space", self.toggle_gesture_input)
        self.base.accept("r", self.toggle_recording)
        self.base.accept("t", self.play_track)
        self.base.accept("s", self.stop_track)
        self.base.accept("u", self.toggle_sustain)
        self.base.accept("=", lambda: self.adjust_volume(+0.10))
        self.base.accept("+", lambda: self.adjust_volume(+0.10))
        self.base.accept("-", lambda: self.adjust_volume(-0.10))
        self.base.accept("n", self.step_chord_progression)

        self.frame.show()
        self.pointer_root.show()

    def hide(self):

        self.active = False

        self.base.ignore("m")
        self.base.ignore("space")
        self.base.ignore("r")
        self.base.ignore("t")
        self.base.ignore("s")
        self.base.ignore("u")
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
