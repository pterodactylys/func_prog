# client_gui_fixed.py
import asyncio
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import base64
import os

class ChatClientGUI:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.authenticated = False
        self.username = None
        self.current_room = "general"
        
        self.setup_gui()
        self.async_loop = asyncio.new_event_loop()
        
        # Запускаем asyncio loop в отдельном потоке
        self.thread = threading.Thread(target=self.start_async_loop, daemon=True)
        self.thread.start()

    def setup_gui(self):
        """Настройка графического интерфейса"""
        self.root = tk.Tk()
        self.root.title("Async Chat Client")
        self.root.geometry("900x700")
        
        # Стиль
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TButton', padding=5)
        style.configure('TLabel', background='#f0f0f0')
        
        self.create_login_frame()
        self.create_chat_frame()
        
        # Показываем окно логина сначала
        self.show_login()

    def create_login_frame(self):
        """Создание фрейма авторизации"""
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(expand=True)
        
        # Центральный контейнер
        center_frame = ttk.Frame(self.login_frame)
        center_frame.pack(expand=True, pady=50)
        
        ttk.Label(center_frame, text="Chat Login", font=('Arial', 16, 'bold')).pack(pady=20)
        
        ttk.Label(center_frame, text="Username:", font=('Arial', 12)).pack(pady=10)
        self.username_entry = ttk.Entry(center_frame, width=25, font=('Arial', 12))
        self.username_entry.pack(pady=5)
        self.username_entry.bind('<Return>', lambda e: self.connect_to_server())
        
        ttk.Label(center_frame, text="Server:", font=('Arial', 12)).pack(pady=5)
        server_frame = ttk.Frame(center_frame)
        server_frame.pack(pady=5)
        
        self.server_entry = ttk.Entry(server_frame, width=15, font=('Arial', 12))
        self.server_entry.insert(0, "localhost")
        self.server_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.port_entry = ttk.Entry(server_frame, width=8, font=('Arial', 12))
        self.port_entry.insert(0, "8888")
        self.port_entry.pack(side=tk.LEFT)
        
        self.connect_button = ttk.Button(center_frame, text="Connect to Chat", 
                                       command=self.connect_to_server)
        self.connect_button.pack(pady=20)
        
        self.login_status = ttk.Label(center_frame, text="", foreground='red', font=('Arial', 10))
        self.login_status.pack()

    def create_chat_frame(self):
        """Создание основного фрейма чата"""
        self.chat_frame = ttk.Frame(self.root)
        
        # Верхняя панель
        top_frame = ttk.Frame(self.chat_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(top_frame, text="Room:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.room_entry = ttk.Entry(top_frame, width=15, font=('Arial', 10))
        self.room_entry.insert(0, "general")
        self.room_entry.pack(side=tk.LEFT, padx=5)
        
        self.join_room_button = ttk.Button(top_frame, text="Join Room", 
                                         command=self.join_room)
        self.join_room_button.pack(side=tk.LEFT, padx=5)
        
        self.rooms_button = ttk.Button(top_frame, text="List Rooms", 
                                     command=self.list_rooms)
        self.rooms_button.pack(side=tk.LEFT, padx=5)
        
        self.upload_button = ttk.Button(top_frame, text="Upload File", 
                                      command=self.upload_file)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        # Информация о пользователе и комнате
        info_frame = ttk.Frame(top_frame)
        info_frame.pack(side=tk.RIGHT)
        
        ttk.Label(info_frame, text="User:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.user_label = ttk.Label(info_frame, text="", font=('Arial', 10, 'bold'), foreground='blue')
        self.user_label.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(info_frame, text="Room:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.room_label = ttk.Label(info_frame, text="general", font=('Arial', 10, 'bold'), foreground='green')
        self.room_label.pack(side=tk.LEFT, padx=2)
        
        # Область чата
        chat_container = ttk.Frame(self.chat_frame)
        chat_container.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(chat_container, 
                                                 wrap=tk.WORD, 
                                                 width=80, 
                                                 height=25,
                                                 font=('Arial', 10),
                                                 bg='#fafafa')
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.config(state=tk.DISABLED)
        
        # Панель ввода сообщения
        input_frame = ttk.Frame(self.chat_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.message_entry = ttk.Entry(input_frame, font=('Arial', 12))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # Панель личных сообщений
        pm_frame = ttk.Frame(self.chat_frame)
        pm_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(pm_frame, text="Private to:", font=('Arial', 9)).pack(side=tk.LEFT)
        self.pm_entry = ttk.Entry(pm_frame, width=15, font=('Arial', 9))
        self.pm_entry.pack(side=tk.LEFT, padx=5)
        
        self.pm_message_entry = ttk.Entry(pm_frame, font=('Arial', 10))
        self.pm_message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.pm_message_entry.bind('<Return>', lambda e: self.send_private_message())
        
        self.pm_button = ttk.Button(pm_frame, text="Send PM", 
                                  command=self.send_private_message)
        self.pm_button.pack(side=tk.RIGHT)

    def show_login(self):
        """Показать окно авторизации"""
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.username_entry.focus()

    def show_chat(self):
        """Показать основное окно чата"""
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.message_entry.focus()

    def connect_to_server(self):
        """Подключение к серверу"""
        username = self.username_entry.get().strip()
        host = self.server_entry.get().strip()
        port_str = self.port_entry.get().strip()
        
        if not username:
            self.login_status.config(text="Please enter username")
            return
        
        try:
            port = int(port_str)
        except ValueError:
            self.login_status.config(text="Invalid port number")
            return
        
        self.login_status.config(text="Connecting...", foreground='blue')
        self.connect_button.config(state='disabled')
        
        # Запускаем подключение в asyncio loop
        asyncio.run_coroutine_threadsafe(
            self.async_connect(host, port, username), 
            self.async_loop
        )

    async def async_connect(self, host, port, username):
        """Асинхронное подключение к серверу"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            
            # Отправляем аутентификацию
            auth_message = {
                'type': 'auth',
                'username': username
            }
            await self.send_message_to_server(auth_message)
            
            # Запускаем прием сообщений
            asyncio.create_task(self.receive_messages())
            
        except Exception as e:
            self.root.after(0, lambda: self.show_connection_error(f"Connection error: {str(e)}"))

    def show_connection_error(self, message):
        """Показать ошибку подключения"""
        self.login_status.config(text=message, foreground='red')
        self.connect_button.config(state='normal')

    async def send_message_to_server(self, message: dict):
        """Отправка сообщения на сервер"""
        try:
            data = json.dumps(message).encode() + b'\n'
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            print(f"Error sending message: {e}")

    async def receive_messages(self):
        """Прием сообщений от сервера"""
        try:
            while True:
                data = await self.reader.readline()
                if not data:
                    break
                
                message = json.loads(data.decode().strip())
                self.root.after(0, lambda: self.handle_server_message(message))
                
        except Exception as e:
            print(f"Error receiving messages: {e}")
        finally:
            self.root.after(0, self.connection_lost)

    def handle_server_message(self, message: dict):
        """Обработка сообщений от сервера"""
        msg_type = message.get('type')
        
        if msg_type == 'auth_success':
            self.authenticated = True
            self.username = self.username_entry.get().strip()
            self.user_label.config(text=self.username)
            self.room_label.config(text=self.current_room)
            self.show_chat()
            self.add_to_chat("System", f"Welcome to the chat, {self.username}!", system=True)
            
        elif msg_type == 'auth_error':
            self.login_status.config(text=message['message'])
            self.connect_button.config(state='normal')
            
        elif msg_type == 'message':
            # Определяем стиль сообщения в зависимости от того, наше оно или чужое
            if message.get('is_self', False):
                self.add_to_chat("You", message['message'], own_message=True)
            else:
                self.add_to_chat(message['username'], message['message'])
            
        elif msg_type == 'system':
            self.add_to_chat("System", message['message'], system=True)
            
        elif msg_type == 'private_message':
            # Личные сообщения
            if message.get('is_self', False):
                self.add_to_chat(f"You to {message.get('target', '')}", 
                               message['message'], private_out=True)
            else:
                self.add_to_chat(f"PM from {message['username']}", 
                               message['message'], private_in=True)
            
        elif msg_type == 'room_list':
            rooms = message['rooms']
            room_list = "\n".join(rooms)
            messagebox.showinfo("Available Rooms", f"Available rooms:\n{room_list}")
            
        elif msg_type == 'room_changed':
            self.current_room = message['room']
            self.room_label.config(text=self.current_room)
            self.add_to_chat("System", message['message'], system=True)
            
        elif msg_type == 'file_upload':
            if message.get('is_self', False):
                self.add_to_chat("You", f"uploaded file: {message['filename']}", system=True)
            else:
                self.add_to_chat("System", 
                               f"{message['username']} uploaded file: {message['filename']}", 
                               system=True)

    def add_to_chat(self, username: str, message: str, system=False, 
                   own_message=False, private_in=False, private_out=False):
        """Добавление сообщения в чат с различными стилями"""
        self.chat_area.config(state=tk.NORMAL)
        
        # Вставляем timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_area.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        if system:
            self.chat_area.insert(tk.END, f"*** {message} ***\n", 'system')
        elif own_message:
            self.chat_area.insert(tk.END, f"{username}: ", 'own_username')
            self.chat_area.insert(tk.END, f"{message}\n", 'own_message')
        elif private_in:
            self.chat_area.insert(tk.END, f"{username}: ", 'private_in_username')
            self.chat_area.insert(tk.END, f"{message}\n", 'private_in_message')
        elif private_out:
            self.chat_area.insert(tk.END, f"{username}: ", 'private_out_username')
            self.chat_area.insert(tk.END, f"{message}\n", 'private_out_message')
        else:
            self.chat_area.insert(tk.END, f"{username}: ", 'other_username')
            self.chat_area.insert(tk.END, f"{message}\n")
        
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def send_message(self):
        """Отправка обычного сообщения"""
        if not self.authenticated:
            return
            
        message = self.message_entry.get().strip()
        if message:
            asyncio.run_coroutine_threadsafe(
                self.send_message_to_server({
                    'type': 'message',
                    'message': message
                }),
                self.async_loop
            )
            self.message_entry.delete(0, tk.END)

    def send_private_message(self):
        """Отправка личного сообщения"""
        if not self.authenticated:
            return
            
        target = self.pm_entry.get().strip()
        message = self.pm_message_entry.get().strip()
        
        if target and message:
            asyncio.run_coroutine_threadsafe(
                self.send_message_to_server({
                    'type': 'private_message',
                    'target': target,
                    'message': message
                }),
                self.async_loop
            )
            self.pm_message_entry.delete(0, tk.END)

    def join_room(self):
        """Смена комнаты"""
        if not self.authenticated:
            return
            
        room_name = self.room_entry.get().strip()
        if room_name and room_name != self.current_room:
            asyncio.run_coroutine_threadsafe(
                self.send_message_to_server({
                    'type': 'join_room',
                    'room': room_name
                }),
                self.async_loop
            )

    def list_rooms(self):
        """Запрос списка комнат"""
        if self.authenticated:
            asyncio.run_coroutine_threadsafe(
                self.send_message_to_server({
                    'type': 'list_rooms'
                }),
                self.async_loop
            )

    def upload_file(self):
        """Загрузка файла"""
        if not self.authenticated:
            return
            
        filename = filedialog.askopenfilename(
            title="Select file to upload",
            filetypes=[("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode()
                
                asyncio.run_coroutine_threadsafe(
                    self.send_message_to_server({
                        'type': 'upload_file',
                        'filename': os.path.basename(filename),
                        'data': file_data
                    }),
                    self.async_loop
                )
                
            except Exception as e:
                messagebox.showerror("Upload Error", f"Error uploading file: {e}")

    def connection_lost(self):
        """Обработка потери соединения"""
        if self.authenticated:
            messagebox.showerror("Connection Lost", "Connection to server was lost")
            self.show_login()
            self.authenticated = False
            self.connect_button.config(state='normal')

    def start_async_loop(self):
        """Запуск asyncio loop в отдельном потоке"""
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def run(self):
        """Запуск приложения"""
        # Настраиваем теги для цветного текста
        self.chat_area.tag_config('timestamp', foreground='gray', font=('Arial', 8))
        self.chat_area.tag_config('system', foreground='blue')
        self.chat_area.tag_config('own_username', foreground='dark green', font=('Arial', 10, 'bold'))
        self.chat_area.tag_config('own_message', foreground='green')
        self.chat_area.tag_config('other_username', foreground='dark blue', font=('Arial', 10, 'bold'))
        self.chat_area.tag_config('private_in_username', foreground='purple', font=('Arial', 10, 'bold'))
        self.chat_area.tag_config('private_in_message', foreground='purple')
        self.chat_area.tag_config('private_out_username', foreground='dark magenta', font=('Arial', 10, 'bold'))
        self.chat_area.tag_config('private_out_message', foreground='magenta')
        
        self.root.mainloop()
        
        # Очистка при закрытии
        if self.writer:
            asyncio.run_coroutine_threadsafe(
                self.writer.close(), 
                self.async_loop
            )
        self.async_loop.call_soon_threadsafe(self.async_loop.stop)

if __name__ == "__main__":
    client = ChatClientGUI()
    client.run()