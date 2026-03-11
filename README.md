# DynaPad 🖱️

DynaPad is a high-performance Linux background engine and configuration suite designed to modernize the touchpad experience. It replaces traditional hardware clicking with intelligent software-defined touch zones and adds advanced gesture controls. Available for Linux Mint Cinnamon

## The Core Innovation: "Buttonless Clicking"

The main goal of DynaPad is to eradicate the need for physical touchpad buttons. It implements a unique logic-based clicking system that allows you to perform clicks without needing to lift a finger off the Touchpad:

- Virtual Left Click: Triggered by touching with a second finger above where the first one is laying.

- Virtual Right Click: Triggered by touching with a second finger below where the first one is laying.

- Holding and Dragging: As long as you keep both fingers down, you will perform a Hold/Drag.

- Scrolling: If you put both fingers down with a short interval in between, you will be able to Scroll, as you normally would when holding two fingers.

## Other Key Features

- Gestures (3-Finger Tiling): * Horizontal swipe to snap windows (Left/Right/Up/Down) with a 3-finger swipe.

- Pinch-to-Maximize: Use a 3-finger pinch for instant window management, maximizing and unmaximizing.

- Inertial Scrolling: Smooth, physics-based scrolling that continues to glide after you release your fingers.

- Modern GUI: A clean GTK4 / Libadwaita interface to toggle the engine and fine-tune sensitivity, scroll speed, and tiling settings.

- System Integration: Low-level hardware communication using evdev and uinput.

## 🛠️ Tech Stack

Language: Python 3

GUI: GTK4 + Libadwaita

Input Handling: evdev (Event reading) & uinput (Virtual device emulation)

System: systemd (Service management) & udev (Hardware permissions)

## 📦 Installation

DynaPad includes an automated installation script that handles the virtual environment, hardware permissions, and systemd service.

Clone the repository:

    git clone https://github.com/BurgerBayBay/DynaPad.git
    cd DynaPad

Make the installer executable:

    chmod +x install.sh

Run the installer:

    ./install.sh

Reboot: You must reboot your system (or restart your session) for the new udev rules and group permissions to take effect.

## Usage

Launch the DynaPad app from your application menu.

Toggle the Master Switch to activate the background engine.

The engine runs as a user-level systemd service, ensuring it starts automatically on login.
