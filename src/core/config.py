# Configuration constants for HoloHand AI

# Gesture detection thresholds and parameters
# Adjust these values to fine‑tune responsiveness and stability.
GESTURE_THRESHOLDS = {
    "pinch_distance_ratio": 0.28,  # thumb‑index tip distance / palm scale
    "pinch_angle_deg": 30,        # maximum angle between thumb‑index vectors
    "stability_window": 5,        # number of recent frames to consider
    "stability_consensus": 0.70,   # required proportion of same gesture
    "cooldown_seconds": 1.5,       # minimum time between mode switches
}

# Hand model assets
# If you add a low‑poly hand mesh, place it under `src/assets/hand/hand_mesh.egg`
# and set HAND_MESH_PATH accordingly.
HAND_MESH_PATH = "src/assets/hand/hand_mesh.egg"
