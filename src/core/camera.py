
import time
import threading
import cv2


class Camera:
    """
    Silent background camera sensor for HoloHand AI.
    The webcam is used ONLY as a data sensor.
    No raw video is displayed.
    Uses dedicated thread capture to guarantee zero-latency real-time frames
    and prevent DirectShow buffer accumulation over long sessions.
    """

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = False
        self._thread = None
        self.camera = self._init_camera()
        if self.is_opened():
            self._start_thread()

    def _start_thread(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        consecutive_failures = 0
        while self._running:
            if self.camera is None or not self.camera.isOpened():
                time.sleep(0.05)
                continue

            success, frame = self.camera.read()
            if success and frame is not None:
                consecutive_failures = 0
                # Horizontal mirror for natural hand movement.
                flipped = cv2.flip(frame, 1)
                with self._lock:
                    self._latest_frame = flipped
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    time.sleep(0.05)
                else:
                    time.sleep(0.002)

    def _init_camera(self):

        # Try available camera indexes and backends.
        for index in (0, 1):

            for backend in (cv2.CAP_DSHOW, None):

                cap = None

                try:
                    if backend is not None:
                        cap = cv2.VideoCapture(index, backend)
                    else:
                        cap = cv2.VideoCapture(index)

                    if not cap.isOpened():
                        cap.release()
                        continue

                    # IMPORTANT: Configure the local cap object.
                    cap.set(
                        cv2.CAP_PROP_FRAME_WIDTH,
                        self.width
                    )

                    cap.set(
                        cv2.CAP_PROP_FRAME_HEIGHT,
                        self.height
                    )

                    # Reduce unnecessary buffering where supported.
                    cap.set(
                        cv2.CAP_PROP_BUFFERSIZE,
                        1
                    )

                    ret, frame = cap.read()

                    if ret and frame is not None:

                        actual_height, actual_width = frame.shape[:2]

                        backend_name = (
                            "DirectShow"
                            if backend is not None
                            else "Default"
                        )

                        print(
                            f"Camera Sensor: READY | "
                            f"Index: {index} | "
                            f"Backend: {backend_name} | "
                            f"Resolution: {actual_width}x{actual_height}"
                        )

                        return cap

                    cap.release()

                except Exception as error:

                    if cap is not None:
                        cap.release()

                    print("Camera initialization warning:", error)

        print("Trying fallback camera...")

        cap = cv2.VideoCapture(0)

        if cap.isOpened():

            cap.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                self.width
            )

            cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                self.height
            )

            cap.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )

            ret, frame = cap.read()

            if ret and frame is not None:

                actual_height, actual_width = frame.shape[:2]

                print(
                    f"Camera Sensor: FALLBACK READY | "
                    f"Resolution: {actual_width}x{actual_height}"
                )

                return cap

        cap.release()

        print("ERROR: Camera sensor could not be opened.")

        return None

    def is_opened(self):

        return (
            self.camera is not None
            and self.camera.isOpened()
        )

    def read(self):

        if not self.is_opened():
            return None

        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()

        # Fallback to direct read if thread hasn't captured a frame yet
        success, frame = self.camera.read()

        if not success or frame is None:
            return None

        # Horizontal mirror for natural hand movement.
        return cv2.flip(frame, 1)

    def release(self):

        self._running = False

        if self._thread is not None:
            try:
                self._thread.join(timeout=0.6)
            except Exception:
                pass
            self._thread = None

        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None

        except Exception:
            pass
