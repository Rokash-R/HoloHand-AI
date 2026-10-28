
import os
import time

import cv2
import mediapipe as mp


class HandLandmarksWrapper:
    """Compatibility wrapper for MediaPipe landmarks."""

    def __init__(self, landmarks):
        self.landmark = landmarks

    def __iter__(self):
        return iter(self.landmark)

    def __getitem__(self, index):
        return self.landmark[index]

    def __len__(self):
        return len(self.landmark)


class HandTracker:

    def __init__(
        self,
        max_hands=2,
        detection_confidence=0.55,
        tracking_confidence=0.55
    ):

        self.max_hands = max_hands
        self.mode = None
        self.detector = None
        self.hands = None
        self.last_timestamp = 0

        model_path = self.get_model_path()

        # Preferred: MediaPipe Tasks VIDEO mode.
        if model_path is not None:

            try:
                options = mp.tasks.vision.HandLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=model_path
                    ),
                    running_mode=mp.tasks.vision.RunningMode.VIDEO,
                    num_hands=max_hands,
                    min_hand_detection_confidence=detection_confidence,
                    min_hand_presence_confidence=detection_confidence,
                    min_tracking_confidence=tracking_confidence
                )

                self.detector = (
                    mp.tasks.vision.HandLandmarker.create_from_options(
                        options
                    )
                )

                self.mode = "tasks"

                print("MediaPipe VIDEO tracking: READY")
                return

            except Exception as error:
                print("Tasks tracker error:", error)

        # Fallback for compatible older MediaPipe versions.
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):

            self.hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                model_complexity=1,
                min_detection_confidence=detection_confidence,
                min_tracking_confidence=tracking_confidence
            )

            self.mode = "legacy"
            print("MediaPipe legacy tracking: READY")
            return

        print("ERROR: No MediaPipe hand tracker available")

    def get_model_path(self):

        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".."
            )
        )

        model_path = os.path.join(
            project_root,
            "models",
            "hand_landmarker.task"
        )

        if os.path.isfile(model_path):
            return model_path

        print("Missing MediaPipe model:", model_path)
        return None

    def process(self, frame):

        if frame is None:
            return []

        try:
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            if self.mode == "tasks":

                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb
                )

                timestamp = max(
                    int(time.monotonic() * 1000),
                    self.last_timestamp + 1
                )

                self.last_timestamp = timestamp

                result = self.detector.detect_for_video(
                    image,
                    timestamp
                )

                if not result.hand_landmarks:
                    return []

                return [
                    HandLandmarksWrapper(landmarks)
                    for landmarks in result.hand_landmarks
                ]

            if self.mode == "legacy":

                rgb.flags.writeable = False

                result = self.hands.process(rgb)

                if result.multi_hand_landmarks:
                    return result.multi_hand_landmarks

        except Exception as error:
            print("Hand tracking error:", error)

        return []

    def close(self):

        if self.detector is not None:
            self.detector.close()

        if self.hands is not None:
            self.hands.close()
