# ============================================================
# HOLOHAND AI - PHASE 6 COMPLETE DEMO
# Virtual Holographic Hand Interaction
# ============================================================

import cv2
import mediapipe as mp
import numpy as np
import math
import random


# ============================================================
# 1. MEDIAPIPE HAND TRACKING
# ============================================================

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


# ============================================================
# 2. CAMERA
# ============================================================

cap = cv2.VideoCapture(0)


# ============================================================
# 3. SCREEN SETTINGS
# ============================================================

WIDTH = 1280
HEIGHT = 720

animation = 0


# ============================================================
# 4. PARTICLES
# ============================================================

particles = []

for i in range(80):

    particles.append([
        random.randint(0, WIDTH - 1),
        random.randint(0, HEIGHT - 1),
        random.randint(1, 3)
    ])


# ============================================================
# 5. DRAW HOLOGRAPHIC PARTICLES
# ============================================================

def draw_particles(screen):

    for particle in particles:

        x = particle[0]
        y = particle[1]
        size = particle[2]

        cv2.circle(
            screen,
            (x, y),
            size,
            (255, 255, 255),
            -1
        )


# ============================================================
# 6. DRAW FLOATING UI
# ============================================================

def draw_interface(screen):

    # Top title
    cv2.putText(
        screen,
        "HOLOHAND AI",
        (40, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (255, 255, 255),
        2
    )

    cv2.putText(
        screen,
        "GESTURE INTERACTION SYSTEM",
        (42, 82),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 180, 180),
        1
    )

    # Right side control panel
    cv2.rectangle(
        screen,
        (930, 150),
        (1230, 570),
        (255, 255, 255),
        1
    )

    cv2.putText(
        screen,
        "HOLO CONTROL",
        (970, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # Piano
    cv2.putText(
        screen,
        "PIANO",
        (970, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1
    )

    piano_x = 960
    piano_y = 260

    for i in range(7):

        x1 = piano_x + i * 35
        x2 = x1 + 35

        cv2.rectangle(
            screen,
            (x1, piano_y),
            (x2, piano_y + 100),
            (255, 255, 255),
            1
        )

    # Drums
    cv2.putText(
        screen,
        "DRUMS",
        (970, 410),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1
    )

    cv2.circle(
        screen,
        (1000, 480),
        45,
        (255, 255, 255),
        2
    )

    cv2.circle(
        screen,
        (1120, 480),
        45,
        (255, 255, 255),
        2
    )


# ============================================================
# 7. DRAW REALISTIC-LOOKING HOLOGRAPHIC HAND
# ============================================================

def draw_holographic_hand(screen, points):

    # Hand connections
    connections = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),

        (0, 5),
        (5, 6),
        (6, 7),
        (7, 8),

        (5, 9),
        (9, 10),
        (10, 11),
        (11, 12),

        (9, 13),
        (13, 14),
        (14, 15),
        (15, 16),

        (13, 17),
        (17, 18),
        (18, 19),
        (19, 20),

        (0, 17)
    ]


    # --------------------------------------------------------
    # Thick inner hand structure
    # --------------------------------------------------------

    for start, end in connections:

        cv2.line(
            screen,
            points[start],
            points[end],
            (255, 255, 255),
            10
        )


    # --------------------------------------------------------
    # Thin holographic skeleton
    # --------------------------------------------------------

    for start, end in connections:

        cv2.line(
            screen,
            points[start],
            points[end],
            (255, 255, 255),
            3
        )


    # --------------------------------------------------------
    # Finger joints
    # --------------------------------------------------------

    for x, y in points:

        cv2.circle(
            screen,
            (x, y),
            11,
            (255, 255, 255),
            -1
        )

        cv2.circle(
            screen,
            (x, y),
            18,
            (255, 255, 255),
            1
        )


# ============================================================
# 8. FINGER STATUS
# ============================================================

def get_finger_state(points):

    index_distance = np.linalg.norm(
        np.array(points[8]) -
        np.array(points[5])
    )

    middle_distance = np.linalg.norm(
        np.array(points[12]) -
        np.array(points[9])
    )

    ring_distance = np.linalg.norm(
        np.array(points[16]) -
        np.array(points[13])
    )

    pinky_distance = np.linalg.norm(
        np.array(points[20]) -
        np.array(points[17])
    )


    fingers = 0

    if index_distance > 80:
        fingers += 1

    if middle_distance > 80:
        fingers += 1

    if ring_distance > 70:
        fingers += 1

    if pinky_distance > 60:
        fingers += 1


    return fingers


# ============================================================
# 9. PINCH DETECTION
# ============================================================

def detect_pinch(points):

    thumb = np.array(points[4])
    index = np.array(points[8])

    distance = np.linalg.norm(
        thumb - index
    )

    if distance < 45:
        return True

    return False


# ============================================================
# 10. OPEN HAND EFFECT
# ============================================================

def open_hand_effect(screen, center, animation):

    x, y = center

    radius = 60 + int(
        25 * math.sin(animation * 0.08)
    )

    cv2.circle(
        screen,
        (x, y),
        radius,
        (255, 255, 255),
        2
    )

    cv2.circle(
        screen,
        (x, y),
        radius + 30,
        (255, 255, 255),
        1
    )

    cv2.circle(
        screen,
        (x, y),
        radius + 60,
        (255, 255, 255),
        1
    )


# ============================================================
# 11. FIST EFFECT
# ============================================================

def fist_effect(screen, center, animation):

    x, y = center

    pulse = 50 + int(
        15 * math.sin(animation * 0.15)
    )

    cv2.circle(
        screen,
        (x, y),
        pulse,
        (255, 255, 255),
        3
    )

    cv2.circle(
        screen,
        (x, y),
        pulse + 20,
        (255, 255, 255),
        1
    )


# ============================================================
# 12. PINCH EFFECT
# ============================================================

def pinch_effect(screen, points):

    thumb = points[4]
    index = points[8]

    x = int(
        (thumb[0] + index[0]) / 2
    )

    y = int(
        (thumb[1] + index[1]) / 2
    )

    cv2.circle(
        screen,
        (x, y),
        25,
        (255, 255, 255),
        2
    )

    cv2.circle(
        screen,
        (x, y),
        8,
        (255, 255, 255),
        -1
    )


# ============================================================
# 13. MAIN LOOP
# ============================================================

while True:

    success, frame = cap.read()

    if not success:
        break


    # Mirror camera
    frame = cv2.flip(frame, 1)


    # Convert image
    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # Detect hand
    results = hands.process(rgb)


    # Create black holographic world
    virtual_screen = np.zeros(
        (HEIGHT, WIDTH, 3),
        dtype=np.uint8
    )


    animation += 1


    # ========================================================
    # BACKGROUND
    # ========================================================

    draw_particles(
        virtual_screen
    )


    # Floating interface
    draw_interface(
        virtual_screen
    )


    # ========================================================
    # HAND DETECTED
    # ========================================================

    if results.multi_hand_landmarks:

        for hand in results.multi_hand_landmarks:

            points = []


            # ------------------------------------------------
            # Convert landmarks to screen coordinates
            # ------------------------------------------------

            for landmark in hand.landmark:

                x = int(
                    landmark.x * WIDTH
                )

                y = int(
                    landmark.y * HEIGHT
                )

                points.append(
                    (x, y)
                )


            # ------------------------------------------------
            # Draw holographic hand
            # ------------------------------------------------

            draw_holographic_hand(
                virtual_screen,
                points
            )


            # ------------------------------------------------
            # Hand center
            # ------------------------------------------------

            hand_x = points[0][0]
            hand_y = points[0][1]


            # ------------------------------------------------
            # Finger detection
            # ------------------------------------------------

            fingers_open = get_finger_state(
                points
            )


            # ------------------------------------------------
            # Pinch
            # ------------------------------------------------

            pinch = detect_pinch(
                points
            )


            # =================================================
            # INDEX FINGER CURSOR
            # =================================================

            index_x = points[8][0]
            index_y = points[8][1]


            cv2.circle(
                virtual_screen,
                (index_x, index_y),
                20,
                (255, 255, 255),
                2
            )

            cv2.circle(
                virtual_screen,
                (index_x, index_y),
                5,
                (255, 255, 255),
                -1
            )


            # =================================================
            # GESTURES
            # =================================================

            if pinch:

                gesture = "PINCH"

                pinch_effect(
                    virtual_screen,
                    points
                )


            elif fingers_open >= 4:

                gesture = "OPEN HAND"

                open_hand_effect(
                    virtual_screen,
                    (hand_x, hand_y),
                    animation
                )


            elif fingers_open == 0:

                gesture = "FIST"

                fist_effect(
                    virtual_screen,
                    (hand_x, hand_y),
                    animation
                )


            else:

                gesture = "FINGER CONTROL"


            # =================================================
            # STATUS PANEL
            # =================================================

            cv2.putText(
                virtual_screen,
                "GESTURE:",
                (40, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (180, 180, 180),
                1
            )

            cv2.putText(
                virtual_screen,
                gesture,
                (40, 185),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )


            # =================================================
            # LANDMARK COUNT
            # =================================================

            cv2.putText(
                virtual_screen,
                "AI LANDMARKS: 21",
                (40, 225),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (180, 180, 180),
                1
            )


            # =================================================
            # FINGER INFORMATION
            # =================================================

            cv2.putText(
                virtual_screen,
                "FINGERS OPEN: "
                + str(fingers_open),
                (40, 255),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (180, 180, 180),
                1
            )


    else:

        cv2.putText(
            virtual_screen,
            "SEARCHING FOR HAND...",
            (40, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


    # ========================================================
    # HOLOGRAPHIC GLOW
    # ========================================================

    glow = cv2.GaussianBlur(
        virtual_screen,
        (21, 21),
        0
    )


    virtual_screen = cv2.addWeighted(
        virtual_screen,
        1.0,
        glow,
        0.35,
        0
    )


    # ========================================================
    # SHOW ONLY VIRTUAL WORLD
    # ========================================================

    cv2.imshow(
        "HOLOHAND AI - PHASE 6",
        virtual_screen
    )


    # ========================================================
    # Q = EXIT
    # ========================================================

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()