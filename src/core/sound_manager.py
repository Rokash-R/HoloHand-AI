import pygame
import math
import wave
import struct
import os
import random


class SoundManager:
    """
    Premium Polyphonic Audio Engine for HoloHand AI.

    Generates real piano harmonics (C4-C5 chromatic including sharps)
    and 6 authentic drum sounds (kick, snare, hi-hat, tom, crash, ride).
    All sounds are synthesized in-memory as WAV files and loaded via pygame.
    """

    def __init__(self):
        print("Starting Audio System...")

        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)  # Polyphonic: up to 32 simultaneous sounds
            self.audio_ready = True
            print("Audio system: READY (32 channels polyphonic)")
        except Exception as error:
            print("Audio ERROR:", error)
            self.audio_ready = False

        # Sound files go to src/ folder (same as before)
        self.sound_folder = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        self.piano_sounds = {}
        self.drum_sounds = {}

        if self.audio_ready:
            self._create_all_piano_sounds()
            self._create_all_drum_sounds()

        print("Audio files: READY")

    # ================================================================
    # PIANO SOUND SYNTHESIS
    # ================================================================

    def _piano_tone_samples(self, frequency, duration=1.6, sample_rate=44100):
        """
        Generates a realistic piano-like tone with multiple harmonics
        and a natural decay envelope. Returns raw PCM bytes (stereo 16-bit).
        """
        total_samples = int(sample_rate * duration)
        frames = []

        attack = 0.010  # 10ms attack
        attack_samples = int(attack * sample_rate)

        for i in range(total_samples):
            t = i / sample_rate

            # Multi-harmonic acoustic piano model
            fundamental = math.sin(2 * math.pi * frequency * t)
            h2 = 0.45 * math.sin(2 * math.pi * frequency * 2 * t)
            h3 = 0.22 * math.sin(2 * math.pi * frequency * 3 * t)
            h4 = 0.12 * math.sin(2 * math.pi * frequency * 4 * t)
            h5 = 0.05 * math.sin(2 * math.pi * frequency * 5 * t)

            value = fundamental + h2 + h3 + h4 + h5

            # Warm exponential decay envelope
            if i < attack_samples:
                env = i / attack_samples
            else:
                env = math.exp(-2.8 * (t - attack) / duration)

            sample = int(10500 * value * env)
            sample = max(-32767, min(32767, sample))
            frames.append(struct.pack("<hh", sample, sample))

        return b"".join(frames)

    def _write_wav(self, path, data, sample_rate=44100):
        with wave.open(path, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            f.writeframes(data)

    def _create_all_piano_sounds(self):
        """
        Full chromatic C4–C5 octave: 13 notes including sharps.
        """
        notes = {
            # White keys
            "C":  261.63,
            "D":  293.66,
            "E":  329.63,
            "F":  349.23,
            "G":  392.00,
            "A":  440.00,
            "B":  493.88,
            "C5": 523.25,
            # Black keys (sharps)
            "Cs": 277.18,   # C#4
            "Ds": 311.13,   # D#4
            "Fs": 369.99,   # F#4
            "Gs": 415.30,   # G#4
            "As": 466.16,   # A#4
        }

        for note, freq in notes.items():
            safe_name = note.replace("#", "s")
            filename = f"holohand_{safe_name}4.wav"
            path = os.path.join(self.sound_folder, filename)
            try:
                data = self._piano_tone_samples(freq, duration=0.9)
                self._write_wav(path, data)
                self.piano_sounds[note] = pygame.mixer.Sound(path)
                print(f"Created: {filename}")
            except Exception as e:
                print(f"Piano error: {filename} — {e}")

    # ================================================================
    # DRUM SOUND SYNTHESIS
    # ================================================================

    def _drum_samples(self, drum_type, sample_rate=44100):
        """
        Synthesizes realistic drum/percussion sounds. Returns PCM bytes.
        """
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
                # Pitched sine sweep downward (120Hz → 40Hz)
                freq = 120 - 80 * (t / duration)
                env = math.exp(-14 * t)
                punch_env = math.exp(-80 * t)  # Sharp initial punch
                value = math.sin(2 * math.pi * freq * t) * env
                value += 0.4 * math.sin(2 * math.pi * 60 * t) * punch_env

            elif drum_type == "snare":
                noise = random.uniform(-1, 1)
                env_noise = math.exp(-22 * t)
                tone = math.sin(2 * math.pi * 185 * t)
                env_tone = math.exp(-30 * t)
                value = 0.70 * noise * env_noise + 0.30 * tone * env_tone

            elif drum_type == "hat":
                # High-frequency noise with very fast decay
                noise = random.uniform(-1, 1)
                env = math.exp(-45 * t)
                # Band-pass simulation: mix two noise rates
                value = noise * env

            elif drum_type == "tom":
                # Floor tom: pitched mid-frequency sweep
                freq = 170 - 55 * (t / duration)
                env = math.exp(-11 * t)
                value = math.sin(2 * math.pi * freq * t) * env

            elif drum_type == "crash":
                # Crash cymbal: white noise + metallic shimmer
                noise = random.uniform(-1, 1)
                env = math.exp(-8 * t)
                shimmer = math.sin(2 * math.pi * 3200 * t) * 0.2
                value = (0.8 * noise + shimmer) * env

            elif drum_type == "ride":
                # Ride cymbal: more metallic, longer sustain
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
                self._write_wav(path, data)
                self.drum_sounds[drum] = pygame.mixer.Sound(path)
                print(f"Created: {filename}")
            except Exception as e:
                print(f"Drum error: {filename} — {e}")

    # ================================================================
    # PLAYBACK API
    # ================================================================

    def play_piano(self, note):
        """
        Plays a piano note. note can be: C, D, E, F, G, A, B, C5,
        Cs (C#), Ds (D#), Fs (F#), Gs (G#), As (A#).
        Returns the active pygame Channel object or None.
        """
        if not self.audio_ready:
            return None
        sound = self.piano_sounds.get(note)
        if sound:
            try:
                return sound.play()
            except Exception as e:
                print("Piano playback error:", e)
        return None

    def play_drum(self, drum):
        """
        Plays a drum sound. drum: kick | snare | hat | tom | crash | ride
        """
        if not self.audio_ready:
            return
        sound = self.drum_sounds.get(drum)
        if sound:
            try:
                sound.play()
            except Exception as e:
                print("Drum playback error:", e)

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