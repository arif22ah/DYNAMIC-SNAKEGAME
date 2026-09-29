"""
DYNAMIC SNAKE 3  -  Python + Pygame
====================================
Install:  pip install pygame
Run:      python dynamic_snake_v3.py

MENU (Up/Down select, Left/Right change, Enter confirm)
    Mode ........ Classic | Wrap | Rival | Time Attack | Maze | Chaos
    Difficulty .. Easy | Normal | Hard
    Theme ....... Neon | Forest | Sunset | Mono
    Skin ........ Viper | Coral | Python | Cyber | Rainbow | Ice | Lava | Theme
    Audio ....... Full | SFX only | Music only | Off

IN GAME
    Arrow keys / WASD ... steer            P ..... pause        R ..... restart (paused)
    SPACE / SHIFT ....... hold to BOOST    Q ..... show / hide quests
    M ................... cycle audio      F11 ... fullscreen   ESC ... back to menu

WHAT'S NEW IN VERSION 3
    * Realistic snake: smooth spline body, scales and patterns, swallowed-food
      bulges travelling down the body, a flicking tongue, eyes that follow food
      and blink, a head that turns smoothly.
    * Living world: day / night cycle with real lighting (the snake carries a
      light), themed weather (sparks, leaves, embers, snow), fireflies at night,
      soft shadows, textured ground, rocks and brick walls.
    * New creatures: mice run away from you (catch them for big points),
      spiders patrol the board, bombs tick down and blow up rocks and spiders.
    * Portals teleport you across the board.
    * Quests: three live missions at any time, each pays a bonus when done.
    * New modes: Maze (a new layout every level) and Chaos (random events).
    * New power-ups: Freeze (freezes rival, mice and spiders - frozen spiders
      can be eaten) and the Dizzy mushroom (controls reversed - avoid it!).
    * Procedural music that gets more intense as you level up, plus richer
      sound effects, a 3-2-1 countdown and a slow-motion death sequence.
    * Close calls: brush past danger while boosting for bonus points.

Best scores, top-5 lists, settings, stats and achievements are stored in
snake_save.json next to this file.
"""
import colorsys
import json
import math
import os
import random
import sys
import threading
from array import array
from collections import deque
from datetime import date

import pygame

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
CELL = 24
COLS, ROWS = 32, 22
HUD = 56
W, H = COLS * CELL, ROWS * CELL + HUD
FPS = 60
BOOST_FACTOR = 0.55

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIRS = [UP, DOWN, LEFT, RIGHT]

MODES = ["Classic", "Wrap", "Rival", "Time Attack", "Maze", "Chaos"]
MODE_INFO = {
    "Classic": "Walls are deadly. Rocks and spiders appear as you level up.",
    "Wrap": "The edges wrap around. Just don't bite yourself.",
    "Rival": "An AI snake steals your food. Beat it for +100 points.",
    "Time Attack": "90 seconds on the clock. Every apple adds 1.5 seconds.",
    "Maze": "Every level brings a new maze layout - and portals.",
    "Chaos": "Random events: quakes, night, bomb drops, spider swarms...",
}
DIFFS = ["Easy", "Normal", "Hard"]
AUDIO_MODES = ["Full", "SFX only", "Music only", "Off"]
BASE_INTERVAL = {"Easy": 170, "Normal": 140, "Hard": 110}
MIN_INTERVAL = {"Easy": 70, "Normal": 55, "Hard": 42}
RIVAL_SPEED = {"Easy": 1.25, "Normal": 1.12, "Hard": 1.0}
RIVAL_WOBBLE = {"Easy": 0.12, "Normal": 0.06, "Hard": 0.02}
SPIDER_CAP = {"Easy": 2, "Normal": 3, "Hard": 5}
SPIDER_INTERVAL = {"Easy": 430, "Normal": 340, "Hard": 260}
MOUSE_INTERVAL = {"Easy": 330, "Normal": 260, "Hard": 200}

TIME_ATTACK_MS = 90_000
APPLE_BONUS_MS = 1_500
COMBO_WINDOW_MS = 3_000
COUNTDOWN_MS = 2400
DEATH_MS = 1500
DAY_LENGTH_MS = 140_000
BOMB_FUSE_MS = 9_000
MOUSE_LIFE_MS = 14_000

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_save.json")

THEMES = {
    "Neon": dict(bg1=(24, 27, 40), bg2=(29, 33, 48), border=(0, 200, 255),
                 head=(90, 255, 170), tail=(20, 130, 130), rock=(110, 115, 140),
                 rock2=(160, 165, 190), accent=(0, 220, 255), text=(235, 240, 250),
                 dim=(140, 150, 175), rival=(255, 90, 140), rival_tail=(140, 30, 90),
                 weather="sparks"),
    "Forest": dict(bg1=(26, 44, 30), bg2=(31, 51, 35), border=(120, 200, 90),
                   head=(190, 240, 90), tail=(60, 130, 50), rock=(105, 95, 80),
                   rock2=(150, 140, 120), accent=(170, 230, 100), text=(235, 245, 225),
                   dim=(150, 175, 140), rival=(240, 150, 60), rival_tail=(140, 70, 20),
                   weather="leaves"),
    "Sunset": dict(bg1=(48, 28, 46), bg2=(56, 32, 52), border=(255, 140, 90),
                   head=(255, 210, 90), tail=(230, 80, 90), rock=(120, 90, 120),
                   rock2=(170, 140, 170), accent=(255, 160, 100), text=(255, 240, 235),
                   dim=(190, 150, 170), rival=(90, 200, 255), rival_tail=(40, 90, 160),
                   weather="embers"),
    "Mono": dict(bg1=(30, 30, 30), bg2=(36, 36, 36), border=(220, 220, 220),
                 head=(255, 255, 255), tail=(110, 110, 110), rock=(90, 90, 90),
                 rock2=(150, 150, 150), accent=(255, 255, 255), text=(240, 240, 240),
                 dim=(140, 140, 140), rival=(200, 200, 200), rival_tail=(70, 70, 70),
                 weather="snow"),
}
THEME_NAMES = list(THEMES)

# Snake skins.  kind: diamond (blotches), bands (coral stripes), cyber (glowing
# rings), rainbow (cycling hues).  "Theme" borrows the colours of the theme.
SKINS = {
    "Viper": dict(kind="diamond", a=(110, 200, 80), b=(30, 110, 60), mark=(24, 70, 40)),
    "Coral": dict(kind="bands", a=(215, 40, 40), b=(25, 25, 25), mark=(245, 210, 50)),
    "Python": dict(kind="diamond", a=(205, 175, 95), b=(125, 92, 42), mark=(80, 55, 25)),
    "Cyber": dict(kind="cyber", a=(45, 75, 95), b=(15, 25, 40), mark=(0, 255, 230)),
    "Rainbow": dict(kind="rainbow", a=(255, 0, 0), b=(0, 0, 255), mark=(255, 255, 255)),
    "Ice": dict(kind="diamond", a=(205, 238, 255), b=(90, 150, 220), mark=(60, 110, 200)),
    "Lava": dict(kind="diamond", a=(255, 190, 60), b=(160, 30, 20), mark=(90, 10, 10)),
    "Theme": None,
}
SKIN_NAMES = list(SKINS)

FX_NAMES = ("slow", "ghost", "double", "magnet", "freeze", "dizzy")
# food kind -> lifetime in ms (None = stays until eaten)
FOOD_LIFE = {"apple": None, "gold": 6000, "slow": 8000, "shield": 9000, "ghost": 8000,
             "double": 8000, "shrink": 8000, "magnet": 8000, "freeze": 8000, "dizzy": 9000}
POWER_KINDS = {"slow", "shield", "ghost", "double", "shrink", "magnet", "freeze"}
# what can spawn after eating an apple (cumulative probabilities are summed in order)
SPECIAL_ROLLS = [("gold", 0.08), ("slow", 0.05), ("shield", 0.06), ("ghost", 0.05),
                 ("double", 0.05), ("shrink", 0.04), ("magnet", 0.05), ("freeze", 0.04),
                 ("dizzy", 0.03), ("mouse", 0.07), ("bomb", 0.04)]

ACHIEVEMENTS = {
    "first_bite": ("First Bite", "Eat your first apple"),
    "score_200": ("Snack Time", "Reach 200 points in one game"),
    "length_20": ("Long Boy", "Grow to a length of 20"),
    "level_5": ("Speed Demon", "Reach level 5"),
    "combo_5": ("Combo King", "Reach a x5 combo"),
    "shield_used": ("Bounce Back", "Survive a hit with a shield"),
    "ghost_run": ("Boo!", "Pick up a ghost power-up"),
    "collector": ("Apple Collector", "Eat 100 apples in total"),
    "rival_slayer": ("Rival Slayer", "Defeat the rival snake"),
    "survivor": ("Beat the Clock", "Finish a Time Attack round"),
    "mouse_hunter": ("Mouse Hunter", "Catch 10 mice in total"),
    "spider_bane": ("Spider Bane", "Squash 5 spiders in total"),
    "portal": ("Wormhole", "Travel through a portal"),
    "quest_master": ("Quest Master", "Complete 5 quests in total"),
    "night_owl": ("Night Owl", "Eat 8 apples in the dark, one game"),
    "marathon": ("Marathon", "Survive 3 minutes in one game"),
}

# Quest templates: kind, text, (min, max) goal, base reward
QUEST_TYPES = [
    ("apples", "Eat {n} apples", (4, 8), 60),
    ("fast", "Eat {n} apples in 12 seconds", (3, 5), 90),
    ("length", "Reach length {n}", (12, 28), 80),
    ("boost", "Boost for {n} seconds", (4, 10), 70),
    ("mouse", "Catch {n} mouse", (1, 2), 100),
    ("power", "Collect {n} power-ups", (2, 4), 80),
    ("score", "Score {n} points", (150, 400), 100),
    ("near", "Make {n} close calls", (3, 6), 70),
]


# ----------------------------------------------------------------------------
# Maze layouts
# ----------------------------------------------------------------------------
def _rect(x0, y0, x1, y1):
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def build_maze_layouts():
    """A handful of hand-designed layouts; the centre row is always left open."""
    layouts = []
    # 0: pillars
    s = set()
    for x in range(4, COLS - 3, 6):
        for y in range(3, ROWS - 2, 5):
            s |= _rect(x, y, x + 1, y + 1)
    layouts.append(s)
    # 1: cross with gaps
    mx, my = COLS // 2, ROWS // 2
    s = (_rect(mx - 1, 2, mx, 7) | _rect(mx - 1, ROWS - 8, mx, ROWS - 3)
         | _rect(3, my - 1, 9, my) | _rect(COLS - 10, my - 1, COLS - 4, my))
    layouts.append(s)
    # 2: four corner rooms
    s = set()
    for cx, cy, sx, sy in ((3, 3, 1, 1), (COLS - 4, 3, -1, 1), (3, ROWS - 4, 1, -1),
                           (COLS - 4, ROWS - 4, -1, -1)):
        for i in range(7):
            s.add((cx + sx * i, cy))
            s.add((cx, cy + sy * i))
    layouts.append(s)
    # 3: serpentine
    s = (_rect(0, 4, 24, 4) | _rect(7, 8, COLS - 1, 8) | _rect(0, 14, 24, 14)
         | _rect(7, 18, COLS - 1, 18))
    layouts.append(s)
    # 4: diamond ring with gaps on the axes
    s = set()
    for x in range(COLS):
        for y in range(ROWS):
            dx, dy = x - COLS // 2, y - ROWS // 2
            if abs(dx) + abs(dy) == 8 and dx != 0 and dy != 0 and abs(dy) != 1:
                s.add((x, y))
    layouts.append(s)
    return layouts


MAZE_LAYOUTS = build_maze_layouts()


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp_col(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hsv(h, s, v):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1.0, s, v))


def draw_text(surf, font, text, color, pos, anchor="topleft", shadow=True):
    img = font.render(str(text), True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = font.render(str(text), True, (0, 0, 0))
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def make_glow(radius, color):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        a = int(90 * (1 - r / radius) ** 2)
        pygame.draw.circle(s, (*color, a), (radius, radius), r)
    return s


def make_light(radius):
    """White radial gradient; subtracted from the night layer to cut light holes."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -3):
        a = int(255 * (1 - r / radius) ** 1.5)
        pygame.draw.circle(s, (255, 255, 255, a), (radius, radius), r)
    return s


def chaikin(points, iterations=2):
    """Corner-cutting subdivision: turns a blocky grid path into a smooth curve."""
    for _ in range(iterations):
        if len(points) < 3:
            break
        new = [points[0]]
        for i in range(len(points) - 1):
            p, q = points[i], points[i + 1]
            new.append((p[0] * 0.75 + q[0] * 0.25, p[1] * 0.75 + q[1] * 0.25))
            new.append((p[0] * 0.25 + q[0] * 0.75, p[1] * 0.25 + q[1] * 0.75))
        new.append(points[-1])
        points = new
    return points


def resample(points, step, start_carry=0.0):
    """Evenly spaced points along a polyline."""
    out = []
    carry = start_carry
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg == 0:
            continue
        d = carry
        while d < seg:
            f = d / seg
            out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
            d += step
        carry = d - seg
    out.append(points[-1])
    return out


# ----------------------------------------------------------------------------
# Audio: a tiny synthesizer (no external files) + procedural music
# ----------------------------------------------------------------------------
class Synth:
    rate = 22050
    channels = 1

    @classmethod
    def pack(cls, samples):
        buf = array("h")
        for v in samples:
            iv = int(clamp(v, -1.0, 1.0) * 32767)
            buf.append(iv)
            if cls.channels == 2:
                buf.append(iv)
        return buf.tobytes()

    @staticmethod
    def osc(wave, x):
        if wave == "square":
            return 1.0 if math.sin(x) >= 0 else -1.0
        if wave == "tri":
            return 2 / math.pi * math.asin(math.sin(x))
        if wave == "saw":
            return ((x / math.tau) % 1.0) * 2 - 1
        return math.sin(x)

    @classmethod
    def tone(cls, freqs, dur, vol=0.25, wave="square"):
        n = int(cls.rate * dur)
        per = max(1, n // len(freqs))
        phase = 0.0
        out = []
        for i in range(n):
            f = freqs[min(i // per, len(freqs) - 1)]
            phase += math.tau * f / cls.rate
            env = (1.0 - i / n) * min(1.0, i / 60)
            out.append(cls.osc(wave, phase) * vol * env)
        return cls.pack(out)

    @classmethod
    def sweep(cls, f0, f1, dur, vol=0.25, wave="sine"):
        n = int(cls.rate * dur)
        phase = 0.0
        out = []
        for i in range(n):
            f = f0 + (f1 - f0) * i / n
            phase += math.tau * f / cls.rate
            out.append(cls.osc(wave, phase) * vol * (1.0 - i / n) * min(1.0, i / 60))
        return cls.pack(out)

    @classmethod
    def noise(cls, dur, vol=0.3, smooth=0.7, power=2.0):
        n = int(cls.rate * dur)
        prev = 0.0
        out = []
        for i in range(n):
            prev = prev * smooth + (random.random() * 2 - 1) * (1 - smooth)
            out.append(prev * vol * (1.0 - i / n) ** power * 3)
        return cls.pack(out)


class Sound:
    """Sound effects.  Fails silently when no audio device is available."""

    def __init__(self):
        self.ok = False
        self.sfx_on = True
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            init = pygame.mixer.get_init()
            if init is None or init[1] != -16:
                return
            Synth.rate, _, Synth.channels = init
            pygame.mixer.set_num_channels(16)
        except pygame.error:
            return
        self.ok = True
        S = Synth
        raw = {
            "eat": S.tone([660, 990], 0.08),
            "gold": S.tone([880, 1175, 1568], 0.18),
            "power": S.tone([440, 660, 880], 0.16, wave="sine"),
            "level": S.tone([523, 659, 784, 1047], 0.32),
            "hit": S.tone([300, 200], 0.14, wave="square"),
            "die": S.sweep(420, 50, 0.7, 0.3, "saw"),
            "menu": S.tone([520], 0.04, 0.2, "sine"),
            "win": S.tone([523, 659, 784, 1047, 1319], 0.5, wave="sine"),
            "explode": S.noise(0.6, 0.5, 0.85, 1.6),
            "tick": S.tone([880], 0.07, 0.25, "sine"),
            "go": S.tone([1320], 0.28, 0.25, "sine"),
            "portal": S.sweep(300, 1400, 0.25, 0.25, "sine"),
            "squeak": S.sweep(1900, 2700, 0.09, 0.2, "sine"),
            "freeze": S.tone([1568, 1975, 2349], 0.3, 0.2, "sine"),
            "dizzy": S.sweep(600, 180, 0.45, 0.25, "tri"),
            "quest": S.tone([784, 988, 1175, 1568], 0.35, 0.22, "sine"),
            "crunch": S.noise(0.08, 0.4, 0.5, 1.0),
            "spider": S.tone([210, 150], 0.12, 0.2, "square"),
        }
        self.sounds = {k: pygame.mixer.Sound(buffer=v) for k, v in raw.items()}

    def play(self, name):
        if self.ok and self.sfx_on and name in self.sounds:
            self.sounds[name].play()


THEME_MUSIC = {
    "Neon": (57, [0, 3, 5, 7, 10]),
    "Forest": (52, [0, 2, 4, 7, 9]),
    "Sunset": (55, [0, 2, 3, 7, 8]),
    "Mono": (50, [0, 3, 5, 6, 7, 10]),
}


def build_music(theme_name, intense, rate, channels):
    """Two bars of bass + arpeggio (+ drums when intense).  Returns raw PCM bytes."""
    root, scale = THEME_MUSIC[theme_name]
    rng = random.Random(sum(map(ord, theme_name)) * (2 if intense else 1))
    bpm = 132 if intense else 92
    beat = 60.0 / bpm
    beats = 8
    total = int(rate * beat * beats)
    buf = [0.0] * total

    def freq(m):
        return 440.0 * 2 ** ((m - 69) / 12.0)

    def note(start, length, f, vol, wave):
        s = int(start * beat * rate)
        n = int(length * beat * rate)
        w = math.tau * f / rate
        for i in range(n):
            env = min(1.0, i / 150) * (1.0 - i / n) ** 1.4
            x = w * i
            if wave == "tri":
                v = 2 / math.pi * math.asin(math.sin(x))
            elif wave == "square":
                v = 1.0 if math.sin(x) >= 0 else -1.0
            else:
                v = math.sin(x)
            buf[(s + i) % total] += v * vol * env

    def kick(b):
        s = int(b * beat * rate)
        n = int(0.14 * rate)
        phase = 0.0
        for i in range(n):
            f = 45 + 90 * math.exp(-i / (n * 0.18))
            phase += math.tau * f / rate
            buf[(s + i) % total] += math.sin(phase) * 0.45 * (1 - i / n)

    def hat(b):
        s = int(b * beat * rate)
        n = int(0.045 * rate)
        for i in range(n):
            buf[(s + i) % total] += (rng.random() * 2 - 1) * 0.07 * (1 - i / n) ** 2

    for b in range(beats):
        m = root - 12 + (scale[0] if b < 4 else scale[2])
        if intense:
            note(b, 0.45, freq(m), 0.26, "tri")
            note(b + 0.5, 0.45, freq(m + 12), 0.18, "tri")
            kick(b)
            hat(b + 0.5)
        else:
            note(b, 0.9, freq(m), 0.28, "tri")
    for k in range(beats * 2):
        if rng.random() < 0.22:
            continue
        m = root + 12 + rng.choice(scale) + 12 * rng.choice([0, 0, 1])
        note(k * 0.5, 0.45, freq(m), 0.06 if intense else 0.05, "square" if intense else "sine")
    note(0, 4, freq(root), 0.05, "sine")
    note(4, 4, freq(root + scale[2]), 0.05, "sine")

    out = array("h")
    for v in buf:
        iv = int(clamp(v, -0.85, 0.85) * 32767)
        out.append(iv)
        if channels == 2:
            out.append(iv)
    return out.tobytes()


class Music:
    """Builds the music loops in a background thread and crossfades between them."""

    def __init__(self, ok):
        self.ok = ok
        self.enabled = True
        self.volume = 0.32
        self.cache = {}
        self.pending = set()
        self.ready = {}
        self.lock = threading.Lock()
        self.want = None
        self.playing = None
        self.channel = None

    def request(self, theme):
        if not self.ok:
            return
        for intense in (False, True):
            key = (theme, intense)
            if key in self.cache or key in self.pending:
                continue
            self.pending.add(key)
            threading.Thread(target=self._work, args=(key,), daemon=True).start()

    def _work(self, key):
        try:
            data = build_music(key[0], key[1], Synth.rate, Synth.channels)
        except Exception:
            data = None
        with self.lock:
            self.ready[key] = data

    def set_track(self, theme, intense):
        self.want = (theme, intense)

    def update(self):
        if not self.ok:
            return
        with self.lock:
            items = list(self.ready.items())
            self.ready.clear()
        for key, data in items:
            self.pending.discard(key)
            if data:
                self.cache[key] = pygame.mixer.Sound(buffer=data)
        snd = self.cache.get(self.want) if (self.enabled and self.want) else None
        if snd is None:
            if self.playing is not None and not self.enabled:
                self.playing.fadeout(300)
                self.playing = None
                self.channel = None
            return
        if self.playing is not snd:
            if self.playing is not None:
                self.playing.fadeout(500)
            snd.set_volume(self.volume)
            self.channel = snd.play(loops=-1, fade_ms=700)
            self.playing = snd


# ----------------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------------
class Storage:
    def __init__(self):
        self.data = {
            "best": {}, "top": {}, "achievements": [], "total_apples": 0, "games": 0,
            "stats": {"play_ms": 0, "longest": 0, "mice": 0, "spiders": 0, "quests": 0,
                      "portals": 0, "bombs": 0},
            "settings": {"mode": 0, "diff": 1, "theme": 0, "skin": 0, "audio": 0},
        }
        self.load()

    def load(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            for k, v in loaded.items():
                if k in self.data:
                    if isinstance(self.data[k], dict) and isinstance(v, dict):
                        self.data[k].update(v)
                    else:
                        self.data[k] = v
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except OSError:
            pass

    def add_record(self, key, score):
        if score <= 0:
            return
        lst = self.data["top"].setdefault(key, [])
        lst.append([score, date.today().isoformat()])
        lst.sort(key=lambda r: -r[0])
        del lst[5:]


# ----------------------------------------------------------------------------
# Game objects
# ----------------------------------------------------------------------------
class Snake:
    def __init__(self, x, y, direction, length=3):
        self.dir = direction
        self.angle = math.atan2(direction[1], direction[0])
        self.body = [(x - direction[0] * i, y - direction[1] * i) for i in range(length)]
        self.prev = list(self.body)          # positions before the last step (smooth motion)
        self.queue = deque()
        self.grow = 0
        self.shield = 0
        self.bulges = []                     # swallowed food travelling down the body
        self.tongue = random.uniform(0, 6)

    @property
    def head(self):
        return self.body[0]


class Food:
    __slots__ = ("pos", "kind", "born", "life")

    def __init__(self, pos, kind, born):
        self.pos = pos
        self.kind = kind
        self.born = born
        self.life = FOOD_LIFE[kind]


class Mouse:
    def __init__(self, pos, born):
        self.pos = pos
        self.prev = pos
        self.dir = random.choice(DIRS)
        self.acc = 0.0
        self.born = born


class Spider:
    def __init__(self, pos):
        self.pos = pos
        self.prev = pos
        self.dir = random.choice(DIRS)
        self.acc = random.uniform(0, 200)
        self.phase = random.uniform(0, 6)


class Bomb:
    def __init__(self, pos, fuse=BOMB_FUSE_MS):
        self.pos = pos
        self.fuse = fuse
        self.max = fuse


# ----------------------------------------------------------------------------
# Sprite drawing (module level so the help screen can reuse them)
# ----------------------------------------------------------------------------
ITEM_COLORS = {
    "apple": (235, 80, 65), "gold": (255, 215, 0), "slow": (90, 170, 255),
    "shield": (120, 220, 255), "ghost": (190, 150, 255), "double": (255, 220, 70),
    "shrink": (255, 150, 90), "magnet": (240, 90, 90), "freeze": (150, 225, 255),
    "dizzy": (190, 80, 220),
}


def draw_item(surf, kind, cx, cy, anim, tiny_font=None):
    """Draw one pickup centred on (cx, cy)."""
    pulse = 1 + 0.07 * math.sin(anim / 130 + cx)
    if kind == "apple":
        r = int(9 * pulse)
        pygame.draw.circle(surf, (140, 28, 30), (cx, cy + 1), r + 1)
        pygame.draw.circle(surf, (225, 60, 55), (cx, cy), r)
        pygame.draw.circle(surf, (245, 115, 98), (cx - 2, cy - 2), max(2, r - 4))
        pygame.draw.ellipse(surf, (255, 215, 205), (cx - 6, cy - 6, 5, 3))
        pygame.draw.line(surf, (90, 60, 30), (cx, cy - r + 1), (cx + 2, cy - r - 4), 2)
        pygame.draw.ellipse(surf, (80, 190, 80), (cx + 1, cy - r - 3, 7, 4))
    elif kind == "gold":
        for scale, col in ((1.0, (230, 170, 20)), (0.65, (255, 225, 90))):
            pts = []
            for i in range(10):
                ang = -math.pi / 2 + i * math.pi / 5 + anim / 600
                rad = (11 if i % 2 == 0 else 5) * pulse * scale
                pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
            pygame.draw.polygon(surf, col, pts)
    elif kind == "slow":
        pygame.draw.circle(surf, (60, 130, 220), (cx, cy + 3), 8)
        pygame.draw.circle(surf, (120, 190, 255), (cx - 2, cy + 1), 5)
        pygame.draw.rect(surf, (210, 235, 255), (cx - 3, cy - 9, 6, 7))
        pygame.draw.rect(surf, (150, 100, 60), (cx - 3, cy - 11, 6, 3))
    elif kind == "shield":
        pygame.draw.polygon(surf, (70, 170, 220), [
            (cx - 9, cy - 8), (cx + 9, cy - 8), (cx + 8, cy + 2), (cx, cy + 11), (cx - 8, cy + 2)])
        pygame.draw.polygon(surf, (150, 235, 255), [
            (cx - 6, cy - 5), (cx + 6, cy - 5), (cx + 5, cy + 1), (cx, cy + 7), (cx - 5, cy + 1)])
    elif kind == "ghost":
        col = (205, 165, 255)
        pygame.draw.circle(surf, col, (cx, cy - 2), 8)
        pygame.draw.rect(surf, col, (cx - 8, cy - 2, 16, 9))
        for i in range(3):
            pygame.draw.circle(surf, col, (cx - 5 + i * 5, cy + 8), 3)
        pygame.draw.circle(surf, (30, 20, 50), (cx - 3, cy - 3), 2)
        pygame.draw.circle(surf, (30, 20, 50), (cx + 3, cy - 3), 2)
    elif kind == "double":
        pygame.draw.circle(surf, (190, 140, 20), (cx, cy), int(11 * pulse))
        pygame.draw.circle(surf, (255, 220, 70), (cx, cy), int(9 * pulse))
        if tiny_font:
            draw_text(surf, tiny_font, "x2", (110, 70, 0), (cx, cy), "center", False)
    elif kind == "magnet":
        red = (235, 70, 70)
        pygame.draw.arc(surf, red, pygame.Rect(cx - 9, cy - 9, 18, 18), math.pi, math.tau, 5)
        for mx in (cx - 9, cx + 4):
            pygame.draw.rect(surf, red, (mx, cy - 6, 5, 7))
            pygame.draw.rect(surf, (230, 230, 240), (mx, cy - 10, 5, 4))
    elif kind == "shrink":
        pygame.draw.circle(surf, (255, 150, 90), (cx, cy), 11)
        pygame.draw.line(surf, (255, 255, 255), (cx - 6, cy - 6), (cx + 5, cy + 4), 2)
        pygame.draw.line(surf, (255, 255, 255), (cx + 6, cy - 6), (cx - 5, cy + 4), 2)
        pygame.draw.circle(surf, (110, 40, 0), (cx - 5, cy + 6), 3, 2)
        pygame.draw.circle(surf, (110, 40, 0), (cx + 5, cy + 6), 3, 2)
    elif kind == "freeze":
        col = (170, 235, 255)
        for k in range(3):
            a = k * math.pi / 3 + anim / 900
            dx, dy = math.cos(a) * 10, math.sin(a) * 10
            pygame.draw.line(surf, col, (cx - dx, cy - dy), (cx + dx, cy + dy), 2)
        pygame.draw.circle(surf, (235, 250, 255), (cx, cy), 3)
    elif kind == "dizzy":
        pygame.draw.rect(surf, (240, 225, 190), (cx - 3, cy, 6, 9), border_radius=2)
        pygame.draw.ellipse(surf, (165, 55, 200), (cx - 10, cy - 10, 20, 14))
        for dx, dy, rr in ((-5, -6, 2), (2, -8, 2), (6, -4, 2), (-1, -3, 1)):
            pygame.draw.circle(surf, (250, 240, 255), (cx + dx, cy + dy), rr)


def draw_mouse(surf, cx, cy, d, anim, frozen=False):
    dx, dy = d
    px, py = -dy, dx
    body = (176, 176, 190) if not frozen else (190, 225, 245)
    dark = (120, 120, 135)
    pink = (245, 165, 175)
    bx, by = cx - dx * 3, cy - dy * 3
    hx, hy = cx + dx * 5, cy + dy * 5
    wag = math.sin(anim / 90) * 3 * (0 if frozen else 1)
    tail_end = (bx - dx * 12 + px * wag, by - dy * 12 + py * wag)
    pygame.draw.line(surf, pink, (bx - dx * 5, by - dy * 5), tail_end, 2)
    pygame.draw.circle(surf, dark, (bx, by), 8)
    pygame.draw.circle(surf, body, (bx, by), 7)
    pygame.draw.circle(surf, dark, (hx, hy), 6)
    pygame.draw.circle(surf, body, (hx, hy), 5)
    for side in (-1, 1):
        ex, ey = hx - dx * 2 + px * 4 * side, hy - dy * 2 + py * 4 * side
        pygame.draw.circle(surf, dark, (int(ex), int(ey)), 4)
        pygame.draw.circle(surf, pink, (int(ex), int(ey)), 2)
        eyx, eyy = hx + dx * 1 + px * 2 * side, hy + dy * 1 + py * 2 * side
        pygame.draw.circle(surf, (20, 20, 30), (int(eyx), int(eyy)), 1)
    pygame.draw.circle(surf, pink, (hx + dx * 5, hy + dy * 5), 2)


def draw_spider(surf, cx, cy, phase, d, frozen=False):
    body = (45, 32, 60) if not frozen else (150, 200, 230)
    leg = (28, 20, 38) if not frozen else (205, 238, 255)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        wig = 0.0 if frozen else math.sin(phase + k * 1.3) * 0.28
        k1 = (cx + math.cos(a + wig) * 8, cy + math.sin(a + wig) * 8)
        k2 = (k1[0] + math.cos(a + wig * 2 + 0.7) * 7, k1[1] + math.sin(a + wig * 2 + 0.7) * 7)
        pygame.draw.line(surf, leg, (cx, cy), k1, 2)
        pygame.draw.line(surf, leg, k1, k2, 2)
    pygame.draw.circle(surf, body, (cx - d[0] * 2, cy - d[1] * 2), 6)
    hx, hy = cx + d[0] * 5, cy + d[1] * 5
    pygame.draw.circle(surf, body, (hx, hy), 4)
    if not frozen:
        pygame.draw.circle(surf, (230, 40, 40), (cx - d[0] * 2, cy - d[1] * 2), 2)
    px, py = -d[1], d[0]
    for side in (-1, 1):
        pygame.draw.circle(surf, (255, 60, 60) if not frozen else (40, 90, 140),
                           (int(hx + d[0] * 2 + px * 2 * side), int(hy + d[1] * 2 + py * 2 * side)), 1)


def draw_bomb(surf, cx, cy, anim, frac):
    """frac = remaining fuse 0..1."""
    danger = frac < 0.28
    blink = danger and int(anim / (60 + 200 * frac)) % 2 == 0
    pygame.draw.circle(surf, (15, 15, 20), (cx, cy + 1), 10)
    pygame.draw.circle(surf, (55, 55, 70) if not blink else (190, 40, 40), (cx, cy), 9)
    pygame.draw.circle(surf, (110, 110, 130), (cx - 3, cy - 3), 3)
    pygame.draw.line(surf, (150, 120, 70), (cx + 3, cy - 8), (cx + 7, cy - 13), 2)
    spark = (255, 200 + int(55 * math.sin(anim / 40)), 60)
    pygame.draw.circle(surf, spark, (cx + 7, cy - 13), 3)
    pygame.draw.circle(surf, (255, 255, 200), (cx + 7, cy - 13), 1)


# ----------------------------------------------------------------------------
# Main game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except (pygame.error, AttributeError):
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Dynamic Snake 3")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16, bold=True)
        self.tiny = pygame.font.SysFont("arial", 12, bold=True)
        self.big = pygame.font.SysFont("arial", 56, bold=True)
        self.medium = pygame.font.SysFont("arial", 32, bold=True)
        self.huge = pygame.font.SysFont("arial", 120, bold=True)

        self.store = Storage()
        self.sound = Sound()
        self.music = Music(self.sound.ok)
        s = self.store.data["settings"]
        self.mode_i = s.get("mode", 0) % len(MODES)
        self.diff_i = s.get("diff", 1) % len(DIFFS)
        self.theme_i = s.get("theme", 0) % len(THEME_NAMES)
        self.skin_i = s.get("skin", 0) % len(SKIN_NAMES)
        self.audio_i = s.get("audio", 0) % len(AUDIO_MODES)
        self.apply_audio()

        self.state = "menu"
        self.last_state = "menu"
        self.fade = 255.0
        self.menu_sel = 5
        self.anim = 0.0
        self.toasts = []
        self.glow_cache = {}
        self.light_cache = {}
        self.rock_cache = {}
        self.vignette = self.make_vignette()
        self.canvas = pygame.Surface((W, H))
        self.tint = pygame.Surface((W, H))
        self.shadow_layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.dark_layer = pygame.Surface((W, H - HUD), pygame.SRCALPHA)
        self.bg_surface = None
        self.ambient = []
        self.fireflies = [[random.uniform(0, W), random.uniform(HUD, H), random.uniform(0, 6.28),
                           random.uniform(0.3, 1.0)] for _ in range(16)]
        self.show_quests = True
        self.head_px = (W / 2, H / 2)
        self.zoom = 1.0
        self.reset()
        self.refresh_theme()

    # ------------------------------------------------------------------
    # convenience properties
    # ------------------------------------------------------------------
    @property
    def mode(self):
        return MODES[self.mode_i]

    @property
    def diff(self):
        return DIFFS[self.diff_i]

    @property
    def theme(self):
        return THEMES[THEME_NAMES[self.theme_i]]

    @property
    def wrap(self):
        return self.mode == "Wrap"

    @property
    def best_key(self):
        return f"{self.mode}-{self.diff}"

    def best(self):
        return self.store.data["best"].get(self.best_key, 0)

    def player_skin(self):
        skin = SKINS[SKIN_NAMES[self.skin_i]]
        if skin is None:
            th = self.theme
            skin = dict(kind="diamond", a=th["head"], b=th["tail"],
                        mark=lerp_col(th["tail"], (0, 0, 0), 0.35))
        return skin

    def rival_skin(self):
        th = self.theme
        return dict(kind="diamond", a=th["rival"], b=th["rival_tail"],
                    mark=lerp_col(th["rival_tail"], (0, 0, 0), 0.3))

    def apply_audio(self):
        self.sound.sfx_on = self.audio_i in (0, 1)
        self.music.enabled = self.audio_i in (0, 2)

    def refresh_theme(self):
        self.glow_cache.clear()
        self.rock_cache.clear()
        self.bg_surface = self.make_background()
        self.ambient = self.make_ambient()
        self.music.request(THEME_NAMES[self.theme_i])

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------
    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.player = Snake(cx, cy, RIGHT)
        self.rival = None
        self.rival_respawn = 0
        self.score = 0
        self.disp_score = 0.0
        self.eaten = 0
        self.level = 1
        self.combo = 1
        self.last_eat = -99999
        self.obstacles = set()
        self.foods = []
        self.mice = []
        self.spiders = []
        self.bombs = []
        self.portals = []
        self.portal_map = {}
        self.portal_cd = 0
        self.particles = []
        self.floaters = []
        self.fx = {n: 0 for n in FX_NAMES}
        self.surge = 0
        self.energy = 100.0
        self.boosting = False
        self.pop = 0.0
        self.flash = 0.0
        self.shake = 0.0
        self.t = 0.0
        self.acc = 0.0
        self.racc = 0.0
        self.mouse_acc = 0.0
        self.time_left = TIME_ATTACK_MS
        self.cause = ""
        self.new_best = False
        self.max_len = 3
        self.night_force = 0
        self.chaos_next = 14000
        self.chaos_events = 0
        self.last_near = -9999
        self.apple_times = deque()
        # per-round counters (NOT named "run": that would shadow Game.run())
        self.rs = dict(mice=0, spiders=0, quests=0, boost_ms=0, night=0, power=0, near=0)
        self.countdown = COUNTDOWN_MS
        self.last_count = 4
        self.death_t = 0.0
        self.death_acc = 0.0
        self.quests = []
        for _ in range(3):
            self.quests.append(self.make_quest())
        self.spawn_food("apple")
        if self.mode == "Maze":
            self.load_maze(0)
        if self.mode == "Rival":
            self.spawn_rival()

    def save_settings(self):
        st = self.store.data["settings"]
        st.update(mode=self.mode_i, diff=self.diff_i, theme=self.theme_i, skin=self.skin_i,
                  audio=self.audio_i)
        self.store.save()

    def interval(self):
        base = BASE_INTERVAL[self.diff] - (self.level - 1) * 8
        base = max(MIN_INTERVAL[self.diff], base)
        if self.active("slow"):
            base *= 1.7
        if self.t < self.surge:
            base *= 0.75
        return base

    def player_interval(self):
        return self.interval() * (BOOST_FACTOR if self.boosting else 1.0)

    def rival_interval(self):
        return self.interval() * RIVAL_SPEED[self.diff]

    def active(self, name):
        return self.t < self.fx[name]

    def daylight(self):
        """1.0 = bright day, 0.0 = deep night."""
        d = 0.5 + 0.5 * math.cos(math.tau * self.t / DAY_LENGTH_MS)
        d = clamp(d * 1.25 - 0.05, 0.0, 1.0)
        if self.t < self.night_force:
            d = min(d, 0.08)
        return d

    # ------------------------------------------------------------------
    # spawning
    # ------------------------------------------------------------------
    def used_cells(self):
        used = set(self.player.body) | self.obstacles | {f.pos for f in self.foods}
        used |= {m.pos for m in self.mice} | {s.pos for s in self.spiders}
        used |= {b.pos for b in self.bombs} | set(self.portals)
        if self.rival:
            used |= set(self.rival.body)
        return used

    def free_cells(self):
        used = self.used_cells()
        return [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in used]

    def far_cells(self, dist):
        hx, hy = self.player.head
        return [c for c in self.free_cells() if abs(c[0] - hx) + abs(c[1] - hy) > dist]

    def spawn_food(self, kind):
        cells = self.free_cells()
        if cells:
            self.foods.append(Food(random.choice(cells), kind, self.t))

    def has_food(self, kind):
        return any(f.kind == kind for f in self.foods)

    def ensure_apple(self):
        if not self.has_food("apple"):
            self.spawn_food("apple")

    def add_obstacles(self, clusters):
        hx, hy = self.player.head
        for _ in range(clusters):
            cells = [c for c in self.free_cells()
                     if abs(c[0] - hx) + abs(c[1] - hy) > 7
                     and 1 < c[0] < COLS - 2 and 1 < c[1] < ROWS - 2]
            if not cells:
                return
            cx, cy = random.choice(cells)
            block = [(cx, cy)]
            for _ in range(random.randint(0, 2)):
                d = random.choice(DIRS)
                nxt = (block[-1][0] + d[0], block[-1][1] + d[1])
                if nxt in cells and nxt not in block:
                    block.append(nxt)
            for c in block:
                self.obstacles.add(c)
                self.rock_cache.pop(c, None)
                self.burst(c, self.theme["rock2"], 6)

    def load_maze(self, idx):
        layout = MAZE_LAYOUTS[idx % len(MAZE_LAYOUTS)]
        hx, hy = self.player.head
        body = set(self.player.body)
        self.obstacles = {c for c in layout
                          if c not in body and abs(c[0] - hx) + abs(c[1] - hy) > 3}
        self.rock_cache.clear()
        # remove anything that now sits inside a wall
        self.foods = [f for f in self.foods if f.pos not in self.obstacles]
        self.mice = [m for m in self.mice if m.pos not in self.obstacles]
        self.spiders = [s for s in self.spiders if s.pos not in self.obstacles]
        self.bombs = [b for b in self.bombs if b.pos not in self.obstacles]
        if any(p in self.obstacles for p in self.portals):
            self.portals, self.portal_map = [], {}
        if self.rival and any(c in self.obstacles for c in self.rival.body):
            self.rival = None
            self.rival_respawn = self.t + 1000
        self.ensure_apple()
        for c in list(self.obstacles)[::4]:
            self.burst(c, self.theme["rock2"], 2)

    def spawn_rival(self):
        px, py = self.player.head
        used = self.used_cells()
        for _ in range(300):
            x = random.randint(4, COLS - 5)
            y = random.randint(2, ROWS - 3)
            cells = [(x - i, y) for i in range(3)]
            if abs(x - px) + abs(y - py) > 10 and all(c not in used for c in cells):
                self.rival = Snake(x, y, RIGHT)
                self.burst((x, y), self.theme["rival"], 16)
                return
        self.rival = None
        self.rival_respawn = self.t + 2000

    def spawn_mouse(self):
        if self.mice:
            return
        cells = self.far_cells(8)
        if cells:
            m = Mouse(random.choice(cells), self.t)
            self.mice.append(m)
            self.burst(m.pos, (200, 200, 210), 8)

    def spawn_bomb(self):
        if len(self.bombs) >= 3:
            return
        cells = self.far_cells(6)
        if cells:
            self.bombs.append(Bomb(random.choice(cells)))

    def spider_target(self):
        if self.level < 3:
            return 0
        return min(SPIDER_CAP[self.diff], (self.level - 1) // 2)

    def ensure_spiders(self):
        while len(self.spiders) < self.spider_target():
            cells = self.far_cells(9)
            if not cells:
                break
            sp = Spider(random.choice(cells))
            self.spiders.append(sp)
            self.burst(sp.pos, (160, 90, 200), 10)

    def make_portals(self):
        hx, hy = self.player.head
        cells = [c for c in self.free_cells() if 2 <= c[0] < COLS - 2 and 2 <= c[1] < ROWS - 2
                 and abs(c[0] - hx) + abs(c[1] - hy) > 4]
        if len(cells) < 2:
            return
        a = random.choice(cells)
        far = [c for c in cells if abs(c[0] - a[0]) + abs(c[1] - a[1]) > 12]
        if not far:
            return
        b = random.choice(far)
        self.portals = [a, b]
        self.portal_map = {a: b, b: a}
        self.burst(a, (80, 170, 255), 18)
        self.burst(b, (255, 150, 60), 18)
        self.toast("Portals opened!", (140, 200, 255))

    # ------------------------------------------------------------------
    # quests
    # ------------------------------------------------------------------
    def make_quest(self):
        have = {q["kind"] for q in self.quests}
        pool = [q for q in QUEST_TYPES if q[0] not in have] or QUEST_TYPES
        kind, text, (lo, hi), reward = random.choice(pool)
        if kind == "length":
            n = max(lo, len(self.player.body) + random.randint(4, 8))
        elif kind == "score":
            n = random.randrange(lo, hi + 1, 50)
        else:
            n = random.randint(lo, hi)
        if kind == "mouse" and n > 1:
            text = "Catch {n} mice"
        return dict(kind=kind, text=text.format(n=n), goal=n, prog=0, reward=reward,
                    done=False, done_at=0, base=self.score)

    def quest_event(self, kind, amt=1):
        for q in self.quests:
            if not q["done"] and q["kind"] == kind:
                q["prog"] = min(q["goal"], q["prog"] + amt)
                if q["prog"] >= q["goal"]:
                    self.complete_quest(q)

    def quest_set(self, kind, value):
        for q in self.quests:
            if not q["done"] and q["kind"] == kind and value > q["prog"]:
                q["prog"] = min(q["goal"], value)
                if q["prog"] >= q["goal"]:
                    self.complete_quest(q)

    def complete_quest(self, q):
        q["done"] = True
        q["done_at"] = self.t
        bonus = q["reward"] * self.level
        self.score += bonus
        self.rs["quests"] += 1
        st = self.store.data["stats"]
        st["quests"] += 1
        self.toast(f"Quest complete!  +{bonus}", (255, 225, 110))
        self.floater(self.player.head, f"+{bonus}", (255, 235, 170))
        self.sound.play("quest")
        if st["quests"] >= 5:
            self.unlock("quest_master")

    def update_quests(self):
        for i, q in enumerate(self.quests):
            if q["done"] and self.t - q["done_at"] > 3000:
                self.quests[i] = self.make_quest()
        self.quest_set("length", len(self.player.body))
        for q in self.quests:
            if not q["done"] and q["kind"] == "score":
                self.quest_set("score", self.score - q["base"])

    # ------------------------------------------------------------------
    # effects and feedback
    # ------------------------------------------------------------------
    def burst(self, cell, color, n=14):
        x = cell[0] * CELL + CELL / 2
        y = cell[1] * CELL + CELL / 2 + HUD
        self.burst_px((x, y), color, n)

    def burst_px(self, pos, color, n=14):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, 5)
            self.particles.append([pos[0], pos[1], math.cos(a) * sp, math.sin(a) * sp,
                                   random.randint(20, 40), color])

    def floater(self, cell, text, color):
        self.floaters.append([cell[0] * CELL + CELL / 2, cell[1] * CELL + HUD,
                              text, color, 50])

    def toast(self, text, color=None):
        self.toasts.append([text, color or self.theme["accent"], 180])

    def unlock(self, key):
        if key in self.store.data["achievements"]:
            return
        self.store.data["achievements"].append(key)
        self.store.save()
        self.toast("Achievement: " + ACHIEVEMENTS[key][0], (255, 215, 80))
        self.sound.play("win")

    def add_score(self, base, cell):
        mult = self.level * self.combo * (2 if self.active("double") else 1)
        pts = base * mult
        self.score += pts
        self.floater(cell, f"+{pts}", (255, 235, 170))
        if self.score >= 200:
            self.unlock("score_200")

    # ------------------------------------------------------------------
    # movement helpers
    # ------------------------------------------------------------------
    def advance(self, cell, d):
        x, y = cell[0] + d[0], cell[1] + d[1]
        if self.wrap:
            x %= COLS
            y %= ROWS
        return x, y

    def block_reason(self, cell):
        p = self.player
        x, y = cell
        if not (0 <= x < COLS and 0 <= y < ROWS):
            return "the wall"
        if any(b.pos == cell for b in self.bombs):
            return "a bomb"
        if self.active("ghost"):
            return None
        body = p.body if p.grow > 0 else p.body[:-1]
        if cell in body:
            return "yourself"
        if cell in self.obstacles:
            return "a wall" if self.mode == "Maze" else "a rock"
        if self.rival and cell in self.rival.body and cell != self.rival.head:
            return "the rival"
        if not self.active("freeze") and any(s.pos == cell for s in self.spiders):
            return "a spider"
        return None

    def turn(self, d):
        if self.active("dizzy"):
            d = (-d[0], -d[1])
        p = self.player
        last = p.queue[-1] if p.queue else p.dir
        if d != last and (d[0] + last[0], d[1] + last[1]) != (0, 0) and len(p.queue) < 2:
            p.queue.append(d)

    def hazard_hit(self, reason):
        """A hazard touched the player.  Returns True if the player died."""
        if self.state != "play":
            return False
        p = self.player
        if p.shield > 0:
            p.shield -= 1
            self.burst(p.head, (120, 220, 255), 20)
            self.sound.play("hit")
            self.shake = 6
            self.flash = 0.5
            self.unlock("shield_used")
            self.toast("Shield absorbed the hit!", (120, 220, 255))
            return False
        self.die(reason)
        return True

    # ------------------------------------------------------------------
    # player step
    # ------------------------------------------------------------------
    def step_player(self):
        p = self.player
        p.prev = list(p.body)
        p.bulges = [b + 1 for b in p.bulges if b + 1 < len(p.body) + 1]
        if p.queue:
            p.dir = p.queue.popleft()
        cell = self.advance(p.head, p.dir)
        reason = self.block_reason(cell)

        if reason:
            if p.shield > 0:
                alts = [d for d in DIRS if d[0] * p.dir[0] + d[1] * p.dir[1] == 0
                        and self.block_reason(self.advance(p.head, d)) is None]
                if alts:
                    p.shield -= 1
                    p.dir = random.choice(alts)
                    p.queue.clear()
                    cell = self.advance(p.head, p.dir)
                    self.burst(p.head, (120, 220, 255), 20)
                    self.sound.play("hit")
                    self.shake = 6
                    self.flash = 0.5
                    self.unlock("shield_used")
                    self.toast("Shield absorbed the hit!", (120, 220, 255))
                else:
                    return self.die(reason)
            else:
                if reason == "a bomb":
                    for b in list(self.bombs):
                        if b.pos == cell:
                            self.detonate(b)
                    if self.state != "play":
                        return
                return self.die(reason)

        # portals
        dest = self.portal_map.get(cell)
        if dest and self.t >= self.portal_cd and self.block_reason(dest) is None:
            self.burst(cell, (120, 190, 255), 16)
            self.burst(dest, (255, 170, 80), 16)
            self.sound.play("portal")
            self.portal_cd = self.t + 500
            self.store.data["stats"]["portals"] += 1
            self.unlock("portal")
            cell = dest

        p.body.insert(0, cell)
        if p.grow > 0:
            p.grow -= 1
        else:
            p.body.pop()
        self.max_len = max(self.max_len, len(p.body))

        if self.rival and cell == self.rival.head:
            self.kill_rival("head-on")

        for m in self.mice[:]:
            if m.pos == cell:
                self.eat_mouse(m)
        for s in self.spiders[:]:
            if s.pos == cell:
                if self.active("freeze"):
                    self.kill_spider(s, "eaten")
                    p.grow += 1
        for f in self.foods[:]:
            if f.pos == cell:
                self.foods.remove(f)
                self.eat(f)

        self.pull_magnet()
        self.check_close_call()
        self.update_quests()
        if len(p.body) >= 20:
            self.unlock("length_20")

    def check_close_call(self):
        """Bonus for brushing past danger at boost speed."""
        if not self.boosting or self.t - self.last_near < 900:
            return
        hx, hy = self.player.head
        danger = set(self.obstacles) | {s.pos for s in self.spiders} | {b.pos for b in self.bombs}
        for d in DIRS:
            if (hx + d[0], hy + d[1]) in danger:
                self.last_near = self.t
                self.rs["near"] += 1
                self.add_score(3, self.player.head)
                self.floater(self.player.head, "CLOSE!", (255, 150, 90))
                self.quest_event("near")
                return

    def pull_magnet(self):
        if not self.active("magnet"):
            return
        hx, hy = self.player.head
        used = self.used_cells()
        for f in list(self.foods):
            if f.kind not in ("apple", "gold"):
                continue
            dx, dy = hx - f.pos[0], hy - f.pos[1]
            if abs(dx) + abs(dy) > 6 or (dx, dy) == (0, 0):
                continue
            if abs(dx) >= abs(dy):
                new = (f.pos[0] + (1 if dx > 0 else -1), f.pos[1])
            else:
                new = (f.pos[0], f.pos[1] + (1 if dy > 0 else -1))
            if new == (hx, hy):
                self.foods.remove(f)
                self.eat(f)
            elif new not in used:
                f.pos = new

    # ------------------------------------------------------------------
    # eating
    # ------------------------------------------------------------------
    def eat(self, f):
        p = self.player
        kind, pos = f.kind, f.pos
        if kind in ("apple", "gold"):
            self.pop = 1.0
            p.bulges.append(0.0)
        if kind in POWER_KINDS:
            self.rs["power"] += 1
            self.quest_event("power")
        if kind == "apple":
            if self.t - self.last_eat <= COMBO_WINDOW_MS:
                self.combo = min(5, self.combo + 1)
            else:
                self.combo = 1
            self.last_eat = self.t
            if self.combo >= 5:
                self.unlock("combo_5")
            self.add_score(10, pos)
            p.grow += 1
            self.eaten += 1
            d = self.store.data
            d["total_apples"] += 1
            self.unlock("first_bite")
            if d["total_apples"] >= 100:
                self.unlock("collector")
            if self.daylight() < 0.35:
                self.rs["night"] += 1
                if self.rs["night"] >= 8:
                    self.unlock("night_owl")
            self.apple_times.append(self.t)
            while self.apple_times and self.t - self.apple_times[0] > 12000:
                self.apple_times.popleft()
            self.quest_event("apples")
            self.quest_set("fast", len(self.apple_times))
            self.burst(pos, (235, 80, 65))
            self.sound.play("eat")
            if self.mode == "Time Attack":
                self.time_left += APPLE_BONUS_MS
            self.ensure_apple()
            self.roll_special()
            if self.eaten % 5 == 0:
                self.level_up()
        elif kind == "gold":
            self.add_score(50, pos)
            p.grow += 2
            self.burst(pos, (255, 215, 0), 26)
            self.sound.play("gold")
        elif kind == "slow":
            self.fx["slow"] = self.t + 5000
            self.power_feedback(pos, (90, 170, 255), "SLOW")
        elif kind == "shield":
            p.shield = min(2, p.shield + 1)
            self.power_feedback(pos, (120, 220, 255), "SHIELD")
        elif kind == "ghost":
            self.fx["ghost"] = self.t + 6000
            self.unlock("ghost_run")
            self.power_feedback(pos, (190, 150, 255), "GHOST")
        elif kind == "double":
            self.fx["double"] = self.t + 8000
            self.power_feedback(pos, (255, 220, 70), "x2 POINTS")
        elif kind == "magnet":
            self.fx["magnet"] = self.t + 7000
            self.power_feedback(pos, (240, 90, 90), "MAGNET")
        elif kind == "freeze":
            self.fx["freeze"] = self.t + 4500
            self.power_feedback(pos, (150, 225, 255), "FREEZE!")
            self.sound.play("freeze")
        elif kind == "dizzy":
            self.fx["dizzy"] = self.t + 5000
            self.power_feedback(pos, (190, 80, 220), "DIZZY!")
            self.sound.play("dizzy")
            self.toast("Controls reversed!", (200, 110, 230))
        elif kind == "shrink":
            cut = max(0, min(3, len(p.body) - 3))
            for _ in range(cut):
                self.burst(p.body.pop(), (255, 150, 90), 4)
            p.prev = list(p.body)
            self.score += 5
            self.power_feedback(pos, (255, 150, 90), "SNIP!")

    def eat_mouse(self, m):
        if m in self.mice:
            self.mice.remove(m)
        p = self.player
        self.pop = 1.0
        p.bulges.append(0.0)
        p.grow += 1
        self.add_score(40, m.pos)
        self.burst(m.pos, (200, 200, 210), 14)
        self.sound.play("crunch")
        self.sound.play("squeak")
        self.rs["mice"] += 1
        st = self.store.data["stats"]
        st["mice"] += 1
        if st["mice"] >= 10:
            self.unlock("mouse_hunter")
        self.quest_event("mouse")

    def power_feedback(self, pos, color, text):
        self.burst(pos, color, 22)
        self.floater(pos, text, color)
        self.sound.play("power")

    def roll_special(self):
        r = random.random()
        acc = 0.0
        for kind, prob in SPECIAL_ROLLS:
            acc += prob
            if r < acc:
                if kind == "mouse":
                    self.spawn_mouse()
                elif kind == "bomb":
                    self.spawn_bomb()
                elif not self.has_food(kind):
                    self.spawn_food(kind)
                return

    def level_up(self):
        self.level += 1
        self.flash = 1.0
        if self.mode == "Maze":
            self.load_maze(self.level - 1)
            self.add_obstacles(1)
            if self.level == 2:
                self.make_portals()
        else:
            self.add_obstacles(2 if self.level < 6 else 3)
        if self.level % 3 == 0:
            self.make_portals()
        self.ensure_spiders()
        self.toast(f"LEVEL {self.level}", (255, 240, 120))
        self.sound.play("level")
        if self.level >= 5:
            self.unlock("level_5")

    # ------------------------------------------------------------------
    # spiders
    # ------------------------------------------------------------------
    def spider_can_enter(self, s, n):
        if not (0 <= n[0] < COLS and 0 <= n[1] < ROWS):
            return False
        if n in self.obstacles or n in self.portal_map:
            return False
        if any(b.pos == n for b in self.bombs):
            return False
        if any(o is not s and o.pos == n for o in self.spiders):
            return False
        if n in self.player.body[1:]:
            return False
        if self.rival and n in self.rival.body:
            return False
        return True

    def move_spider(self, s):
        hx, hy = self.player.head
        dist = abs(s.pos[0] - hx) + abs(s.pos[1] - hy)
        # strike when adjacent
        if dist == 1 and random.random() < 0.6 and not self.active("ghost"):
            s.prev = s.pos
            s.dir = (hx - s.pos[0], hy - s.pos[1])
            s.pos = (hx, hy)
            self.sound.play("spider")
            if self.hazard_hit("a spider"):
                return
            self.kill_spider(s, "shield")
            return
        opts = []
        for d in DIRS:
            n = (s.pos[0] + d[0], s.pos[1] + d[1])
            if self.spider_can_enter(s, n) and n != (hx, hy):
                opts.append((d, n))
        if not opts:
            return
        pick = None
        r = random.random()
        if dist <= 9 and r < 0.35:
            pick = min(opts, key=lambda o: abs(o[1][0] - hx) + abs(o[1][1] - hy))
        elif r < 0.75:
            pick = next((o for o in opts if o[0] == s.dir), None)
        if pick is None:
            pick = random.choice(opts)
        s.prev = s.pos
        s.dir, s.pos = pick

    def update_spiders(self, dt):
        frozen = self.active("freeze")
        iv = SPIDER_INTERVAL[self.diff]
        for s in list(self.spiders):
            if frozen:
                continue
            s.phase += dt / 60
            s.acc += dt
            while s.acc >= iv and self.state == "play":
                s.acc -= iv
                self.move_spider(s)
                if s not in self.spiders:
                    break
        self.ensure_spiders()

    def kill_spider(self, s, how):
        if s in self.spiders:
            self.spiders.remove(s)
        self.burst(s.pos, (170, 110, 210), 16)
        if how in ("eaten", "bomb"):
            self.add_score(30, s.pos)
            self.sound.play("crunch")
        st = self.store.data["stats"]
        st["spiders"] += 1
        self.rs["spiders"] += 1
        if st["spiders"] >= 5:
            self.unlock("spider_bane")

    # ------------------------------------------------------------------
    # mice
    # ------------------------------------------------------------------
    def update_mice(self, dt):
        if self.active("freeze"):
            return
        iv = MOUSE_INTERVAL[self.diff]
        for m in list(self.mice):
            if self.t - m.born > MOUSE_LIFE_MS:
                self.mice.remove(m)
                self.burst(m.pos, (200, 200, 210), 8)
                continue
            m.acc += dt
            while m.acc >= iv:
                m.acc -= iv
                self.move_mouse(m)

    def move_mouse(self, m):
        hx, hy = self.player.head
        opts = []
        for d in DIRS:
            n = (m.pos[0] + d[0], m.pos[1] + d[1])
            if not (0 <= n[0] < COLS and 0 <= n[1] < ROWS):
                continue
            if n in self.obstacles or n in self.portal_map or n in self.player.body:
                continue
            if any(b.pos == n for b in self.bombs) or any(s.pos == n for s in self.spiders):
                continue
            if self.rival and n in self.rival.body:
                continue
            opts.append((d, n))
        if not opts:
            return
        dist = abs(m.pos[0] - hx) + abs(m.pos[1] - hy)
        if dist <= 6 and random.random() < 0.85:
            pick = max(opts, key=lambda o: abs(o[1][0] - hx) + abs(o[1][1] - hy)
                       + random.random() * 0.5)
        elif random.random() < 0.5:
            return
        else:
            pick = random.choice(opts)
        m.prev = m.pos
        m.dir, m.pos = pick

    # ------------------------------------------------------------------
    # bombs
    # ------------------------------------------------------------------
    def update_bombs(self, dt):
        for b in list(self.bombs):
            b.fuse -= dt
            if b.fuse <= 0:
                self.detonate(b)
                if self.state != "play":
                    return

    def detonate(self, b):
        if b in self.bombs:
            self.bombs.remove(b)
        cx, cy = b.pos
        self.sound.play("explode")
        self.shake = 16
        self.flash = 0.9
        area = [(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                if abs(dx) + abs(dy) <= 2]
        fire = [(255, 200, 60), (255, 120, 40), (90, 90, 90)]
        for c in area:
            self.burst(c, random.choice(fire), 4)
        for c in area:
            if c in self.obstacles:
                self.obstacles.discard(c)
                self.rock_cache.pop(c, None)
                self.score += 5
        for s in list(self.spiders):
            if s.pos in area:
                self.kill_spider(s, "bomb")
                self.store.data["stats"]["bombs"] += 1
        self.mice = [m for m in self.mice if m.pos not in area]
        self.foods = [f for f in self.foods if f.pos not in area]
        self.ensure_apple()
        for o in self.bombs:                            # chain reaction
            if o.pos in area:
                o.fuse = min(o.fuse, 180)
        if self.rival and any(c in area for c in self.rival.body[:2]):
            self.kill_rival("bomb")
        near = [c for c in self.player.body if abs(c[0] - cx) + abs(c[1] - cy) <= 1]
        if near:
            self.hazard_hit("an explosion")

    # ------------------------------------------------------------------
    # rival AI
    # ------------------------------------------------------------------
    def ai_choose(self):
        r = self.rival
        own = r.body if r.grow > 0 else r.body[:-1]
        blocked = (self.obstacles | set(self.player.body) | set(own)
                   | {s.pos for s in self.spiders} | {b.pos for b in self.bombs}
                   | set(self.portals))

        def neighbours(c):
            for d in DIRS:
                n = (c[0] + d[0], c[1] + d[1])
                if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and n not in blocked:
                    yield n

        options = list(neighbours(r.head))
        if not options:
            return None
        if random.random() < RIVAL_WOBBLE[self.diff]:
            return random.choice(options)

        targets = {f.pos for f in self.foods if f.kind in ("apple", "gold")}
        targets |= {m.pos for m in self.mice}
        prev = {r.head: None}
        queue = deque([r.head])
        goal = None
        while queue:
            c = queue.popleft()
            if c in targets and c != r.head:
                goal = c
                break
            for n in neighbours(c):
                if n not in prev:
                    prev[n] = c
                    queue.append(n)
        if goal is None:
            return random.choice(options)
        while prev[goal] != r.head:
            goal = prev[goal]
        return goal

    def step_rival(self):
        r = self.rival
        if not r:
            return
        move = self.ai_choose()
        if move is None:
            self.kill_rival("trapped")
            return
        r.prev = list(r.body)
        r.bulges = [b + 1 for b in r.bulges if b + 1 < len(r.body) + 1]
        r.dir = (move[0] - r.head[0], move[1] - r.head[1])
        r.body.insert(0, move)
        if r.grow > 0:
            r.grow -= 1
        else:
            r.body.pop()
        for f in self.foods[:]:
            if f.pos == move:
                self.foods.remove(f)
                if f.kind in ("apple", "gold"):
                    r.grow += 1
                    r.bulges.append(0.0)
                    self.burst(move, self.theme["rival"], 10)
                    self.ensure_apple()
        for m in self.mice[:]:
            if m.pos == move:
                self.mice.remove(m)
                r.grow += 1
                r.bulges.append(0.0)
                self.burst(move, self.theme["rival"], 10)

    def kill_rival(self, how):
        r = self.rival
        if not r:
            return
        for i, c in enumerate(r.body):
            if i % 3 == 0 and not any(f.pos == c for f in self.foods):
                self.foods.append(Food(c, "apple", self.t))
            self.burst(c, self.theme["rival"], 3)
        self.score += 100
        self.floater(r.head, "+100", (255, 235, 170))
        self.toast(f"Rival defeated ({how})!", self.theme["rival"])
        self.flash = 0.8
        self.shake = 8
        self.unlock("rival_slayer")
        self.sound.play("gold")
        self.rival = None
        self.rival_respawn = self.t + 6000

    # ------------------------------------------------------------------
    # chaos mode
    # ------------------------------------------------------------------
    def update_chaos(self):
        if self.mode != "Chaos" or self.t < self.chaos_next:
            return
        self.chaos_next = self.t + random.randint(13000, 19000)
        self.chaos_events += 1
        ev = random.choice(["quake", "rain", "night", "surge", "dizzy", "bombs", "swarm"])
        if ev == "quake":
            self.add_obstacles(3)
            self.shake = 18
            self.toast("EARTHQUAKE!", (230, 170, 100))
        elif ev == "rain":
            for _ in range(6):
                self.spawn_food("apple")
            self.toast("APPLE RAIN!", (255, 110, 100))
        elif ev == "night":
            self.night_force = self.t + 15000
            self.toast("NIGHT FALLS...", (140, 150, 255))
        elif ev == "surge":
            self.surge = self.t + 8000
            self.toast("SPEED SURGE!", (255, 200, 90))
        elif ev == "dizzy":
            self.fx["dizzy"] = self.t + 4000
            self.sound.play("dizzy")
            self.toast("DIZZY WINDS!", (200, 110, 230))
        elif ev == "bombs":
            for _ in range(3):
                self.spawn_bomb()
            self.toast("BOMB DROP!", (255, 140, 60))
        else:
            for _ in range(3):
                cells = self.far_cells(8)
                if cells:
                    self.spiders.append(Spider(random.choice(cells)))
            self.toast("SPIDER SWARM!", (170, 110, 210))
        self.sound.play("level")

    # ------------------------------------------------------------------
    # end of round
    # ------------------------------------------------------------------
    def finish(self, cause, survived=False):
        self.state = "dead"
        self.cause = cause
        d = self.store.data
        st = d["stats"]
        d["games"] += 1
        st["play_ms"] += int(self.t)
        st["longest"] = max(st["longest"], self.max_len)
        if self.score > d["best"].get(self.best_key, 0):
            d["best"][self.best_key] = self.score
            self.new_best = self.score > 0
        self.store.add_record(self.best_key, self.score)
        if survived:
            self.unlock("survivor")
        self.store.save()

    def die(self, reason):
        if self.state != "play":
            return
        self.state = "dying"
        self.cause = f"You crashed into {reason}"
        self.death_t = 0.0
        self.death_acc = 0.0
        self.shake = 14
        self.flash = 0.6
        self.boosting = False
        self.sound.play("die")

    def update_dying(self, dt):
        self.death_t += dt
        self.death_acc += dt
        skin = self.player_skin()
        while self.death_acc >= 45 and self.player.body:
            self.death_acc -= 45
            c = self.player.body.pop(0)
            self.burst(c, skin["a"], 5)
        if not self.player.body or self.death_t >= DEATH_MS:
            self.finish(self.cause)

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def update_music_track(self):
        intense = self.state in ("play", "pause", "dying", "countdown") and (
            self.level >= 3 or self.mode in ("Rival", "Chaos"))
        self.music.set_track(THEME_NAMES[self.theme_i], intense)

    def update_ambient(self, dt):
        wtype = self.theme["weather"]
        for a in self.ambient:
            a[0] += a[2] * dt / 16
            a[1] += a[3] * dt / 16
            a[5] += dt / 400
            if wtype in ("leaves", "snow"):
                a[0] += math.sin(a[5]) * 0.3
            if a[1] > H + 8 or a[1] < HUD - 20 or a[0] < -10 or a[0] > W + 10:
                if wtype in ("sparks", "embers"):
                    a[0], a[1] = random.uniform(0, W), H + 4
                else:
                    a[0], a[1] = random.uniform(0, W), HUD - 8
        for f in self.fireflies:
            f[2] += random.uniform(-0.25, 0.25)
            f[0] += math.cos(f[2]) * 0.4 * f[3]
            f[1] += math.sin(f[2]) * 0.4 * f[3]
            f[0] = clamp(f[0], 6, W - 6)
            f[1] = clamp(f[1], HUD + 6, H - 6)

    def update(self, dt):
        self.anim += dt
        self.music.update()
        self.update_music_track()
        self.update_ambient(dt)

        if self.state == "countdown":
            self.countdown -= dt
            n = int(self.countdown // 800) + 1
            if n != self.last_count and self.countdown > 0:
                self.last_count = n
                self.sound.play("tick")
            if self.countdown <= 0:
                self.state = "play"
                self.sound.play("go")
        elif self.state == "play":
            self.update_play(dt)
        elif self.state == "dying":
            self.update_dying(dt)
        self.update_fx(dt)

    def update_play(self, dt):
        self.t += dt
        self.acc += dt
        self.racc += dt
        if self.t - self.last_eat > COMBO_WINDOW_MS:
            self.combo = 1

        if self.mode == "Time Attack":
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.sound.play("win")
                self.finish("Time is up!", survived=True)
                return
        if self.t >= 180_000:
            self.unlock("marathon")

        # boost: hold SPACE / SHIFT, drains energy, recharges when released
        keys = pygame.key.get_pressed()
        want = keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        self.boosting = bool(want) and self.energy > (0 if self.boosting else 15)
        if self.boosting:
            self.energy = max(0.0, self.energy - 45 * dt / 1000)
            self.rs["boost_ms"] += dt
            self.quest_set("boost", self.rs["boost_ms"] // 1000)
            if random.random() < 0.8:
                tail = self.player.body[min(2, len(self.player.body) - 1)]
                self.burst(tail, self.player_skin()["a"], 1)
        else:
            self.energy = min(100.0, self.energy + 18 * dt / 1000)

        iv = self.player_interval()
        while self.state == "play" and self.acc >= iv:
            self.acc -= iv
            self.step_player()
        if self.state != "play":
            return

        if self.active("freeze"):
            self.racc = 0
        else:
            riv = self.rival_interval()
            while self.state == "play" and self.rival and self.racc >= riv:
                self.racc -= riv
                self.step_rival()
            if self.racc > 1000:
                self.racc = 0
        if self.state != "play":
            return

        self.update_mice(dt)
        self.update_spiders(dt)
        if self.state != "play":
            return
        self.update_bombs(dt)
        if self.state != "play":
            return
        self.update_chaos()
        self.update_quests()

        if self.mode == "Rival" and not self.rival and self.t >= self.rival_respawn:
            self.spawn_rival()
            self.rival_respawn = self.t + 1500

        for f in self.foods[:]:
            if f.life and self.t - f.born > f.life:
                self.foods.remove(f)

    def update_fx(self, dt):
        ts = 0.35 if self.state == "dying" else 1.0
        for p in self.particles[:]:
            p[0] += p[2] * ts
            p[1] += p[3] * ts
            p[3] += 0.12 * ts
            p[4] -= 1
            if p[4] <= 0:
                self.particles.remove(p)
        for f in self.floaters[:]:
            f[1] -= 0.8
            f[4] -= 1
            if f[4] <= 0:
                self.floaters.remove(f)
        for t in self.toasts[:]:
            t[2] -= 1
            if t[2] <= 0:
                self.toasts.remove(t)
        self.shake *= 0.9
        self.pop *= 0.86
        self.flash *= 0.92
        self.fade = max(0.0, self.fade - dt * 0.8)
        diff = self.score - self.disp_score
        self.disp_score = self.score if abs(diff) < 1 else self.disp_score + diff * 0.2
        if self.state == "dying":
            target = 1.0 + 0.06 * min(1.0, self.death_t / 600)
        else:
            target = 1.0 + 0.012 * self.pop
        self.zoom += (target - self.zoom) * 0.15

    # ------------------------------------------------------------------
    # drawing helpers
    # ------------------------------------------------------------------
    def cell_rect(self, c, pad=0):
        return pygame.Rect(c[0] * CELL + pad, c[1] * CELL + HUD + pad,
                           CELL - 2 * pad, CELL - 2 * pad)

    def cell_center(self, c):
        return c[0] * CELL + CELL // 2, c[1] * CELL + HUD + CELL // 2

    def glow(self, color):
        if color not in self.glow_cache:
            self.glow_cache[color] = make_glow(30, color)
        return self.glow_cache[color]

    def light(self, radius):
        radius = int(radius)
        if radius not in self.light_cache:
            self.light_cache[radius] = make_light(radius)
        return self.light_cache[radius]

    def make_vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(0, 40, 3):
            pygame.draw.rect(v, (0, 0, 0, int(95 * (1 - i / 40) ** 2)),
                             (i, i, W - 2 * i, H - 2 * i), 3)
        return v

    def make_background(self):
        """Pre-rendered ground texture for the current theme."""
        th = self.theme
        name = THEME_NAMES[self.theme_i]
        rng = random.Random(1234)
        surf = pygame.Surface((W, H))
        surf.fill((12, 14, 20))
        for x in range(COLS):
            for y in range(ROWS):
                col = th["bg1"] if (x + y) % 2 else th["bg2"]
                r = self.cell_rect((x, y))
                pygame.draw.rect(surf, col, r)
                if name == "Neon":
                    pygame.draw.rect(surf, lerp_col(col, th["accent"], 0.09), r, 1)
                elif name == "Forest":
                    for _ in range(6):
                        gx = r.x + rng.randint(1, CELL - 2)
                        gy = r.y + rng.randint(4, CELL - 1)
                        pygame.draw.line(surf, lerp_col(col, (120, 190, 80), rng.uniform(0.1, 0.28)),
                                         (gx, gy), (gx + rng.randint(-2, 2), gy - rng.randint(2, 5)))
                elif name == "Sunset":
                    for _ in range(2):
                        gx = r.x + rng.randint(2, CELL - 10)
                        gy = r.y + rng.randint(3, CELL - 3)
                        pygame.draw.line(surf, lerp_col(col, (255, 190, 140), 0.10),
                                         (gx, gy), (gx + rng.randint(5, 9), gy))
                else:
                    for _ in range(4):
                        pygame.draw.circle(surf, lerp_col(col, (255, 255, 255), rng.uniform(0.02, 0.09)),
                                           (r.x + rng.randint(1, CELL - 2), r.y + rng.randint(1, CELL - 2)), 1)
        return surf

    def make_ambient(self):
        wt = self.theme["weather"]
        out = []
        for _ in range(38):
            x, y = random.uniform(0, W), random.uniform(HUD, H)
            if wt == "sparks":
                vx, vy, size = random.uniform(-0.1, 0.1), random.uniform(-0.8, -0.25), random.choice((1, 1, 2))
            elif wt == "leaves":
                vx, vy, size = random.uniform(-0.3, 0.3), random.uniform(0.25, 0.7), random.choice((2, 3))
            elif wt == "embers":
                vx, vy, size = random.uniform(-0.2, 0.3), random.uniform(-0.7, -0.2), random.choice((1, 2))
            else:
                vx, vy, size = random.uniform(-0.15, 0.15), random.uniform(0.2, 0.7), random.choice((1, 2, 2))
            out.append([x, y, vx, vy, size, random.uniform(0, 6.28)])
        return out

    def move_alphas(self):
        """How far between the previous and current cell each snake is drawn (0..1)."""
        if self.state == "dying":
            return 1.0, 1.0
        return (min(1.0, self.acc / self.player_interval()),
                min(1.0, self.racc / self.rival_interval()))

    def draw_border(self, surf):
        th = self.theme
        if not self.wrap:
            pygame.draw.rect(surf, th["border"], (0, HUD, W, H - HUD), 3)
        else:
            for i in range(0, W, 16):
                pygame.draw.line(surf, th["border"], (i, HUD), (i + 6, HUD), 2)
                pygame.draw.line(surf, th["border"], (i, H - 2), (i + 6, H - 2), 2)
            for j in range(HUD, H, 16):
                pygame.draw.line(surf, th["border"], (0, j), (0, j + 6), 2)
                pygame.draw.line(surf, th["border"], (W - 2, j), (W - 2, j + 6), 2)

    # ------------------------------------------------------------------
    # weather / ambient
    # ------------------------------------------------------------------
    def draw_weather(self, surf):
        th = self.theme
        wt = th["weather"]
        for x, y, _, _, size, ph in self.ambient:
            tw = 0.5 + 0.5 * math.sin(ph * 3)
            if wt == "sparks":
                col = lerp_col(th["bg2"], th["accent"], 0.35 + 0.65 * tw)
                pygame.draw.circle(surf, col, (int(x), int(y)), size)
            elif wt == "leaves":
                col = lerp_col((70, 115, 40), (170, 130, 45), 0.5 + 0.5 * math.sin(ph))
                a = ph * 1.5
                pts = [(x + math.cos(a) * 4, y + math.sin(a) * 2),
                       (x + math.cos(a + 1.6) * 2, y + math.sin(a + 1.6) * 4),
                       (x - math.cos(a) * 4, y - math.sin(a) * 2),
                       (x + math.cos(a - 1.6) * 2, y + math.sin(a - 1.6) * 4)]
                pygame.draw.polygon(surf, col, pts)
            elif wt == "embers":
                col = lerp_col((255, 110, 40), (255, 225, 130), tw)
                pygame.draw.circle(surf, col, (int(x), int(y)), size)
            else:
                pygame.draw.circle(surf, (225, 230, 240), (int(x), int(y)), size)
        night = 1 - self.daylight()
        if night > 0.25 and self.state in ("play", "pause", "countdown", "dying", "dead"):
            for f in self.fireflies:
                pulse = 0.5 + 0.5 * math.sin(self.anim / 300 + f[2] * 3)
                col = lerp_col((70, 80, 20), (255, 255, 150), pulse)
                pygame.draw.circle(surf, col, (int(f[0]), int(f[1])), 2)

    def draw_lighting(self, surf):
        night = 1 - self.daylight()
        alpha = int(night * 175)
        if alpha < 6:
            return
        dark = self.dark_layer
        dark.fill((6, 8, 26, alpha))

        def lamp(px, py, radius):
            spr = self.light(radius)
            dark.blit(spr, (int(px) - radius, int(py) - HUD - radius),
                      special_flags=pygame.BLEND_RGBA_SUB)

        hx, hy = self.head_px
        lamp(hx, hy, 150 if self.boosting else 125)
        if self.rival and self.rival.body:
            lamp(*self.cell_center(self.rival.head), 70)
        for f in self.foods:
            if f.kind != "apple":
                lamp(*self.cell_center(f.pos), 46)
        for b in self.bombs:
            lamp(*self.cell_center(b.pos), 58)
        for p in self.portals:
            lamp(*self.cell_center(p), 64)
        for m in self.mice:
            lamp(*self.cell_center(m.pos), 30)
        for f in self.fireflies:
            lamp(f[0], f[1], 26)
        for p in self.particles[::3]:
            lamp(p[0], p[1], 20)
        surf.blit(dark, (0, HUD))

    # ------------------------------------------------------------------
    # snake rendering
    # ------------------------------------------------------------------
    def skin_at(self, skin, d, L):
        """Colour of the body at distance d (px) from the head.  Returns (base, mark, style)."""
        kind = skin["kind"]
        u = d / max(L, 1.0)
        base = lerp_col(skin["a"], skin["b"], min(1.0, u * 1.15))
        mark = style = None
        if kind == "diamond":
            per = CELL * 1.7
            if (d % per) / per < 0.5:
                mark, style = skin["mark"], "dot"
        elif kind == "bands":
            base = (skin["a"], skin["mark"], skin["b"], skin["mark"])[int(d / (CELL * 0.5)) % 4]
        elif kind == "cyber":
            if (d % (CELL * 1.2)) < 4:
                mark, style = skin["mark"], "ring"
        elif kind == "rainbow":
            base = hsv(d * 0.0035 - self.anim * 0.0002, 0.75, 0.95)
        return base, mark, style

    def body_radius(self, d, L, bulge_px, pop):
        R = CELL * 0.47
        r = R
        rem = L - d
        taper = CELL * 4.5
        if rem < taper:
            r *= 0.32 + 0.68 * (max(rem, 0) / taper) ** 0.8
        if d < CELL * 0.6:
            r *= 0.92
        for bd in bulge_px:
            r += 3.4 * math.exp(-((d - bd) / 9.0) ** 2)
        if pop > 0.02:
            r += 2.5 * pop * math.exp(-(d / 22.0) ** 2)
        return r

    def build_samples(self, snake, alpha):
        """Smooth, evenly spaced points along the snake's body (glides between cells)."""
        if not snake.body:
            return None
        prev = snake.prev
        pts = []
        for i, b in enumerate(snake.body):
            a = prev[min(i, len(prev) - 1)]
            if abs(a[0] - b[0]) > 1 or abs(a[1] - b[1]) > 1:      # wrapped / teleported
                a = b
            pts.append(((a[0] + (b[0] - a[0]) * alpha) * CELL + CELL / 2,
                        (a[1] + (b[1] - a[1]) * alpha) * CELL + HUD + CELL / 2))
        runs = [[pts[0]]]
        for i in range(1, len(pts)):
            if math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) > CELL * 1.6:
                runs.append([pts[i]])
            else:
                runs[-1].append(pts[i])
        step = 4.0
        samples = []
        dist = 0.0
        for run in runs:
            sm = chaikin(run) if len(run) > 2 else run
            rs = resample(sm, step) if len(sm) > 1 else [sm[0]]
            for k, (x, y) in enumerate(rs):
                samples.append((x, y, dist + k * step))
            dist += len(rs) * step
        return {"samples": samples, "L": max(1.0, samples[-1][2])}

    def paint_body(self, surf, samples, L, skin, bulge_px=(), pop=0.0, tint=None):
        """Draws the tube.  Three passes so patterns are not hidden by neighbouring circles."""
        info = []
        for x, y, d in samples:
            r = self.body_radius(d, L, bulge_px, pop)
            base, mark, style = self.skin_at(skin, d, L)
            if tint:
                base = lerp_col(base, tint[0], tint[1])
                if mark:
                    mark = lerp_col(mark, tint[0], tint[1])
            info.append((r, base, mark, style))
        n = len(samples)
        for k in range(n - 1, -1, -1):                             # outline
            x, y, _ = samples[k]
            r, base, _, _ = info[k]
            pygame.draw.circle(surf, lerp_col(base, (0, 0, 0), 0.55), (int(x), int(y)), int(r) + 2)
        for k in range(n - 1, -1, -1):                             # body + sheen
            x, y, _ = samples[k]
            r, base, _, _ = info[k]
            c = (int(x), int(y))
            pygame.draw.circle(surf, base, c, int(r))
            pygame.draw.circle(surf, lerp_col(base, (255, 255, 255), 0.2),
                               (c[0] - int(r * 0.22), c[1] - int(r * 0.3)), max(1, int(r * 0.42)))
        for k in range(n - 1, -1, -1):                             # pattern
            r, base, mark, style = info[k]
            if not mark:
                continue
            x, y, _ = samples[k]
            c = (int(x), int(y))
            if style == "dot":
                pygame.draw.circle(surf, mark, c, max(2, int(r * 0.52)))
            else:
                pygame.draw.circle(surf, mark, c, max(2, int(r * 0.85)), 2)
        return info[0][1] if info else skin["a"]

    def smooth_angle(self, snake):
        target = math.atan2(snake.dir[1], snake.dir[0])
        diff = (target - snake.angle + math.pi) % math.tau - math.pi
        snake.angle += diff * 0.3
        return snake.angle

    def paint_head(self, surf, x, y, ang, col, look=None, seed=0.0, pop=0.0, scale=1.0):
        ca, sa = math.cos(ang), math.sin(ang)
        s = CELL / 24 * 1.15 * (1 + 0.12 * pop) * scale

        def P(px, py):
            return (x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s)

        outline = lerp_col(col, (0, 0, 0), 0.55)
        shape = [(-6, -9), (2, -10), (9, -7.5), (14, -4), (16.5, 0), (14, 4), (9, 7.5), (2, 10), (-6, 9)]
        pygame.draw.polygon(surf, outline, [P(px * 1.13, py * 1.13) for px, py in shape])
        pygame.draw.polygon(surf, col, [P(px, py) for px, py in shape])
        pygame.draw.circle(surf, lerp_col(col, (255, 255, 255), 0.25), P(2, -3), max(2, int(4 * s)))
        for sy in (-2.2, 2.2):
            pygame.draw.circle(surf, outline, P(14, sy), max(1, int(1.3 * s)))
        # forked tongue flicking in and out
        f = max(0.0, math.sin(self.anim / 260 + seed * 1.7)) ** 6
        tl = 16 * f
        if tl > 3:
            tip = P(16.5 + tl, 0)
            pygame.draw.line(surf, (225, 45, 80), P(16, 0), tip, 2)
            for sy in (-1, 1):
                pygame.draw.line(surf, (225, 45, 80), tip, P(16.5 + tl + 4, sy * 3.2), 2)
        # eyes: blink now and then, pupils follow the food
        blink = (self.anim + seed * 777) % 4300 < 130
        er = max(2, int(4 * s))
        for sy in (-1, 1):
            ex, ey = P(6, sy * 6.5)
            if blink:
                pygame.draw.line(surf, outline, (ex - er, ey), (ex + er, ey), 2)
                continue
            pygame.draw.circle(surf, (250, 250, 240), (int(ex), int(ey)), er)
            if look:
                vx, vy = look[0] - x, look[1] - y
                n = math.hypot(vx, vy) or 1.0
                ox, oy = vx / n * 1.8 * s, vy / n * 1.8 * s
            else:
                ox, oy = ca * 1.4 * s, sa * 1.4 * s
            pygame.draw.circle(surf, (15, 15, 25), (int(ex + ox), int(ey + oy)), max(1, int(2 * s)))

    def nearest_target(self, px, py):
        best, bd = None, 1e9
        for f in self.foods:
            if f.kind in ("apple", "gold"):
                c = self.cell_center(f.pos)
                d = (c[0] - px) ** 2 + (c[1] - py) ** 2
                if d < bd:
                    best, bd = c, d
        for m in self.mice:
            c = self.cell_center(m.pos)
            d = (c[0] - px) ** 2 + (c[1] - py) ** 2
            if d < bd:
                best, bd = c, d
        return best

    def paint_snake(self, surf, snake, data, skin, alpha, pop=0.0, tint=None, head=True,
                    player=False):
        if not data:
            return
        samples, L = data["samples"], data["L"]
        bpx = [(b + alpha) * CELL for b in snake.bulges]
        head_col = self.paint_body(surf, samples, L, skin, bpx, pop if player else 0.0, tint)
        hx, hy = samples[0][0], samples[0][1]
        if player:
            self.head_px = (hx, hy)
        if head:
            ang = self.smooth_angle(snake)
            self.paint_head(surf, hx, hy, ang, head_col, self.nearest_target(hx, hy),
                            snake.tongue, pop if player else 0.0)

    # ------------------------------------------------------------------
    # world objects
    # ------------------------------------------------------------------
    def rock_surface(self, cell):
        s = self.rock_cache.get(cell)
        if s is not None:
            return s
        th = self.theme
        s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        if self.mode == "Maze":
            base = th["rock"]
            dark = lerp_col(base, (0, 0, 0), 0.45)
            pygame.draw.rect(s, dark, (0, 0, CELL, CELL))
            pygame.draw.rect(s, base, (1, 1, CELL - 2, CELL - 2), border_radius=3)
            pygame.draw.rect(s, lerp_col(base, th["rock2"], 0.6), (2, 2, CELL - 6, 3))
            pygame.draw.line(s, dark, (0, CELL // 2), (CELL, CELL // 2), 1)
            vx = CELL // 3 if cell[1] % 2 else 2 * CELL // 3
            pygame.draw.line(s, dark, (vx, 0), (vx, CELL // 2), 1)
            pygame.draw.line(s, dark, (CELL - vx, CELL // 2), (CELL - vx, CELL), 1)
        else:
            rng = random.Random(cell[0] * 131 + cell[1] * 7)
            n = 9
            cx = cy = CELL / 2
            pts = []
            for i in range(n):
                a = i * math.tau / n + rng.uniform(-0.15, 0.15)
                r = rng.uniform(9, 11.5)
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            pygame.draw.polygon(s, lerp_col(th["rock"], (0, 0, 0), 0.45), pts)
            inner = [(cx + (x - cx) * 0.86 - 0.8, cy + (y - cy) * 0.86 - 1) for x, y in pts]
            pygame.draw.polygon(s, th["rock"], inner)
            top = [(cx + (x - cx) * 0.55 - 1.8, cy + (y - cy) * 0.55 - 2.4) for x, y in pts]
            pygame.draw.polygon(s, th["rock2"], top)
            x0, y0 = rng.uniform(6, 10), rng.uniform(12, 18)
            pygame.draw.lines(s, lerp_col(th["rock"], (0, 0, 0), 0.5), False,
                              [(x0, y0), (x0 + 4, y0 + 2), (x0 + 6, y0 + 6)], 1)
        self.rock_cache[cell] = s
        return s

    def draw_shadows(self, psamp, rsamp):
        sl = self.shadow_layer
        sl.fill((0, 0, 0, 0))
        col = (0, 0, 0, 70)
        for data in (psamp, rsamp):
            if not data:
                continue
            L = data["L"]
            for k in range(0, len(data["samples"]), 2):
                x, y, d = data["samples"][k]
                pygame.draw.circle(sl, col, (int(x + 3), int(y + 5)),
                                   int(self.body_radius(d, L, (), 0) * 0.95))
        for o in self.obstacles:
            pygame.draw.rect(sl, col, (o[0] * CELL + 3, o[1] * CELL + HUD + 4, CELL - 2, CELL - 2),
                             border_radius=6)
        things = [f.pos for f in self.foods] + [m.pos for m in self.mice]
        things += [s.pos for s in self.spiders] + [b.pos for b in self.bombs]
        for c in things:
            cx, cy = self.cell_center(c)
            pygame.draw.ellipse(sl, col, (cx - 7, cy + 5, 15, 7))

    def draw_obstacles(self, surf):
        for o in self.obstacles:
            surf.blit(self.rock_surface(o), (o[0] * CELL, o[1] * CELL + HUD))

    def draw_portals(self, surf):
        cols = [(80, 170, 255), (255, 150, 60)]
        for i, p in enumerate(self.portals):
            cx, cy = self.cell_center(p)
            base = cols[i % 2]
            g = self.glow(base)
            surf.blit(g, g.get_rect(center=(cx, cy)))
            for k in range(4):
                rr = 11 - k * 2.5
                rect = pygame.Rect(0, 0, rr * 2, rr * 2)
                rect.center = (cx, cy)
                a0 = self.anim / (240 - 40 * k) * (1 if k % 2 else -1) + k
                pygame.draw.arc(surf, lerp_col(base, (255, 255, 255), k * 0.2), rect, a0, a0 + 4.2, 2)
            pygame.draw.circle(surf, (10, 10, 25), (cx, cy), 3)

    def draw_bombs(self, surf):
        for b in self.bombs:
            cx, cy = self.cell_center(b.pos)
            frac = b.fuse / b.max
            if frac < 0.3:
                pygame.draw.circle(surf, (210, 70, 50), (cx, cy), int(CELL * 2.5), 1)
            draw_bomb(surf, cx, cy - 1, self.anim, frac)

    def draw_food(self, surf):
        for f in self.foods:
            r = self.cell_rect(f.pos)
            cx, cy = r.center
            cy += int(1.5 * math.sin(self.anim / 300 + cx))
            if f.kind != "apple":
                g = self.glow(ITEM_COLORS[f.kind])
                surf.blit(g, g.get_rect(center=(cx, cy)))
            draw_item(surf, f.kind, cx, cy, self.anim, self.tiny)
            if f.life:
                left = 1 - (self.t - f.born) / f.life
                if left < 0.3 and int(self.anim / 120) % 2:
                    continue
                pygame.draw.arc(surf, (255, 255, 255), r.inflate(6, 6), math.pi / 2,
                                math.pi / 2 + math.tau * max(0.01, left), 2)

    def draw_mice(self, surf):
        iv = MOUSE_INTERVAL[self.diff]
        frozen = self.active("freeze")
        for m in self.mice:
            f = clamp(m.acc / iv, 0.0, 1.0)
            x = (m.prev[0] + (m.pos[0] - m.prev[0]) * f) * CELL + CELL / 2
            y = (m.prev[1] + (m.pos[1] - m.prev[1]) * f) * CELL + HUD + CELL / 2
            draw_mouse(surf, int(x), int(y), m.dir, self.anim, frozen)
            if self.t - m.born > MOUSE_LIFE_MS * 0.75 and int(self.anim / 150) % 2:
                pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 14, 1)

    def draw_spiders(self, surf):
        iv = SPIDER_INTERVAL[self.diff]
        frozen = self.active("freeze")
        for s in self.spiders:
            f = clamp(s.acc / iv, 0.0, 1.0)
            x = (s.prev[0] + (s.pos[0] - s.prev[0]) * f) * CELL + CELL / 2
            y = (s.prev[1] + (s.pos[1] - s.prev[1]) * f) * CELL + HUD + CELL / 2
            draw_spider(surf, int(x), int(y), s.phase, s.dir, frozen)
            if frozen:
                pygame.draw.circle(surf, (170, 235, 255), (int(x), int(y)), 14, 2)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def time_of_day(self):
        d = self.daylight()
        return "DAY" if d > 0.66 else "DUSK" if d > 0.33 else "NIGHT"

    def draw_hud(self, surf):
        th = self.theme
        pygame.draw.rect(surf, (10, 12, 18), (0, 0, W, HUD))
        pygame.draw.line(surf, th["border"], (0, HUD - 1), (W, HUD - 1), 1)
        draw_text(surf, self.font, f"SCORE {int(round(self.disp_score))}", th["text"], (12, 6))
        draw_text(surf, self.small, f"BEST {max(self.best(), self.score)}", th["dim"], (12, 33))
        draw_text(surf, self.small, f"LEVEL {self.level}", th["text"], (170, 10))
        draw_text(surf, self.small, f"LENGTH {len(self.player.body)}", th["dim"], (170, 33))
        if self.combo > 1:
            draw_text(surf, self.font, f"COMBO x{self.combo}", (255, 220, 100), (270, 6))
            frac = 1 - min(1, (self.t - self.last_eat) / COMBO_WINDOW_MS)
            pygame.draw.rect(surf, (255, 220, 100), (270, 34, int(110 * frac), 5), border_radius=2)

        # boost energy bar
        draw_text(surf, self.tiny, "BOOST", th["dim"], (400, 8), "topleft", False)
        pygame.draw.rect(surf, (40, 44, 60), (400, 22, 70, 8), border_radius=4)
        ec = (255, 150, 60) if self.boosting else th["accent"]
        pygame.draw.rect(surf, ec, (400, 22, int(70 * self.energy / 100), 8), border_radius=4)

        if self.mode == "Time Attack":
            secs = self.time_left / 1000
            col = (255, 90, 90) if secs < 10 else th["text"]
            draw_text(surf, self.medium, f"{secs:4.1f}", col, (W // 2 + 110, 8))

        chips = []
        if self.player.shield:
            chips.append((f"SHIELD x{self.player.shield}", (120, 220, 255)))
        for name, label, col in (("slow", "SLOW", (90, 170, 255)),
                                 ("ghost", "GHOST", (190, 150, 255)),
                                 ("double", "x2", (255, 220, 70)),
                                 ("magnet", "MAGNET", (240, 90, 90)),
                                 ("freeze", "FREEZE", (150, 225, 255)),
                                 ("dizzy", "DIZZY", (200, 110, 230))):
            if self.active(name):
                chips.append((f"{label} {(self.fx[name] - self.t) / 1000:.1f}s", col))
        if self.t < self.surge:
            chips.append((f"SURGE {(self.surge - self.t) / 1000:.1f}s", (255, 200, 90)))
        limit = 575 if self.mode == "Time Attack" else 485
        x, row = W - 10, 0
        for label, col in chips:
            img = self.tiny.render(label, True, (10, 10, 20))
            rect = pygame.Rect(0, 0, img.get_width() + 14, 18)
            if x - rect.width < limit and row == 0:
                x, row = W - 10, 1
            rect.topright = (x, 4 + row * 21)
            pygame.draw.rect(surf, col, rect, border_radius=9)
            surf.blit(img, img.get_rect(center=rect.center))
            x = rect.left - 6
        draw_text(surf, self.tiny, f"{self.mode} / {self.diff}  -  {self.time_of_day()}",
                  th["dim"], (W - 10, 44), "topright", False)

    def draw_toasts(self, surf):
        y = HUD + 10
        for text, col, life in self.toasts[-3:]:
            alpha = min(255, life * 4)
            img = self.small.render(text, True, col)
            bg = pygame.Surface((img.get_width() + 24, 28), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, min(170, alpha)), bg.get_rect(), border_radius=14)
            bg.blit(img, (12, 5))
            bg.set_alpha(alpha)
            surf.blit(bg, bg.get_rect(midtop=(W // 2, y)))
            y += 32

    def draw_quests(self, surf):
        if not self.show_quests:
            return
        th = self.theme
        w, row = 236, 26
        h = len(self.quests) * row + 8
        x0, y0 = 8, H - h - 8
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 125), panel.get_rect(), border_radius=8)
        surf.blit(panel, (x0, y0))
        for i, q in enumerate(self.quests):
            y = y0 + 5 + i * row
            done = q["done"]
            col = (140, 255, 160) if done else th["text"]
            draw_text(surf, self.tiny, q["text"], col, (x0 + 8, y), "topleft", False)
            cnt = "DONE" if done else f"{int(q['prog'])}/{q['goal']}"
            draw_text(surf, self.tiny, cnt, col, (x0 + w - 8, y), "topright", False)
            pygame.draw.rect(surf, (50, 55, 70), (x0 + 8, y + 15, w - 16, 4), border_radius=2)
            frac = 1.0 if done else q["prog"] / q["goal"]
            pygame.draw.rect(surf, col, (x0 + 8, y + 15, int((w - 16) * frac), 4), border_radius=2)

    def draw_overlay(self, surf, alpha=150):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        surf.blit(ov, (0, 0))

    def draw_countdown(self, surf):
        th = self.theme
        if self.state == "countdown":
            n = int(self.countdown // 800) + 1
            sub = (self.countdown % 800) / 800
            img = self.huge.render(str(n), True, th["accent"])
            img = pygame.transform.rotozoom(img, 0, 0.7 + 0.6 * sub)
            img.set_alpha(int(255 * (1 - 0.6 * (1 - sub))))
            surf.blit(img, img.get_rect(center=(W // 2, H // 2)))
            draw_text(surf, self.small, "Get ready!", th["text"], (W // 2, H // 2 + 80), "midtop")
        elif self.state == "play" and self.t < 700:
            img = self.big.render("GO!", True, (255, 240, 140))
            img = pygame.transform.rotozoom(img, 0, 1.0 + self.t / 700)
            img.set_alpha(int(255 * (1 - self.t / 700)))
            surf.blit(img, img.get_rect(center=(W // 2, H // 2)))

    # ------------------------------------------------------------------
    # play screen
    # ------------------------------------------------------------------
    def draw_play(self, surf):
        surf.blit(self.bg_surface, (0, 0))
        self.draw_border(surf)
        self.draw_portals(surf)
        pa, ra = self.move_alphas()
        psamp = self.build_samples(self.player, pa)
        rsamp = self.build_samples(self.rival, ra) if self.rival else None
        self.draw_shadows(psamp, rsamp)
        surf.blit(self.shadow_layer, (0, 0))
        self.draw_obstacles(surf)
        self.draw_bombs(surf)
        self.draw_food(surf)
        self.draw_mice(surf)
        self.draw_spiders(surf)

        frozen = self.active("freeze")
        if self.rival:
            self.paint_snake(surf, self.rival, rsamp, self.rival_skin(), ra,
                             tint=((190, 230, 255), 0.55) if frozen else None)
        tint = None
        if self.active("ghost"):
            tint = ((200, 160, 255), 0.55)
        elif self.active("slow"):
            tint = ((110, 180, 255), 0.4)
        elif frozen:
            tint = ((190, 230, 255), 0.4)
        if psamp:
            hp = (psamp["samples"][0][0], psamp["samples"][0][1])
            g = self.glow(self.player_skin()["a"])
            surf.blit(g, g.get_rect(center=(int(hp[0]), int(hp[1]))))
        self.paint_snake(surf, self.player, psamp, self.player_skin(), pa, self.pop, tint,
                         head=self.state != "dying", player=True)

        c = (int(self.head_px[0]), int(self.head_px[1]))
        if self.player.shield and self.player.body:
            pygame.draw.circle(surf, (140, 230, 255), c, 18 + int(2 * math.sin(self.anim / 100)), 2)
        if self.active("magnet") and self.player.body:
            ring = int(6 * CELL * (0.85 + 0.15 * math.sin(self.anim / 150)))
            pygame.draw.circle(surf, (240, 90, 90), c, ring, 1)
        for p in self.particles:
            pygame.draw.circle(surf, p[5], (int(p[0]), int(p[1])), max(1, p[4] // 12))
        self.draw_weather(surf)
        self.draw_lighting(surf)
        for f in self.floaters:
            draw_text(surf, self.small, f[2], f[3], (f[0], f[1]), "center")
        self.draw_hud(surf)
        self.draw_quests(surf)
        self.draw_toasts(surf)
        self.draw_countdown(surf)

    # ------------------------------------------------------------------
    # menu and other screens
    # ------------------------------------------------------------------
    def draw_backdrop(self, surf):
        surf.blit(self.bg_surface, (0, 0))
        self.draw_weather(surf)

    def draw_menu_snake(self, surf, y0=104):
        n = 72
        head_x = (self.anim * 0.14) % (W + 120) - 60
        samples = []
        for i in range(n):
            x = head_x - i * 5
            if x < -60:
                x += W + 120
            y = y0 + math.sin(x / 42 + self.anim / 450) * 20
            samples.append((x, y, i * 5.0))
        L = (n - 1) * 5.0
        skin = self.player_skin()
        col = self.paint_body(surf, samples, L, skin)
        x, y, _ = samples[0]
        slope = math.cos(x / 42 + self.anim / 450) * 20 / 42
        self.paint_head(surf, x, y, math.atan2(slope, 1.0), col, None, 1.0, 0.0, 1.05)

    def draw_menu(self, surf):
        th = self.theme
        self.draw_backdrop(surf)
        self.draw_menu_snake(surf)
        draw_text(surf, self.big, "DYNAMIC SNAKE", th["text"], (W // 2, 14), "midtop")

        items = [("Mode", MODES[self.mode_i]), ("Difficulty", DIFFS[self.diff_i]),
                 ("Theme", THEME_NAMES[self.theme_i]), ("Skin", SKIN_NAMES[self.skin_i]),
                 ("Audio", AUDIO_MODES[self.audio_i]),
                 ("START GAME", None), ("Achievements", None), ("Records & Stats", None),
                 ("How to Play", None), ("Quit", None)]
        y = 150
        for i, (label, value) in enumerate(items):
            sel = i == self.menu_sel
            col = th["accent"] if sel else th["text"]
            if sel:
                bar = pygame.Rect(0, 0, 420, 32)
                bar.center = (W // 2, y + 14)
                pygame.draw.rect(surf, lerp_col(th["bg1"], th["accent"], 0.25), bar, border_radius=12)
                pygame.draw.rect(surf, th["accent"], bar, 2, border_radius=12)
            if value is None:
                draw_text(surf, self.font, label, col, (W // 2, y), "midtop")
            else:
                draw_text(surf, self.font, label, col, (W // 2 - 190, y), "topleft")
                draw_text(surf, self.font, f"<  {value}  >" if sel else value, col,
                          (W // 2 + 190, y), "topright")
            y += 36

        d = self.store.data
        draw_text(surf, self.small, MODE_INFO[self.mode], th["text"], (W // 2, H - 76), "midtop")
        draw_text(surf, self.small, f"Best ({self.best_key}): {self.best()}     "
                  f"Games: {d['games']}     Trophies: {len(d['achievements'])}/{len(ACHIEVEMENTS)}",
                  th["dim"], (W // 2, H - 52), "midtop")
        draw_text(surf, self.tiny, "Arrows: steer   SPACE: boost   P: pause   Q: quests   "
                  "M: audio   F11: fullscreen", th["dim"], (W // 2, H - 26), "midtop", False)

    def draw_panel(self, surf, title):
        self.draw_backdrop(surf)
        self.draw_overlay(surf, 150)
        draw_text(surf, self.medium, title, self.theme["text"], (W // 2, 18), "midtop")

    def draw_achievements(self, surf):
        th = self.theme
        self.draw_panel(surf, "ACHIEVEMENTS")
        got = self.store.data["achievements"]
        items = list(ACHIEVEMENTS.items())
        for idx, (key, (title, desc)) in enumerate(items):
            colx = idx // 8
            row = idx % 8
            x = 24 + colx * (W // 2)
            y = 78 + row * 56
            have = key in got
            col = (255, 215, 80) if have else th["dim"]
            card = pygame.Rect(x, y, W // 2 - 40, 48)
            pygame.draw.rect(surf, (0, 0, 0), card.move(2, 2), border_radius=10)
            pygame.draw.rect(surf, lerp_col(th["bg1"], col, 0.18 if have else 0.04), card, border_radius=10)
            pygame.draw.rect(surf, col, card, 2 if have else 1, border_radius=10)
            pygame.draw.circle(surf, col, (card.x + 22, card.centery), 10, 0 if have else 2)
            draw_text(surf, self.small, title, col, (card.x + 44, card.y + 6), "topleft", False)
            draw_text(surf, self.tiny, desc, th["text"] if have else th["dim"],
                      (card.x + 44, card.y + 27), "topleft", False)
        draw_text(surf, self.small, f"{len(got)} / {len(ACHIEVEMENTS)} unlocked     ESC / ENTER: back",
                  th["dim"], (W // 2, H - 36), "midtop")

    def draw_records(self, surf):
        th = self.theme
        d = self.store.data
        st = d["stats"]
        self.draw_panel(surf, "RECORDS & STATS")
        draw_text(surf, self.font, f"Best scores  ({self.diff})", th["accent"], (40, 72))
        y = 108
        for m in MODES:
            draw_text(surf, self.small, m, th["text"], (40, y), "topleft", False)
            draw_text(surf, self.small, d["best"].get(f"{m}-{self.diff}", 0), (255, 225, 120),
                      (270, y), "topright", False)
            y += 26
        draw_text(surf, self.font, f"Top 5  ({self.best_key})", th["accent"], (40, y + 14))
        y += 50
        top = d["top"].get(self.best_key, [])
        for i in range(5):
            if i < len(top):
                draw_text(surf, self.small, f"{i + 1}.  {top[i][0]}", th["text"], (40, y), "topleft", False)
                draw_text(surf, self.tiny, top[i][1], th["dim"], (270, y + 3), "topright", False)
            else:
                draw_text(surf, self.small, f"{i + 1}.  ---", th["dim"], (40, y), "topleft", False)
            y += 26

        x0 = W // 2 + 30
        draw_text(surf, self.font, "Lifetime", th["accent"], (x0, 72))
        mins = st["play_ms"] // 60000
        rows = [("Games played", d["games"]), ("Apples eaten", d["total_apples"]),
                ("Mice caught", st["mice"]), ("Spiders squashed", st["spiders"]),
                ("Bombs that got spiders", st["bombs"]), ("Portals used", st["portals"]),
                ("Quests completed", st["quests"]), ("Longest snake", st["longest"]),
                ("Time played", f"{mins} min")]
        y = 108
        for label, val in rows:
            draw_text(surf, self.small, label, th["text"], (x0, y), "topleft", False)
            draw_text(surf, self.small, val, (255, 225, 120), (W - 40, y), "topright", False)
            y += 26
        draw_text(surf, self.small, "Left / Right: change mode      ESC / ENTER: back",
                  th["dim"], (W // 2, H - 36), "midtop")

    def draw_help(self, surf):
        th = self.theme
        self.draw_panel(surf, "HOW TO PLAY")
        lines = ["Arrows / WASD: steer        SPACE / SHIFT: hold to boost (uses energy)",
                 "P: pause     R: restart (while paused)     Q: show / hide quests",
                 "Eat apples to grow. Chain them for a combo (up to x5). Every 5 apples = new level.",
                 "Mice run away - catch them! Spiders bite - avoid them. Bombs tick, then blow up.",
                 "Night falls slowly: your snake carries a light. Complete quests for bonus points."]
        y = 66
        for ln in lines:
            draw_text(surf, self.tiny, ln, th["text"], (W // 2, y), "midtop", False)
            y += 20
        legend = [("apple", "Apple: points + grow"), ("gold", "Star: big bonus, fades fast"),
                  ("slow", "Potion: slows the game"), ("shield", "Shield: absorbs a hit"),
                  ("ghost", "Ghost: pass through things"), ("double", "x2: double points"),
                  ("shrink", "Scissors: cut 3 segments"), ("magnet", "Magnet: pulls in food"),
                  ("freeze", "Freeze: stops enemies, edible"), ("dizzy", "Mushroom: reversed controls!"),
                  ("mouse", "Mouse: +40, runs away"), ("spider", "Spider: deadly (freeze it!)"),
                  ("bomb", "Bomb: clears rocks, kills"), ("portal", "Portal: teleports you")]
        for i, (kind, text) in enumerate(legend):
            col_i, row_i = i // 7, i % 7
            cx = 44 + col_i * (W // 2)
            cy = 200 + row_i * 44
            if kind in ITEM_COLORS:
                g = self.glow(ITEM_COLORS[kind])
                surf.blit(g, g.get_rect(center=(cx, cy)))
                draw_item(surf, kind, cx, cy, self.anim, self.tiny)
            elif kind == "mouse":
                draw_mouse(surf, cx, cy, RIGHT, self.anim)
            elif kind == "spider":
                draw_spider(surf, cx, cy, self.anim / 60, RIGHT)
            elif kind == "bomb":
                draw_bomb(surf, cx, cy, self.anim, 1.0)
            else:
                base = (80, 170, 255)
                for j in range(4):
                    rr = 11 - j * 2.5
                    rect = pygame.Rect(0, 0, rr * 2, rr * 2)
                    rect.center = (cx, cy)
                    a0 = self.anim / (240 - 40 * j) * (1 if j % 2 else -1) + j
                    pygame.draw.arc(surf, lerp_col(base, (255, 255, 255), j * 0.2), rect, a0, a0 + 4.2, 2)
            draw_text(surf, self.small, text, th["text"], (cx + 30, cy - 9), "topleft", False)
        draw_text(surf, self.small, "ESC / ENTER: back", th["dim"], (W // 2, H - 36), "midtop")

    def draw_end(self, surf):
        th = self.theme
        self.draw_overlay(surf, 165)
        title = "TIME UP!" if self.mode == "Time Attack" and self.time_left <= 0 else "GAME OVER"
        draw_text(surf, self.big, title, th["text"], (W // 2, H // 2 - 170), "midtop")
        draw_text(surf, self.small, self.cause, th["dim"], (W // 2, H // 2 - 100), "midtop")
        draw_text(surf, self.medium, f"Score {self.score}", (255, 225, 120),
                  (W // 2, H // 2 - 70), "midtop")
        if self.new_best:
            draw_text(surf, self.font, "NEW BEST!", th["accent"], (W // 2, H // 2 - 22), "midtop")
        else:
            draw_text(surf, self.small, f"Best {self.best()}", th["dim"], (W // 2, H // 2 - 18), "midtop")
        r = self.rs
        stats = (f"Level {self.level}    Length {self.max_len}    Apples {self.eaten}    "
                 f"Mice {r['mice']}    Spiders {r['spiders']}    Quests {r['quests']}")
        draw_text(surf, self.small, stats, th["text"], (W // 2, H // 2 + 24), "midtop")
        draw_text(surf, self.small, f"Survived {int(self.t / 1000)} s", th["dim"],
                  (W // 2, H // 2 + 50), "midtop")
        draw_text(surf, self.font, "ENTER: play again     ESC: menu", th["text"],
                  (W // 2, H // 2 + 100), "midtop")

    # ------------------------------------------------------------------
    # frame composition
    # ------------------------------------------------------------------
    def draw(self):
        surf = self.canvas
        st = self.state
        if st == "menu":
            self.draw_menu(surf)
        elif st == "trophies":
            self.draw_achievements(surf)
        elif st == "records":
            self.draw_records(surf)
        elif st == "help":
            self.draw_help(surf)
        else:
            self.draw_play(surf)
            if st == "pause":
                self.draw_overlay(surf)
                draw_text(surf, self.big, "PAUSED", self.theme["text"], (W // 2, H // 2 - 70), "midtop")
                draw_text(surf, self.font, "P: resume     R: restart     ESC: menu",
                          self.theme["dim"], (W // 2, H // 2 + 10), "midtop")
            elif st == "dead":
                self.draw_end(surf)

        surf.blit(self.vignette, (0, 0))
        if self.flash > 0.03:                                   # screen flash on level-up / hits
            self.tint.fill(self.theme["accent"])
            self.tint.set_alpha(int(70 * self.flash))
            surf.blit(self.tint, (0, 0))
        if st in ("play", "pause", "dying"):
            if self.active("freeze"):
                self.tint.fill((150, 220, 255))
                self.tint.set_alpha(30)
                surf.blit(self.tint, (0, 0))
            if self.active("dizzy"):
                self.tint.fill((190, 80, 220))
                self.tint.set_alpha(int(28 + 14 * math.sin(self.anim / 120)))
                surf.blit(self.tint, (0, 0))
        if self.state != self.last_state:                       # fade between screens
            if self.state in ("menu", "trophies", "records", "help") or \
                    (self.state == "countdown" and self.last_state in ("menu", "dead")):
                self.fade = 220.0
            self.last_state = self.state
        if self.fade > 1:
            self.tint.fill((0, 0, 0))
            self.tint.set_alpha(int(self.fade))
            surf.blit(self.tint, (0, 0))

        ox = int(random.uniform(-1, 1) * self.shake)
        oy = int(random.uniform(-1, 1) * self.shake)
        if self.active("dizzy") and st == "play":
            oy += int(3 * math.sin(self.anim / 90))
            ox += int(3 * math.cos(self.anim / 110))
        self.screen.fill((0, 0, 0))
        if abs(self.zoom - 1.0) > 0.003:
            sw, sh = int(W * self.zoom), int(H * self.zoom)
            scaled = pygame.transform.scale(surf, (sw, sh))
            self.screen.blit(scaled, ((W - sw) // 2 + ox, (H - sh) // 2 + oy))
        else:
            self.screen.blit(surf, (ox, oy))
        pygame.display.flip()

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def start_game(self):
        self.reset()
        self.state = "countdown"
        self.sound.play("tick")

    def menu_change(self, delta):
        if self.menu_sel == 0:
            self.mode_i = (self.mode_i + delta) % len(MODES)
        elif self.menu_sel == 1:
            self.diff_i = (self.diff_i + delta) % len(DIFFS)
        elif self.menu_sel == 2:
            self.theme_i = (self.theme_i + delta) % len(THEME_NAMES)
            self.refresh_theme()
        elif self.menu_sel == 3:
            self.skin_i = (self.skin_i + delta) % len(SKIN_NAMES)
        elif self.menu_sel == 4:
            self.audio_i = (self.audio_i + delta) % len(AUDIO_MODES)
            self.apply_audio()
        else:
            return
        self.sound.play("menu")
        self.save_settings()

    def menu_activate(self):
        if self.menu_sel == 5:
            self.start_game()
        elif self.menu_sel == 6:
            self.state = "trophies"
        elif self.menu_sel == 7:
            self.state = "records"
        elif self.menu_sel == 8:
            self.state = "help"
        elif self.menu_sel == 9:
            self.quit()
        else:
            self.menu_change(1)

    def quit(self):
        self.store.save()
        pygame.quit()
        sys.exit()

    def back_to_menu(self):
        self.state = "menu"
        self.reset()

    def handle_key(self, key):
        steer = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
                 pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}
        enter = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)

        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        if key == pygame.K_m and self.state != "menu":
            self.audio_i = (self.audio_i + 1) % len(AUDIO_MODES)
            self.apply_audio()
            self.toast("Audio: " + AUDIO_MODES[self.audio_i])
            self.save_settings()
            return

        if self.state == "menu":
            n = 10
            if key == pygame.K_ESCAPE:
                self.quit()
            elif key in (pygame.K_UP, pygame.K_w):
                self.menu_sel = (self.menu_sel - 1) % n
                self.sound.play("menu")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_sel = (self.menu_sel + 1) % n
                self.sound.play("menu")
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.menu_change(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.menu_change(1)
            elif key in enter:
                self.menu_activate()
        elif self.state in ("trophies", "help"):
            if key in (pygame.K_ESCAPE,) + enter:
                self.state = "menu"
        elif self.state == "records":
            if key in (pygame.K_ESCAPE,) + enter:
                self.state = "menu"
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.mode_i = (self.mode_i - 1) % len(MODES)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.mode_i = (self.mode_i + 1) % len(MODES)
        elif self.state in ("play", "countdown"):
            if key in steer:
                self.turn(steer[key])
            elif key == pygame.K_p and self.state == "play":
                self.state = "pause"
            elif key == pygame.K_q:
                self.show_quests = not self.show_quests
            elif key == pygame.K_ESCAPE:
                self.back_to_menu()
        elif self.state == "pause":
            if key in (pygame.K_p,) + enter:
                self.state = "play"
            elif key == pygame.K_r:
                self.start_game()
            elif key == pygame.K_q:
                self.show_quests = not self.show_quests
            elif key == pygame.K_ESCAPE:
                self.back_to_menu()
        elif self.state == "dying":
            if key == pygame.K_ESCAPE:
                self.back_to_menu()
        elif self.state == "dead":
            if key in enter:
                self.start_game()
            elif key == pygame.K_ESCAPE:
                self.back_to_menu()

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = min(50, self.clock.tick(FPS))
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit()
                elif e.type == pygame.KEYDOWN:
                    self.handle_key(e.key)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()