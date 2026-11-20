# ============================================================
# HOLOHAND AI - STAGE 2
# HOLOGRAPHIC HAND + RESPONSIVE CURSOR + PINCH NAVIGATION
# HOME + PIANO + DRUMS + GESTURE FX
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
from direct.gui.DirectGui import DirectButton
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
from music.gesture_fx.gesture_fx import GestureFx


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
            width=640,
            height=480
        )

        # Responsive tracking confidence
        self.hand_tracker = HandTracker(
            max_hands=2,
            detection_confidence=0.45,
            tracking_confidence=0.45,
            presence_confidence=0.45
        )

        self.gesture_engine = GestureEngine(
            stable_frames=4
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
        # USER INTERFACES
        # -----------------------------------------
        self.home_ui = Home(
            self,
            on_mode_select=self.set_mode
        )
        if hasattr(self.home_ui, "frame") and self.home_ui.frame:
            self.home_ui.frame.setBin("fixed", 10)

        self.piano_ui = Piano(
            self,
            self.sound_manager
        )

        self.drums_ui = Drums(
            self,
            self.sound_manager
        )

        self.gesture_fx_ui = GestureFx(self)
        self.fx_ui = self.gesture_fx_ui  # Alias for compatibility

        # Top-left Return Home Button coordinates for in-studio click test
        self.home_btn_pos = (-1.45, 0.88)

        # -----------------------------------------
        # APPLICATION STATE
        # -----------------------------------------
        self.mode = None
        self.hand_detected = False
        self.active_gesture = "UNKNOWN"

        # Mode switching cooldown to prevent sudden exits / bouncing
        self.last_mode_switch_time = 0.0
        self.mode_switch_cooldown = 1.0

        # Pinch detection state
        self.pinch_active = False
        self.pinch_navigation_active = False
        self.last_click_time = 0.0
        self.click_cooldown = 0.35

        self.pinch_start_threshold = 0.38
        self.pinch_release_threshold = 0.52
        self.smooth_pinch_ratio = None

        # Hand loss tracking
        self.hand_loss_frames = 0
        self.max_hand_loss_frames = 8

        # Responsive cursor positioning
        self.cursor_position = None
        self.cursor_smoothing = 0.60
        self.primary_hand_position = None

        # -----------------------------------------
        # NAVIGATION OVERLAY
        # -----------------------------------------
        self.create_navigation_ui()

        # -----------------------------------------
        # KEYBOARD CONTROLS
        # -----------------------------------------
        self.accept("h", self.set_mode, ["HOME"])
        self.accept("H", self.set_mode, ["HOME"])
        self.accept("p", self.set_mode, ["PIANO"])
        self.accept("P", self.set_mode, ["PIANO"])
        self.accept("d", self.set_mode, ["DRUMS"])
        self.accept("D", self.set_mode, ["DRUMS"])
        self.accept("g", self.set_mode, ["FX"])
        self.accept("G", self.set_mode, ["FX"])

        self.accept("1", self.set_mode, ["HOME"])
        self.accept("2", self.set_mode, ["PIANO"])
        self.accept("3", self.set_mode, ["DRUMS"])
        self.accept("4", self.set_mode, ["FX"])

        self.accept("f", self.toggle_fullscreen)
        self.accept("F", self.toggle_fullscreen)
        self.accept("f11", self.toggle_fullscreen)

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
        print("Responsive cursor: READY")
        print("Pinch interaction: READY")
        print("Gesture navigation: READY")
        print("Gesture FX Studio: READY")
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
        ambient.setColor(
            Vec4(0.35, 0.45, 0.6, 1)
        )

        ambient_node = self.render.attachNewNode(
            ambient
        )

        self.render.setLight(ambient_node)

        directional = DirectionalLight("CyberLight")
        directional.setColor(
            Vec4(0.5, 0.9, 1, 1)
        )

        directional_node = self.render.attachNewNode(
            directional
        )

        directional_node.setHpr(-35, -30, 0)

        self.render.setLight(directional_node)

    # ========================================================
    # NAVIGATION BUTTONS & TARGETS
    # ========================================================

    def create_navigation_ui(self):

        self.nav_root = self.aspect2d.attachNewNode(
            "HoloNavigation"
        )

        self.nav_root.setBin("fixed", 90)
        self.nav_root.setDepthTest(False)
        self.nav_root.setDepthWrite(False)
        self.nav_root.hide()

        self.nav_buttons = {}

        # Screen positions matching 3 Hero Cards on aspect2d
        self.nav_targets = {
            "PIANO": (-0.63, 0.04),
            "DRUMS": (0.0, 0.04),
            "FX": (0.63, 0.04),
            "HOLOLAB": (0.63, 0.04),
            "HOME": (0.0, -0.82)
        }

        self.nav_buttons["PIANO"] = self.make_button(
            "PIANO",
            "OPEN PIANO",
            -0.63,
            0.04
        )

        self.nav_buttons["DRUMS"] = self.make_button(
            "DRUMS",
            "OPEN DRUMS",
            0.0,
            0.04
        )

        self.nav_buttons["FX"] = self.make_button(
            "FX",
            "OPEN GESTURE FX",
            0.63,
            0.04
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
        # Navigation is hosted inside each studio; keep nav_root hidden
        if hasattr(self, "nav_root") and self.nav_root:
            self.nav_root.hide()

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

        mode = str(mode).upper()

        if mode == "HOLOLAB":
            mode = "FX"

        if mode not in ("HOME", "PIANO", "DRUMS", "FX"):
            return

        # Avoid redundant screen rebuilding
        if mode == self.mode:
            return

        self.mode = mode
        self.last_mode_switch_time = time.monotonic()
        self.pinch_navigation_active = False

        print("HoloHand Mode:", mode)

        # Play audio confirmation if available
        if hasattr(self.sound_manager, "play_ui_click"):
            try:
                self.sound_manager.play_ui_click()
            except Exception:
                pass

        # Safely hide all interfaces first (ignoring any already destroyed UI frames)
        for ui in (self.home_ui, self.piano_ui, self.drums_ui, self.gesture_fx_ui):
            if ui is not None:
                try:
                    ui.hide()
                except Exception:
                    pass

        # Show only requested interface (re-instantiating if previously destroyed on exit)
        if mode == "HOME":
            if self.home_ui is None or not hasattr(self.home_ui, "frame") or (hasattr(self.home_ui.frame, "isEmpty") and self.home_ui.frame.isEmpty()):
                self.home_ui = Home(self, on_mode_select=self.set_mode)
            try:
                self.home_ui.show()
            except Exception:
                pass
            if hasattr(self.home_ui, "frame") and self.home_ui.frame and not (hasattr(self.home_ui.frame, "isEmpty") and self.home_ui.frame.isEmpty()):
                self.home_ui.frame.setBin("fixed", 10)
            if hasattr(self.hand_model, "root") and self.hand_model.root and not (hasattr(self.hand_model.root, "isEmpty") and self.hand_model.root.isEmpty()):
                self.hand_model.root.setBin("fixed", 200)

        elif mode == "PIANO":
            if self.piano_ui is None or not hasattr(self.piano_ui, "frame") or (hasattr(self.piano_ui.frame, "isEmpty") and self.piano_ui.frame.isEmpty()):
                print("[HoloHand] Re-instantiating Piano Studio...")
                self.piano_ui = Piano(self, self.sound_manager)
            self.piano_ui.show()
            if hasattr(self.hand_model, "root") and self.hand_model.root and not (hasattr(self.hand_model.root, "isEmpty") and self.hand_model.root.isEmpty()):
                self.hand_model.root.setBin("fixed", 200)

        elif mode == "DRUMS":
            if self.drums_ui is None:
                self.drums_ui = Drums(self, self.sound_manager)
            self.drums_ui.show()

        elif mode == "FX":
            if self.gesture_fx_ui is None or not hasattr(self.gesture_fx_ui, "ui_root") or (hasattr(self.gesture_fx_ui.ui_root, "isEmpty") and self.gesture_fx_ui.ui_root.isEmpty()):
                print("[HoloHand] Re-instantiating Gesture FX Studio...")
                self.gesture_fx_ui = GestureFx(self)
                self.fx_ui = self.gesture_fx_ui
            self.gesture_fx_ui.show()

        self.update_navigation_ui()

    # ========================================================
    # GESTURE NAVIGATION
    # ========================================================

    def handle_gestures(self, gesture):

        # Only allow gestures to switch modes if explicitly configured,
        # never while inside active studio performance to prevent accidental kicks
        if self.mode in ("PIANO", "DRUMS", "FX"):
            return

        # On Home screen, user selects studios via Pinch or Click
        return

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
            return (
                float(landmark.x),
                float(landmark.y)
            )

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

        return math.hypot(
            ax - bx,
            ay - by
        )

    # ========================================================
    # PRIMARY HAND SELECTION (Adaptive to rapid motions)
    # ========================================================

    def select_primary_hand(self, detected_hands):

        valid_hands = []

        for hand in detected_hands:

            landmarks = self.get_landmarks(hand)

            if landmarks is None or len(landmarks) < 21:
                continue

            try:
                x, y = self.get_xy(landmarks[8])

                if not (
                    math.isfinite(x)
                    and math.isfinite(y)
                    and -0.15 <= x <= 1.15
                    and -0.15 <= y <= 1.15
                ):
                    continue

                valid_hands.append(
                    (hand, landmarks, (x, y))
                )

            except (TypeError, ValueError, KeyError, IndexError):
                continue

        if not valid_hands:
            return None, None

        if self.primary_hand_position is None:
            selected = valid_hands[0]
        else:
            previous_x, previous_y = self.primary_hand_position

            selected = min(
                valid_hands,
                key=lambda item: math.hypot(
                    item[2][0] - previous_x,
                    item[2][1] - previous_y
                )
            )

        self.primary_hand_position = selected[2]

        return selected[0], selected[1]

    # ========================================================
    # RESPONSIVE CURSOR (Adaptive low-latency tracking)
    # ========================================================

    def update_cursor(self, landmarks):

        x, y = self.get_xy(landmarks[8])

        aspect = self.getAspectRatio()

        target_x = (x - 0.5) * 2.0 * aspect
        target_z = (0.5 - y) * 2.0

        if self.cursor_position is None:
            self.cursor_position = (
                target_x,
                target_z
            )
            return self.cursor_position

        old_x, old_z = self.cursor_position

        dist = math.hypot(
            target_x - old_x,
            target_z - old_z
        )

        # Dynamic smoothing: high responsiveness on fast moves, smooth on rest
        if dist > 0.08:
            alpha = min(0.98, self.cursor_smoothing + dist * 2.5)
        elif dist > 0.02:
            alpha = self.cursor_smoothing + dist * 1.5
        else:
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

        # Only process pinch clicks on the Home screen or navigation
        if self.mode != "HOME":
            return

        pinch_distance = self.distance(
            landmarks[4],
            landmarks[8]
        )

        palm_width = self.distance(
            landmarks[5],
            landmarks[17]
        )

        if palm_width < 0.020:
            return

        ratio = pinch_distance / palm_width

        # Exponential moving average for smooth, effortless pinch triggering
        if self.smooth_pinch_ratio is None:
            self.smooth_pinch_ratio = ratio
        else:
            self.smooth_pinch_ratio = 0.70 * ratio + 0.30 * self.smooth_pinch_ratio
        eff_ratio = self.smooth_pinch_ratio

        if not self.pinch_active:
            if eff_ratio < self.pinch_start_threshold:
                self.pinch_active = True
                self.perform_click()
        else:
            if eff_ratio > self.pinch_release_threshold:
                self.pinch_active = False
                self.pinch_navigation_active = False  # Reset lock on pinch release

    # ========================================================
    # PINCH-TO-CLICK & STUDIO LAUNCH
    # ========================================================

    def perform_click(self):

        if self.pinch_navigation_active:
            return

        now = time.monotonic()

        if now - self.last_click_time < self.click_cooldown:
            return

        if self.cursor_position is None:
            return

        cx, cz = self.cursor_position

        # 1. In-Studio Return Home Button Check (top-left <- RETURN HOME)
        if self.mode in ("PIANO", "DRUMS", "FX"):
            if abs(cx - self.home_btn_pos[0]) <= 0.35 and abs(cz - self.home_btn_pos[1]) <= 0.15:
                self.last_click_time = now
                self.pinch_navigation_active = True
                print("PINCH CLICK SELECTION: RETURN HOME")
                self.set_mode("HOME")
                return
            return

        # 2. Home screen 3 Hero Studio Cards
        if self.mode == "HOME":
            # Check hover target from home_ui if available
            target = None
            if hasattr(self.home_ui, "update_cursor_hover"):
                target = self.home_ui.update_cursor_hover(self.cursor_position)

            if target is None:
                # Fallback to direct geometric card hit-testing
                for mode, pos in [("PIANO", (-0.63, 0.04)), ("DRUMS", (0.0, 0.04)), ("FX", (0.63, 0.04))]:
                    if abs(cx - pos[0]) <= 0.285 and abs(cz - pos[1]) <= 0.335:
                        target = mode
                        break

            if target:
                self.last_click_time = now
                self.pinch_navigation_active = True
                print(f"PINCH CLICK SELECTION: {target}")

                if hasattr(self.sound_manager, "play_ui_click"):
                    try:
                        self.sound_manager.play_ui_click()
                    except Exception:
                        pass

                self.set_mode(target)
                return

    # ========================================================
    # MAIN UPDATE LOOP
    # ========================================================

    def update(self, task):

        # -----------------------------------------
        # CAMERA FRAME
        # -----------------------------------------
        frame = self.camera_sensor.read()

        if frame is None:
            self.handle_no_hand()
            return task.cont

        # -----------------------------------------
        # HAND TRACKING
        # -----------------------------------------
        detected_hands = self.hand_tracker.process(
            frame
        )

        self.frame_count += 1

        # -----------------------------------------
        # FPS REPORT
        # -----------------------------------------
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
        # SELECT STABLE PRIMARY HAND
        # -----------------------------------------
        primary_hand, landmarks = self.select_primary_hand(
            detected_hands
        )

        if primary_hand is None or landmarks is None:
            self.handle_no_hand()
            return task.cont

        self.hand_detected = True
        self.hand_loss_frames = 0

        # -----------------------------------------
        # UPDATE HOLOGRAPHIC HAND
        # -----------------------------------------
        self.hand_model.update(
            primary_hand
        )

        # -----------------------------------------
        # UPDATE CURSOR & PINCH
        # -----------------------------------------
        self.update_cursor(
            landmarks
        )

        # Real-time card hover update on Home Screen
        if self.mode == "HOME":
            if hasattr(self.home_ui, "update_cursor_hover"):
                self.home_ui.update_cursor_hover(
                    self.cursor_position
                )

        self.update_pinch(
            landmarks
        )

        # -----------------------------------------
        # GESTURE DETECTION
        # -----------------------------------------
        self.active_gesture = self.gesture_engine.update(
            primary_hand
        )

        self.handle_gestures(
            self.active_gesture
        )

        # -----------------------------------------
        # ACTIVE INTERFACE UPDATE
        # -----------------------------------------
        self._update_active_mode(
            detected_hands
        )

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
        self.hand_loss_frames += 1
        self.smooth_pinch_ratio = None

        if hasattr(self, "gesture_engine"):
            self.gesture_engine.reset()

        if self.hand_loss_frames > self.max_hand_loss_frames:
            self.cursor_position = None
            self.primary_hand_position = None
            self.pinch_active = False
            self.pinch_navigation_active = False

            self.hand_model.update(None)

            if self.mode == "HOME":
                mw = getattr(self, "mouseWatcherNode", None)
                if mw and mw.hasMouse():
                    m = mw.getMouse()
                    aspect = self.getAspectRatio()
                    if hasattr(self.home_ui, "update_cursor_hover"):
                        self.home_ui.update_cursor_hover((m.getX() * aspect, m.getY()))
                elif hasattr(self.home_ui, "clear_hover"):
                    self.home_ui.clear_hover()

        # Clear FX pointer and hand state when tracking is lost
        if self.mode == "FX":
            self.gesture_fx_ui.update(None)

        # Never send cached landmarks to instruments
        self._update_active_mode(None)

        if self.mode == "HOME":
            self.home_ui.update_telemetry(
                False,
                "WAITING FOR HAND",
                self.mode,
                confidence=0.0
            )

    # ========================================================
    # ACTIVE MODE UPDATE
    # ========================================================

    def _update_active_mode(self, hands):

        if self.mode == "PIANO":
            if self.piano_ui and hasattr(self.piano_ui, "frame") and not (hasattr(self.piano_ui.frame, "isEmpty") and self.piano_ui.frame.isEmpty()):
                self.piano_ui.update(hands)
        elif self.mode == "DRUMS":
            if self.drums_ui:
                self.drums_ui.update(hands)
        elif self.mode == "FX":
            if self.gesture_fx_ui and hasattr(self.gesture_fx_ui, "ui_root") and not (hasattr(self.gesture_fx_ui.ui_root, "isEmpty") and self.gesture_fx_ui.ui_root.isEmpty()):
                self.gesture_fx_ui.update(hands)

    # ========================================================
    # EXIT AND CLEANUP
    # ========================================================

    def exit_app(self):
        print("Closing HoloHand AI...")
        self.userExit()

    def cleanup(self):
        print("Closing HoloHand AI...")

        for name, method in [
            ("camera", lambda: self.camera_sensor.release()),
            ("tracker", lambda: self.hand_tracker.close()),
            ("audio", lambda: self.sound_manager.close()),
            ("hand", lambda: self.hand_model.cleanup()),
            ("home", lambda: self.home_ui.cleanup()),
            ("piano", lambda: self.piano_ui.cleanup() if (self.piano_ui and hasattr(self.piano_ui, "frame") and not (hasattr(self.piano_ui.frame, "isEmpty") and self.piano_ui.frame.isEmpty())) else None),
            ("drums", lambda: self.drums_ui.cleanup()),
            ("gesture_fx", lambda: self.gesture_fx_ui.cleanup())
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
