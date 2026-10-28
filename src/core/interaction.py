

class Interaction:

    def __init__(self):

        self.index_x = 0.0
        self.index_y = 0.0
        self.index_z = 0.0

    def update(self, hand):

        if hand is None:
            return

        point = hand.landmark[8]

        self.index_x = point.x
        self.index_y = point.y
        self.index_z = point.z

    def get_position(self):

        return (
            self.index_x,
            self.index_y,
            self.index_z
        )