import time
import evdev
from evdev import ecodes
import uinput
import select
import threading
import math

class DynaPadCore:
    def __init__(self):
        self.running = False
        self.thread = None
        self.dev = None
        self.v_mouse = None
        
        # Config defaults
        self.config = {
            "start_enabled": False,
            "tiling_enabled": False,
            "scale": 4,
            "max_movement_per_step": 150,
            "tap_max_duration": 0.25,
            "tap_max_movement": 5,
            "deadzone_threshold": 15,
            "rc_region_height": 0.25,
            "rc_region_width": 0.50,
            "scroll_trigger_window": 0.15,
            "scroll_speed": 10.0,
            "scroll_max_step": 150,
            "scroll_inertia_friction": 0.92,
            "scroll_inertia_cutoff": 0.05,
            "scroll_inertia_timeout": 0.1,
            "scroll_lock_ratio": 2.5,
            "scroll_exit_cooldown": 0.2,
            "typing_timeout": 0.6,
            "drag_scale_ratio": 1.0,
            "swipe_threshold": 15,
            "swipe_cooldown": 0.5,
            "palm_size_threshold": 45,
            "pinch_threshold": 50 
        }

        # State storage
        self.slots = {}
        self.current_slot = 0
        self.pending_update = False
        self.using_mt = False
        
        self.prev_centroid = None
        self.prev_num_fingers = 0
        self.prev_target_ids = set()
        self.prev_active_slots = set()

        self.virtual_left_down = False
        self.virtual_right_down = False
        self.phys_left_down = False
        self.phys_right_down = False
        self.last_emitted_left = False
        self.last_emitted_right = False
        self.click_lock_active = False

        self.tap_start_time = 0.0
        self.tap_acc_movement = 0.0
        self.is_potential_tap = False
        self.deadzone_broken = False
        
        self.last_known_pos = {"x": 0, "y": 0}
        
        # Scroll State
        self.is_scrolling = False
        self.active_scroll_axis = None
        self.first_finger_time = 0.0
        self.acc_wheel_hires_x = 0.0
        self.acc_wheel_hires_y = 0.0
        self.scroll_velocity_x = 0.0
        self.scroll_velocity_y = 0.0
        self.last_scroll_update = 0.0
        self.last_scroll_stop_time = 0.0
        
        self.active_click_mode = None
        self.remain_x = 0.0
        self.remain_y = 0.0

        # Swipe/Pinch State
        self.last_swipe_time = 0.0
        self.swipe_acc_x = 0.0
        self.swipe_acc_y = 0.0
        self.pinch_acc = 0.0
        self.prev_spread = None
        self.three_finger_lock = False 

        # Device info
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self.rc_min_x = 0
        self.rc_min_y = 0

    def find_touchpad(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if "touchpad" in device.name.lower():
                return device.path
        return None
    
    def find_keyboard(self):
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for device in devices:
                if "keyboard" in device.name.lower():
                    return device
        except: pass
        return None

    def start(self):
        if self.running: return
        
        self.using_mt = False 
        self.pending_update = False

        path = self.find_touchpad()
        if not path:
            print("Touchpad not found")
            return

        try:
            self.dev = evdev.InputDevice(path)
            self.dev.grab()
        except OSError as e:
            print(f"Failed to grab device: {e}")
            return

        self.v_mouse = uinput.Device([
            uinput.BTN_LEFT, uinput.BTN_RIGHT, uinput.BTN_MIDDLE,
            uinput.REL_X, uinput.REL_Y,
            uinput.REL_WHEEL, uinput.REL_WHEEL_HI_RES,
            uinput.REL_HWHEEL, uinput.REL_HWHEEL_HI_RES,
            uinput.KEY_LEFTMETA, uinput.KEY_UP, uinput.KEY_DOWN, 
            uinput.KEY_LEFT, uinput.KEY_RIGHT,
            uinput.KEY_LEFTALT, uinput.KEY_F10
        ])

        # Get device specific abs info
        abs_x_info = self.dev.absinfo(ecodes.ABS_X)
        abs_y_info = self.dev.absinfo(ecodes.ABS_Y)
        self.min_x, self.max_x = abs_x_info.min, abs_x_info.max
        self.min_y, self.max_y = abs_y_info.min, abs_y_info.max
        self.last_known_pos = {"x": self.min_x, "y": self.min_y}

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.v_mouse:
            for btn in [uinput.BTN_LEFT, uinput.BTN_RIGHT, uinput.BTN_MIDDLE]:
                self.v_mouse.emit(btn, 0)
            self.v_mouse.syn()
        if self.dev:
            try:
                self.dev.ungrab()
            except:
                pass

    def update_config(self, key, value):
        if key in self.config:
            self.config[key] = value

    # --- Helpers ---
    def _clamp(self, n, minn, maxn):
        return max(min(maxn, n), minn)

    def _same_sign(self, a, b):
        return (a >= 0 and b >= 0) or (a < 0 and b < 0)

    def _compute_centroid(self, active_slots_list):
        if not active_slots_list: return None
        xs = [s["x"] for s in active_slots_list if s["x"] is not None]
        ys = [s["y"] for s in active_slots_list if s["y"] is not None]
        if not xs or not ys: return None
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _compute_spread(self, active_slots_list, centroid):
        if not active_slots_list or not centroid: return 0
        total_dist = 0
        cx, cy = centroid
        for s in active_slots_list:
            if s["x"] is None or s["y"] is None: continue
            dist = math.hypot(s["x"] - cx, s["y"] - cy)
            total_dist += dist
        return total_dist / len(active_slots_list)

    def _reset_scroll_state(self):
        self.acc_wheel_hires_x = 0.0
        self.acc_wheel_hires_y = 0.0
        self.scroll_velocity_x = 0.0
        self.scroll_velocity_y = 0.0
        self.active_scroll_axis = None

    def _update_buttons(self):
        if self.is_scrolling:
            want_left = False
            want_right = False
        else:
            want_left = self.phys_left_down or self.virtual_left_down
            want_right = self.phys_right_down or self.virtual_right_down
            
        if want_left != self.last_emitted_left:
            self.v_mouse.emit(uinput.BTN_LEFT, 1 if want_left else 0)
            self.last_emitted_left = want_left
        if want_right != self.last_emitted_right:
            self.v_mouse.emit(uinput.BTN_RIGHT, 1 if want_right else 0)
            self.last_emitted_right = want_right
        self.v_mouse.syn()

    def _set_virtual_buttons(self, mode):
        target_left = (mode == 'left')
        target_right = (mode == 'right')
        if self.is_scrolling:
            target_left = target_right = False
        if target_left and self.click_lock_active: return 
        changed = False
        if self.virtual_left_down != target_left:
            self.virtual_left_down = target_left
            changed = True
        if self.virtual_right_down != target_right:
            self.virtual_right_down = target_right
            changed = True
        if changed:
            self._update_buttons()

    def _emit_move(self, dx, dy):
        lim = self.config["max_movement_per_step"]
        dx = int(self._clamp(dx, -lim, lim))
        dy = int(self._clamp(dy, -lim, lim))
        if dx != 0: self.v_mouse.emit(uinput.REL_X, dx)
        if dy != 0: self.v_mouse.emit(uinput.REL_Y, dy)
        if dx != 0 or dy != 0: self.v_mouse.syn()

    def _emit_scroll(self, dx, dy):
        spd = self.config["scroll_speed"]
        lim = self.config["scroll_max_step"]

        if self.acc_wheel_hires_y != 0 and not self._same_sign(dy, self.acc_wheel_hires_y):
            self.acc_wheel_hires_y = 0.0
        raw_val_y = dy * spd
        raw_val_y = self._clamp(raw_val_y, -lim, lim)
        self.acc_wheel_hires_y += raw_val_y
        emit_hires_y = int(self.acc_wheel_hires_y)
        if emit_hires_y != 0:
            self.v_mouse.emit(uinput.REL_WHEEL_HI_RES, emit_hires_y)
            self.v_mouse.emit(uinput.REL_WHEEL, int(emit_hires_y / 120)) 
            self.acc_wheel_hires_y -= emit_hires_y

        dx = -dx 
        if self.acc_wheel_hires_x != 0 and not self._same_sign(dx, self.acc_wheel_hires_x):
            self.acc_wheel_hires_x = 0.0
        raw_val_x = dx * spd
        raw_val_x = self._clamp(raw_val_x, -lim, lim)
        self.acc_wheel_hires_x += raw_val_x
        emit_hires_x = int(self.acc_wheel_hires_x)
        if emit_hires_x != 0:
            self.v_mouse.emit(uinput.REL_HWHEEL_HI_RES, emit_hires_x)
            self.v_mouse.emit(uinput.REL_HWHEEL, int(emit_hires_x / 120))
            self.acc_wheel_hires_x -= emit_hires_x
        if emit_hires_y != 0 or emit_hires_x != 0:
            self.v_mouse.syn()

    def _click_left(self):
        if not self.phys_left_down and not self.phys_right_down and not self.is_scrolling:
            self.v_mouse.emit(uinput.BTN_LEFT, 1); self.v_mouse.syn()
            self.v_mouse.emit(uinput.BTN_LEFT, 0); self.v_mouse.syn()

    def _trigger_tile(self, key):
        self.v_mouse.emit(uinput.KEY_LEFTMETA, 1)
        self.v_mouse.emit(key, 1)
        self.v_mouse.syn()
        time.sleep(0.05)
        self.v_mouse.emit(uinput.KEY_LEFTMETA, 0)
        self.v_mouse.emit(key, 0)
        self.v_mouse.syn()
        self.last_swipe_time = time.time()
        self.swipe_acc_x = 0.0
        self.swipe_acc_y = 0.0
        
    def _trigger_maximize(self):
        self.v_mouse.emit(uinput.KEY_LEFTALT, 1)
        self.v_mouse.emit(uinput.KEY_F10, 1)
        self.v_mouse.syn()
        time.sleep(0.05)
        self.v_mouse.emit(uinput.KEY_LEFTALT, 0)
        self.v_mouse.emit(uinput.KEY_F10, 0)
        self.v_mouse.syn()
        self.last_swipe_time = time.time()
        self.pinch_acc = 0.0

    def _handle_syn(self):
        # PALM REJECTION
        active_dict = {
            i: s for i, s in self.slots.items() 
            if s.get("active") and not s.get("is_palm", False)
        }
        active_list = list(active_dict.values())
        current_active_slots = set(active_dict.keys())
        num_active = len(active_list)
        
        target_ids = current_active_slots
        target_list = active_list

        if self.using_mt and target_list:
            c = self._compute_centroid(target_list)
            if c: self.last_known_pos["x"], self.last_known_pos["y"] = c

        # --- STATE MANAGEMENT ---
        if len(self.prev_active_slots) == 1 and num_active == 2:
            new_ids = current_active_slots - self.prev_active_slots
            old_ids = self.prev_active_slots
            if new_ids and old_ids:
                new_id, old_id = list(new_ids)[0], list(old_ids)[0]
                if self.slots[new_id]["y"] is not None and self.slots[old_id]["y"] is not None:
                    self.active_click_mode = 'left' if self.slots[new_id]["y"] < self.slots[old_id]["y"] else 'right'
                else: self.active_click_mode = None
        elif num_active < 2:
            self.active_click_mode = None

        self.prev_active_slots = current_active_slots

        if num_active < 3:
            self.three_finger_lock = False

        if self.prev_num_fingers == 0 and num_active > 0:
            self.tap_start_time = time.time()
            self.tap_acc_movement = 0.0
            self.is_potential_tap = True
            self.deadzone_broken = False
            self.first_finger_time = time.time()
            self.is_scrolling = False
            self._reset_scroll_state()
            self.swipe_acc_x = 0.0
            self.swipe_acc_y = 0.0
            self.pinch_acc = 0.0
            self.prev_spread = None

        if self.prev_num_fingers == 1 and num_active == 0:
            if self.is_potential_tap and (time.time() - self.tap_start_time) < self.config["tap_max_duration"]:
                if self.tap_acc_movement < self.config["tap_max_movement"]: 
                    self._click_left()
            self.is_potential_tap = False
            if time.time() - self.last_scroll_update > self.config["scroll_inertia_timeout"]:
                self.scroll_velocity_x = self.scroll_velocity_y = 0.0

        if num_active >= 2:
            if not self.is_scrolling and (time.time() - self.first_finger_time) < self.config["scroll_trigger_window"]:
                self.is_scrolling = True
                self.is_potential_tap = False
                self.active_click_mode = None
                self._reset_scroll_state()
        else:
            if self.is_scrolling:
                self.is_scrolling = False
                self.is_potential_tap = False
                self.active_scroll_axis = None 
                self.last_scroll_stop_time = time.time()
            # Reset pinch state when not 3 fingers
            self.pinch_acc = 0.0
            self.prev_spread = None

        if target_ids != self.prev_target_ids:
            self.prev_target_ids = target_ids
            self.prev_num_fingers = num_active
            self.prev_centroid = self._compute_centroid(target_list) if target_list else None
            self.prev_spread = self._compute_spread(target_list, self.prev_centroid) if target_list and num_active == 3 else None
            self.remain_x = 0.0
            self.remain_y = 0.0
            self._set_virtual_buttons(self.active_click_mode)
            return

        # --- MOVEMENT LOGIC ---
        if self.using_mt and target_list:
            centroid = self._compute_centroid(target_list)
            if centroid is None or self.prev_centroid is None:
                self.prev_centroid = centroid
                return
            
            ratio = self.config.get("drag_scale_ratio", 1.0)
            current_scale = self.config["scale"]

            raw_dx = (centroid[0] - self.prev_centroid[0]) / current_scale
            raw_dy = (centroid[1] - self.prev_centroid[1]) / current_scale

            if num_active == 3 and self.config.get("tiling_enabled", False):
                if self.three_finger_lock:
                    self.prev_centroid = centroid
                    return

                if time.time() - self.last_swipe_time > self.config["swipe_cooldown"]:
                    # 1. Update Pinch
                    current_spread = self._compute_spread(target_list, centroid)
                    if self.prev_spread is not None:
                        spread_diff = current_spread - self.prev_spread
                        self.pinch_acc += spread_diff
                        
                        pinch_thresh = self.config["pinch_threshold"]
                        # Check Pinch FIRST
                        if abs(self.pinch_acc) > pinch_thresh:
                            self._trigger_maximize()
                            self.three_finger_lock = True
                            self.prev_spread = current_spread
                            self.prev_centroid = centroid
                            return

                    self.prev_spread = current_spread

                    # 2. Update Swipe (only if pinch didn't trigger)
                    self.swipe_acc_x += raw_dx
                    self.swipe_acc_y += raw_dy
                    thresh = self.config["swipe_threshold"]
                    
                    if abs(self.swipe_acc_x) > thresh:
                        if self.swipe_acc_x > 0: self._trigger_tile(uinput.KEY_RIGHT)
                        else: self._trigger_tile(uinput.KEY_LEFT)
                        self.three_finger_lock = True
                    elif abs(self.swipe_acc_y) > thresh:
                        if self.swipe_acc_y > 0: self._trigger_tile(uinput.KEY_DOWN)
                        else: self._trigger_tile(uinput.KEY_UP)
                        self.three_finger_lock = True
                
                self.prev_centroid = centroid
                return 

            if self.active_click_mode:
                raw_dx *= ratio
                raw_dy *= ratio
                
            if self.is_scrolling:
                abs_x, abs_y = abs(raw_dx), abs(raw_dy)
                if self.active_scroll_axis is None:
                    if abs_y > abs_x: self.active_scroll_axis = 'y'; raw_dx = 0
                    elif abs_x > abs_y: self.active_scroll_axis = 'x'; raw_dy = 0
                elif self.active_scroll_axis == 'y':
                    if abs_x > abs_y * self.config["scroll_lock_ratio"]: self.active_scroll_axis = 'x'; raw_dx = 0 
                    else: raw_dx = 0
                elif self.active_scroll_axis == 'x':
                    if abs_y > abs_x * self.config["scroll_lock_ratio"]: self.active_scroll_axis = 'y'; raw_dx = 0
                    else: raw_dy = 0

                self.scroll_velocity_x, self.scroll_velocity_y = raw_dx, raw_dy
                self.last_scroll_update = time.time()
                self._emit_scroll(raw_dx, raw_dy)
                self._set_virtual_buttons(None)
            else:
                if (time.time() - self.last_scroll_stop_time) < self.config["scroll_exit_cooldown"]:
                    self.prev_centroid = centroid
                    return

                self.tap_acc_movement += abs(raw_dx) + abs(raw_dy)

                # --- Deadzone Implementation ---
                if not self.deadzone_broken:
                    if self.tap_acc_movement > self.config["deadzone_threshold"]:
                        self.deadzone_broken = True
                    else:
                        self.prev_centroid = centroid
                        return

                self.remain_x += raw_dx
                self.remain_y += raw_dy
                step_x, step_y = int(self.remain_x), int(self.remain_y)
                self.remain_x -= step_x
                self.remain_y -= step_y
                
                self._emit_move(step_x, step_y)
                self._set_virtual_buttons(self.active_click_mode)

            self.prev_centroid = centroid
        else:
            self.prev_centroid = None
            self._set_virtual_buttons(None)
            if self.is_scrolling:
                self.is_scrolling = False
                self.active_scroll_axis = None
                self.last_scroll_stop_time = time.time()

    def _loop(self):
        # Reset runtime state vars
        self.slots = {}
        self.current_slot = 0
        self.pending_update = False
        self.using_mt = False
        self.prev_centroid = None
        self.prev_num_fingers = 0
        self.prev_target_ids = set()
        self.prev_active_slots = set()
        self.virtual_left_down = False
        self.virtual_right_down = False
        self.phys_left_down = False  
        self.phys_right_down = False 
        self.last_emitted_left = False
        self.last_emitted_right = False
        self.click_lock_active = False
        self.tap_start_time = 0.0
        self.tap_acc_movement = 0.0
        self.is_potential_tap = False
        self.deadzone_broken = False
        self.is_scrolling = False
        self.active_scroll_axis = None 
        self.first_finger_time = 0.0
        self.acc_wheel_hires_x = 0.0
        self.acc_wheel_hires_y = 0.0
        self.scroll_velocity_x = 0.0
        self.scroll_velocity_y = 0.0
        self.last_scroll_update = 0.0
        self.last_scroll_stop_time = 0.0
        self.active_click_mode = None
        self.prev_active_slots = set()
        self.swipe_acc_x = 0.0
        self.swipe_acc_y = 0.0
        self.pinch_acc = 0.0
        self.prev_spread = None
        self.three_finger_lock = False

        # Recalculate Region based on dynamic max_x/y
        self.rc_min_x = self.max_x - (self.max_x - self.min_x) * self.config["rc_region_width"]
        self.rc_min_y = self.max_y - (self.max_y - self.min_y) * self.config["rc_region_height"]

        while self.running:
            # removed keyboard fd from select
            fds = [self.dev.fd]
            r, w, x = select.select(fds, [], [], 0.015)   

            if self.dev.fd in r:
                for ev in self.dev.read():
                    if ev.type == ecodes.EV_KEY:
                        if ev.code == ecodes.BTN_LEFT:
                            is_press = (ev.value == 1)
                            if is_press:
                                self.click_lock_active = True
                                self.scroll_velocity_x = self.scroll_velocity_y = 0.0
                                active_dict = {i: s for i, s in self.slots.items() if s.get("active") and not s.get("is_palm", False)}
                                
                                if active_dict:
                                    target_slot = max(active_dict, key=lambda i: self.slots[i]["y"])
                                    lx = active_dict[target_slot]["x"]
                                    ly = active_dict[target_slot]["y"]
                                else:
                                    lx, ly = self.last_known_pos["x"], self.last_known_pos["y"]
                                
                                if lx > self.rc_min_x and ly > self.rc_min_y:
                                    self.phys_right_down = True
                                else:
                                    self.phys_left_down = True
                                self._update_buttons()
                            else:
                                self.click_lock_active = False
                                self.phys_left_down = self.phys_right_down = False
                                self._update_buttons()
                        elif ev.code in [ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE]:
                            self.v_mouse.emit(ev.code, ev.value); self.v_mouse.syn()

                    elif ev.type == ecodes.EV_ABS:
                        a, val = ev.code, ev.value
                        if a == ecodes.ABS_MT_SLOT:
                            self.current_slot = val
                            if self.current_slot not in self.slots: 
                                self.slots[self.current_slot] = {"x": None, "y": None, "active": False, "size": 0, "tool": 0, "is_palm": False}
                        elif a == ecodes.ABS_MT_TRACKING_ID:
                            self.using_mt = True
                            if val == -1:
                                if self.current_slot in self.slots: self.slots[self.current_slot]["active"] = False
                            else:
                                if self.current_slot not in self.slots: 
                                    self.slots[self.current_slot] = {"x": None, "y": None, "active": True, "size": 0, "tool": 0, "is_palm": False}
                                else: 
                                    self.slots[self.current_slot]["active"] = True
                            self.pending_update = True
                        elif a == ecodes.ABS_MT_POSITION_X:
                            if self.current_slot not in self.slots:
                                self.slots[self.current_slot] = {"x": val, "y": None, "active": True, "size": 0, "tool": 0, "is_palm": False}
                            self.slots[self.current_slot]["x"] = val
                            self.pending_update = True
                        elif a == ecodes.ABS_MT_POSITION_Y:
                            if self.current_slot not in self.slots:
                                self.slots[self.current_slot] = {"x": None, "y": val, "active": True, "size": 0, "tool": 0, "is_palm": False}
                            self.slots[self.current_slot]["y"] = val
                            self.pending_update = True
                        
                        elif a == ecodes.ABS_MT_TOOL_TYPE:
                            if self.current_slot not in self.slots:
                                self.slots[self.current_slot] = {"x": None, "y": None, "active": True, "size": 0, "tool": val, "is_palm": False}
                            self.slots[self.current_slot]["tool"] = val
                            
                            is_palm_tool = (val == 2) 
                            size = self.slots[self.current_slot].get("size", 0)
                            is_large = size > self.config["palm_size_threshold"]
                            
                            self.slots[self.current_slot]["is_palm"] = is_palm_tool or is_large
                            self.pending_update = True

                        elif a == ecodes.ABS_MT_TOUCH_MAJOR:
                            if self.current_slot not in self.slots:
                                self.slots[self.current_slot] = {"x": None, "y": None, "active": True, "size": val, "tool": 0, "is_palm": False}
                            self.slots[self.current_slot]["size"] = val
                            
                            tool = self.slots[self.current_slot].get("tool", 0)
                            is_palm_tool = (tool == 2)
                            is_large = val > self.config["palm_size_threshold"]

                            self.slots[self.current_slot]["is_palm"] = is_palm_tool or is_large
                            self.pending_update = True

                    elif ev.type == ecodes.EV_SYN and ev.code == ecodes.SYN_REPORT:
                        if self.pending_update:
                            self._handle_syn()
                            self.pending_update = False

            active_fingers = sum(1 for s in self.slots.values() if s.get("active") and not s.get("is_palm", False))
            flick_threshold = 0.8
            if not self.is_scrolling and active_fingers == 0 and (abs(self.scroll_velocity_x) > flick_threshold or abs(self.scroll_velocity_y) > flick_threshold):
                cutoff = self.config["scroll_inertia_cutoff"]
                friction = self.config["scroll_inertia_friction"]
                if abs(self.scroll_velocity_x) > cutoff or abs(self.scroll_velocity_y) > cutoff:
                    self._emit_scroll(self.scroll_velocity_x, self.scroll_velocity_y)
                    self.scroll_velocity_x *= friction
                    self.scroll_velocity_y *= friction