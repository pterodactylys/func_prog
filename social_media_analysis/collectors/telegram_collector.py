import os
import re
import sqlite3
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import Message, Channel, Chat
from telethon.tl.functions.messages import GetHistoryRequest

TOKEN_RE = re.compile(r"\b[а-яА-ЯёЁa-zA-Z0-9_#@]{2,}\b")

STOPWORDS = {
    # EN
    "the", "and", "for", "that", "with", "this", "from", "are", "you", "not",
    "have", "has", "was", "but", "they", "your", "all", "can", "like", "just",
    "we", "our", "it", "in", "on", "to", "of", "a", "an", "is", "at", "by",
    # RU (basic)
    "и", "в", "на", "с", "что", "это", "не", "как", "по", "для", "от", "до",
}


def _preprocess_text(text: str) -> Tuple[List[str], List[str]]:
    text = text.lower()
    hashtags = re.findall(r"#\w+", text)
    tokens = TOKEN_RE.findall(text)
    filtered = [t for t in tokens if t not in STOPWORDS and not t.startswith("#") and len(t) > 1]
    return filtered, hashtags


def _save_to_db(word_counts: List[Tuple[str, int]],
                hashtag_counts: List[Tuple[str, int]],
                db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS topics (word TEXT PRIMARY KEY, count INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT PRIMARY KEY, count INTEGER)")
    cur.execute("DELETE FROM topics")
    cur.execute("DELETE FROM hashtags")
    cur.executemany("INSERT INTO topics(word, count) VALUES (?, ?)", word_counts)
    cur.executemany("INSERT INTO hashtags(tag, count) VALUES (?, ?)", hashtag_counts)
    conn.commit()
    conn.close()


async def collect_telegram(
    channels: List[str],
    messages_per_channel: int = 100,
    include_replies: bool = True,
    top_k_words: int = 50,
    top_k_hashtags: int = 20,
    save_db_path: Optional[str] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict:
    """
    Собирает данные из Telegram каналов/чатов
    
    Args:
        channels: Список username или ID каналов/чатов
        messages_per_channel: Количество сообщений для сбора с каждого канала
        include_replies: Включать ли ответы на сообщения
        top_k_words: Количество топовых слов для возврата
        top_k_hashtags: Количество топовых хэштегов для возврата
        save_db_path: Путь для сохранения в SQLite базу
        progress_cb: Callback для отслеживания прогресса
    
    Returns:
        Словарь с результатами анализа
    """
    load_dotenv()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    
    if not api_id or not api_hash:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables.")

    client = TelegramClient('telegram_session', api_id, api_hash)
    await client.start(phone=phone)

    all_texts: List[str] = []
    
    for idx, channel_identifier in enumerate([c.strip() for c in channels if c.strip()]):
        if progress_cb:
            progress_cb(channel_identifier, idx, len(channels))
        
        try:
            # Получаем entity канала/чата
            entity = await client.get_entity(channel_identifier)
            
            messages_collected = 0
            async for message in client.iter_messages(entity, limit=messages_per_channel):
                if not isinstance(message, Message) or not message.text:
                    continue
                
                pieces: List[str] = []
                
                # Добавляем текст сообщения
                if message.text:
                    pieces.append(str(message.text))
                
                # Добавляем ответы если нужно
                if include_replies and message.reply_to:
                    try:
                        reply_msg = await client.get_messages(entity, ids=message.reply_to.reply_to_msg_id)
                        if reply_msg and reply_msg.text:
                            pieces.append(str(reply_msg.text))
                    except Exception:
                        pass
                
                if pieces:
                    all_texts.append("\n".join(pieces))
                    messages_collected += 1
                    
                    if messages_collected >= messages_per_channel:
                        break
                        
        except Exception as e:
            if progress_cb:
                progress_cb(f"error:{channel_identifier} -> {e}", idx + 1, len(channels))

    await client.disconnect()

    # Анализ текста (аналогично оригинальному коду)
    word_counter: Counter = Counter()
    hashtag_counter: Counter = Counter()
    
    for txt in all_texts:
        tokens, hashtags = _preprocess_text(txt)
        word_counter.update(tokens)
        hashtag_counter.update(hashtags)

    top_words = word_counter.most_common(top_k_words)
    top_hashtags = hashtag_counter.most_common(top_k_hashtags)

    if save_db_path:
        _save_to_db(top_words, top_hashtags, save_db_path)

    return {
        "total_messages": len(all_texts),
        "top_words": top_words,
        "top_hashtags": top_hashtags,
        "channels_processed": len([c for c in channels if c.strip()]),
    }


# Синхронная обёртка для удобства
def collect(
    channels: List[str],
    messages_per_channel: int = 100,
    include_replies: bool = True,
    top_k_words: int = 50,
    top_k_hashtags: int = 20,
    save_db_path: Optional[str] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict:
    """
    Синхронная версия функции сбора данных из Telegram
    """
    import asyncio
    return asyncio.run(collect_telegram(
        channels=channels,
        messages_per_channel=messages_per_channel,
        include_replies=include_replies,
        top_k_words=top_k_words,
        top_k_hashtags=top_k_hashtags,
        save_db_path=save_db_path,
        progress_cb=progress_cb
    ))


# Пример использования
if __name__ == "__main__":
    # Настройка переменных окружения в .env файле:
    # TELEGRAM_API_ID=your_api_id
    # TELEGRAM_API_HASH=your_api_hash  
    # TELEGRAM_PHONE=your_phone_number
    
    def progress_callback(channel: str, current: int, total: int):
        print(f"Обрабатывается {channel} ({current}/{total})")
    
    results = collect(
        channels=["telegram", "durov", "tjournal"],  # Пример каналов
        messages_per_channel=50,
        include_replies=True,
        top_k_words=30,
        top_k_hashtags=15,
        save_db_path="telegram_data.db",
        progress_cb=progress_callback
    )
    
    print(f"Обработано сообщений: {results['total_messages']}")
    print(f"Топ слова: {results['top_words'][:10]}")
    print(f"Топ хэштеги: {results['top_hashtags'][:10]}")