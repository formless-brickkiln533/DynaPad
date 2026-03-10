#!/bin/bash
# dynapad clean installer

project_dir=$(pwd)
venv_path="$project_dir/.venv"
python_bin="$venv_path/bin/python"

# setup venv
python3 -m venv .venv --system-site-packages
$venv_path/bin/pip install evdev python-uinput

# systemd service
mkdir -p ~/.config/systemd/user/
cat <<EOF > ~/.config/systemd/user/DynaPad.service
[Unit]
Description=DynaPad Background Engine
After=graphical-session.target

[Service]
Type=simple
# we run from project root but add src to path
WorkingDirectory=$project_dir
ExecStart=$python_bin $project_dir/src/service_worker.py
Restart=always
Environment=PYTHONPATH=$project_dir/src

[Install]
WantedBy=default.target
EOF

# desktop file
mkdir -p ~/.local/share/applications/
cat <<EOF > ~/.local/share/applications/DynaPad.desktop
[Desktop Entry]
Name=DynaPad
Exec=$python_bin $project_dir/src/main.py
Icon=input-mouse
Terminal=false
Type=Application
EOF

# permissions (requires sudo)
sudo groupadd -f uinput
sudo usermod -aG input $USER
sudo usermod -aG uinput $USER
echo 'KERNEL=="uinput", MODE="0660", GROUP="uinput", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-DynaPad.rules
echo 'KERNEL=="event*", MODE="660", GROUP="input"' | sudo tee -a /etc/udev/rules.d/99-DynaPad.rules

systemctl --user daemon-reload
systemctl --user enable DynaPad.service
systemctl --user start DynaPad.service
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "done. you may need to RESTART your computer"