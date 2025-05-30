import tkinter as tk
from tkinter import messagebox
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
import vlc
import threading
import time
from PIL import Image, ImageTk
import io
import requests

API_KEY = 'AIzaSyD_41Fdi9PqJJOh4J_6ZSemDWxw0T8JF_o'  # Vervang met je geldige YouTube API sleutel
youtube = build('youtube', 'v3', developerKey=API_KEY)

BG_COLOR = "#121212"
FG_COLOR = "#E0E0E0"
BTN_BG = "#1F1F1F"
BTN_FG = "#FFFFFF"
ENTRY_BG = "#222222"
ENTRY_FG = "#E0E0E0"
LISTBOX_BG = "#222222"
LISTBOX_FG = "#FFFFFF"
SLIDER_BG = "#1F1F1F"
SLIDER_FG = "#FFFFFF"

class YouTubeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Kijker met Wachtrij")
        self.root.config(bg=BG_COLOR)

        top_frame = tk.Frame(root, bg=BG_COLOR)
        top_frame.pack(pady=5)
        mid_frame = tk.Frame(root, bg=BG_COLOR)
        mid_frame.pack(pady=5)
        bottom_frame = tk.Frame(root, bg=BG_COLOR)
        bottom_frame.pack(pady=5)

        self.search_entry = tk.Entry(top_frame, width=40, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
        self.search_entry.pack(side=tk.LEFT, padx=(0,5))
        self.search_button = tk.Button(top_frame, text="Zoek Video", command=self.search_video, bg=BTN_BG, fg=BTN_FG)
        self.search_button.pack(side=tk.LEFT)

        self.video_listbox = tk.Listbox(mid_frame, width=60, height=10, bg=LISTBOX_BG, fg=LISTBOX_FG)
        self.video_listbox.pack(side=tk.LEFT, pady=5)
        self.video_listbox.bind('<<ListboxSelect>>', self.select_video)

        self.thumbnail_label = tk.Label(mid_frame, bg=BG_COLOR)
        self.thumbnail_label.pack(side=tk.LEFT, padx=10)

        control_frame = tk.Frame(root, bg=BG_COLOR)
        control_frame.pack(pady=5)

        self.prev_button = tk.Button(control_frame, text="⏮️ Vorige", command=self.skip_previous, state=tk.DISABLED, bg=BTN_BG, fg=BTN_FG)
        self.prev_button.pack(side=tk.LEFT, padx=2)

        self.play_button = tk.Button(control_frame, text="▶️ Play", command=self.toggle_play_pause, state=tk.DISABLED, bg=BTN_BG, fg=BTN_FG)
        self.play_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = tk.Button(control_frame, text="⏹️ Stop", command=self.stop_video, state=tk.DISABLED, bg=BTN_BG, fg=BTN_FG)
        self.stop_button.pack(side=tk.LEFT, padx=2)

        self.next_button = tk.Button(control_frame, text="⏭️ Volgende", command=self.skip_next, state=tk.DISABLED, bg=BTN_BG, fg=BTN_FG)
        self.next_button.pack(side=tk.LEFT, padx=2)

        # Nettere volumeregelaar
        volume_frame = tk.Frame(root, bg=BG_COLOR)
        volume_frame.pack(pady=10)

        volume_label = tk.Label(volume_frame, text="🔊 Volume", bg=BG_COLOR, fg=FG_COLOR)
        volume_label.pack(side=tk.LEFT, padx=(10, 5))

        self.volume_slider = tk.Scale(
            volume_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            command=self.set_volume, showvalue=False,
            troughcolor="#444", sliderlength=15, length=200,
            bg=BG_COLOR, fg=FG_COLOR, highlightthickness=0
        )
        self.volume_slider.set(50)
        self.volume_slider.pack(side=tk.LEFT)

        self.add_to_queue_button = tk.Button(root, text="➕ Voeg toe aan wachtrij", command=self.add_to_queue, bg=BTN_BG, fg=BTN_FG)
        self.add_to_queue_button.pack()

        self.remove_from_queue_button = tk.Button(root, text="❌ Verwijder geselecteerde uit wachtrij", command=self.remove_from_queue, bg=BTN_BG, fg=BTN_FG)
        self.remove_from_queue_button.pack()

        self.queue_listbox = tk.Listbox(root, width=80, height=8, bg=LISTBOX_BG, fg=LISTBOX_FG)
        self.queue_listbox.pack(pady=5)

        self.videos = []
        self.queue = []
        self.player = None
        self.is_playing = False
        self.is_paused = False
        self.current_queue_index = None
        self.check_end_thread = threading.Thread(target=self.check_end_loop)
        self.check_end_thread.daemon = True
        self.check_end_thread.start()

    def search_video(self):
        query = self.search_entry.get()
        if not query:
            messagebox.showerror("Fout", "Voer een zoekterm in.")
            return

        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=10
        )
        response = request.execute()

        self.videos.clear()
        self.video_listbox.delete(0, tk.END)
        self.thumbnail_label.config(image='')

        for item in response['items']:
            title = item['snippet']['title']
            video_id = item['id']['videoId']
            thumb_url = item['snippet']['thumbnails']['default']['url']
            self.videos.append({'title': title, 'id': video_id, 'thumbnail': thumb_url})
            self.video_listbox.insert(tk.END, title)

        if self.videos:
            self.show_thumbnail(0)

    def show_thumbnail(self, index):
        try:
            thumb_url = self.videos[index]['thumbnail']
            image_data = requests.get(thumb_url).content
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail((120, 90))
            photo = ImageTk.PhotoImage(image)
            self.thumbnail_label.config(image=photo)
            self.thumbnail_label.image = photo
        except:
            self.thumbnail_label.config(image='')
            self.thumbnail_label.image = None

    def select_video(self, event):
        selection = self.video_listbox.curselection()
        if selection:
            self.show_thumbnail(selection[0])

    def add_to_queue(self):
        selection = self.video_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        video = self.videos[index]
        self.queue.append(video)
        self.queue_listbox.insert(tk.END, video['title'])
        if self.current_queue_index is None:
            self.current_queue_index = 0
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)
        self.prev_button.config(state=tk.NORMAL)

    def remove_from_queue(self):
        selection = self.queue_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        del self.queue[index]
        self.queue_listbox.delete(index)

    def toggle_play_pause(self):
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.is_paused = True
            self.play_button.config(text="▶️ Play")
        elif self.player and self.is_paused:
            self.player.play()
            self.is_playing = True
            self.is_paused = False
            self.play_button.config(text="⏸️ Pause")
        else:
            self.play_current_video()

    def stop_video(self):
        if self.player:
            self.player.stop()
        self.is_playing = False
        self.is_paused = False
        self.play_button.config(text="▶️ Play")

    def skip_next(self):
        if self.queue and self.current_queue_index is not None:
            self.current_queue_index = (self.current_queue_index + 1) % len(self.queue)
            self.play_current_video()

    def skip_previous(self):
        if self.queue and self.current_queue_index is not None:
            self.current_queue_index = (self.current_queue_index - 1) % len(self.queue)
            self.play_current_video()

    def set_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(int(volume))

    def play_current_video(self):
        if not self.queue or self.current_queue_index is None:
            return
        video = self.queue[self.current_queue_index]
        url = f"https://www.youtube.com/watch?v={video['id']}"
        ydl_opts = {'quiet': True, 'format': 'best'}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']

        if self.player:
            self.player.stop()

        self.player = vlc.MediaPlayer(video_url)
        self.player.audio_set_volume(self.volume_slider.get())
        self.player.play()
        self.is_playing = True
        self.is_paused = False
        self.play_button.config(text="⏸️ Pause")

    def check_end_loop(self):
        while True:
            if self.player and self.is_playing:
                state = self.player.get_state()
                if state == vlc.State.Ended:
                    self.skip_next()
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeApp(root)
    root.mainloop()
