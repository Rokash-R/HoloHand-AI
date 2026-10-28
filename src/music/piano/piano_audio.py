import os
import pygame


class PianoAudio:

    def __init__(self):

        pygame.mixer.init()

        self.sounds = {}

        names = [
            "A4",
            "B4",
            "C4",
            "C5",
            "D4",
            "D5",
            "E4",
            "E5",
            "F4",
            "G4"
        ]

        src_folder = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        for name in names:

            path = os.path.join(
                src_folder,
                f"holohand_{name}.wav"
            )

            if os.path.exists(path):

                self.sounds[name] = pygame.mixer.Sound(
                    path
                )

    def play(self, note):

        if note in self.sounds:

            self.sounds[note].play()