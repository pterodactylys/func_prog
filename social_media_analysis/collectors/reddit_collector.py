import os
import re
import sqlite3
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv

import praw

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


def collect(
    subreddits: List[str],
    posts_per_subreddit: int = 100,
    include_comments: bool = True,
    top_k_words: int = 50,
    top_k_hashtags: int = 20,
    submission_urls: Optional[List[str]] = None,
    save_db_path: Optional[str] = None,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict:
    load_dotenv()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "social-media-analysis-app")
    if not client_id or not client_secret:
        raise RuntimeError("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables.")

    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)

    all_texts: List[str] = []
    for idx, sub in enumerate([s.strip() for s in subreddits if s.strip()]):
        if progress_cb:
            progress_cb(sub, idx, len(subreddits))
        try:
            sr = reddit.subreddit(sub)
            for submission in sr.new(limit=posts_per_subreddit):
                pieces: List[str] = []
                title = getattr(submission, "title", None)
                if title:
                    pieces.append(str(title))
                selftext = getattr(submission, "selftext", None)
                if selftext:
                    pieces.append(str(selftext))
                if include_comments:
                    try:
                        submission.comments.replace_more(limit=0)
                        for c in submission.comments.list():
                            body = getattr(c, "body", None)
                            if body:
                                pieces.append(str(body))
                    except Exception:
                        pass
                if pieces:
                    all_texts.append("\n".join(pieces))
        except Exception as e:
            if progress_cb:
                progress_cb(f"error:{sub} -> {e}", idx + 1, len(subreddits))

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
