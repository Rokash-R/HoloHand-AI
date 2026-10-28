import cv2


class Camera:
    """
    Silent background camera sensor for HoloHand AI.
    The webcam is used ONLY as a data sensor; no raw video is displayed.
    """

    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.camera = self._init_camera()

    def _init_camera(self):
        # On Windows, try DirectShow first (much faster, avoids MSMF lockups)
        # Also check index 0 and 1 (laptops often have IR camera at 0 and RGB at 1)
        for index in (0, 1):
            for backend in (cv2.CAP_DSHOW, None):
                try:
                    if backend is not None:
                        cap = cv2.VideoCapture(index, backend)
                    else:
                        cap = cv2.VideoCapture(index)

                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            backend_name = "DirectShow" if backend is not None else "Default"
                            print(f"Camera Sensor: READY on index {index} ({backend_name})")
                            return cap
                        cap.release()
                except Exception:
                    pass

        # Fallback to standard index 0
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if cap.isOpened():
            print("Camera Sensor: Fallback index 0 opened.")
        else:
            print("ERROR: Camera sensor could not be opened on any device index.")
        return cap

    def is_opened(self):
        return self.camera is not None and self.camera.isOpened()

    def read(self):
        if not self.is_opened():
            return None

        success, frame = self.camera.read()
        if not success or frame is None:
            return None

        # Flip horizontally for natural mirror hand movement
        return cv2.flip(frame, 1)

    def release(self):
        try:
            if self.camera is not None:
                self.camera.release()
        except Exception:
            pass
