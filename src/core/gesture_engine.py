import math
from collections import deque


class GestureEngine:
    """
    Responsive 3D landmark gesture recognition for HoloHand AI.

    Recognizes:
      OPEN PALM
      CLOSED FIST
      ONE FINGER
      TWO FINGERS
      THREE FINGERS
      FOUR FINGERS
      PINCH
      UNKNOWN / TRANSITION

    Uses 3D joint angles and palm-relative measurements to
    reduce sensitivity to hand rotation.
    """

    def __init__(self, stable_frames=4):
        try:
            from .config import GESTURE_THRESHOLDS as config

            self.pinch_dist_ratio = config.get(
                "pinch_distance_ratio", 0.40
            )
            self.pinch_angle_deg = config.get(
                "pinch_angle_deg", 65
            )
            configured_window = config.get(
                "stability_window", stable_frames
            )
            self.stability_consensus = config.get(
                "stability_consensus", 0.50
            )

        except Exception:
            self.pinch_dist_ratio = 0.40
            self.pinch_angle_deg = 65
            configured_window = stable_frames
            self.stability_consensus = 0.50

        # Prevent a configuration file from restoring a very slow window.
        self.stable_frames = max(
            3,
            min(5, int(configured_window)),
        )

        self.history = deque(maxlen=self.stable_frames)

        self.current_gesture = "UNKNOWN"
        self.raw_gesture = "UNKNOWN"
        self.confidence = 0.0

    @staticmethod
    def _xyz(point):
        return (
            float(point.x),
            float(point.y),
            float(getattr(point, "z", 0.0)),
        )

    @classmethod
    def _dist_3d(cls, a, b):
        ax, ay, az = cls._xyz(a)
        bx, by, bz = cls._xyz(b)

        return math.sqrt(
            (ax - bx) ** 2
            + (ay - by) ** 2
            + (az - bz) ** 2
        )

    @classmethod
    def _joint_angle(cls, point_a, point_b, point_c):
        """
        Angle at point_b between point_a -> point_b
        and point_c -> point_b.
        """

        ax, ay, az = cls._xyz(point_a)
        bx, by, bz = cls._xyz(point_b)
        cx, cy, cz = cls._xyz(point_c)

        v1 = (ax - bx, ay - by, az - bz)
        v2 = (cx - bx, cy - by, cz - bz)

        len1 = math.sqrt(sum(value * value for value in v1))
        len2 = math.sqrt(sum(value * value for value in v2))

        if len1 < 1e-6 or len2 < 1e-6:
            return 0.0

        dot = sum(v1[i] * v2[i] for i in range(3))
        cosine = max(-1.0, min(1.0, dot / (len1 * len2)))

        return math.degrees(math.acos(cosine))

    def _is_finger_extended(
        self,
        landmarks,
        tip_idx,
        pip_idx,
        mcp_idx,
        palm_scale,
    ):
        """
        Determine extension primarily from the PIP joint angle
        and finger length, rather than the hand's direction
        relative to the wrist.
        """

        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        mcp = landmarks[mcp_idx]

        angle = self._joint_angle(mcp, pip, tip)

        tip_to_mcp = self._dist_3d(tip, mcp)
        pip_to_mcp = self._dist_3d(pip, mcp)

        if pip_to_mcp < 1e-6:
            return False

        length_ratio = tip_to_mcp / pip_to_mcp

        # A straight finger generally has a near-180-degree PIP angle.
        # The length ratio helps reject curled fingers.
        return (
            angle >= 125.0
            and length_ratio >= 1.05
            and tip_to_mcp > palm_scale * 0.38
        )

    def _is_thumb_extended(self, landmarks, palm_scale):
        thumb_angle = self._joint_angle(
            landmarks[2],
            landmarks[3],
            landmarks[4],
        )

        distance_from_index = self._dist_3d(
            landmarks[4],
            landmarks[5],
        )

        distance_from_pinky = self._dist_3d(
            landmarks[4],
            landmarks[17],
        )

        return (
            thumb_angle >= 125.0
            and max(distance_from_index, distance_from_pinky)
            > palm_scale * 0.55
        )

    def _is_pinch(self, landmarks, palm_scale):
        """
        Detect thumb-index contact before checking for a fist.
        """

        distance_ratio = (
            self._dist_3d(landmarks[4], landmarks[8])
            / max(palm_scale, 1e-6)
        )

        thumb_direction = (
            self._xyz(landmarks[4])[0] - self._xyz(landmarks[2])[0],
            self._xyz(landmarks[4])[1] - self._xyz(landmarks[2])[1],
            self._xyz(landmarks[4])[2] - self._xyz(landmarks[2])[2],
        )

        index_direction = (
            self._xyz(landmarks[8])[0] - self._xyz(landmarks[5])[0],
            self._xyz(landmarks[8])[1] - self._xyz(landmarks[5])[1],
            self._xyz(landmarks[8])[2] - self._xyz(landmarks[5])[2],
        )

        dot = sum(
            thumb_direction[i] * index_direction[i]
            for i in range(3)
        )

        len_thumb = math.sqrt(
            sum(value * value for value in thumb_direction)
        )
        len_index = math.sqrt(
            sum(value * value for value in index_direction)
        )

        denominator = len_thumb * len_index

        if denominator < 1e-8:
            return distance_ratio < 0.28

        cosine = max(
            -1.0,
            min(1.0, dot / denominator),
        )

        angle = math.degrees(math.acos(cosine))

        return (
            distance_ratio < 0.28
            or (
                distance_ratio < self.pinch_dist_ratio
                and angle < self.pinch_angle_deg
            )
        )

    def detect_raw(self, hand):
        """Classify the current hand pose."""

        if hand is None:
            return "UNKNOWN"

        landmarks = getattr(hand, "landmark", hand)

        if landmarks is None or len(landmarks) < 21:
            return "UNKNOWN"

        wrist = landmarks[0]
        middle_mcp = landmarks[9]

        palm_scale = self._dist_3d(wrist, middle_mcp)

        if palm_scale < 0.015:
            return "UNKNOWN"

        # PINCH must be checked before CLOSED FIST.
        if self._is_pinch(landmarks, palm_scale):
            return "PINCH"

        index_up = self._is_finger_extended(
            landmarks, 8, 6, 5, palm_scale
        )
        middle_up = self._is_finger_extended(
            landmarks, 12, 10, 9, palm_scale
        )
        ring_up = self._is_finger_extended(
            landmarks, 16, 14, 13, palm_scale
        )
        pinky_up = self._is_finger_extended(
            landmarks, 20, 18, 17, palm_scale
        )

        thumb_up = self._is_thumb_extended(
            landmarks, palm_scale
        )

        count = sum(
            (index_up, middle_up, ring_up, pinky_up)
        )

        if count == 0:
            return "CLOSED FIST"

        if count == 4:
            return "OPEN PALM" if thumb_up else "FOUR FINGERS"

        if (
            index_up
            and middle_up
            and not ring_up
            and not pinky_up
        ):
            return "TWO FINGERS"

        if (
            index_up
            and middle_up
            and ring_up
            and not pinky_up
        ):
            return "THREE FINGERS"

        if (
            index_up
            and not middle_up
            and not ring_up
            and not pinky_up
        ):
            return "ONE FINGER"

        return "UNKNOWN"

    def update(self, hand):
        """
        Update temporal gesture stability.

        Uses a shorter history for faster response while still
        requiring repeated detections before changing gestures.
        """

        raw = self.detect_raw(hand)
        self.raw_gesture = raw
        self.history.append(raw)

        if not self.history:
            self.confidence = 0.0
            return self.current_gesture

        counts = {}

        for gesture in self.history:
            counts[gesture] = counts.get(gesture, 0) + 1

        most_frequent = max(
            counts,
            key=counts.get,
        )

        frequency = counts[most_frequent]
        self.confidence = frequency / len(self.history)

        required = max(
            2,
            math.ceil(
                self.stable_frames
                * self.stability_consensus
            ),
        )

        if frequency >= required:
            self.current_gesture = most_frequent

        elif self.current_gesture == "UNKNOWN":
            self.current_gesture = "TRANSITION"

        return self.current_gesture

    def reset(self):
        """Clear gesture history when tracking is lost."""

        self.history.clear()
        self.current_gesture = "UNKNOWN"
        self.raw_gesture = "UNKNOWN"
        self.confidence = 0.0

    def get_status(self):
        return {
            "current": self.current_gesture,
            "raw": self.raw_gesture,
            "confidence": self.confidence,
            "stable": self.confidence >= self.stability_consensus,
        }