# test_server.py
import asyncio
import unittest
import server
import time

class TestChatServer(unittest.TestCase):
    def setUp(self):
        self.server = server.ChatServer('localhost', 8889)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def test_create_room(self):
        """Тест создания комнаты"""
        room = self.server.create_room("test_room")
        self.assertEqual(room.name, "test_room")
        self.assertIn("test_room", self.server.rooms)

    def test_room_broadcast(self):
        """Тест рассылки сообщений в комнате"""
        room = self.server.create_room("test_room")
        
        # Создаем mock клиентов
        class MockClient:
            def __init__(self, name):
                self.username = name
                self.messages = []
            
            async def send_message(self, message):
                self.messages.append(message)
        
        client1 = MockClient("user1")
        client2 = MockClient("user2")
        
        room.add_client(client1)
        room.add_client(client2)
        
        # Тестируем broadcast
        test_message = {'type': 'message', 'message': 'Hello', 'username': 'test'}
        self.loop.run_until_complete(room.broadcast(test_message))
        
        self.assertEqual(len(client1.messages), 1)
        self.assertEqual(len(client2.messages), 1)
        self.assertEqual(client1.messages[0]['message'], 'Hello')

    def test_room_history(self):
        """Тест истории сообщений"""
        room = self.server.create_room("test_room")
        
        # Добавляем сообщения
        for i in range(150):
            room.history.append({'message': f'test_{i}'})
        
        # Проверяем ограничение истории
        self.assertEqual(len(room.history), 100)
        self.assertEqual(room.history[0]['message'], 'test_50')

class TestChatIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    async def async_setup(self):
        self.server = server.ChatServer('localhost', 8890)
        self.server_task = asyncio.create_task(self.server.start_server())
        await asyncio.sleep(0.1)  # Даем серверу время запуститься

    async def async_teardown(self):
        self.server_task.cancel()
        try:
            await self.server_task
        except asyncio.CancelledError:
            pass

    def test_client_connection(self):
        """Тест подключения клиента"""
        async def test():
            await self.async_setup()
            
            try:
                # Пытаемся подключиться
                reader, writer = await asyncio.open_connection('localhost', 8890)
                
                # Отправляем аутентификацию
                auth_msg = json.dumps({'type': 'auth', 'username': 'test_user'}).encode() + b'\n'
                writer.write(auth_msg)
                await writer.drain()
                
                # Читаем ответ
                data = await reader.readline()
                response = json.loads(data.decode())
                
                self.assertEqual(response['type'], 'auth_success')
                self.assertIn('test_user', response['message'])
                
                writer.close()
                await writer.wait_closed()
                
            finally:
                await self.async_teardown()
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(test())

if __name__ == '__main__':
    unittest.main()