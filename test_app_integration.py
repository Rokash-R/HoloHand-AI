import sys
import os
import time

# Ensure src in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, "src")

import mediapipe as mp
from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData

# Use offscreen window for automated verification without popping a window
loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")

from main import HoloHandApp

print("=== STARTING FULL HOLOHAND AI INTEGRATION TEST ===")
app = HoloHandApp()

print("\n[STEP 1] Testing Application Initialization...")
assert app is not None, "App failed to instantiate"
assert app.camera_sensor is not None, "Camera sensor missing"
assert app.hand_tracker is not None, "Hand tracker missing"
assert app.gesture_engine is not None, "Gesture engine missing"
assert app.hand_model is not None, "Hand model missing"
assert app.home_ui is not None, "Home UI missing"
print("  >> All subsystems instantiated correctly.")

print("\n[STEP 2] Simulating 30 Frames in Idle Standby State...")
for frame_idx in range(30):
    app.taskMgr.step()
print("  >> 30 idle frames rendered smoothly without errors.")

print("\n[STEP 3] Simulating Live Hand Tracking Frame...")
class MockLandmark:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class MockHand:
    def __init__(self):
        self.landmark = [MockLandmark(0.5 + i*0.01, 0.5 - i*0.01, -0.05) for i in range(21)]

mock_hand = MockHand()

# Test direct HandModel update with mock hand
app.hand_model.update(mock_hand)
# Test direct GestureEngine update with mock hand
gesture = app.gesture_engine.update(mock_hand)
print(f"  HandModel updated with mock hand. Gesture classified as: {gesture}")

# Step multiple frames with hand
for frame_idx in range(20):
    app.hand_model.update(mock_hand)
    app.taskMgr.step()
print("  >> 20 active tracking frames rendered successfully.")

print("\n[STEP 4] Testing Mode Switching...")
app.set_mode("PIANO")
assert app.mode == "PIANO"
app.set_mode("DRUMS")
assert app.mode == "DRUMS"
app.set_mode("HOME")
assert app.mode == "HOME"
print("  >> Mode switching (PIANO, DRUMS, HOME) verified.")

print("\n[STEP 5] Clean Shutdown...")
app.cleanup()
print("  >> Clean shutdown complete.")

print("\n=== INTEGRATION TEST PASSED PERFECTLY ===")
