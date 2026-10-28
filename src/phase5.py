import cv2
import mediapipe as mp
import pyautogui
import keyboard
import time
import math


# ==================================================
# SETTINGS
# ==================================================

STABLE_FRAMES = 6
COOLDOWN = 1.0

MIN_HAND_SIZE = 0.18

# Hand orientation limit
# Smaller = stricter
MAX_TILT = 0.35


# ==================================================
# CAMERA
# ==================================================

cap = cv2.VideoCapture(0)


# ==================================================
# MEDIAPIPE
# ==================================================

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)


# ==================================================
# MEMORY
# ==================================================

last_gesture = ""
gesture_frames = 0

last_action = ""
last_action_time = 0


# ==================================================
# DISTANCE
# ==================================================

def distance(p1, p2):

    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )


# ==================================================
# HAND SIZE
# ==================================================

def hand_is_clear(hand):

    wrist = hand.landmark[0]
    middle_base = hand.landmark[9]

    size = distance(
        wrist,
        middle_base
    )

    if size >= MIN_HAND_SIZE:
        return True

    return False


# ==================================================
# HAND FACING CAMERA
# ==================================================

def hand_is_facing_camera(hand):

    wrist = hand.landmark[0]
    index_base = hand.landmark[5]
    pinky_base = hand.landmark[17]

    # Width of palm
    palm_width = distance(
        index_base,
        pinky_base
    )

    # Distance between wrist and palm
    palm_height = distance(
        wrist,
        index_base
    )

    if palm_height == 0:
        return False

    ratio = palm_width / palm_height

    # A clearly visible palm should have
    # a reasonable width-to-height ratio

    if ratio < 0.45:
        return False

    if ratio > 1.8:
        return False

    return True


# ==================================================
# CHECK FINGERS
# ==================================================

def get_fingers(hand):

    fingers = []


    # INDEX

    if hand.landmark[8].y < hand.landmark[6].y - 0.02:
        fingers.append(1)
    else:
        fingers.append(0)


    # MIDDLE

    if hand.landmark[12].y < hand.landmark[10].y - 0.02:
        fingers.append(1)
    else:
        fingers.append(0)


    # RING

    if hand.landmark[16].y < hand.landmark[14].y - 0.02:
        fingers.append(1)
    else:
        fingers.append(0)


    # LITTLE

    if hand.landmark[20].y < hand.landmark[18].y - 0.02:
        fingers.append(1)
    else:
        fingers.append(0)


    # THUMB

    thumb_tip = hand.landmark[4]
    thumb_base = hand.landmark[2]
    index_base = hand.landmark[5]

    thumb_distance = distance(
        thumb_tip,
        index_base
    )

    palm_size = distance(
        hand.landmark[0],
        hand.landmark[9]
    )

    if thumb_distance > palm_size * 0.85:
        thumb = 1
    else:
        thumb = 0


    return thumb, fingers


# ==================================================
# RECOGNIZE GESTURE
# ==================================================

def recognize_gesture(hand):

    thumb, fingers = get_fingers(hand)

    index = fingers[0]
    middle = fingers[1]
    ring = fingers[2]
    little = fingers[3]


    # FIVE FINGERS

    if (
        thumb == 1
        and index == 1
        and middle == 1
        and ring == 1
        and little == 1
    ):
        return "OPEN_PALM"


    # FOUR FINGERS

    if (
        thumb == 0
        and index == 1
        and middle == 1
        and ring == 1
        and little == 1
    ):
        return "FOUR_FINGERS"


    # THREE FINGERS

    if (
        thumb == 0
        and index == 1
        and middle == 1
        and ring == 1
        and little == 0
    ):
        return "THREE_FINGERS"


    # TWO FINGERS

    if (
        thumb == 0
        and index == 1
        and middle == 1
        and ring == 0
        and little == 0
    ):
        return "TWO_FINGERS"


    # ONE FINGER

    if (
        thumb == 0
        and index == 1
        and middle == 0
        and ring == 0
        and little == 0
    ):
        return "ONE_FINGER"


    # FIST

    if (
        thumb == 0
        and index == 0
        and middle == 0
        and ring == 0
        and little == 0
    ):
        return "FIST"


    return "UNKNOWN"


# ==================================================
# COMPUTER ACTION
# ==================================================

def do_action(gesture):

    global last_action
    global last_action_time

    current_time = time.time()

    if gesture == last_action:

        if current_time - last_action_time < COOLDOWN:
            return

    last_action = gesture
    last_action_time = current_time


    # FIST

    if gesture == "FIST":

        pyautogui.press("playpause")

        print("FIST -> PLAY / PAUSE")


    # TWO FINGERS

    elif gesture == "TWO_FINGERS":

        pyautogui.hotkey("alt", "tab")

        print("TWO FINGERS -> SWITCH WINDOW")


    # THREE FINGERS

    elif gesture == "THREE_FINGERS":

        pyautogui.hotkey("win", "d")

        print("THREE FINGERS -> SHOW DESKTOP")


    # FOUR FINGERS

    elif gesture == "FOUR_FINGERS":

        pyautogui.press("printscreen")

        print("FOUR FINGERS -> SCREENSHOT")


    # FIVE FINGERS

    elif gesture == "OPEN_PALM":

        pyautogui.press("volumemute")

        print("FIVE FINGERS -> MUTE / UNMUTE")


# ==================================================
# START
# ==================================================

print()
print("----------------------------------------")
print("       HOLOHAND AI - PHASE 5")
print("----------------------------------------")
print("Camera: RUNNING IN BACKGROUND")
print("Camera window: OFF")
print()
print("Show your palm straight to the camera.")
print("Press ESC to stop.")
print("----------------------------------------")
print()


# ==================================================
# MAIN LOOP
# ==================================================

while True:


    # ESC

    if keyboard.is_pressed("esc"):

        print("Stopping...")

        break


    # Read camera

    success, frame = cap.read()

    if not success:
        print("Camera error.")
        break


    # Flip

    frame = cv2.flip(
        frame,
        1
    )


    # Convert

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # Detect

    result = hands.process(rgb)


    # ==================================================
    # HAND FOUND
    # ==================================================

    if result.multi_hand_landmarks:

        hand = result.multi_hand_landmarks[0]


        # ----------------------------------------------
        # CHECK HAND SIZE
        # ----------------------------------------------

        if not hand_is_clear(hand):

            last_gesture = ""
            gesture_frames = 0

            continue


        # ----------------------------------------------
        # CHECK PALM ORIENTATION
        # ----------------------------------------------

        if not hand_is_facing_camera(hand):

            last_gesture = ""
            gesture_frames = 0

            continue


        # ----------------------------------------------
        # RECOGNIZE
        # ----------------------------------------------

        gesture = recognize_gesture(hand)


        # ----------------------------------------------
        # UNKNOWN
        # ----------------------------------------------

        if gesture == "UNKNOWN":

            last_gesture = ""
            gesture_frames = 0


        else:


            # Same gesture

            if gesture == last_gesture:

                gesture_frames += 1


            # New gesture

            else:

                last_gesture = gesture

                gesture_frames = 1


            # Stable gesture

            if gesture_frames >= STABLE_FRAMES:

                do_action(gesture)

                gesture_frames = 0


    # ==================================================
    # NO HAND
    # ==================================================

    else:

        last_gesture = ""
        gesture_frames = 0


# ==================================================
# CLOSE
# ==================================================

cap.release()

hands.close()

print()
print("HoloHand AI closed.")