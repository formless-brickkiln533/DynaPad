import time
import os
import json
from backend import DynaPadCore

CONFIG_FILE = os.path.expanduser("~/.DynaPad_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return None

def main():
    core = DynaPadCore()
    print("dynapad service active")    

    while True:
        conf = load_config()
        if conf:
            # Sync sensitivity/scroll even if running
            core.update_config("scale", conf.get("scale", 4))
            core.update_config("scroll_speed", conf.get("scroll_speed", 10.0))
            core.update_config("drag_scale_ratio", conf.get("drag_scale_ratio", 1.0))
            core.update_config("tiling_enabled", conf.get("tiling_enabled", False)) # synced here

            # The Logic Wire
            target_state = conf.get("enabled", False)
            
            if target_state and not core.running:
                print("Switch turned ON: Grabbing touchpad...")
                core.start()
            elif not target_state and core.running:
                print("Switch turned OFF: Releasing touchpad...")
                core.stop()
        
        time.sleep(0.5) # Poll the config twice a second

if __name__ == "__main__":
    main()