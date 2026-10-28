import math
from collections import deque


class GestureEngine:
    """
    Robust 3D Landmark Geometry Gesture Recognition Engine for HoloHand AI.
    Recognizes milestone hand states:
      1. OPEN PALM
      2. CLOSED FIST
      3. ONE FINGER
      4. TWO FINGERS
      5. THREE FINGERS
      6. FOUR FINGERS
      7. PINCH
      8. UNKNOWN / TRANSITION
    Uses orientation-independent 3D joint angles, normalized palm-scale ratios,
    and multi-frame temporal debouncing.
    """

    def __init__(self, stable_frames=7):
        # Load configurable thresholds (if available)
        try:
            from .config import GESTURE_THRESHOLDS as _cfg
            # Override defaults with config values
            self.pinch_dist_ratio = _cfg.get("pinch_distance_ratio", 0.28)
            self.pinch_angle_deg = _cfg.get("pinch_angle_deg", 30)
            self.stability_window = _cfg.get("stability_window", stable_frames)
            self.stability_consensus = _cfg.get("stability_consensus", 0.70)
            self.cooldown_seconds = _cfg.get("cooldown_seconds", 1.5)
        except Exception:
            # Fallback defaults
            self.pinch_dist_ratio = 0.28
            self.pinch_angle_deg = 30
            self.stability_window = stable_frames
            self.stability_consensus = 0.70
            self.cooldown_seconds = 1.5
        # Use stability window for history length
        self.stable_frames = max(3, self.stability_window)
        self.history = deque(maxlen=self.stable_frames)
        self.current_gesture = "UNKNOWN"
        self.raw_gesture = "UNKNOWN"
        self.confidence = 0.0

    @staticmethod
    def _dist_3d(a, b):
        """Calculates 3D Euclidean distance between two landmarks."""
        dx = a.x - b.x
        dy = a.y - b.y
        dz = getattr(a, 'z', 0.0) - getattr(b, 'z', 0.0)
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def _joint_angle(p_a, p_b, p_c):
        """Calculates 3D angle (in degrees) at vertex p_b between vectors BA and BC."""
        v1 = (p_a.x - p_b.x, p_a.y - p_b.y, getattr(p_a, 'z', 0.0) - getattr(p_b, 'z', 0.0))
        v2 = (p_c.x - p_b.x, p_c.y - p_b.y, getattr(p_c, 'z', 0.0) - getattr(p_b, 'z', 0.0))

        len1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
        len2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)

        if len1 < 1e-5 or len2 < 1e-5:
            return 180.0

        dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
        cos_val = max(-1.0, min(1.0, dot / (len1 * len2)))
        return math.degrees(math.acos(cos_val))

    def _is_finger_extended(self, lm, tip_idx, pip_idx, mcp_idx, wrist_idx, palm_center, palm_scale):
        """
        Determines if a finger (index, middle, ring, pinky) is extended or curled.
        Orientation-invariant: evaluates distance to wrist/palm center and angle at PIP joint.
        """
        p_tip = lm[tip_idx]
        p_pip = lm[pip_idx]
        p_mcp = lm[mcp_idx]
        p_wrist = lm[wrist_idx]

        dist_tip_wrist = self._dist_3d(p_tip, p_wrist)
        dist_pip_wrist = self._dist_3d(p_pip, p_wrist)
        dist_tip_center = self._dist_3d(p_tip, palm_center)

        angle = self._joint_angle(p_mcp, p_pip, p_tip)

        # Extended: tip is farther from wrist than PIP joint, straight angle, and tip not tucked in palm
        is_straight = (dist_tip_wrist > dist_pip_wrist * 1.04) and (angle > 120.0)
        is_curled = (dist_tip_wrist < dist_pip_wrist * 1.02) or (dist_tip_center < palm_scale * 0.68) or (angle < 112.0)

        if is_straight and not is_curled:
            return True
        return False

    def _is_thumb_extended(self, lm, palm_scale):
        """Evaluates whether the thumb is extended away from the palm or curled/tucked."""
        p_tip = lm[4]
        p_mcp = lm[2]
        p_index_mcp = lm[5]
        p_pinky_mcp = lm[17]

        dist_tip_index = self._dist_3d(p_tip, p_index_mcp)
        dist_tip_pinky = self._dist_3d(p_tip, p_pinky_mcp)

        angle_thumb = self._joint_angle(p_mcp, lm[3], p_tip)

        # When thumb is extended outward away from the hand:
        if dist_tip_index > palm_scale * 0.52 and angle_thumb > 125.0:
            return True
        return False

    def detect_raw(self, hand):
        """Classifies the instant raw pose of the given hand landmark set."""
        if hand is None or not hasattr(hand, 'landmark') or len(hand.landmark) < 21:
            return "UNKNOWN"

        lm = hand.landmark

        # Palm scale reference (wrist lm[0] to middle knuckle lm[9])
        p_wrist = lm[0]
        p_mid_mcp = lm[9]
        palm_scale = self._dist_3d(p_wrist, p_mid_mcp)
        if palm_scale < 0.02:
            palm_scale = 0.18

        # Approximate palm center
        center_x = (lm[0].x + lm[5].x + lm[9].x + lm[13].x + lm[17].x) * 0.2
        center_y = (lm[0].y + lm[5].y + lm[9].y + lm[13].y + lm[17].y) * 0.2
        center_z = (getattr(lm[0], 'z', 0.0) + getattr(lm[5], 'z', 0.0) + getattr(lm[9], 'z', 0.0) +
                    getattr(lm[13], 'z', 0.0) + getattr(lm[17], 'z', 0.0)) * 0.2

        class Point3D:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z

        palm_center = Point3D(center_x, center_y, center_z)

        # 1. Check 4 main fingers
        index_up = self._is_finger_extended(lm, 8, 6, 5, 0, palm_center, palm_scale)
        middle_up = self._is_finger_extended(lm, 12, 10, 9, 0, palm_center, palm_scale)
        ring_up = self._is_finger_extended(lm, 16, 14, 13, 0, palm_center, palm_scale)
        pinky_up = self._is_finger_extended(lm, 20, 18, 17, 0, palm_center, palm_scale)
        thumb_up = self._is_thumb_extended(lm, palm_scale)

        four_count = sum([index_up, middle_up, ring_up, pinky_up])

        # 2. CLOSED FIST: All 4 fingers curled
        if four_count == 0:
            return "CLOSED FIST"

        # 3. PINCH: Thumb tip to Index tip proximity (while not in a fist)
        pinch_dist = self._dist_3d(lm[4], lm[8]) / palm_scale
        thumb_dir = (lm[4].x - lm[2].x, lm[4].y - lm[2].y, getattr(lm[4], 'z', 0.0) - getattr(lm[2], 'z', 0.0))
        index_dir = (lm[8].x - lm[5].x, lm[8].y - lm[5].y, getattr(lm[8], 'z', 0.0) - getattr(lm[5], 'z', 0.0))
        dot = thumb_dir[0] * index_dir[0] + thumb_dir[1] * index_dir[1] + thumb_dir[2] * index_dir[2]
        len_thumb = math.sqrt(thumb_dir[0]**2 + thumb_dir[1]**2 + thumb_dir[2]**2)
        len_index = math.sqrt(index_dir[0]**2 + index_dir[1]**2 + index_dir[2]**2)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / (len_thumb * len_index + 1e-9)))))
        if pinch_dist < self.pinch_dist_ratio and angle < self.pinch_angle_deg:
            return "PINCH"

        # 4. OPEN PALM / FOUR FINGERS
        if four_count >= 4:
            if thumb_up:
                return "OPEN PALM"
            return "FOUR FINGERS"

        # 5. TWO FINGERS: Index and Middle up ("V" / Peace gesture); Ring and Pinky curled
        if index_up and middle_up and not ring_up and not pinky_up:
            return "TWO FINGERS"

        # 6. THREE FINGERS: Index, Middle, Ring up; Pinky curled
        if index_up and middle_up and ring_up and not pinky_up:
            return "THREE FINGERS"

        # 7. ONE FINGER: Index up; Middle, Ring, Pinky curled
        if index_up and not middle_up and not ring_up and not pinky_up:
            return "ONE FINGER"

        return "UNKNOWN"

    def update(self, hand):
        """
        Processes the hand, updates the multi-frame debouncing buffer,
        and returns the stable confirmed gesture.
        """
        raw = self.detect_raw(hand)
        self.raw_gesture = raw
        self.history.append(raw)

        # Count frequencies in recent window
        counts = {}
        for g in self.history:
            counts[g] = counts.get(g, 0) + 1

        most_frequent = max(counts, key=counts.get)
        freq = counts[most_frequent]
        self.confidence = freq / float(len(self.history))

        # Require at least 70% consensus to switch gesture
        required_consensus = max(2, int(self.stable_frames * 0.70))
        if freq >= required_consensus:
            self.current_gesture = most_frequent
        elif self.current_gesture == "UNKNOWN":
            self.current_gesture = "TRANSITION"

        return self.current_gesture

    def get_status(self):
        """Returns structured gesture telemetry."""
        return {
            "current": self.current_gesture,
            "raw": self.raw_gesture,
            "confidence": self.confidence,
            "stable": self.confidence >= 0.75
        }