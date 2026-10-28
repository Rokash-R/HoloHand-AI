from direct.gui.DirectGui import DirectLabel


class Hologram:

    def __init__(self, base):

        self.base = base

        self.status = DirectLabel(
            text="HOLO CORE",
            scale=0.055,
            text_fg=(0.1, 1, 1, 1),
            pos=(-1.45, 0, 0.75)
        )

    def set_status(self, text):

        self.status["text"] = text

    def destroy(self):

        self.status.destroy()