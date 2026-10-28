
import cv2
import sys

# Allow Python to find the src/core modules
sys.path.insert(0, "src")

from core.hand_tracker import HandTracker

camera = None
tracker = None

try:
    # Open the default laptop camera
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("ERROR: Could not open camera 0.")
        print("Close apps using the camera and try again.")
        sys.exit(1)

    tracker = HandTracker(max_hands=2)

    if tracker.mode is None:
        print("ERROR: Hand tracker did not initialize.")
        sys.exit(1)

    print("Camera: READY")
    print("Show your hand clearly to the camera.")
    print("Press Q to quit.")

    while True:
        success, frame = camera.read()

        if not success:
            print("ERROR: Could not read a camera frame.")
            break

        # Mirror the preview for natural movement
        frame = cv2.flip(frame, 1)

        # Detect hands
        hands = tracker.process(frame)

        # Draw the detected hand landmarks
        for hand in hands:
            points = hand.landmark

            for point in points:
                x = int(point.x * frame.shape[1])
                y = int(point.y * frame.shape[0])
                cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)

            # Connect the 21 hand landmarks
            connections = [
                (0,1),(1,2),(2,3),(3,4),
                (0,5),(5,6),(6,7),(7,8),
                (5,9),(9,10),(10,11),(11,12),
                (9,13),(13,14),(14,15),(15,16),
                (13,17),(17,18),(18,19),(19,20),
                (0,17)
            ]

            for start, end in connections:
                p1 = points[start]
                p2 = points[end]

                cv2.line(
                    frame,
                    (int(p1.x * frame.shape[1]),
                     int(p1.y * frame.shape[0])),
                    (int(p2.x * frame.shape[1]),
                     int(p2.y * frame.shape[0])),
                    (0, 255, 255),
                    2
                )

        cv2.putText(
            frame,
            f"Hands detected: {len(hands)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        cv2.imshow("HoloHand AI - Camera Diagnostic", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    if tracker is not None:
        tracker.close()

    if camera is not None:
        camera.release()

    cv2.destroyAllWindows()
    print("Camera test ended.")
