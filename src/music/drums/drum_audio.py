import os
import pygame


class DrumAudio:

    def __init__(self):

        self.sounds = {}

        pygame.mixer.init()

        src_folder = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        files = {
            "KICK": "holohand_kick.wav",
            "SNARE": "holohand_snare.wav",
            "HAT": "holohand_hat.wav",
            "TOM": "holohand_tom.wav"
        }

        for name, filename in files.items():

            path = os.path.join(
                src_folder,
                filename
            )

            if os.path.exists(path):

                self.sounds[name] = pygame.mixer.Sound(
                    path
                )

    def play(self, name):

        if name in self.sounds:

            self.sounds[name].play()