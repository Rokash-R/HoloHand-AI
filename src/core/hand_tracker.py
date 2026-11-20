import os
import time

import cv2
import numpy as np
import mediapipe as mp


class HandLandmarksWrapper:
    """Expose MediaPipe landmarks in a legacy-compatible format."""

    def __init__(self, landmarks):
        self.landmark = landmarks

    def __iter__(self):
        return iter(self.landmark)

    def __getitem__(self, index):
        return self.landmark[index]

    def __len__(self):
        return len(self.landmark)


class HandTracker:
    """
    Responsive MediaPipe VIDEO hand tracker for HoloHand AI.

    - Supports up to two hands.
    - Uses temporal tracking between frames.
    - Applies lightweight brightness correction in dark conditions.
    - Never returns stale landmarks.
    - Supports MediaPipe Tasks and legacy MediaPipe.
    """

    def __init__(
        self,
        max_hands=2,
        detection_confidence=0.35,
        tracking_confidence=0.35,
        presence_confidence=0.35,
    ):
        self.max_hands = max_hands
        self.mode = None
        self.detector = None
        self.hands = None

        self._detection_confidence = detection_confidence
        self._tracking_confidence = tracking_confidence
        self._presence_confidence = presence_confidence
        self._consecutive_errors = 0

        self._last_timestamp_ms = -1
        self._last_error_time = 0.0

        self._gamma_lut = self._build_gamma_lut(1.35)

        model_path = self.get_model_path()

        # Preferred: MediaPipe Tasks VIDEO mode.
        if model_path and hasattr(mp, "tasks"):
            try:
                options = mp.tasks.vision.HandLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=model_path
                    ),
                    running_mode=mp.tasks.vision.RunningMode.VIDEO,
                    num_hands=max_hands,
                    min_hand_detection_confidence=detection_confidence,
                    min_hand_presence_confidence=presence_confidence,
                    min_tracking_confidence=tracking_confidence,
                )

                self.detector = (
                    mp.tasks.vision.HandLandmarker.create_from_options(
                        options
                    )
                )

                self.mode = "tasks_video"
                print("MediaPipe Tasks VIDEO tracking: READY")
                return

            except Exception as error:
                print("MediaPipe Tasks initialization failed:", error)

        # Fallback: legacy MediaPipe VIDEO mode.
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
            try:
                self.hands = mp.solutions.hands.Hands(
                    static_image_mode=False,
                    max_num_hands=max_hands,
                    model_complexity=1,
                    min_detection_confidence=detection_confidence,
                    min_tracking_confidence=tracking_confidence,
                )

                self.mode = "legacy"
                print("MediaPipe legacy VIDEO tracking: READY")
                return

            except Exception as error:
                print("MediaPipe legacy initialization failed:", error)

        raise RuntimeError(
            "No usable MediaPipe hand tracker. "
            "Check MediaPipe installation and "
            "models/hand_landmarker.task."
        )

    @staticmethod
    def _build_gamma_lut(gamma):
        inverse_gamma = 1.0 / gamma
        return np.array(
            [
                ((value / 255.0) ** inverse_gamma) * 255
                for value in range(256)
            ],
            dtype=np.uint8,
        )

    def get_model_path(self):
        """Locate the hand_landmarker.task model."""

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        model_path = os.path.join(
            project_root,
            "models",
            "hand_landmarker.task",
        )

        if os.path.isfile(model_path):
            return model_path

        print("Missing MediaPipe model:", model_path)
        return None

    def _reinit_detector(self):
        """Self-healing re-initialization if MediaPipe Tasks encounters fatal errors."""
        try:
            if self.detector is not None:
                self.detector.close()
        except Exception:
            pass
        self.detector = None
        self._last_timestamp_ms = -1
        model_path = self.get_model_path()
        if model_path and hasattr(mp, "tasks"):
            try:
                options = mp.tasks.vision.HandLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=model_path
                    ),
                    running_mode=mp.tasks.vision.RunningMode.VIDEO,
                    num_hands=self.max_hands,
                    min_hand_detection_confidence=self._detection_confidence,
                    min_hand_presence_confidence=self._presence_confidence,
                    min_tracking_confidence=self._tracking_confidence,
                )
                self.detector = mp.tasks.vision.HandLandmarker.create_from_options(options)
                self.mode = "tasks_video"
                print("[HandTracker] Auto-recovery: MediaPipe Tasks restored.")
            except Exception as e:
                print("[HandTracker] Auto-recovery failed:", e)

    def _prepare_frame(self, frame):
        """
        Correct very dark frames without unnecessarily processing
        normally illuminated frames.
        """

        brightness = float(np.mean(frame))

        if brightness < 85:
            return cv2.LUT(frame, self._gamma_lut)

        return frame

    def process(self, frame):
        """
        Process one camera frame.

        Returns only landmarks detected in the current frame.
        Returns [] if no hand is detected.
        """

        if frame is None or not isinstance(frame, np.ndarray):
            return []

        if frame.size == 0:
            return []

        try:
            processed_frame = self._prepare_frame(frame)

            rgb = cv2.cvtColor(
                processed_frame,
                cv2.COLOR_BGR2RGB,
            )

            rgb = np.ascontiguousarray(rgb)

            if self.mode == "tasks_video":
                # Ensure monotonically increasing timestamp in milliseconds
                timestamp_ms = int(time.monotonic() * 1000)
                if timestamp_ms <= self._last_timestamp_ms:
                    timestamp_ms = self._last_timestamp_ms + 1
                self._last_timestamp_ms = timestamp_ms

                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb,
                )
                result = self.detector.detect_for_video(image, timestamp_ms)
                detected = result.hand_landmarks or []
                return [
                    HandLandmarksWrapper(landmarks)
                    for landmarks in detected
                ]
            
            if self.mode == "legacy":
                rgb.flags.writeable = False

                result = self.hands.process(rgb)
                detected = result.multi_hand_landmarks or []

                return [
                    HandLandmarksWrapper(hand.landmark)
                    for hand in detected
                ]

            self._consecutive_errors = 0

        except Exception as error:
            self._consecutive_errors += 1
            # Avoid flooding the terminal if a frame repeatedly fails.
            now = time.monotonic()

            if now - self._last_error_time > 2.0:
                print("Hand tracking error:", error)
                self._last_error_time = now

            if self._consecutive_errors >= 6 and self.mode == "tasks_video":
                self._consecutive_errors = 0
                self._reinit_detector()

        # Never return landmarks from an older frame.
        return []

    def close(self):
        """Release MediaPipe resources."""

        if self.detector is not None:
            self.detector.close()
            self.detector = None

        if self.hands is not None:
            self.hands.close()
            self.hands = None

        self.mode = None
        print("Hand tracker closed.")