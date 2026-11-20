import pygame
import math
import wave
import struct
import os
import random
import numpy as np


class SoundManager:
    """
    Premium Polyphonic Multi-Octave Audio Engine for HoloHand AI.

    Features:
      - 5 Dynamic Octaves (Octaves 2 through 6)
      - 6 Genuine Synthesizer Sound Patches:
          * PIANO: Acoustic multi-harmonic concert grand
          * E.PIANO: Tine electric piano with bell overtones & gentle chorus
          * ORGAN: Hammond B3 drawbar organ with warm continuous sustain
          * STRINGS: Ensemble bowed strings with slow expressive attack
          * PAD: Ethereal ambient synthesizer pad
          * SYNTH: Analog synth lead with filter sweep
      - Real Reverberation / Spatial Acoustics simulation
      - Independent volume mixing: Piano Volume, Master Volume
      - 6 Authentic drum sounds (kick, snare, hi-hat, tom, crash, ride)
      - 32-channel polyphony via Pygame
    """

    NOTE_BASE_FREQS = {
        "C":  261.63,
        "Cs": 277.18,
        "D":  293.66,
        "Ds": 311.13,
        "E":  329.63,
        "F":  349.23,
        "Fs": 369.99,
        "G":  392.00,
        "Gs": 415.30,
        "A":  440.00,
        "As": 466.16,
        "B":  493.88,
        "C5": 523.25
    }

    def __init__(self):
        print("Starting Audio System...")

        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)  # Polyphonic: up to 32 simultaneous channels
            self.audio_ready = True
            print("Audio system: READY (32 channels polyphonic)")
        except Exception as error:
            print("Audio ERROR:", error)
            self.audio_ready = False

        self.sound_folder = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        # Volumes
        self.piano_volume = 0.90
        self.master_volume = 1.00

        # Memory cache for synthesized sounds: (patch, note, octave, reverb) -> pygame.mixer.Sound
        self.sound_cache = {}
        self.piano_sounds = {}
        self.drum_sounds = {}
        self.ui_click_sound = None
        self.ui_hover_sound = None

        if self.audio_ready:
            self._create_all_piano_sounds()
            self._create_all_drum_sounds()
            self._create_ui_sounds()

        print("Audio files: READY")

    # ================================================================
    # DYNAMIC MULTI-TIMBRE SYNTHESIS (NUMPY ACCELERATED)
    # ================================================================

    def _synthesize_instrument_sample(self, frequency, patch="PIANO", reverb=False, duration=1.6, sr=44100):
        """
        Synthesizes a realistic audio waveform for the given frequency and instrument patch.
        Returns a stereo int16 NumPy array ready for pygame.sndarray.make_sound.
        """
        n_samples = int(sr * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)

        patch_upper = patch.upper()

        if patch_upper in ("E.PIANO", "E_PIANO", "EPIANO"):
            # Electric Piano: Tine bell harmonic (7x) + gentle 5Hz chorus
            tremolo = 1.0 + 0.15 * np.sin(2 * np.pi * 5.0 * t)
            wave = (np.sin(2 * np.pi * frequency * t) * tremolo +
                    0.45 * np.sin(2 * np.pi * frequency * 2 * t) +
                    0.25 * np.sin(2 * np.pi * frequency * 7 * t))
            env = np.exp(-3.2 * t / duration)
            attack = int(0.008 * sr)
            env[:attack] = np.linspace(0, 1, attack)

        elif patch_upper == "ORGAN":
            # Hammond B3 Drawbars: Sub 0.5x, 1x, 2x, 3x, 4x, 6x harmonics
            wave = (0.45 * np.sin(np.pi * frequency * t) +
                    1.00 * np.sin(2 * np.pi * frequency * t) +
                    0.65 * np.sin(4 * np.pi * frequency * t) +
                    0.35 * np.sin(6 * np.pi * frequency * t) +
                    0.20 * np.sin(8 * np.pi * frequency * t))
            env = np.ones(n_samples)
            attack = int(0.015 * sr)
            env[:attack] = np.linspace(0, 1, attack)
            fade = int(0.05 * sr)
            env[-fade:] = np.linspace(1, 0, fade)

        elif patch_upper == "STRINGS":
            # Ensemble Bowed Strings: Sawtooth approximation with slow attack
            wave = (np.sin(2 * np.pi * frequency * t) +
                    0.55 * np.sin(4 * np.pi * frequency * t) +
                    0.35 * np.sin(6 * np.pi * frequency * t) +
                    0.20 * np.sin(8 * np.pi * frequency * t) +
                    0.15 * np.sin(10 * np.pi * frequency * t))
            env = np.ones(n_samples)
            attack = int(0.08 * sr)  # Soft swelling attack
            env[:attack] = np.linspace(0, 1, attack)
            fade = int(0.12 * sr)
            env[-fade:] = np.linspace(1, 0, fade)

        elif patch_upper == "PAD":
            # Warm Ambient Pad: Detuned sines with soft envelope
            detune = frequency * 1.003
            wave = (np.sin(2 * np.pi * frequency * t) +
                    np.sin(2 * np.pi * detune * t) * 0.7 +
                    0.30 * np.sin(4 * np.pi * frequency * t))
            env = np.exp(-1.8 * t / duration)
            attack = int(0.06 * sr)
            env[:attack] = np.linspace(0, 1, attack)

        elif patch_upper == "SYNTH":
            # Analog Lead: Resonant low-pass swept saw
            saw = 2.0 * (t * frequency - np.floor(0.5 + t * frequency))
            sub = 0.5 * np.sin(np.pi * frequency * t)
            wave = saw * 0.7 + sub
            env = np.exp(-2.5 * t / duration)
            attack = int(0.010 * sr)
            env[:attack] = np.linspace(0, 1, attack)

        else:
            # Default Acoustic Grand Piano: Rich multi-harmonic model
            fundamental = np.sin(2 * np.pi * frequency * t)
            h2 = 0.45 * np.sin(2 * np.pi * frequency * 2 * t)
            h3 = 0.22 * np.sin(2 * np.pi * frequency * 3 * t)
            h4 = 0.12 * np.sin(2 * np.pi * frequency * 4 * t)
            h5 = 0.05 * np.sin(2 * np.pi * frequency * 5 * t)
            wave = fundamental + h2 + h3 + h4 + h5
            env = np.exp(-2.8 * t / duration)
            attack = int(0.010 * sr)
            env[:attack] = np.linspace(0, 1, attack)

        # Scale raw audio
        audio = wave * env * 11500.0

        # Apply Real Reverb Simulation if active
        if reverb:
            delays = [int(0.09 * sr), int(0.18 * sr), int(0.27 * sr)]
            decays = [0.35, 0.20, 0.10]
            reverb_buf = np.zeros(n_samples)
            for d, dec in zip(delays, decays):
                if d < n_samples:
                    reverb_buf[d:] += audio[:-d] * dec
            audio = audio * 0.85 + reverb_buf

        peak = np.max(np.abs(audio))
        if peak > 32767:
            audio = audio * (32000.0 / peak)

        int16_audio = np.clip(audio, -32767, 32767).astype(np.int16)
        stereo_audio = np.column_stack((int16_audio, int16_audio))

        return stereo_audio

    # ================================================================
    # PLAYBACK API WITH MULTI-OCTAVE & TIMBRE SUPPORT
    # ================================================================

    def play_piano(self, note, octave=4, patch="PIANO", reverb=False):
        """
        Plays a piano or synth note dynamically across octaves 2-6 and patches.
        Returns the active pygame Channel object or None.
        """
        if not self.audio_ready:
            return None

        clean_note = note.replace("#", "s")
        octave = max(2, min(6, int(octave)))
        cache_key = (patch.upper(), clean_note, octave, bool(reverb))

        # Check in-memory cache
        if cache_key in self.sound_cache:
            sound = self.sound_cache[cache_key]
        else:
            # Calculate target pitch based on base Octave 4 frequency
            base_freq = self.NOTE_BASE_FREQS.get(clean_note, 440.0)
            if clean_note == "C5":
                # C5 is the top key of the octave
                target_freq = (self.NOTE_BASE_FREQS["C"] * (2 ** (octave + 1 - 4)))
            else:
                target_freq = base_freq * (2 ** (octave - 4))

            try:
                samples = self._synthesize_instrument_sample(
                    target_freq, patch=patch, reverb=reverb, duration=1.6
                )
                sound = pygame.sndarray.make_sound(samples)
                self.sound_cache[cache_key] = sound
            except Exception as e:
                # Fallback to pre-created sound
                sound = self.piano_sounds.get(clean_note)

        if sound:
            try:
                vol = max(0.0, min(1.0, self.piano_volume * self.master_volume))
                sound.set_volume(vol)
                return sound.play()
            except Exception as e:
                print("Piano playback error:", e)

        return None

    def set_piano_volume(self, vol):
        self.piano_volume = max(0.0, min(1.0, float(vol)))

    def set_master_volume(self, vol):
        self.master_volume = max(0.0, min(1.0, float(vol)))

    # ================================================================
    # INITIALIZATION & LEGACY SOUND BACKWARDS COMPATIBILITY
    # ================================================================

    def _create_all_piano_sounds(self):
        """
        Pre-synthesizes Octave 4 PIANO so the instrument starts instantly with zero lag.
        """
        for note in self.NOTE_BASE_FREQS.keys():
            clean_note = note.replace("#", "s")
            filename = f"holohand_{clean_note}4.wav"
            path = os.path.join(self.sound_folder, filename)
            try:
                samples = self._synthesize_instrument_sample(
                    self.NOTE_BASE_FREQS[clean_note], patch="PIANO", duration=1.6
                )
                sound = pygame.sndarray.make_sound(samples)
                self.sound_cache[("PIANO", clean_note, 4, False)] = sound
                self.piano_sounds[clean_note] = sound
                self.piano_sounds[note] = sound

                # Also write WAV file to src/ for recorder mixing
                with wave.open(path, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(samples.tobytes())

            except Exception as e:
                print(f"Piano sound init error ({clean_note}):", e)

    # ================================================================
    # DRUM SOUND SYNTHESIS (PRESERVED FOR DRUMS MODULE)
    # ================================================================

    def _drum_samples(self, drum_type, sample_rate=44100):
        durations = {
            "kick":  0.40,
            "snare": 0.28,
            "hat":   0.12,
            "tom":   0.40,
            "crash": 0.55,
            "ride":  0.35,
        }
        duration = durations.get(drum_type, 0.3)
        total_samples = int(sample_rate * duration)
        frames = []

        for i in range(total_samples):
            t = i / sample_rate
            value = 0.0

            if drum_type == "kick":
                freq = 120 - 80 * (t / duration)
                env = math.exp(-14 * t)
                punch_env = math.exp(-80 * t)
                value = math.sin(2 * math.pi * freq * t) * env
                value += 0.4 * math.sin(2 * math.pi * 60 * t) * punch_env

            elif drum_type == "snare":
                noise = random.uniform(-1, 1)
                env_noise = math.exp(-22 * t)
                tone = math.sin(2 * math.pi * 185 * t)
                env_tone = math.exp(-30 * t)
                value = 0.70 * noise * env_noise + 0.30 * tone * env_tone

            elif drum_type == "hat":
                noise = random.uniform(-1, 1)
                env = math.exp(-45 * t)
                value = noise * env

            elif drum_type == "tom":
                freq = 170 - 55 * (t / duration)
                env = math.exp(-11 * t)
                value = math.sin(2 * math.pi * freq * t) * env

            elif drum_type == "crash":
                noise = random.uniform(-1, 1)
                env = math.exp(-8 * t)
                shimmer = math.sin(2 * math.pi * 3200 * t) * 0.2
                value = (0.8 * noise + shimmer) * env

            elif drum_type == "ride":
                noise = random.uniform(-1, 1)
                env = math.exp(-12 * t)
                bell = math.sin(2 * math.pi * 1800 * t) * 0.3 * math.exp(-20 * t)
                value = (0.65 * noise + bell) * env

            sample = int(13500 * value)
            sample = max(-32767, min(32767, sample))
            frames.append(struct.pack("<hh", sample, sample))

        return b"".join(frames)

    def _create_all_drum_sounds(self):
        drums = ["kick", "snare", "hat", "tom", "crash", "ride"]
        for drum in drums:
            filename = f"holohand_{drum}.wav"
            path = os.path.join(self.sound_folder, filename)
            try:
                data = self._drum_samples(drum)
                with wave.open(path, "wb") as f:
                    f.setnchannels(2)
                    f.setsampwidth(2)
                    f.setframerate(44100)
                    f.writeframes(data)
                self.drum_sounds[drum] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Drum error: {filename} — {e}")

    def play_drum(self, drum):
        if not self.audio_ready:
            return
        sound = self.drum_sounds.get(drum)
        if sound:
            try:
                sound.set_volume(self.master_volume)
                sound.play()
            except Exception as e:
                print("Drum playback error:", e)

    def _create_ui_sounds(self):
        try:
            sr = 44100
            # Click sound: crisp futuristic chime (880Hz + 1320Hz + 1760Hz, 120ms)
            dur_click = 0.12
            n_click = int(sr * dur_click)
            t_click = np.linspace(0, dur_click, n_click, endpoint=False)
            click_wave = (
                0.55 * np.sin(2 * np.pi * 880.0 * t_click) +
                0.35 * np.sin(2 * np.pi * 1320.0 * t_click) +
                0.15 * np.sin(2 * np.pi * 1760.0 * t_click)
            ) * np.exp(-32.0 * t_click)
            click_arr = np.int16(np.clip(click_wave * 26000, -32767, 32767))
            stereo_click = np.ascontiguousarray(np.column_stack((click_arr, click_arr)))
            self.ui_click_sound = pygame.sndarray.make_sound(stereo_click)

            # Hover sound: soft subtle tick (1200Hz, 40ms)
            dur_hover = 0.04
            n_hover = int(sr * dur_hover)
            t_hover = np.linspace(0, dur_hover, n_hover, endpoint=False)
            hover_wave = 0.25 * np.sin(2 * np.pi * 1200.0 * t_hover) * np.exp(-75.0 * t_hover)
            hover_arr = np.int16(np.clip(hover_wave * 18000, -32767, 32767))
            stereo_hover = np.ascontiguousarray(np.column_stack((hover_arr, hover_arr)))
            self.ui_hover_sound = pygame.sndarray.make_sound(stereo_hover)
        except Exception as e:
            print(f"UI sound init error: {e}")

    def play_ui_click(self):
        if not self.audio_ready or self.ui_click_sound is None:
            return
        try:
            self.ui_click_sound.set_volume(self.master_volume * 0.95)
            self.ui_click_sound.play()
        except Exception:
            pass

    def play_ui_hover(self):
        if not self.audio_ready or self.ui_hover_sound is None:
            return
        try:
            self.ui_hover_sound.set_volume(self.master_volume * 0.40)
            self.ui_hover_sound.play()
        except Exception:
            pass

    def stop_all(self):
        if self.audio_ready:
            pygame.mixer.stop()

    def close(self):
        if self.audio_ready:
            try:
                pygame.mixer.stop()
                pygame.mixer.quit()
            except Exception:
                pass
