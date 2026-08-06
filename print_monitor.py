import time
import subprocess
import socket
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
print_server_path = os.path.join(script_dir, "print_server.py")

def is_port_open(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

# Check and start immediately on run
if not is_port_open(5000):
    subprocess.Popen([sys.executable, print_server_path], creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=script_dir)

# Monitor loop every 30 seconds
while True:
    time.sleep(30)
    if not is_port_open(5000):
        try:
            subprocess.Popen([sys.executable, print_server_path], creationflags=subprocess.CREATE_NEW_CONSOLE, cwd=script_dir)
        except Exception as e:
            print("Failed to auto-restart print server:", e)
