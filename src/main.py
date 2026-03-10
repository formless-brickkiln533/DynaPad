import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import json
import os
import subprocess

# using the same config path as the service worker
CONFIG_FILE = os.path.expanduser("~/.DynaPad_config.json")

class DynaPadApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.user.DynaPad')
        self.config = self.load_settings()

    def load_settings(self):
        default_conf = {"scale": 4, "scroll_speed": 10.0, "enabled": False, "tiling_enabled": True}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return default_conf

    def save_settings(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def do_activate(self):
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_title("DynaPad")
        self.win.set_default_size(500, 600)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=32)
        page.set_margin_top(40)
        page.set_margin_bottom(40)
        page.set_margin_start(24)
        page.set_margin_end(24)

        # status
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        status_label = Gtk.Label(label="System Status")
        status_label.add_css_class("title-4")
        
        self.enable_switch = Gtk.Switch()
        self.enable_switch.set_halign(Gtk.Align.CENTER)
        self.enable_switch.set_size_request(90, 45)
        self.enable_switch.set_active(self.config.get("enabled", False))
        self.enable_switch.connect("state-set", self.on_toggle_enabled)
        
        status_box.append(status_label)
        status_box.append(self.enable_switch)
        page.append(status_box)

        # config
        pref_group = Adw.PreferencesGroup(title="Settings")
        
        sens_row = Adw.ActionRow(title="Sensitivity")
        sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 0.1)
        sens_scale.set_value(11 - self.config.get("scale", 4))
        sens_scale.set_hexpand(True)
        sens_scale.set_draw_value(True)
        sens_scale.set_digits(1) 
        sens_scale.connect("value-changed", self.on_config_changed, "scale", True)
        sens_row.add_suffix(sens_scale)
        pref_group.add(sens_row)

        drag_sens_row = Adw.ActionRow(title="Drag Sensitivity", subtitle="Multiplier")
        drag_sens_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 3, 0.5)
        drag_sens_scale.set_value(self.config.get("drag_scale_ratio", 1.5))
        drag_sens_scale.set_hexpand(True)
        drag_sens_scale.set_draw_value(True)
        drag_sens_scale.connect("value-changed", self.on_config_changed, "drag_scale_ratio", False)
        drag_sens_row.add_suffix(drag_sens_scale)
        pref_group.add(drag_sens_row)

        scroll_row = Adw.ActionRow(title="Scroll Speed")
        scroll_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 30, 0.5)
        scroll_scale.set_value(self.config.get("scroll_speed", 10.0))
        scroll_scale.set_hexpand(True)
        scroll_scale.set_draw_value(True)
        scroll_scale.set_digits(1)
        scroll_scale.connect("value-changed", self.on_config_changed, "scroll_speed", False)
        scroll_row.add_suffix(scroll_scale)
        pref_group.add(scroll_row)

        # 3-FINGER TOGGLE HERE
        tile_row = Adw.ActionRow(title="3-Finger Tiling/Maximize", subtitle="Swipe to tile windows, Pinch to maximize")
        tile_switch = Gtk.Switch()
        tile_switch.set_valign(Gtk.Align.CENTER)
        tile_switch.set_active(self.config.get("tiling_enabled", False))
        tile_switch.connect("state-set", self.on_toggle_tiling)
        tile_row.add_suffix(tile_switch)
        pref_group.add(tile_row)

        page.append(pref_group)

        # maintenance/uninstall
        maint_group = Adw.PreferencesGroup(title="Maintenance")
        uninst_row = Adw.ActionRow(title="Uninstall DynaPad", subtitle="removes service and desktop files")
        
        uninst_btn = Gtk.Button(label="Uninstall")
        uninst_btn.set_valign(Gtk.Align.CENTER)
        uninst_btn.add_css_class("destructive-action")
        uninst_btn.connect("clicked", self.confirm_uninstall)
        
        uninst_row.add_suffix(uninst_btn)
        maint_group.add(uninst_row)
        page.append(maint_group)
        
        clamp = Adw.Clamp()
        clamp.set_child(page)
        
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(clamp)
        
        self.win.set_content(toolbar_view)
        self.win.present()

    def on_toggle_enabled(self, switch, state):
        self.config["enabled"] = state
        self.save_settings()
        return False

    def on_toggle_tiling(self, switch, state):
        self.config["tiling_enabled"] = state
        self.save_settings()
        return False

    def on_config_changed(self, scale, key, invert):
        val = scale.get_value()
        self.config[key] = round((11 - val) if invert else val, 2)
        self.save_settings()

    def confirm_uninstall(self, button):
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading="Uninstall DynaPad?",
            body="this will stop the background engine and remove system files. udev rules must be removed manually.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("uninstall", "Uninstall")
        dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self.on_uninstall_response)
        dialog.present()

    def on_uninstall_response(self, dialog, response):
        if response == "uninstall":
            # cleanup based on install.sh paths
            subprocess.run(["systemctl", "--user", "stop", "DynaPad.service"])
            subprocess.run(["systemctl", "--user", "disable", "DynaPad.service"])
            
            paths = [
                "~/.config/systemd/user/DynaPad.service",
                "~/.local/share/applications/DynaPad.desktop",
                CONFIG_FILE
            ]
            for p in paths:
                full_path = os.path.expanduser(p)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            self.quit()

if __name__ == "__main__":
    app = DynaPadApp()
    app.run(None)