# -*- coding: utf-8 -*-
"""
Naipei 桌面宠物
点击: 弹跳 | 拖拽: 移动(>8px触发)+松手掉落
滚轮: 缩放 | 双击: 开心 | 滚轮键: 狗叫
右键单击: 语音对话 | 右键双击: 退出
快速连点>=5次/3秒: 红温
"""
import tkinter as tk
import random, math, os, time, threading, ctypes
from collections import deque
from PIL import Image, ImageTk, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PET_IMG = os.path.join(SCRIPT_DIR, "assets", "pet.png")
TRANS_COLOR = "#FF00FF"
GRAVITY = 0.6
FPS = 30
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# === 狗叫 ===
import pygame
pygame.mixer.init()
_mp3 = os.path.join(SCRIPT_DIR, "assets", "dog.mp3")
_wav = os.path.join(SCRIPT_DIR, "bark.wav")
if os.path.exists(_mp3) and os.path.getsize(_mp3) > 1000:
    _bark_sound = pygame.mixer.Sound(_mp3)
elif os.path.exists(_wav) and os.path.getsize(_wav) > 1000:
    _bark_sound = pygame.mixer.Sound(_wav)
else:
    _bark_sound = None

def play_bark():
    try:
        if _bark_sound and _bark_sound.get_num_channels() == 0:
            _bark_sound.play()
    except: pass

# === TTS ===
import pyttsx3
def speak(text, pet=None, angry=False, duration=None):
    if duration is None:
        duration = max(1500, min(8000, len(text) * 180))
    if pet: pet._say(text, duration)
    def _do():
        try:
            e = pyttsx3.init(); e.setProperty('rate', 130 if angry else 180)
            e.setProperty('volume', 1.0); e.say(text); e.runAndWait(); e.stop(); del e
        except: pass
    threading.Thread(target=_do, daemon=True).start()

# === 语音识别 ===
import speech_recognition as sr

def deepseek_chat(user_text):
    if not DEEPSEEK_API_KEY: return "API Key 未设置，汪！"
    try:
        import requests
        r = requests.post("https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [
                {"role": "system", "content": "你是桌面宠物狗奈陪(Naipei)，活泼可爱。回答不超过50字，语气萌，加'汪！'结尾。不用markdown。"},
                {"role": "user", "content": user_text}],
                "max_tokens": 120, "temperature": 0.9}, timeout=15)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
        return "唔... 出错了汪"
    except: return "网络好像不太好，汪！"

def voice_chat(pet):
    def _do():
        pet._say("正在听...")
        try:
            rec = sr.Recognizer(); rec.energy_threshold = 300; rec.dynamic_energy_threshold = True
            with sr.Microphone() as s:
                rec.adjust_for_ambient_noise(s, duration=0.3)
                pet._say("说话中...")
                audio = rec.listen(s, timeout=3, phrase_time_limit=4)
        except sr.WaitTimeoutError:
            speak("没听到声音，汪！", pet=pet); return
        except:
            speak("麦克风出问题了，汪！", pet=pet); return
        pet._say("识别中...")
        try:
            text = rec.recognize_google(audio, language="zh-CN")
        except sr.UnknownValueError:
            speak("没听清楚，汪！", pet=pet); return
        except sr.RequestError:
            speak("识别服务连不上，汪！", pet=pet); return
        text = text.strip()
        if not text: pet._hide_say(); return
        reply = deepseek_chat(text)
        speak(reply, pet=pet)
    threading.Thread(target=_do, daemon=True).start()

# ============================================================
class NaipeiPet:
    def __init__(self):
        self.root = tk.Tk(); self.root.withdraw()
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.base_image = Image.open(PET_IMG).convert("RGBA")
        self.scale = 1.0
        self.w = int(self.base_image.width * self.scale)
        self.h = int(self.base_image.height * self.scale)
        self.x = self.screen_w - self.w - 40
        self.y = self.screen_h - self.h - 100
        self.base_y = self.y
        self.target_x, self.target_y = self.x, self.y
        self.vel_y = 0.0; self.grounded = True; self.bounce_count = 0
        self.state = "idle"; self.state_timer = 0; self.anim_tick = 0
        self.frame_idx = 0; self.walk_dir = "right"
        self._click_x = self._click_y = 0; self._moved = False
        self.dragging = False; self.drag_off_x = self.drag_off_y = 0
        self.click_history = deque(); self.rage_until = 0; self._rage_cooldown = 0
        self._last_right_time = 0

        # 气泡窗口
        self._bubble_win = None
        self._bubble_label = None
        self._bubble_timer = None

        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.overrideredirect(True); self.root.attributes('-topmost', True)
        self.root.configure(bg=TRANS_COLOR)
        self.root.wm_attributes('-transparentcolor', TRANS_COLOR)
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        s = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, s | 0x00000080)

        self.frames = {}; self._rebuild_all_frames()
        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h,
                                bg=TRANS_COLOR, highlightthickness=0)
        self.canvas.pack()
        self.sprite = self.canvas.create_image(self.w//2, self.h//2,
                                               image=self.frames["idle"][0], anchor=tk.CENTER)
        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Button-3>", self.on_right)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Button-2>", self.on_middle)
        self.root.deiconify()
        self.update_loop(); self.behavior_loop()
        self.root.mainloop()

    def _make_tkframe(self, img):
        f = Image.new("RGBA", (self.w, self.h), (255,0,255,255))
        f.paste(img, (0,0), img if img.mode=="RGBA" else None)
        return ImageTk.PhotoImage(f)

    def _redden(self, img):
        r,g,b,a = img.split()
        return Image.merge("RGBA", (ImageEnhance.Brightness(r).enhance(1.8),
            ImageEnhance.Brightness(g).enhance(0.25),
            ImageEnhance.Brightness(b).enhance(0.25), a))

    def _rebuild_all_frames(self):
        base = self.base_image; w, h = self.w, self.h
        s = base if self.scale==1.0 else base.resize((w,h), Image.LANCZOS)
        rs = self._redden(s)
        for pf, src in [("", s), ("rage_", rs)]:
            dr = lambda img,a: img.rotate(a, Image.BICUBIC, expand=False, fillcolor=(0,0,0,0))
            self.frames[pf+"idle"] = [self._make_tkframe(dr(src,a)) for a in [0,2,0,-2]]
            dxs = [0, max(1,int(2*self.scale)), max(2,int(4*self.scale)), max(1,int(2*self.scale))]
            self.frames[pf+"walk_right"] = []; self.frames[pf+"walk_left"] = []
            for dx in dxs:
                a = Image.new("RGBA",(w+4,h),(0,0,0,0)); a.paste(src,(dx,0))
                self.frames[pf+"walk_right"].append(self._make_tkframe(a.crop((0,0,w,h))))
                b = Image.new("RGBA",(w+4,h),(0,0,0,0)); b.paste(src,(-dx,0))
                self.frames[pf+"walk_left"].append(self._make_tkframe(b.crop((0,0,w,h))))
            self.frames[pf+"jump"] = []; self.frames[pf+"happy"] = []
            for r in [0.85,0.92,1.12,1.0]:
                nw,nh = int(w*r),int(h*r); bg = Image.new("RGBA",(w,h),(0,0,0,0))
                bg.paste(src.resize((nw,nh),Image.LANCZOS),((w-nw)//2,(h-nh)//2))
                self.frames[pf+"jump"].append(self._make_tkframe(bg))
            for r in [1.1,1.0,1.08,1.0]:
                nw,nh = int(w*r),int(h*r); bg = Image.new("RGBA",(w,h),(0,0,0,0))
                bg.paste(src.resize((nw,nh),Image.LANCZOS),((w-nw)//2,(h-nh)//2))
                self.frames[pf+"happy"].append(self._make_tkframe(bg))
            self.frames[pf+"clicked"] = [self._make_tkframe(ImageEnhance.Brightness(src).enhance(1.15))]

    def _raging(self): return time.time() < self.rage_until
    def _get_frames(self, name):
        return self.frames["rage_"+name] if self._raging() else self.frames[name]

    # === 气泡 (独立窗口) ===
    def _say(self, text, duration=2000):
        if not self._bubble_win:
            self._bubble_win = tk.Toplevel(self.root)
            self._bubble_win.overrideredirect(True)
            self._bubble_win.attributes('-topmost', True)
            self._bubble_win.configure(bg='white')
            self._bubble_win.withdraw()
            self._bubble_label = tk.Label(self._bubble_win, text='', bg='white', fg='#333',
                font=('Microsoft YaHei', 10), padx=10, pady=5, relief='solid', bd=1,
                wraplength=280)
            self._bubble_label.pack()
        if self._bubble_timer:
            self.root.after_cancel(self._bubble_timer)
        self._bubble_label.config(text=text)
        self._bubble_win.deiconify()
        self._bubble_win.update_idletasks()
        bw = self._bubble_win.winfo_reqwidth()
        bh = self._bubble_win.winfo_reqheight()
        self._bubble_win.geometry(f"+{self.x + self.w//2 - bw//2}+{self.y - bh - 4}")
        self._bubble_timer = self.root.after(duration, self._hide_say)

    def _hide_say(self):
        if self._bubble_win: self._bubble_win.withdraw()
        self._bubble_timer = None

    # === 事件 ===
    def _register_click(self):
        now = time.time(); self.click_history.append(now)
        while self.click_history and self.click_history[0] < now-3.0: self.click_history.popleft()
        if now < self._rage_cooldown: return
        if len(self.click_history) >= 5 and not self._raging():
            self.rage_until = now+3.5; self._rage_cooldown = now+6.0
            speak("别再搞我了！", pet=self, angry=True, duration=3000)

    def on_scroll(self, event):
        d = 0.1 if event.delta>0 else -0.1; ns = max(0.4, min(2.5, self.scale+d))
        if abs(ns-self.scale)<0.01: return
        cx, cy = self.x+self.w//2, self.y+self.h//2
        self.scale = ns
        self.w = int(self.base_image.width*self.scale); self.h = int(self.base_image.height*self.scale)
        self.x, self.y = cx-self.w//2, cy-self.h//2
        self.base_y = self.y; self.target_x, self.target_y = self.x, self.y
        self._rebuild_all_frames()
        self.canvas.config(width=self.w, height=self.h)
        self.canvas.coords(self.sprite, self.w//2, self.h//2)
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")

    def on_down(self, event):
        self._register_click()
        if len(self.click_history) < 3: speak("主人不要啊", pet=self, duration=1500)
        self._click_x, self._click_y = event.x_root, event.y_root
        self._moved = False; self.dragging = False
        if self.state in ("idle","walking"): self.state="clicked"; self.state_timer=0; self.frame_idx=0

    def on_drag(self, event):
        dx, dy = event.x_root-self._click_x, event.y_root-self._click_y
        if abs(dx)>=8 or abs(dy)>=8:
            self._moved = True
            if not self.dragging:
                self.dragging = True
                self.drag_off_x = event.x_root-self.x; self.drag_off_y = event.y_root-self.y
            self.x = event.x_root-self.drag_off_x; self.y = event.y_root-self.drag_off_y
            self.base_y = self.y; self.target_x, self.target_y = self.x, self.y
            self.root.geometry(f"+{self.x}+{self.y}")

    def on_up(self, event):
        if self._moved or self.dragging:
            self.dragging = False
            if self.y < 35: self.root.destroy(); return
            self.grounded = False; self.base_y = self.screen_h-self.h-60
            self.vel_y = 3; self.bounce_count = 0
        else:
            self.grounded = False; self.vel_y = -8; self.bounce_count = 0
        self.state = "jump"; self.state_timer = 0; self.frame_idx = 0

    def on_double(self, event):
        self.state = "happy"; self.state_timer = 0; self.frame_idx = 0
        self.grounded = False; self.vel_y = -8

    def on_middle(self, event):
        play_bark()

    def on_right(self, event):
        now = time.time()
        if now - self._last_right_time < 0.5:
            speak("拜拜", pet=self)
            self.root.after(800, self.root.destroy)
        else:
            self._last_right_time = now
            voice_chat(self)

    # === 动画 ===
    def update_loop(self):
        self.anim_tick += 1; self.state_timer += 1
        if not self.grounded and not self.dragging:
            self.vel_y += GRAVITY; self.y += int(self.vel_y)
            if self.y >= self.base_y:
                self.y = self.base_y; self.bounce_count += 1
                if self.bounce_count <= 2 and abs(self.vel_y) > 2: self.vel_y *= -0.45
                else: self.vel_y = 0; self.bounce_count = 0; self.grounded = True
                if self.state in ("jump","clicked","happy"): self.state = "idle"
        if self.state == "walking" and not self.dragging:
            dx, dy = self.target_x-self.x, self.target_y-self.y
            dist = math.hypot(dx, dy)
            if dist > 3:
                sp = max(1.5, 2.5*self.scale)
                self.x += int(dx/dist*sp); self.y += int(dy/dist*sp)
                self.walk_dir = "right" if dx >= 0 else "left"; self.base_y = self.y
            else: self.state = "idle"
        if self.state == "walking":
            if self.x <= 30 or self.x >= self.screen_w-self.w-30:
                self.target_x = random.randint(50, self.screen_w-self.w-50)
                self.walk_dir = "right" if self.target_x >= self.x else "left"
            if self.y <= 30 or self.y >= self.screen_h-self.h-30:
                self.target_y = random.randint(50, self.screen_h-self.h-50)
        self.x = max(-20, min(self.screen_w-self.w+20, self.x))
        self.y = max(0, min(self.screen_h-self.h+10, self.y))
        if self.grounded: self.base_y = self.y
        spd = {"idle":16,"walking":6,"jump":6,"clicked":5,"happy":5}
        self.frame_idx = self.anim_tick//spd.get(self.state,10)
        to = {"clicked":12,"happy":24,"jump":30}
        if self.state in to and self.state_timer > to[self.state] and self.grounded: self.state = "idle"
        fn = {"idle":"idle","walking":f"walk_{self.walk_dir}","jump":"jump","clicked":"clicked","happy":"happy"}.get(self.state,"idle")
        frames = self._get_frames(fn)
        self.canvas.itemconfig(self.sprite, image=frames[self.frame_idx%len(frames)])
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.after(1000//FPS, self.update_loop)

    def behavior_loop(self):
        if self.state == "idle" and not self.dragging and not self._raging():
            r = random.random()
            if r < 0.04:
                self.state = "jump"; self.state_timer = 0; self.frame_idx = 0
                self.bounce_count = 0; self.grounded = False; self.vel_y = -10
            elif r < 0.09:
                m = 60
                self.target_x = random.randint(m, self.screen_w-self.w-m)
                self.target_y = random.randint(m, self.screen_h-self.h-m)
                self.walk_dir = "right" if self.target_x >= self.x else "left"
                self.state = "walking"; self.state_timer = 0
        self.root.after(random.randint(2000,5000), self.behavior_loop)

if __name__ == "__main__":
    os.chdir(SCRIPT_DIR)
    NaipeiPet()
