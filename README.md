# LED CNTRL — Windows RGB lighting controller

**Created by Keynes**  
Version: 0.3.3 prototype

LED CNTRL is an offline-first Windows desktop controller for ESP32-driven addressable LEDs. Its UI uses a dark charcoal palette, muted gold accents, a sidebar dashboard, and an animated two-pass gold LED chase at startup.

## Current features

- Dark/gold desktop dashboard inspired by premium gaming control panels
- USB serial port discovery and connection
- Newline-terminated comma-separated RGB frame output (R,G,B repeated for each LED)
- Screen Sync via monitor-edge color sampling
- Solid Colour, Rainbow, Breathing, and Gold Chase effects
- Brightness control\n- Dark Armoury Crate-inspired dashboard layout\n- Dark screen regions below the luminance threshold turn the corresponding LEDs fully off\n- Closing the window hides it to the system tray when enabled; tray menu provides Open and Exit\n- CPU/RAM usage tiles; GPU telemetry is shown only when NVIDIA SMI is available
- Editable total LED count and top/right/bottom/left segment counts
- Local profiles and JSON settings export
- Windows startup preference and startup animation settings
- Close-to-system-tray behavior (when enabled and a system tray is available)
- Screen-edge black cutoff: near-black sampled zones turn the corresponding LED fully off
- No cloud account or internet required after dependencies are installed

## Important compatibility notes

This is a **prototype source package**, not a verified commercial release. It has not been built or hardware-tested in this environment.

The app expects a compatible ESP32 firmware protocol:
- USB serial at the selected baud rate (default 115200)
- Each frame is one line containing exactly 3 × LED-count decimal channel values separated by commas
- Channel order: RGB
- Example for two LEDs: `255,0,0,0,255,0` followed by newline

The existing 42-LED firmware should use the same LED count and ordering. A different LED chipset or firmware may require a compatible firmware build. The "data pin" in LED Layout is a reference setting; changing it in the app does not reflash firmware or physically change the ESP32 pin.

## Run from source

1. Install Python 3.11+ on Windows and enable **Add Python to PATH**.
2. Extract this folder.
3. Double-click `run_led_cntrl.bat`.
4. Connect the ESP32 over USB.
5. Close Arduino Serial Monitor or any other program using the same COM port.
6. In LED CNTRL → Devices, refresh ports, select the ESP32 COM port, and click Connect.
7. Start Screen Sync or select an effect.

The first launch installs Python dependencies and therefore needs internet access. After installation, lighting control itself runs locally.

## Build a Windows application

1. Run `build_windows.bat`.
2. Output is created under `dist\LED CNTRL\`.
3. Install [Inno Setup](https://jrsoftware.org/isinfo.php).
4. Open `LED_CNTRL.iss` in Inno Setup and compile it.
5. Installer output is written to `installer_output\`.

A signed installer, automatic updater, tray-icon behavior, robust hardware testing, multi-monitor discovery, and broad firmware compatibility should be completed before public commercial distribution.

## Initial LED layout

- Total: 42
- Top: 15
- Right: 8
- Bottom: 11
- Left: 8
- Reference data pin: GPIO 2
- Baud: 115200
- Default order in preview/capture: top → right → bottom → left

## Troubleshooting

- **No ports found:** reconnect the ESP32, check Windows Device Manager, and install the correct USB-serial driver.
- **Port busy:** close Arduino Serial Monitor and other serial apps.
- **No physical LEDs:** check 5V supply, common ground, data wiring, firmware chipset/order, and LED count.
- **Screen Sync error:** ensure dependencies installed successfully; screen capture is done locally using `mss`.
- **LED colors/order incorrect:** confirm firmware uses RGB input and the same physical LED ordering. Some strips are GRB at the chipset level; the firmware should convert the received RGB values to the strip's expected order.

## Safety

Do not power a long LED strip through the ESP32's USB/VIN pin. Use a suitable regulated 5V supply for the LED strip, connect supply ground to ESP32 ground, and ensure the data signal is electrically compatible with the strip.


## Latest behavior update

- In Screen Sync, each edge sample with estimated luminance below 18/255 is sent as RGB black so that LED turns off when its corresponding screen-edge region is near-black. This cutoff is fixed in this prototype.
- When **Minimize to system tray when closing** is enabled, clicking the window close button hides the window instead of exiting. Lighting continues in the background. Use the tray icon menu → **Exit LED CNTRL** to fully exit. If Windows system tray is unavailable, the close button exits normally.


## Automatic USB port management
The app checks available COM ports every few seconds when disconnected. It preserves the active connection while connected, and can automatically reconnect to the last selected port when it reappears. These options can be changed in Settings. Manual Refresh, Connect, and Disconnect controls remain available.


## Fix: console windows appearing during app use
Version 0.1.1 hides the Windows console for the periodic `nvidia-smi` telemetry query. The app is built with PyInstaller's `--windowed` mode, so opening the app should not open repeated command prompt windows. Rebuild and recompile the installer to apply this fix.


## Dashboard UI refresh — v0.2.0
The Home dashboard has been redesigned around the supplied visual reference: compact left navigation, top account/tooltip area, multi-card hardware dashboard, health/support cards, and platform settings. Metrics are sourced from available local telemetry; unavailable readings are labeled rather than fabricated. The dashboard is scrollable on smaller displays.


## Custom perimeter layout editor — v0.2.1
The LED Layout page now includes a live monitor-perimeter preview, editable top/right/bottom/left LED counts, a total-count validation, configurable starting corner and strip direction, and a reset-to-42-LEDs option. The corner/direction choices are saved in settings; firmware LED ordering must still match the physical strip.


## v0.2.3 Brightness persistence update
- Brightness slider changes apply immediately during Screen Sync and visual effects.
- Every slider change is saved to `%APPDATA%\LED CNTRL\settings.json`, so brightness is restored on the next launch.
- The slider tooltip explains that changes save automatically.

## LED CNTRL v0.3.0 — Offline AI Lighting Assistant

- **Adaptive screen analysis:** locally estimates average screen luminance and classifies scenes as dark, balanced, or bright.
- **Automatic brightness:** gently scales Screen Sync brightness according to sampled screen luminance; the manual brightness slider remains the master limit.
- **White-balance calibration:** separate red, green, and blue gain sliders. These compensate for a color cast but cannot repair a physically failed LED channel or make a non-RGB strip emit true white.
- **Lighting profiles:** Adaptive, Gaming, Movie, and Neutral presets for Screen Sync behavior.
- **Command assistant:** offline text commands such as `brightness 45`, `gaming mode`, `movie mode`, `screen sync`, `white`, `blue`, `reset white balance`, and `lights off`.
- **Optional offline voice input:** the Voice command button supports local Vosk speech recognition when the optional `vosk` and `sounddevice` packages and a local model are installed. No audio is sent to a cloud service. Place an extracted English Vosk model folder at `%APPDATA%\\LED CNTRL\\vosk-model`.
- **Saved preferences:** AI toggles, profile, and white-balance gains are persisted in `%APPDATA%\\LED CNTRL\\settings.json`.

The “AI” scene analysis is a lightweight local adaptive heuristic rather than a trained vision model or cloud service. Gaming/movie modes adjust the lighting response; they do not inspect game processes. Optional voice dependencies are not installed by default. Install them manually with `py -3 -m pip install vosk sounddevice`, then add a compatible Vosk model folder as described above.


## v0.3.3 mapping and startup update

- Physical LED mapping default is Bottom-right, then bottom toward bottom-left, up the left side, across the top, and down the right side (42 LEDs: top 15, right 8, bottom 11, left 8).
- The matching traversal setting is **Clockwise** in the app's perimeter convention.
- Settings now include **Minimize to system tray on startup** and **Start LED CNTRL when Windows starts**.
- Windows startup uses a per-user Startup-folder shortcut. The `pywin32` dependency is installed on Windows for shortcut creation.
- Startup minimization requires a working Windows system tray; if no tray is available, the app stays visible.


## PC Audio Smart Sync (v0.4.0)
- New **Sound Sync** page captures Windows PC output audio using local loopback capture (no microphone and no internet required).
- Smart Sync analyses bass, midrange, treble and overall audio energy to animate the 42 LEDs.
- **Screen + Sound** blends monitor-edge colors with audio energy.
- Controls: sensitivity, bass intensity, reaction speed, min/max brightness, and Neon/Warm/Cool palettes.
- Install `requirements.txt` to include the `soundcard` loopback dependency. If Windows audio loopback is unavailable on a device, select a normal Windows output device and retry.


### Monitor switching (v0.4.2)
The Screen Sync page detects connected displays and lists each display with its resolution. Selecting another display saves the selection and restarts the active screen-capture worker, so Screen Sync and Screen + Sound both switch to the selected display.
