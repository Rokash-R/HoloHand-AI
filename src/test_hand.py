import sys
import os
import cv2

# Ensure src directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.hand_tracker import HandTracker

# MediaPipe 21 hand connections
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]

tracker = HandTracker(max_hands=2, detection_confidence=0.5, tracking_confidence=0.5)
camera = cv2.VideoCapture(0)

print("Hand Detection Diagnostic Test Started")
print("Press 'q' to stop")

while True:
    success, frame = camera.read()
    if not success or frame is None:
        print("Camera frame read failed")
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    hands = tracker.process(frame)

    if hands:
        for hand in hands:
            pts = []
            for lm in hand.landmark:
                cx, cy = int(lm.x * w), int(lm.y * h)
                pts.append((cx, cy))
                cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)

            for p1_idx, p2_idx in HAND_CONNECTIONS:
                if p1_idx < len(pts) and p2_idx < len(pts):
                    cv2.line(frame, pts[p1_idx], pts[p2_idx], (0, 255, 0), 2)

        cv2.putText(frame, f"Hands: {len(hands)}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Hands: 0 (Searching)", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("HoloHand Diagnostic View", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
tracker.close()
cv2.destroyAllWindows()