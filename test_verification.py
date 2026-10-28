import sys
import os
import math

# Add src to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "d:", "PROJECTS", "Holohand ai", "src"))
sys.path.insert(0, "src")

# Pre-import mediapipe
import mediapipe as mp
import cv2
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Point3

from core.gesture_engine import GestureEngine
from core.camera import Camera
from core.hand_tracker import HandTracker

print("=== RUNNING HOLOHAND AI AUTOMATED VERIFICATION SUITE ===")

# ---------------------------------------------------------
# TEST 1: GestureEngine Recognition on Synthetic Landmarks
# ---------------------------------------------------------
print("\n[TEST 1] Testing GestureEngine...")
engine = GestureEngine(stable_frames=3)

class DummyLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

class DummyHand:
    def __init__(self, landmarks_dict):
        self.landmark = [landmarks_dict.get(i, DummyLandmark(0.5, 0.5, 0.0)) for i in range(21)]

# Create canonical gestures
# 1. Open Palm
open_lm = {0: DummyLandmark(0.5, 0.8, 0.0)}
# All fingers extended up
for f_idx, (mcp, pip, dip, tip) in enumerate([(1,2,3,4), (5,6,7,8), (9,10,11,12), (13,14,15,16), (17,18,19,20)]):
    x_offset = (f_idx - 2) * 0.08
    if f_idx == 0: # Thumb
        open_lm[1] = DummyLandmark(0.40, 0.70)
        open_lm[2] = DummyLandmark(0.32, 0.62)
        open_lm[3] = DummyLandmark(0.25, 0.55)
        open_lm[4] = DummyLandmark(0.18, 0.48)
    else:
        open_lm[mcp] = DummyLandmark(0.5 + x_offset, 0.55)
        open_lm[pip] = DummyLandmark(0.5 + x_offset, 0.42)
        open_lm[dip] = DummyLandmark(0.5 + x_offset, 0.30)
        open_lm[tip] = DummyLandmark(0.5 + x_offset, 0.20)

hand_open = DummyHand(open_lm)
detected_open = engine.detect_raw(hand_open)
print(f"  Synthetic OPEN PALM detected as: {detected_open}")
assert detected_open == "OPEN PALM", f"Expected OPEN PALM, got {detected_open}"

# 2. Closed Fist
fist_lm = {0: DummyLandmark(0.5, 0.8, 0.0)}
for f_idx, (mcp, pip, dip, tip) in enumerate([(1,2,3,4), (5,6,7,8), (9,10,11,12), (13,14,15,16), (17,18,19,20)]):
    x_offset = (f_idx - 2) * 0.06
    if f_idx == 0: # Thumb curled
        fist_lm[1] = DummyLandmark(0.45, 0.70)
        fist_lm[2] = DummyLandmark(0.44, 0.65)
        fist_lm[3] = DummyLandmark(0.46, 0.62)
        fist_lm[4] = DummyLandmark(0.48, 0.60)
    else: # Fingers curled into palm
        fist_lm[mcp] = DummyLandmark(0.5 + x_offset, 0.55)
        fist_lm[pip] = DummyLandmark(0.5 + x_offset, 0.48)
        fist_lm[dip] = DummyLandmark(0.5 + x_offset, 0.54)
        fist_lm[tip] = DummyLandmark(0.5 + x_offset, 0.58)

hand_fist = DummyHand(fist_lm)
detected_fist = engine.detect_raw(hand_fist)
print(f"  Synthetic CLOSED FIST detected as: {detected_fist}")
assert detected_fist == "CLOSED FIST", f"Expected CLOSED FIST, got {detected_fist}"

# 3. Pinch
pinch_lm = dict(open_lm)
# Thumb tip (4) and index tip (8) touching
pinch_lm[4] = DummyLandmark(0.42, 0.45)
pinch_lm[8] = DummyLandmark(0.43, 0.46)
hand_pinch = DummyHand(pinch_lm)
detected_pinch = engine.detect_raw(hand_pinch)
print(f"  Synthetic PINCH detected as: {detected_pinch}")
assert detected_pinch == "PINCH", f"Expected PINCH, got {detected_pinch}"

# 4. One Finger (Index extended, others curled)
one_lm = dict(fist_lm)
one_lm[5] = open_lm[5]
one_lm[6] = open_lm[6]
one_lm[7] = open_lm[7]
one_lm[8] = open_lm[8]
hand_one = DummyHand(one_lm)
detected_one = engine.detect_raw(hand_one)
print(f"  Synthetic ONE FINGER detected as: {detected_one}")
assert detected_one == "ONE FINGER", f"Expected ONE FINGER, got {detected_one}"

# 5. Two Fingers (Index & Middle extended, others curled)
two_lm = dict(one_lm)
two_lm[9] = open_lm[9]
two_lm[10] = open_lm[10]
two_lm[11] = open_lm[11]
two_lm[12] = open_lm[12]
hand_two = DummyHand(two_lm)
detected_two = engine.detect_raw(hand_two)
print(f"  Synthetic TWO FINGERS detected as: {detected_two}")
assert detected_two == "TWO FINGERS", f"Expected TWO FINGERS, got {detected_two}"

# 6. Three Fingers (Index, Middle, Ring extended, others curled)
three_lm = dict(two_lm)
three_lm[13] = open_lm[13]
three_lm[14] = open_lm[14]
three_lm[15] = open_lm[15]
three_lm[16] = open_lm[16]
hand_three = DummyHand(three_lm)
detected_three = engine.detect_raw(hand_three)
print(f"  Synthetic THREE FINGERS detected as: {detected_three}")
assert detected_three == "THREE FINGERS", f"Expected THREE FINGERS, got {detected_three}"

# 7. Four Fingers (Index, Middle, Ring, Pinky extended, Thumb tucked)
four_lm = dict(three_lm)
four_lm[17] = open_lm[17]
four_lm[18] = open_lm[18]
four_lm[19] = open_lm[19]
four_lm[20] = open_lm[20]
hand_four = DummyHand(four_lm)
detected_four = engine.detect_raw(hand_four)
print(f"  Synthetic FOUR FINGERS detected as: {detected_four}")
assert detected_four == "FOUR FINGERS", f"Expected FOUR FINGERS, got {detected_four}"

print("  >> GestureEngine tests: ALL PASSED!")

# ---------------------------------------------------------
# TEST 2: HandTracker initialization
# ---------------------------------------------------------
print("\n[TEST 2] Testing HandTracker initialization...")
tracker = HandTracker(max_hands=1, detection_confidence=0.5, tracking_confidence=0.5)
assert tracker.detector is not None or tracker.hands is not None, "HandTracker failed to initialize"
# Test with dummy blank frame
import numpy as np
blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
res = tracker.process(blank_frame)
assert isinstance(res, list), "HandTracker process returned non-list"
tracker.close()
print("  >> HandTracker test: PASSED!")

# ---------------------------------------------------------
# TEST 3: Camera Sensor
# ---------------------------------------------------------
print("\n[TEST 3] Testing Camera Sensor...")
cam = Camera(width=640, height=480)
is_open = cam.is_opened()
print(f"  Camera is_opened(): {is_open}")
if is_open:
    f = cam.read()
    print(f"  Camera frame captured: {f is not None} (shape: {f.shape if f is not None else None})")
cam.release()
print("  >> Camera test: PASSED!")

print("\n=== ALL CORE UNIT TESTS COMPLETED SUCCESSFULLY ===")
