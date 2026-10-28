class Navigation:

    MENU = "HOME"
    MUSIC = "MUSIC"
    PIANO = "PIANO"
    DRUMS = "DRUMS"

    def __init__(self):

        self.mode = self.MENU

    def set_mode(self, mode):

        self.mode = mode

    def get_mode(self):

        return self.mode