# ============================================================
# HOLOHAND AI - PHASE 2
# Hand Tracking and 21 Landmark Detection
# ============================================================

import os
import sys
import cv2

# Import robust core tracker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.hand_tracker import HandTracker

# 21 Hand Connections
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]


class _ResultsWrapper:
    def __init__(self, hands):
        self.multi_hand_landmarks = hands


class handDetector:
    """Class that keeps all hand detection functions together."""

    def __init__(self):
        self.tracker = HandTracker(max_hands=2, detection_confidence=0.5, tracking_confidence=0.5)
        self.results = _ResultsWrapper([])

    def findHands(self, img, draw=True):
        hands = self.tracker.process(img)
        self.results = _ResultsWrapper(hands)

        if draw and hands:
            h, w, _ = img.shape
            for hand in hands:
                pts = []
                for lm in hand.landmark:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    pts.append((cx, cy))
                    cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

                for p1, p2 in HAND_CONNECTIONS:
                    if p1 < len(pts) and p2 < len(pts):
                        cv2.line(img, pts[p1], pts[p2], (0, 255, 0), 2)

        return img

    def findPosition(self, img):
        lmList = []
        if self.results and self.results.multi_hand_landmarks:
            myHand = self.results.multi_hand_landmarks[0]
            h, w, _ = img.shape
            for id, lm in enumerate(myHand.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])
                cv2.putText(
                    img,
                    str(id),
                    (cx, cy),
                    cv2.FONT_HERSHEY_PLAIN,
                    1,
                    (255, 0, 255),
                    1
                )
        return lmList