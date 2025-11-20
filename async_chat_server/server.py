# server_fixed.py
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Set, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ChatServer')

class ChatRoom:
    def __init__(self, name: str):
        self.name = name
        self.clients: Set['ChatClient'] = set()
        self.history: List[dict] = []
        self.max_history = 100

    def add_client(self, client: 'ChatClient'):
        self.clients.add(client)
        logger.info(f"Client {client.username} joined room {self.name}")

    def remove_client(self, client: 'ChatClient'):
        self.clients.discard(client)
        logger.info(f"Client {client.username} left room {self.name}")

    async def broadcast(self, message: dict, sender: 'ChatClient' = None):
        """Отправка сообщения всем клиентам в комнате (включая отправителя)"""
        message['timestamp'] = datetime.now().isoformat()
        
        # Добавляем флаг, указывающий что сообщение от самого пользователя
        if sender:
            message['is_self'] = False  # Для всех получателей
        
        self.history.append(message)
        
        # Ограничиваем размер истории
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Рассылаем сообщение всем клиентам в комнате
        tasks = []
        for client in self.clients:
            # Создаем копию сообщения для каждого клиента
            client_message = message.copy()
            
            # Помечаем сообщение как "свое" для отправителя
            if client == sender:
                client_message['is_self'] = True
            else:
                client_message['is_self'] = False
                
            tasks.append(client.send_message(client_message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_others(self, message: dict, sender: 'ChatClient'):
        """Отправка сообщения всем, кроме отправителя (для системных сообщений)"""
        message['timestamp'] = datetime.now().isoformat()
        
        tasks = []
        for client in self.clients:
            if client != sender:
                tasks.append(client.send_message(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

class ChatClient:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.username = None
        self.current_room: ChatRoom = None
        self.address = writer.get_extra_info('peername')
        self.authenticated = False

    async def send_message(self, message: dict):
        """Отправка сообщения клиенту"""
        try:
            data = json.dumps(message).encode() + b'\n'
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending message to {self.username}: {e}")

    async def receive_message(self):
        """Чтение сообщения от клиента"""
        try:
            data = await self.reader.readline()
            if not data:
                return None
            return json.loads(data.decode().strip())
        except Exception as e:
            logger.error(f"Error receiving message from {self.username}: {e}")
            return None

class ChatServer:
    def __init__(self, host: str = 'localhost', port: int = 8888):
        self.host = host
        self.port = port
        self.rooms: Dict[str, ChatRoom] = {}
        self.clients: Set[ChatClient] = set()
        self.message_queue = asyncio.Queue()
        self.file_storage = "uploads"
        
        # Создаем папку для файлов
        os.makedirs(self.file_storage, exist_ok=True)
        
        # Создаем общую комнату по умолчанию
        self.create_room("general")

    def create_room(self, room_name: str) -> ChatRoom:
        """Создание новой комнаты"""
        if room_name not in self.rooms:
            self.rooms[room_name] = ChatRoom(room_name)
            logger.info(f"Created room: {room_name}")
        return self.rooms[room_name]

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Обработка подключения клиента"""
        client = ChatClient(reader, writer)
        self.clients.add(client)
        
        logger.info(f"New connection from {client.address}")
        
        try:
            # Аутентификация
            await self.authenticate_client(client)
            
            # Основной цикл обработки сообщений
            await self.handle_client_messages(client)
            
        except Exception as e:
            logger.error(f"Error handling client {client.username}: {e}")
        finally:
            # Очистка при отключении
            await self.cleanup_client(client)

    async def authenticate_client(self, client: ChatClient):
        """Аутентификация клиента"""
        while not client.authenticated:
            message = await client.receive_message()
            if not message:
                return
            
            if message.get('type') == 'auth':
                username = message.get('username', '').strip()
                if username and len(username) <= 20:
                    # Проверяем уникальность имени пользователя
                    if any(c.username == username for c in self.clients if c.authenticated):
                        await client.send_message({
                            'type': 'auth_error',
                            'message': 'Username already taken'
                        })
                        continue
                    
                    client.username = username
                    client.authenticated = True
                    
                    # Добавляем в общую комнату
                    general_room = self.rooms["general"]
                    general_room.add_client(client)
                    client.current_room = general_room
                    
                    await client.send_message({
                        'type': 'auth_success',
                        'message': f'Welcome {username}!',
                        'username': username
                    })
                    
                    # Уведомляем комнату о новом пользователе (кроме самого пользователя)
                    await general_room.broadcast_to_others({
                        'type': 'system',
                        'message': f'{username} joined the room',
                        'username': 'System'
                    }, client)
                    
                    # Отправляем историю комнаты новому пользователю
                    for msg in general_room.history[-10:]:
                        await client.send_message(msg)
                        
                else:
                    await client.send_message({
                        'type': 'auth_error',
                        'message': 'Invalid username (1-20 characters)'
                    })

    async def handle_client_messages(self, client: ChatClient):
        """Обработка сообщений от клиента"""
        while client.authenticated:
            message = await client.receive_message()
            if not message:
                break
            
            try:
                await self.process_message(client, message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await client.send_message({
                    'type': 'error',
                    'message': 'Error processing message'
                })

    async def process_message(self, client: ChatClient, message: dict):
        """Обработка различных типов сообщений"""
        msg_type = message.get('type')
        
        if msg_type == 'message':
            # Обычное текстовое сообщение - отправляем ВСЕМ в комнате включая отправителя
            if client.current_room:
                await client.current_room.broadcast({
                    'type': 'message',
                    'message': message['message'],
                    'username': client.username
                }, client)  # Передаем отправителя для маркировки сообщения
        
        elif msg_type == 'join_room':
            # Смена комнаты
            room_name = message['room']
            await self.change_room(client, room_name)
        
        elif msg_type == 'list_rooms':
            # Список комнат
            await client.send_message({
                'type': 'room_list',
                'rooms': list(self.rooms.keys())
            })
        
        elif msg_type == 'private_message':
            # Личное сообщение
            await self.send_private_message(client, message)
        
        elif msg_type == 'upload_file':
            # Загрузка файла
            await self.handle_file_upload(client, message)

    async def change_room(self, client: ChatClient, room_name: str):
        """Смена комнаты клиентом"""
        if client.current_room:
            # Уведомляем старую комнату о выходе (кроме самого пользователя)
            await client.current_room.broadcast_to_others({
                'type': 'system',
                'message': f'{client.username} left the room',
                'username': 'System'
            }, client)
            client.current_room.remove_client(client)
        
        # Создаем комнату если не существует
        new_room = self.create_room(room_name)
        new_room.add_client(client)
        client.current_room = new_room
        
        # Уведомляем новую комнату о входе (кроме самого пользователя)
        await new_room.broadcast_to_others({
            'type': 'system',
            'message': f'{client.username} joined the room',
            'username': 'System'
        }, client)
        
        # Отправляем историю новой комнаты только новому пользователю
        for msg in new_room.history[-10:]:
            await client.send_message(msg)
        
        await client.send_message({
            'type': 'room_changed',
            'room': room_name,
            'message': f'You joined room: {room_name}'
        })

    async def send_private_message(self, sender: ChatClient, message: dict):
        """Отправка личного сообщения"""
        target_username = message['target']
        private_msg = message['message']
        
        # Ищем целевого клиента
        target_client = None
        for client in self.clients:
            if client.username == target_username and client.authenticated:
                target_client = client
                break
        
        if target_client:
            # Отправляем получателю
            await target_client.send_message({
                'type': 'private_message',
                'message': private_msg,
                'username': sender.username,
                'timestamp': datetime.now().isoformat(),
                'is_self': False
            })
            
            # Отправляем отправителю (чтобы он видел свое сообщение)
            await sender.send_message({
                'type': 'private_message',
                'message': private_msg,
                'username': sender.username,
                'target': target_username,
                'timestamp': datetime.now().isoformat(),
                'is_self': True
            })
        else:
            # Уведомляем отправителя, что пользователь не найден
            await sender.send_message({
                'type': 'system',
                'message': f'User {target_username} not found or offline',
                'username': 'System'
            })

    async def handle_file_upload(self, client: ChatClient, message: dict):
        """Обработка загрузки файла"""
        filename = message['filename']
        file_data = message['data']  # base64 encoded
        
        # Сохраняем файл
        filepath = os.path.join(self.file_storage, filename)
        try:
            import base64
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(file_data))
            
            # Уведомляем комнату о загруженном файле (включая отправителя)
            if client.current_room:
                await client.current_room.broadcast({
                    'type': 'file_upload',
                    'filename': filename,
                    'username': client.username,
                    'message': f'uploaded file: {filename}'
                }, client)
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            await client.send_message({
                'type': 'error',
                'message': f'File upload failed: {str(e)}'
            })

    async def cleanup_client(self, client: ChatClient):
        """Очистка при отключении клиента"""
        if client.current_room and client.username:
            await client.current_room.broadcast_to_others({
                'type': 'system',
                'message': f'{client.username} left the chat',
                'username': 'System'
            }, client)
            client.current_room.remove_client(client)
        
        self.clients.discard(client)
        
        try:
            client.writer.close()
            await client.writer.wait_closed()
        except Exception:
            pass
        
        logger.info(f"Client {client.username} disconnected")

    async def start_server(self):
        """Запуск сервера"""
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        logger.info(f"Chat server started on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()

async def main():
    server = ChatServer()
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())