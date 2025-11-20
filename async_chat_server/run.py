# run.py
import subprocess
import sys
import time

def start_server():
    """Запуск сервера"""
    print("Starting chat server...")
    subprocess.Popen([sys.executable, "server.py"])

def start_client():
    """Запуск клиента"""
    print("Starting chat client...")
    subprocess.Popen([sys.executable, "client_gui.py"])

if __name__ == "__main__":
    print("Chat Application")
    print("1. Start Server")
    print("2. Start Client")
    print("3. Start Both")
    
    choice = input("Enter choice (1-3): ")
    
    if choice == "1":
        start_server()
    elif choice == "2":
        start_client()
    elif choice == "3":
        start_server()
        time.sleep(1)
        start_client()
    else:
        print("Invalid choice")