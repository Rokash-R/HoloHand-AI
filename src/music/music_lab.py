class MusicLab:

    def __init__(self, piano, drums):

        self.piano = piano

        self.drums = drums

        self.active = False

    def update(self, mode, hand):

        if mode == "PIANO":

            self.piano.update(hand)

        elif mode == "DRUMS":

            self.drums.update(hand)