
"""
HoloHand AI
Stage 1 - Holographic Hand Tracking + Cursor

Features:
- Smooths all 21 MediaPipe landmarks.
- Reduces visible hand shaking.
- Preserves responsive cursor movement.
- Keeps the hologram visible during brief tracking interruptions.
- Smoothly resumes tracking when the hand is detected again.
- Preserves holographic skeleton and glow effects.
- Compatible with HandModel(base), update(hand), cleanup().
"""

import math
import time

from panda3d.core import LineSegs, TransparencyAttrib


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

        self.root.setBin("fixed", 200)
        self.root.setDepthTest(False)
        self.root.setDepthWrite(False)

        self.root.setTransparency(
            TransparencyAttrib.MAlpha
        )

        self.drawing = None
        self.cursor_position = None
        self.is_tracking = False

        # Cursor smoothing.
        self.smoothing = 0.65

        # Smooth all 21 hand landmarks.
        self.smoothed_points = None
        self.landmark_smoothing = 0.35

        # Tracking-loss protection.
        # Keep the last hologram visible briefly if
        # MediaPipe temporarily loses the hand.
        self.last_seen_time = None
        self.tracking_grace_period = 0.45

        print("Holographic Hand Renderer: ONLINE")
        print("3D GLB renderer disabled")
        print("Index-finger cursor enabled")
        print("21 Landmark smoothing: ENABLED")
        print("Temporary tracking-loss protection: ENABLED")

    # ========================================================
    # LANDMARK HELPERS
    # ========================================================

    def get_landmarks(self, hand):

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

        if hasattr(landmark, "x"):
            return (
                float(landmark.x),
                float(landmark.y)
            )

        if isinstance(landmark, dict):
            return (
                float(landmark["x"]),
                float(landmark["y"])
            )

        return (
            float(landmark[0]),
            float(landmark[1])
        )

    # ========================================================
    # SCREEN COORDINATES
    # ========================================================

    def screen_position(self, landmark):

        x, y = self.get_xy(landmark)

        aspect = self.base.getAspectRatio()

        sx = (x - 0.5) * 2.0 * aspect
        sz = (0.5 - y) * 2.0

        return sx, sz

    # ========================================================
    # HOLOGRAPHIC CIRCLE
    # ========================================================

    def circle(
        self,
        lines,
        x,
        z,
        radius,
        color,
        thickness=2
    ):

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

    # ========================================================
    # HOLOGRAPHIC LINE
    # ========================================================

    def line(
        self,
        lines,
        start,
        end,
        color,
        thickness
    ):

        lines.setThickness(thickness)
        lines.setColor(*color)

        lines.moveTo(
            start[0], 0, start[1]
        )

        lines.drawTo(
            end[0], 0, end[1]
        )

    # ========================================================
    # LANDMARK SMOOTHING
    # ========================================================

    def smooth_landmarks(self, raw_points):

        if self.smoothed_points is None:
            self.smoothed_points = list(raw_points)
            return self.smoothed_points

        # Calculate wrist / palm movement speed to adapt smoothing
        wrist_movement = math.hypot(
            raw_points[0][0] - self.smoothed_points[0][0],
            raw_points[0][1] - self.smoothed_points[0][1]
        )

        # Dynamic landmark alpha: fast motion increases responsiveness (no lag/drag),
        # still posture provides calm stability
        if wrist_movement > 0.08:
            base_alpha = 0.88
        elif wrist_movement > 0.02:
            base_alpha = min(0.85, self.landmark_smoothing + wrist_movement * 4.0)
        else:
            base_alpha = self.landmark_smoothing

        smoothed = []
        for old_point, new_point in zip(
            self.smoothed_points,
            raw_points
        ):
            old_x, old_z = old_point
            new_x, new_z = new_point

            smooth_x = old_x + (new_x - old_x) * base_alpha
            smooth_z = old_z + (new_z - old_z) * base_alpha
            smoothed.append((smooth_x, smooth_z))

        self.smoothed_points = smoothed
        return self.smoothed_points

    # ========================================================
    # TRACKING LOSS HANDLER
    # ========================================================

    def handle_tracking_loss(self):

        self.is_tracking = False

        current_time = time.monotonic()

        # Keep the previous hologram temporarily.
        if self.last_seen_time is not None:

            elapsed = (
                current_time - self.last_seen_time
            )

            if elapsed <= self.tracking_grace_period:
                return

        # The hand has been missing for too long.
        self.remove_drawing()

        self.cursor_position = None
        self.smoothed_points = None
        self.last_seen_time = None

    # ========================================================
    # REMOVE PREVIOUS DRAWING
    # ========================================================

    def remove_drawing(self):

        if self.drawing is not None:

            self.drawing.removeNode()
            self.drawing = None

    # ========================================================
    # MAIN UPDATE
    # ========================================================

    def update(self, hand):

        landmarks = self.get_landmarks(hand)

        # Do not immediately remove the hologram when
        # MediaPipe briefly loses the hand.
        if landmarks is None or len(landmarks) < 21:

            self.handle_tracking_loss()
            return

        # -----------------------------------------
        # GET LANDMARK POSITIONS
        # -----------------------------------------

        try:

            raw_points = [
                self.screen_position(lm)
                for lm in landmarks[:21]
            ]

            # Smooth every landmark.
            # Previous positions are preserved during
            # short tracking interruptions.
            points = self.smooth_landmarks(
                raw_points
            )

        except (
            TypeError,
            ValueError,
            KeyError,
            IndexError
        ):

            self.handle_tracking_loss()
            return

        # A valid hand has been detected again.
        self.last_seen_time = time.monotonic()
        self.is_tracking = True

        # Remove the old drawing only after valid
        # replacement landmark data is available.
        self.remove_drawing()

        # -----------------------------------------
        # SMOOTH INDEX-FINGER CURSOR
        # -----------------------------------------

        target_x, target_z = points[8]

        if self.cursor_position is None:

            self.cursor_position = (
                target_x,
                target_z
            )

        else:

            old_x, old_z = self.cursor_position
            c_dist = math.hypot(target_x - old_x, target_z - old_z)
            if c_dist > 0.08:
                alpha = 0.95
            elif c_dist > 0.02:
                alpha = min(0.92, self.smoothing + c_dist * 2.0)
            else:
                alpha = self.smoothing

            self.cursor_position = (
                old_x + (target_x - old_x) * alpha,
                old_z + (target_z - old_z) * alpha
            )

        # -----------------------------------------
        # CREATE HOLOGRAPHIC DRAWING
        # -----------------------------------------

        lines = LineSegs("HoloHandLines")

        # Outer glow for skeleton connections (thicker & brighter)
        for a, b in self.CONNECTIONS:
            self.line(
                lines,
                points[a],
                points[b],
                (0.0, 0.7, 1.0, 0.35),
                8
            )

        # Bright skeleton lines
        for a, b in self.CONNECTIONS:
            self.line(
                lines,
                points[a],
                points[b],
                (0.1, 1.0, 1.0, 1.0),
                4
            )

        # Finger joint rings for all 21 landmarks
        for index, (x, z) in enumerate(points):
            if index in (4, 8, 12, 16, 20):
                radius = 0.024
                thickness = 3
                color = (0.4, 1.0, 1.0, 1.0)
            elif index == 0:
                radius = 0.022
                thickness = 3
                color = (0.2, 0.9, 1.0, 1.0)
            else:
                radius = 0.016
                thickness = 2
                color = (0.1, 0.95, 1.0, 0.95)
            self.circle(
                lines,
                x,
                z,
                radius,
                color,
                thickness
            )

        # -----------------------------------------
        # GLOWING CURSOR
        # -----------------------------------------

        cx, cz = self.cursor_position

        pulse = (
            math.sin(time.monotonic() * 5.0)
            + 1.0
        ) * 0.5

        # Outer animated glow.
        self.circle(
            lines,
            cx,
            cz,
            0.055 + pulse * 0.012,
            (0.0, 0.7, 1.0, 0.25),
            5
        )

        # Main cursor ring.
        self.circle(
            lines,
            cx,
            cz,
            0.038,
            (0.0, 1.0, 1.0, 1.0),
            3
        )

        # Inner ring.
        self.circle(
            lines,
            cx,
            cz,
            0.012,
            (1.0, 1.0, 1.0, 1.0),
            2
        )

        # Cursor crosshair.
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

        # -----------------------------------------
        # ATTACH GEOMETRY
        # -----------------------------------------

        self.drawing = self.root.attachNewNode(
            lines.create()
        )
        self.drawing.setBin("fixed", 200)

        self.drawing.setTransparency(
            TransparencyAttrib.MAlpha
        )

        self.drawing.setDepthTest(False)
        self.drawing.setDepthWrite(False)

    # ========================================================
    # SHOW / HIDE
    # ========================================================

    def show(self):

        self.root.show()

    def hide(self):

        self.root.hide()

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self):

        self.is_tracking = False

        self.cursor_position = None
        self.smoothed_points = None
        self.last_seen_time = None

        self.remove_drawing()

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self):

        self.clear()
        self.root.removeNode()
