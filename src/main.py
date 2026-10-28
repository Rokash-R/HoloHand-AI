
# ============================================================
# HOLOHAND AI - STAGE 2
# HOLOGRAPHIC HAND + CURSOR + PINCH NAVIGATION
# ============================================================

# Import MediaPipe before Panda3D on Windows.
try:
    import mediapipe as mp
except Exception as error:
    print("MediaPipe import warning:", error)

import time
import math
import traceback

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectFrame
from panda3d.core import (
    WindowProperties,
    AmbientLight,
    DirectionalLight,
    Point3,
    Vec4,
    TransparencyAttrib
)

from core.camera import Camera
from core.hand_tracker import HandTracker
from core.gesture_engine import GestureEngine
from core.sound_manager import SoundManager

from hand3d.hand_model import HandModel
from interface.home import Home
from music.piano.piano import Piano
from music.drums.drums import Drums


class HoloHandApp(ShowBase):

    def __init__(self):
        super().__init__()

        print("\n" + "=" * 55)
        print("HOLOHAND AI - STAGE 2")
        print("GESTURE INTERACTION SYSTEM")
        print("=" * 55)

        # -----------------------------------------
        # WINDOW (FULLSCREEN BY DEFAULT)
        # -----------------------------------------
        props = WindowProperties()
        props.setSize(1920, 1080)
        props.setFullscreen(True)
        props.setTitle("HoloHand AI - Gesture Interface")
        props.setCursorHidden(False)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(props)

        self.is_fullscreen = True
        self.accept("f11", self.toggle_fullscreen)
        self.accept("f", self.toggle_fullscreen)

        self.disableMouse()
        self.setup_3d_world()

        # -----------------------------------------
        # CAMERA AND TRACKING
        # -----------------------------------------
        self.camera_sensor = Camera(
            width=320,
            height=240
        )

        self.hand_tracker = HandTracker(
            max_hands=2,
            detection_confidence=0.55,
            tracking_confidence=0.55
        )

        self.gesture_engine = GestureEngine(
            stable_frames=7
        )

        # -----------------------------------------
        # AUDIO
        # -----------------------------------------
        self.sound_manager = SoundManager()

        # -----------------------------------------
        # HOLOGRAPHIC HAND
        # -----------------------------------------
        self.hand_model = HandModel(self)

        # -----------------------------------------
        # EXISTING USER INTERFACES
        # -----------------------------------------
        self.home_ui = Home(
            self,
            on_mode_select=self.set_mode
        )

        self.piano_ui = Piano(
            self,
            self.sound_manager
        )

        self.drums_ui = Drums(
            self,
            self.sound_manager
        )

        # -----------------------------------------
        # APPLICATION STATE
        # -----------------------------------------
        self.mode = "HOME"
        self.hand_detected = False
        self.active_gesture = "UNKNOWN"

        self.last_mode_switch_time = 0.0
        self.mode_switch_cooldown = 1.5

        # Pinch state with hysteresis.
        self.pinch_active = False
        self.last_click_time = 0.0
        self.click_cooldown = 0.65

        self.pinch_start_threshold = 0.28
        self.pinch_release_threshold = 0.42

        # Smoothed cursor position.
        self.cursor_position = None
        self.cursor_smoothing = 0.7

        # -----------------------------------------
        # NAVIGATION OVERLAY
        # -----------------------------------------
        self.create_navigation_ui()

        # -----------------------------------------
        # KEYBOARD CONTROLS
        # -----------------------------------------
        self.accept("h", self.set_mode, ["HOME"])
        self.accept("p", self.set_mode, ["PIANO"])
        self.accept("d", self.set_mode, ["DRUMS"])

        self.accept("1", self.set_mode, ["HOME"])
        self.accept("2", self.set_mode, ["PIANO"])
        self.accept("3", self.set_mode, ["DRUMS"])

        self.accept("escape", self.userExit)

        # -----------------------------------------
        # PERFORMANCE
        # -----------------------------------------
        self.last_report = time.perf_counter()
        self.frame_count = 0

        # -----------------------------------------
        # INITIAL SCREEN
        # -----------------------------------------
        self.set_mode("HOME")

        self.taskMgr.add(
            self.update,
            "HoloHandMainUpdate"
        )

        print("Holographic tracking: READY")
        print("Pinch interaction: READY")
        print("Gesture navigation: READY")
        print("=" * 55)

    # ========================================================
    # WORLD
    # ========================================================

    def setup_3d_world(self):

        self.setBackgroundColor(
            0.008, 0.012, 0.022, 1
        )

        self.camera.setPos(0, -12, 0.4)
        self.camera.lookAt(Point3(0, 0, 0.4))

        ambient = AmbientLight("Ambient")
        ambient.setColor(Vec4(0.35, 0.45, 0.6, 1))

        ambient_node = self.render.attachNewNode(
            ambient
        )

        self.render.setLight(ambient_node)

        directional = DirectionalLight("CyberLight")
        directional.setColor(Vec4(0.5, 0.9, 1, 1))

        directional_node = self.render.attachNewNode(
            directional
        )

        directional_node.setHpr(-35, -30, 0)

        self.render.setLight(directional_node)

    # ========================================================
    # NAVIGATION BUTTONS
    # ========================================================

    def create_navigation_ui(self):

        # Separate overlay so existing Home UI is preserved.
        self.nav_root = self.aspect2d.attachNewNode(
            "HoloNavigation"
        )

        self.nav_root.setBin("fixed", 90)
        self.nav_root.setDepthTest(False)
        self.nav_root.setDepthWrite(False)

        self.nav_buttons = {}

        # Normalized positions on aspect2d.
        self.nav_targets = {
            "PIANO": (-0.60, -0.72),
            "DRUMS": (0.60, -0.72),
            "HOME": (0.0, -0.82)
        }

        self.nav_buttons["PIANO"] = self.make_button(
            "PIANO",
            "OPEN PIANO",
            -0.60,
            -0.72
        )

        self.nav_buttons["DRUMS"] = self.make_button(
            "DRUMS",
            "OPEN DRUMS",
            0.60,
            -0.72
        )

        self.nav_buttons["HOME"] = self.make_button(
            "HOME",
            "HOME",
            0.0,
            -0.82
        )

    def make_button(self, mode, title, x, z):

        button = DirectButton(
            parent=self.nav_root,
            text=title,
            text_scale=0.055,
            text_fg=(0.75, 1.0, 1.0, 1),
            text_pos=(0, -0.018),
            frameSize=(-0.28, 0.28, -0.075, 0.075),
            frameColor=(0.015, 0.12, 0.20, 0.92),
            relief=1,
            pos=(x, 0, z),
            command=self.set_mode,
            extraArgs=[mode]
        )

        button.setTransparency(
            TransparencyAttrib.MAlpha
        )

        return button

    def update_navigation_ui(self):

        if self.mode == "HOME":
            self.nav_buttons["PIANO"].show()
            self.nav_buttons["DRUMS"].show()
            self.nav_buttons["HOME"].hide()

        elif self.mode == "PIANO":
            self.nav_buttons["PIANO"].hide()
            self.nav_buttons["DRUMS"].hide()
            self.nav_buttons["HOME"].hide()  # Piano workstation hosts its own professional dock

        else:
            self.nav_buttons["PIANO"].hide()
            self.nav_buttons["DRUMS"].hide()
            self.nav_buttons["HOME"].show()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        props = WindowProperties()
        props.setFullscreen(self.is_fullscreen)
        if not self.is_fullscreen:
            props.setSize(1280, 720)
        else:
            props.setSize(1920, 1080)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(props)
        print("Fullscreen toggled:", self.is_fullscreen)

    # ========================================================
    # MODE SWITCHING
    # ========================================================

    def set_mode(self, mode):

        if mode not in ("HOME", "PIANO", "DRUMS"):
            return

        self.mode = mode

        print("HoloHand Mode:", mode)

        if mode == "HOME":
            self.home_ui.show()
            self.piano_ui.hide()
            self.drums_ui.hide()

        elif mode == "PIANO":
            self.home_ui.hide()
            self.piano_ui.show()
            self.drums_ui.hide()

        elif mode == "DRUMS":
            self.home_ui.hide()
            self.piano_ui.hide()
            self.drums_ui.show()

        self.update_navigation_ui()

    # ========================================================
    # GESTURE NAVIGATION
    # ========================================================


    def handle_gestures(self, gesture):

        # Lock navigation while playing instruments.
        # Prevent accidental switching to HOME or DRUMS while playing.
        if self.mode in ("PIANO", "DRUMS"):
            return

        now = time.monotonic()

        if now - self.last_mode_switch_time < self.mode_switch_cooldown:
            return

        if self.pinch_active:
            return

        mapping = {
            "OPEN PALM": "HOME",
            "TWO FINGERS": "PIANO",
            "CLOSED FIST": "DRUMS"
        }

        target_mode = mapping.get(gesture)

        if target_mode and target_mode != self.mode:
            self.set_mode(target_mode)
            self.last_mode_switch_time = now

    # ========================================================
    # LANDMARK HELPERS
    # ========================================================

    def get_landmarks(self, hand):

        if hand is None:
            return None

        if hasattr(hand, "landmark"):
            return hand.landmark

        if hasattr(hand, "landmarks"):
            return hand.landmarks

        if isinstance(hand, dict):
            return hand.get(
                "landmarks",
                hand.get("landmark")
            )

        if isinstance(hand, (list, tuple)):
            return hand

        return None

    def get_xy(self, landmark):

        if hasattr(landmark, "x"):
            return float(landmark.x), float(landmark.y)

        if isinstance(landmark, dict):
            return (
                float(landmark["x"]),
                float(landmark["y"])
            )

        return (
            float(landmark[0]),
            float(landmark[1])
        )

    def distance(self, a, b):

        ax, ay = self.get_xy(a)
        bx, by = self.get_xy(b)

        return math.hypot(ax - bx, ay - by)

    # ========================================================
    # CURSOR
    # ========================================================

    def update_cursor(self, landmarks):

        # Landmark 8 = index fingertip.
        x, y = self.get_xy(landmarks[8])

        aspect = self.getAspectRatio()

        target_x = (x - 0.5) * 2 * aspect
        target_z = (0.5 - y) * 2

        if self.cursor_position is None:
            self.cursor_position = (
                target_x,
                target_z
            )

        else:
            old_x, old_z = self.cursor_position

            alpha = self.cursor_smoothing

            self.cursor_position = (
                old_x + (target_x - old_x) * alpha,
                old_z + (target_z - old_z) * alpha
            )

        return self.cursor_position

    # ========================================================
    # PINCH DETECTION
    # ========================================================

    def update_pinch(self, landmarks):

        # Thumb tip = 4
        # Index tip = 8
        # Index MCP = 5
        # Pinky MCP = 17

        pinch_distance = self.distance(
            landmarks[4],
            landmarks[8]
        )

        palm_width = self.distance(
            landmarks[5],
            landmarks[17]
        )

        if palm_width < 0.025:
            return

        ratio = pinch_distance / palm_width

        # A pinch begins only after crossing the lower
        # threshold. It must be released before another click.
        if not self.pinch_active:

            if ratio < self.pinch_start_threshold:
                self.pinch_active = True
                self.perform_click()

        else:

            if ratio > self.pinch_release_threshold:
                self.pinch_active = False

    # ========================================================
    # PINCH-TO-CLICK
    # ========================================================

    def perform_click(self):
        now = time.monotonic()

        if now - self.last_click_time < self.click_cooldown:
            return

        if self.cursor_position is None:
            return

        cx, cz = self.cursor_position

        # Check only visible navigation targets.
        if self.mode == "HOME":
            available = ("PIANO", "DRUMS")
        else:
            available = ("HOME",)

        for mode in available:

            bx, bz = self.nav_targets[mode]

            # Same dimensions as the visible buttons.
            inside_x = abs(cx - bx) <= 0.28
            inside_z = abs(cz - bz) <= 0.075

            if inside_x and inside_z:

                self.last_click_time = now
                self.last_mode_switch_time = now

                print("PINCH CLICK:", mode)

                self.set_mode(mode)
                return

    # ========================================================
    # MAIN UPDATE LOOP
    # ========================================================

    def update(self, task):

        frame = self.camera_sensor.read()

        if frame is None:
            self.handle_no_hand()
            return task.cont

        detected_hands = self.hand_tracker.process(
            frame
        )

        self.frame_count += 1

        now = time.perf_counter()

        if now - self.last_report >= 2.0:

            fps = self.frame_count / (
                now - self.last_report
            )

            print(f"[HOLOHAND] FPS: {fps:.1f}")

            self.frame_count = 0
            self.last_report = now

        if not detected_hands:
            self.handle_no_hand()
            return task.cont

        # -----------------------------------------
        # PRIMARY HAND
        # -----------------------------------------
        primary_hand = detected_hands[0]

        landmarks = self.get_landmarks(primary_hand)

        if landmarks is None or len(landmarks) < 21:
            self.handle_no_hand()
            return task.cont

        self.hand_detected = True

        # -----------------------------------------
        # UPDATE HOLOGRAPHIC HAND ONCE
        # -----------------------------------------
        self.hand_model.update(primary_hand)

        # -----------------------------------------
        # UPDATE CURSOR AND PINCH
        # -----------------------------------------
        self.update_cursor(landmarks)
        self.update_pinch(landmarks)

        # -----------------------------------------
        # GESTURE DETECTION
        # -----------------------------------------
        self.active_gesture = (
            self.gesture_engine.update(primary_hand)
        )

        self.handle_gestures(
            self.active_gesture
        )

        # -----------------------------------------
        # MUSIC
        # -----------------------------------------
        self._update_active_mode(detected_hands)

        # -----------------------------------------
        # HOME TELEMETRY
        # -----------------------------------------
        if self.mode == "HOME":

            status = self.gesture_engine.get_status()

            confidence = status.get(
                "confidence",
                0.0
            )

            self.home_ui.update_telemetry(
                True,
                self.active_gesture,
                self.mode,
                confidence=confidence
            )

        return task.cont

    # ========================================================
    # NO HAND DETECTED
    # ========================================================

    def handle_no_hand(self):

        self.hand_detected = False
        self.active_gesture = "UNKNOWN"

        self.cursor_position = None
        self.pinch_active = False

        self.hand_model.update(None)

        self._update_active_mode(None)

        if self.mode == "HOME":

            self.home_ui.update_telemetry(
                False,
                "WAITING FOR HAND",
                self.mode,
                confidence=0.0
            )

    # ========================================================
    # MUSIC UPDATE
    # ========================================================

    def _update_active_mode(self, hands):

        if self.mode == "PIANO":
            self.piano_ui.update(hands)

        elif self.mode == "DRUMS":
            primary = hands[0] if isinstance(hands, (list, tuple)) and len(hands) > 0 else hands
            self.drums_ui.update(primary)

    # ========================================================
    # EXIT AND CLEANUP
    # ========================================================

    def exit_app(self):
        print("Closing HoloHand AI...")
        self.userExit()

    def cleanup(self):
        print("Closing HoloHand AI...")
        # Keep your existing cleanup code here.

        for name, method in [
            ("camera", lambda: self.camera_sensor.release()),
            ("tracker", lambda: self.hand_tracker.close()),
            ("audio", lambda: self.sound_manager.close()),
            ("hand", lambda: self.hand_model.cleanup()),
            ("home", lambda: self.home_ui.cleanup()),
            ("piano", lambda: self.piano_ui.cleanup()),
            ("drums", lambda: self.drums_ui.cleanup())
        ]:

            try:
                method()
            except Exception as error:
                print(f"Cleanup warning ({name}):", error)

        try:
            self.nav_root.removeNode()
        except Exception:
            pass

        print("HoloHand AI closed.")


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app = None

    try:
        app = HoloHandApp()
        app.run()

    except Exception as error:

        print("\n" + "=" * 55)
        print("HOLOHAND AI RUNTIME ERROR")
        print("=" * 55)

        print(type(error).__name__, error)
        traceback.print_exc()

    finally:

        if app is not None:
            app.cleanup()
