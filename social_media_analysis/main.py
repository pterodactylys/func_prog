import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple

from dotenv import load_dotenv

from collectors import reddit_collector, vk_collector, telegram_collector


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Social Media Analysis")
        self.geometry("980x700")
        load_dotenv()

        self.ui_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        self.reddit_tab = ttk.Frame(nb)
        self.vk_tab = ttk.Frame(nb)
        self.telegram_tab = ttk.Frame(nb)
        nb.add(self.reddit_tab, text="Reddit")
        nb.add(self.vk_tab, text="VK")
        nb.add(self.telegram_tab, text="Telegram")

        self._build_reddit_tab()
        self._build_vk_tab()
        self._build_telegram_tab()

        # Start all button
        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btns, text="Start All", command=self.start_all).pack(side=tk.RIGHT)

        self.after(150, self._drain_ui_queue)

    # ----- Reddit -----
    def _build_reddit_tab(self) -> None:
        f = self.reddit_tab
        p = 8
        row = 0

        ttk.Label(f, text="Subreddits (comma-separated)").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.re_subs = tk.Entry(f, width=60)
        self.re_subs.insert(0, "python,datascience,MachineLearning")
        self.re_subs.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Posts per subreddit").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.re_posts = tk.Spinbox(f, from_=10, to=500, width=8)
        self.re_posts.delete(0, tk.END)
        self.re_posts.insert(0, "100")
        self.re_posts.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        self.re_comments = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Include comments", variable=self.re_comments).grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Top-K words / hashtags").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.re_top_words = tk.Spinbox(f, from_=10, to=200, width=6)
        self.re_top_words.delete(0, tk.END)
        self.re_top_words.insert(0, "50")
        self.re_top_words.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        self.re_top_hash = tk.Spinbox(f, from_=5, to=100, width=6)
        self.re_top_hash.delete(0, tk.END)
        self.re_top_hash.insert(0, "20")
        self.re_top_hash.grid(row=row, column=1, sticky=tk.W, padx=100, pady=p)
        row += 1

        self.re_save = tk.BooleanVar(value=True)
        self.re_db_path = tk.Entry(f, width=40)
        self.re_db_path.insert(0, "reddit_analysis.db")
        ttk.Checkbutton(f, text="Save to SQLite", variable=self.re_save).grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.re_db_path.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Button(f, text="Start Reddit", command=self.start_reddit).grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        self.re_out = tk.Text(f, height=20)
        self.re_out.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=p, pady=p)
        f.rowconfigure(row, weight=1)
        f.columnconfigure(1, weight=1)

    # ----- VK -----
    def _build_vk_tab(self) -> None:
        f = self.vk_tab
        p = 8
        row = 0

        ttk.Label(f, text="VK group IDs (comma-separated, numeric)").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.vk_groups = tk.Entry(f, width=60)
        self.vk_groups.insert(0, "1, 2")
        self.vk_groups.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Posts per group").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.vk_posts = tk.Spinbox(f, from_=10, to=500, width=8)
        self.vk_posts.delete(0, tk.END)
        self.vk_posts.insert(0, "100")
        self.vk_posts.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Top-K words / hashtags").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.vk_top_words = tk.Spinbox(f, from_=10, to=200, width=6)
        self.vk_top_words.delete(0, tk.END)
        self.vk_top_words.insert(0, "50")
        self.vk_top_words.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        self.vk_top_hash = tk.Spinbox(f, from_=5, to=100, width=6)
        self.vk_top_hash.delete(0, tk.END)
        self.vk_top_hash.insert(0, "20")
        self.vk_top_hash.grid(row=row, column=1, sticky=tk.W, padx=100, pady=p)
        row += 1

        self.vk_save = tk.BooleanVar(value=True)
        self.vk_db_path = tk.Entry(f, width=40)
        self.vk_db_path.insert(0, "vk_analysis.db")
        ttk.Checkbutton(f, text="Save to SQLite", variable=self.vk_save).grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.vk_db_path.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Button(f, text="Start VK", command=self.start_vk).grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        self.vk_out = tk.Text(f, height=20)
        self.vk_out.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=p, pady=p)
        f.rowconfigure(row, weight=1)
        f.columnconfigure(1, weight=1)

    # ----- Telegram -----
    def _build_telegram_tab(self) -> None:
        f = self.telegram_tab
        p = 8
        row = 0

        ttk.Label(f, text="Channels/Chats (comma-separated usernames or IDs)").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.tg_channels = tk.Entry(f, width=60)
        self.tg_channels.insert(0, "telegram,durov,tjournal")
        self.tg_channels.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Messages per channel").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.tg_messages = tk.Spinbox(f, from_=10, to=1000, width=8)
        self.tg_messages.delete(0, tk.END)
        self.tg_messages.insert(0, "100")
        self.tg_messages.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        self.tg_replies = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Include replies", variable=self.tg_replies).grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        ttk.Label(f, text="Top-K words / hashtags").grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.tg_top_words = tk.Spinbox(f, from_=10, to=200, width=6)
        self.tg_top_words.delete(0, tk.END)
        self.tg_top_words.insert(0, "50")
        self.tg_top_words.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        self.tg_top_hash = tk.Spinbox(f, from_=5, to=100, width=6)
        self.tg_top_hash.delete(0, tk.END)
        self.tg_top_hash.insert(0, "20")
        self.tg_top_hash.grid(row=row, column=1, sticky=tk.W, padx=100, pady=p)
        row += 1

        self.tg_save = tk.BooleanVar(value=True)
        self.tg_db_path = tk.Entry(f, width=40)
        self.tg_db_path.insert(0, "telegram_analysis.db")
        ttk.Checkbutton(f, text="Save to SQLite", variable=self.tg_save).grid(row=row, column=0, sticky=tk.W, padx=p, pady=p)
        self.tg_db_path.grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        # Информация о настройке Telegram API
        info_frame = ttk.LabelFrame(f, text="Telegram API Setup")
        info_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W+tk.E, padx=p, pady=p)
        ttk.Label(info_frame, text="1. Get API credentials at https://my.telegram.org/", foreground="blue").pack(anchor=tk.W, padx=p, pady=2)
        ttk.Label(info_frame, text="2. Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE in .env file", foreground="blue").pack(anchor=tk.W, padx=p, pady=2)
        ttk.Label(info_frame, text="3. First run will require verification code", foreground="blue").pack(anchor=tk.W, padx=p, pady=2)
        row += 1

        ttk.Button(f, text="Start Telegram", command=self.start_telegram).grid(row=row, column=1, sticky=tk.W, padx=p, pady=p)
        row += 1

        self.tg_out = tk.Text(f, height=20)
        self.tg_out.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=p, pady=p)
        f.rowconfigure(row, weight=1)
        f.columnconfigure(1, weight=1)

    # ----- Control -----
    def start_all(self) -> None:
        self.start_reddit()
        self.start_vk()
        self.start_telegram()

    def _post(self, channel: str, msg: str) -> None:
        self.ui_queue.put((channel, msg))

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                channel, msg = self.ui_queue.get_nowait()
                if channel == "reddit":
                    self.re_out.insert(tk.END, msg + "\n")
                    self.re_out.see(tk.END)
                elif channel == "vk":
                    self.vk_out.insert(tk.END, msg + "\n")
                    self.vk_out.see(tk.END)
                elif channel == "telegram":
                    self.tg_out.insert(tk.END, msg + "\n")
                    self.tg_out.see(tk.END)
        except queue.Empty:
            pass
        self.after(150, self._drain_ui_queue)

    def start_reddit(self) -> None:
        try:
            subs = [s.strip() for s in self.re_subs.get().split(',') if s.strip()]
            posts = int(self.re_posts.get())
            include_comments = bool(self.re_comments.get())
            top_w = int(self.re_top_words.get())
            top_h = int(self.re_top_hash.get())
            db_path = self.re_db_path.get() if self.re_save.get() else None
        except Exception as e:
            messagebox.showerror("Reddit", f"Invalid input: {e}")
            return

        def run():
            lbl = ", ".join(subs) if subs else "(no subreddits)"
            self._post("reddit", f"Starting Reddit collection for: {lbl}")
            def progress(name: str, i: int, total: int):
                self._post("reddit", f"[{i+1}/{total}] {name}")
            try:
                res = reddit_collector.collect(
                    subreddits=subs,
                    posts_per_subreddit=posts,
                    include_comments=include_comments,
                    top_k_words=top_w,
                    top_k_hashtags=top_h,
                    save_db_path=db_path,
                    progress_cb=progress,
                )
                self._post("reddit", f"Total texts: {res['total_texts']}")
                self._post("reddit", "Top words:")
                for w, c in res["top_words"]:
                    self._post("reddit", f"  {w}: {c}")
                self._post("reddit", "Top hashtags:")
                for h, c in res["top_hashtags"]:
                    self._post("reddit", f"  {h}: {c}")
                if db_path:
                    self._post("reddit", f"Saved to {db_path}")
            except Exception as e:
                self._post("reddit", f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def start_vk(self) -> None:
        try:
            groups: List[int] = [int(x.strip()) for x in self.vk_groups.get().split(',') if x.strip()]
            posts = int(self.vk_posts.get())
            top_w = int(self.vk_top_words.get())
            top_h = int(self.vk_top_hash.get())
            db_path = self.vk_db_path.get() if self.vk_save.get() else None
        except Exception as e:
            messagebox.showerror("VK", f"Invalid input: {e}")
            return

        def run():
            self._post("vk", f"Starting VK collection for: {', '.join(map(str, groups))}")
            def progress(name: str, i: int, total: int):
                self._post("vk", f"[{i+1}/{total}] group {name}")
            try:
                res = vk_collector.collect_from_groups(
                    group_ids=groups,
                    posts_per_group=posts,
                    top_k_words=top_w,
                    top_k_hashtags=top_h,
                    save_db_path=db_path,
                    progress_cb=progress,
                )
                self._post("vk", f"Total texts: {res['total_texts']}")
                self._post("vk", "Top words:")
                for w, c in res["top_words"]:
                    self._post("vk", f"  {w}: {c}")
                self._post("vk", "Top hashtags:")
                for h, c in res["top_hashtags"]:
                    self._post("vk", f"  {h}: {c}")
                if db_path:
                    self._post("vk", f"Saved to {db_path}")
            except Exception as e:
                self._post("vk", f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def start_telegram(self) -> None:
        try:
            channels = [c.strip() for c in self.tg_channels.get().split(',') if c.strip()]
            messages = int(self.tg_messages.get())
            include_replies = bool(self.tg_replies.get())
            top_w = int(self.tg_top_words.get())
            top_h = int(self.tg_top_hash.get())
            db_path = self.tg_db_path.get() if self.tg_save.get() else None
        except Exception as e:
            messagebox.showerror("Telegram", f"Invalid input: {e}")
            return

        def run():
            lbl = ", ".join(channels) if channels else "(no channels)"
            self._post("telegram", f"Starting Telegram collection for: {lbl}")
            def progress(name: str, i: int, total: int):
                self._post("telegram", f"[{i+1}/{total}] {name}")
            try:
                res = telegram_collector.collect(
                    channels=channels,
                    messages_per_channel=messages,
                    include_replies=include_replies,
                    top_k_words=top_w,
                    top_k_hashtags=top_h,
                    save_db_path=db_path,
                    progress_cb=progress,
                )
                self._post("telegram", f"Total messages: {res['total_messages']}")
                self._post("telegram", f"Channels processed: {res['channels_processed']}")
                self._post("telegram", "Top words:")
                for w, c in res["top_words"]:
                    self._post("telegram", f"  {w}: {c}")
                self._post("telegram", "Top hashtags:")
                for h, c in res["top_hashtags"]:
                    self._post("telegram", f"  {h}: {c}")
                if db_path:
                    self._post("telegram", f"Saved to {db_path}")
            except Exception as e:
                self._post("telegram", f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()