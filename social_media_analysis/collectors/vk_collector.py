import os
import re
import sqlite3
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


TOKEN_RE = re.compile(r"\b[а-яА-ЯёЁa-zA-Z0-9_#@]{2,}\b")

STOPWORDS = {
    # RU common
    "и", "в", "на", "с", "что", "это", "а", "но", "же", "у", "из", "не", "то", "за", "по",
    "для", "как", "так", "от", "до", "во", "со", "о", "об", "мы", "вы", "они", "он", "она",
    "его", "ее", "их", "наш", "ваш", "при", "к", "над", "под",
    # EN basic
    "the", "and", "for", "that", "with", "this", "from", "are", "you", "not",
    "have", "has", "was", "but", "they", "your", "all", "can", "like", "just",
    "we", "our", "it", "in", "on", "to", "of", "a", "an", "is", "at", "by",
}


def _preprocess_text(text: str) -> Tuple[List[str], List[str]]:
    t = text.lower()
    hashtags = re.findall(r"#\w+", t)
    tokens = TOKEN_RE.findall(t)
    filtered = [tok for tok in tokens if tok not in STOPWORDS and not tok.startswith("#")]
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


def _vk_api(method: str, params: Dict) -> Dict:
    url = f"https://api.vk.com/method/{method}"
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    payload = r.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload.get("response", {})


def collect_from_groups(
    group_ids: List[int],
    posts_per_group: int = 100,
    top_k_words: int = 50,
    top_k_hashtags: int = 20,
    save_db_path: Optional[str] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict:
    """
    Fetch posts from VK groups (by numeric IDs, without the - sign) and compute stats.
    """
    load_dotenv()
    token = os.getenv("VK_TOKEN")
    if not token:
        raise RuntimeError("Set VK_TOKEN in environment (see README).")

    all_texts: List[str] = []
    for idx, gid in enumerate(group_ids):
        if progress_cb:
            progress_cb(str(gid), idx, len(group_ids))
        # VK uses negative owner_id for groups
        owner_id = -abs(int(gid))
        remaining = posts_per_group
        offset = 0
        while remaining > 0:
            batch = min(remaining, 100)
            params = {
                "owner_id": owner_id,
                "count": batch,
                "offset": offset,
                "access_token": token,
                "v": "5.199",
                "lang": "ru",
            }
            try:
                resp = _vk_api("wall.get", params)
                items = resp.get("items", [])
                if not items:
                    break
                for post in items:
                    txt = post.get("text") or ""
                    if txt:
                        all_texts.append(txt)
                fetched = len(items)
                remaining -= fetched
                offset += fetched
                if fetched < batch:  # no more posts
                    break
            except Exception as e:
                if progress_cb:
                    progress_cb(f"error:{gid} -> {e}", idx + 1, len(group_ids))
                break

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
        "total_texts": len(all_texts),
        "top_words": top_words,
        "top_hashtags": top_hashtags,
    }
