from panda3d.core import AmbientLight
from direct.interval.IntervalGlobal import Sequence
from direct.interval.IntervalGlobal import LerpColorScaleInterval
from direct.interval.IntervalGlobal import Func


class HandEffects:

    def __init__(self, base):

        self.base = base

        light = AmbientLight(
            "HoloAmbient"
        )

        light.setColor(
            (0.15, 0.35, 0.6, 1)
        )

        self.light_node = (
            base.render.attachNewNode(light)
        )

        base.render.setLight(
            self.light_node
        )

    def pulse(self, node):

        if node is None:
            return

        Sequence(
            LerpColorScaleInterval(
                node,
                0.15,
                (0.3, 1.5, 2.0, 1)
            ),
            LerpColorScaleInterval(
                node,
                0.25,
                (1, 1, 1, 1)
            )
        ).start()