
"""
HoloHand AI
Stage 1 - Holographic Hand Tracking + Cursor

Uses MediaPipe landmarks instead of a 3D GLB model.
Compatible with HandModel(self), update(hand), cleanup().
"""

import math
import time

from panda3d.core import LineSegs, NodePath, TransparencyAttrib


class HandModel:

    # MediaPipe hand skeleton connections
    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17)
    ]

    def __init__(self, base):

        self.base = base

        # Render in 2D over the interface.
        self.root = base.aspect2d.attachNewNode(
            "HoloHandOverlay"
        )

        self.root.setBin("fixed", 100)
        self.root.setDepthTest(False)
        self.root.setDepthWrite(False)
        self.root.setTransparency(
            TransparencyAttrib.MAlpha
        )

        self.drawing = None
        self.cursor_position = None
        self.is_tracking = False

        self.smoothing = 0.65

        print("Holographic Hand Renderer: ONLINE")
        print("3D GLB renderer disabled")
        print("Index-finger cursor enabled")

    def get_landmarks(self, hand):
        """Read landmarks from supported tracker formats."""

        if hand is None:
            return None

        if hasattr(hand, "landmark"):
            return hand.landmark

        if hasattr(hand, "landmarks"):
            return hand.landmarks

        if isinstance(hand, dict):
            return hand.get(
                "landmarks",
                hand.get("landmark")
            )

        if isinstance(hand, (list, tuple)):
            return hand

        return None

    def get_xy(self, landmark):
        """Get normalized x/y coordinates."""

        if hasattr(landmark, "x"):
            return float(landmark.x), float(landmark.y)

        if isinstance(landmark, dict):
            return (
                float(landmark["x"]),
                float(landmark["y"])
            )

        return float(landmark[0]), float(landmark[1])

    def screen_position(self, landmark):
        """Convert camera coordinates to Panda3D screen coordinates."""

        x, y = self.get_xy(landmark)

        aspect = self.base.getAspectRatio()

        # Map [0, 1] camera sensor coordinates to Panda3D aspect2d space [-aspect, +aspect]
        sx = (x - 0.5) * 2.0 * aspect
        sz = (0.5 - y) * 2.0

        return sx, sz

    def circle(
        self,
        lines,
        x,
        z,
        radius,
        color,
        thickness=2
    ):
        """Draw a circular holographic ring."""

        lines.setThickness(thickness)
        lines.setColor(*color)

        segments = 20

        for i in range(segments + 1):

            angle = (
                2.0 * math.pi * i / segments
            )

            px = x + math.cos(angle) * radius
            pz = z + math.sin(angle) * radius

            if i == 0:
                lines.moveTo(px, 0, pz)
            else:
                lines.drawTo(px, 0, pz)

    def line(
        self,
        lines,
        start,
        end,
        color,
        thickness
    ):
        """Draw a connection between two landmarks."""

        lines.setThickness(thickness)
        lines.setColor(*color)

        lines.moveTo(start[0], 0, start[1])
        lines.drawTo(end[0], 0, end[1])

    def update(self, hand):

        landmarks = self.get_landmarks(hand)

        # Remove old drawing.
        if self.drawing is not None:
            self.drawing.removeNode()
            self.drawing = None

        if landmarks is None or len(landmarks) < 21:
            self.is_tracking = False
            self.cursor_position = None
            return

        try:
            points = [
                self.screen_position(lm)
                for lm in landmarks[:21]
            ]
        except (TypeError, ValueError, KeyError, IndexError):
            self.is_tracking = False
            self.cursor_position = None
            return

        self.is_tracking = True

        # -----------------------------------
        # SMOOTH INDEX-FINGER CURSOR
        # -----------------------------------

        target_x, target_z = points[8]

        if self.cursor_position is None:
            self.cursor_position = (
                target_x,
                target_z
            )
        else:
            old_x, old_z = self.cursor_position

            alpha = self.smoothing

            self.cursor_position = (
                old_x + (target_x - old_x) * alpha,
                old_z + (target_z - old_z) * alpha
            )

        # -----------------------------------
        # CREATE HOLOGRAPHIC DRAWING
        # -----------------------------------

        lines = LineSegs("HoloHandLines")

        # Outer glow for skeleton connections
        for a, b in self.CONNECTIONS:
            self.line(
                lines,
                points[a],
                points[b],
                (0.0, 0.7, 1.0, 0.18),
                8
            )

        # Bright skeleton lines
        for a, b in self.CONNECTIONS:
            self.line(
                lines,
                points[a],
                points[b],
                (0.0, 0.95, 1.0, 0.95),
                2
            )

        # Finger joint rings
        for index, (x, z) in enumerate(points):

            radius = 0.013

            if index in (4, 8, 12, 16, 20):
                radius = 0.019

            self.circle(
                lines,
                x,
                z,
                radius,
                (0.2, 0.95, 1.0, 0.9),
                2
            )

        # -----------------------------------
        # GLOWING CURSOR
        # -----------------------------------

        cx, cz = self.cursor_position

        pulse = (
            math.sin(time.monotonic() * 5.0)
            + 1.0
        ) * 0.5

        # Outer animated glow
        self.circle(
            lines,
            cx,
            cz,
            0.055 + pulse * 0.012,
            (0.0, 0.7, 1.0, 0.25),
            5
        )

        # Main cursor ring
        self.circle(
            lines,
            cx,
            cz,
            0.038,
            (0.0, 1.0, 1.0, 1.0),
            3
        )

        # Inner ring
        self.circle(
            lines,
            cx,
            cz,
            0.012,
            (1.0, 1.0, 1.0, 1.0),
            2
        )

        # Cursor crosshair
        self.line(
            lines,
            (cx - 0.018, cz),
            (cx + 0.018, cz),
            (1.0, 1.0, 1.0, 0.8),
            1
        )

        self.line(
            lines,
            (cx, cz - 0.018),
            (cx, cz + 0.018),
            (1.0, 1.0, 1.0, 0.8),
            1
        )

        # Attach geometry to 2D interface.
        self.drawing = self.root.attachNewNode(
            lines.create()
        )

        self.drawing.setTransparency(
            TransparencyAttrib.MAlpha
        )

        self.drawing.setDepthTest(False)
        self.drawing.setDepthWrite(False)

    def show(self):
        self.root.show()

    def hide(self):
        self.root.hide()

    def clear(self):
        self.is_tracking = False
        self.cursor_position = None

        if self.drawing is not None:
            self.drawing.removeNode()
            self.drawing = None

    def cleanup(self):
        self.clear()
        self.root.removeNode()
