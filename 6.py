"""
DYNAMIC SNAKE 2  -  Python + Pygame
====================================
Install:  pip install pygame
Run:      python dynamic_snake.py

MENU (Up/Down select, Left/Right change, Enter confirm)
    Mode ........ Classic | Wrap | Rival | Time Attack
    Difficulty .. Easy | Normal | Hard
    Theme ....... Neon | Forest | Sunset | Mono
    Sound ....... On | Off

IN GAME
    Arrow keys / WASD ... steer          P ..... pause
    SPACE / SHIFT ....... hold to BOOST (drains the energy bar, recharges)
    ESC ................. back to menu

WHAT'S NEW
    Smooth interpolated movement, tube-style snake, boost with energy bar,
    magnet power-up, animated board, vignette, screen flashes, fade transitions,
    score count-up, resizable window.

MODES
    Classic ..... walls are deadly
    Wrap ........ pass through the edges
    Rival ....... an AI snake competes with you for food. Hit its body and you
                  die. Win a head-on collision or trap it and it explodes into
                  apples (+100 points). It respawns after a few seconds.
    Time Attack . 90 seconds on the clock, every apple adds 1.5 seconds.

PICKUPS
    Red apple ... points + grow (chain them quickly for a combo, up to x5)
    Gold star ... big bonus, vanishes quickly
    Blue potion . slows the game for 5 seconds
    Shield ...... absorbs one deadly hit (max 2) and steers you away
    Ghost ....... pass through rocks, yourself and the rival for 6 seconds
    x2 .......... double points for 8 seconds
    Scissors .... cuts 3 segments off your tail
    Magnet ...... pulls nearby apples and stars toward you for 7 seconds

Best scores, settings and achievements are saved in snake_save.json.
"""
import json
import math
import os
import random
import sys
from array import array
from collections import deque

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

MODES = ["Classic", "Wrap", "Rival", "Time Attack"]
DIFFS = ["Easy", "Normal", "Hard"]
BASE_INTERVAL = {"Easy": 170, "Normal": 140, "Hard": 110}
MIN_INTERVAL = {"Easy": 70, "Normal": 55, "Hard": 42}

TIME_ATTACK_MS = 90_000
APPLE_BONUS_MS = 1_500
COMBO_WINDOW_MS = 3_000

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_save.json")

THEMES = {
    "Neon": dict(bg1=(24, 27, 40), bg2=(29, 33, 48), border=(0, 200, 255),
                 head=(90, 255, 170), tail=(20, 130, 130), rock=(110, 115, 140),
                 rock2=(160, 165, 190), accent=(0, 220, 255), text=(235, 240, 250),
                 dim=(140, 150, 175), rival=(255, 90, 140), rival_tail=(140, 30, 90)),
    "Forest": dict(bg1=(26, 44, 30), bg2=(31, 51, 35), border=(120, 200, 90),
                   head=(190, 240, 90), tail=(60, 130, 50), rock=(105, 95, 80),
                   rock2=(150, 140, 120), accent=(170, 230, 100), text=(235, 245, 225),
                   dim=(150, 175, 140), rival=(240, 150, 60), rival_tail=(140, 70, 20)),
    "Sunset": dict(bg1=(48, 28, 46), bg2=(56, 32, 52), border=(255, 140, 90),
                   head=(255, 210, 90), tail=(230, 80, 90), rock=(120, 90, 120),
                   rock2=(170, 140, 170), accent=(255, 160, 100), text=(255, 240, 235),
                   dim=(190, 150, 170), rival=(90, 200, 255), rival_tail=(40, 90, 160)),
    "Mono": dict(bg1=(30, 30, 30), bg2=(36, 36, 36), border=(220, 220, 220),
                 head=(255, 255, 255), tail=(110, 110, 110), rock=(90, 90, 90),
                 rock2=(150, 150, 150), accent=(255, 255, 255), text=(240, 240, 240),
                 dim=(140, 140, 140), rival=(200, 200, 200), rival_tail=(70, 70, 70)),
}
THEME_NAMES = list(THEMES)

# food kind -> lifetime in ms (None = stays until eaten)
FOOD_LIFE = {"apple": None, "gold": 6000, "slow": 8000, "shield": 9000,
             "ghost": 8000, "double": 8000, "shrink": 8000, "magnet": 8000}
SPECIAL_ROLLS = [("gold", 0.10), ("slow", 0.07), ("shield", 0.07),
                 ("ghost", 0.06), ("double", 0.06), ("shrink", 0.05), ("magnet", 0.06)]

ACHIEVEMENTS = {
    "first_bite": ("First Bite", "Eat your first apple"),
    "score_200": ("Snack Time", "Reach 200 points in one game"),
    "length_20": ("Long Boy", "Grow to a length of 20"),
    "level_5": ("Speed Demon", "Reach level 5"),
    "combo_5": ("Combo King", "Reach a x5 combo"),
    "shield_used": ("Bounce Back", "Survive a hit with a shield"),
    "ghost_run": ("Boo!", "Pick up a ghost power-up"),
    "rival_slayer": ("Rival Slayer", "Defeat the rival snake"),
    "survivor": ("Beat the Clock", "Finish a Time Attack round"),
    "collector": ("Apple Collector", "Eat 100 apples in total"),
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def lerp_col(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


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


# ----------------------------------------------------------------------------
# Sound (tiny synthesizer, no external files)
# ----------------------------------------------------------------------------
class Sound:
    def __init__(self):
        self.ok = False
        self.enabled = True
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except pygame.error:
            return
        self.ok = True
        self.sounds = {
            "eat": self.make([660, 990], 0.08),
            "gold": self.make([880, 1175, 1568], 0.18),
            "power": self.make([440, 660, 880], 0.16, wave="sine"),
            "level": self.make([523, 659, 784, 1047], 0.32),
            "hit": self.make([300, 200], 0.14, wave="square"),
            "die": self.make([320, 240, 160, 90], 0.45, wave="square"),
            "menu": self.make([520], 0.04, wave="sine", vol=0.2),
            "win": self.make([523, 659, 784, 1047, 1319], 0.5, wave="sine"),
        }

    @staticmethod
    def make(freqs, duration, vol=0.25, wave="square"):
        rate = 22050
        n = int(rate * duration)
        per = max(1, n // len(freqs))
        buf = array("h")
        for i in range(n):
            f = freqs[min(i // per, len(freqs) - 1)]
            s = math.sin(2 * math.pi * f * i / rate)
            v = (1.0 if s >= 0 else -1.0) if wave == "square" else s
            env = 1.0 - i / n
            buf.append(int(v * vol * env * 32767))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.ok and self.enabled and name in self.sounds:
            self.sounds[name].play()


# ----------------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------------
class Storage:
    def __init__(self):
        self.data = {"best": {}, "achievements": [], "total_apples": 0,
                     "games": 0, "settings": {"mode": 0, "diff": 1, "theme": 0, "sound": True}}
        self.load()

    def load(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            for k, v in loaded.items():
                if k in self.data:
                    self.data[k] = v
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except OSError:
            pass


# ----------------------------------------------------------------------------
# Game objects
# ----------------------------------------------------------------------------
class Snake:
    def __init__(self, x, y, direction, length=3):
        self.dir = direction
        self.body = [(x - direction[0] * i, y - direction[1] * i) for i in range(length)]
        self.prev = list(self.body)          # positions before the last step (for smooth motion)
        self.queue = deque()
        self.grow = 0
        self.shield = 0

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


# ----------------------------------------------------------------------------
# Main game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except (pygame.error, AttributeError):
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Dynamic Snake 2")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16, bold=True)
        self.tiny = pygame.font.SysFont("arial", 12, bold=True)
        self.big = pygame.font.SysFont("arial", 56, bold=True)
        self.medium = pygame.font.SysFont("arial", 32, bold=True)

        self.store = Storage()
        self.sound = Sound()
        s = self.store.data["settings"]
        self.mode_i = s.get("mode", 0) % len(MODES)
        self.diff_i = s.get("diff", 1) % len(DIFFS)
        self.theme_i = s.get("theme", 0) % len(THEME_NAMES)
        self.sound.enabled = bool(s.get("sound", True))

        self.state = "menu"
        self.last_state = "menu"
        self.fade = 255.0
        self.menu_sel = 4
        self.menu_t = 0.0
        self.dots = [[random.uniform(0, W), random.uniform(0, H), random.uniform(6, 22),
                      random.uniform(1, 3)] for _ in range(45)]
        self.toasts = []
        self.glow_cache = {}
        self.vignette = self.make_vignette()
        self.reset()

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
        self.particles = []
        self.floaters = []
        self.fx = {"slow": 0, "ghost": 0, "double": 0, "magnet": 0}
        self.energy = 100.0
        self.boosting = False
        self.pop = 0.0
        self.flash = 0.0
        self.head_px = (0, 0)
        self.shake = 0.0
        self.t = 0.0
        self.acc = 0.0
        self.racc = 0.0
        self.time_left = TIME_ATTACK_MS
        self.cause = ""
        self.new_best = False
        self.spawn_food("apple")
        if self.mode == "Rival":
            self.spawn_rival()

    def save_settings(self):
        st = self.store.data["settings"]
        st.update(mode=self.mode_i, diff=self.diff_i, theme=self.theme_i,
                  sound=self.sound.enabled)
        self.store.save()

    def interval(self):
        base = BASE_INTERVAL[self.diff] - (self.level - 1) * 8
        base = max(MIN_INTERVAL[self.diff], base)
        if self.active("slow"):
            base *= 1.7
        return base

    def player_interval(self):
        return self.interval() * (BOOST_FACTOR if self.boosting else 1.0)

    def active(self, name):
        return self.t < self.fx[name]

    # ------------------------------------------------------------------
    # spawning
    # ------------------------------------------------------------------
    def used_cells(self):
        used = set(self.player.body) | self.obstacles | {f.pos for f in self.foods}
        if self.rival:
            used |= set(self.rival.body)
        return used

    def free_cells(self):
        used = self.used_cells()
        return [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in used]

    def spawn_food(self, kind):
        cells = self.free_cells()
        if cells:
            self.foods.append(Food(random.choice(cells), kind, self.t))

    def has_food(self, kind):
        return any(f.kind == kind for f in self.foods)

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
                self.burst(c, self.theme["rock2"], 6)

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

    # ------------------------------------------------------------------
    # effects and feedback
    # ------------------------------------------------------------------
    def burst(self, cell, color, n=14):
        x = cell[0] * CELL + CELL / 2
        y = cell[1] * CELL + CELL / 2 + HUD
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, 5)
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp,
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
        if self.active("ghost"):
            return None
        body = p.body if p.grow > 0 else p.body[:-1]
        if cell in body:
            return "yourself"
        if cell in self.obstacles:
            return "a rock"
        if self.rival and cell in self.rival.body and cell != self.rival.head:
            return "the rival"
        return None

    def turn(self, d):
        p = self.player
        last = p.queue[-1] if p.queue else p.dir
        if d != last and (d[0] + last[0], d[1] + last[1]) != (0, 0) and len(p.queue) < 2:
            p.queue.append(d)

    # ------------------------------------------------------------------
    # player step
    # ------------------------------------------------------------------
    def step_player(self):
        p = self.player
        p.prev = list(p.body)
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
                return self.die(reason)

        p.body.insert(0, cell)
        if p.grow > 0:
            p.grow -= 1
        else:
            p.body.pop()

        if self.rival and cell == self.rival.head:
            self.kill_rival("head-on")

        for f in self.foods[:]:
            if f.pos == cell:
                self.foods.remove(f)
                self.eat(f)

        self.pull_magnet()
        if len(p.body) >= 20:
            self.unlock("length_20")

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

    def eat(self, f):
        p = self.player
        kind, pos = f.kind, f.pos
        if kind in ("apple", "gold"):
            self.pop = 1.0
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
            self.store.data["total_apples"] += 1
            self.unlock("first_bite")
            if self.store.data["total_apples"] >= 100:
                self.unlock("collector")
            self.burst(pos, (235, 80, 65))
            self.sound.play("eat")
            if self.mode == "Time Attack":
                self.time_left += APPLE_BONUS_MS
            if not self.has_food("apple"):
                self.spawn_food("apple")
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
        elif kind == "shrink":
            cut = max(0, min(3, len(p.body) - 3))
            for _ in range(cut):
                self.burst(p.body.pop(), (255, 150, 90), 4)
            p.prev = list(p.body)
            self.score += 5
            self.power_feedback(pos, (255, 150, 90), "SNIP!")

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
                if not self.has_food(kind):
                    self.spawn_food(kind)
                return

    def level_up(self):
        self.level += 1
        self.flash = 1.0
        self.add_obstacles(2 if self.level < 6 else 3)
        self.toast(f"LEVEL {self.level}", (255, 240, 120))
        self.sound.play("level")
        if self.level >= 5:
            self.unlock("level_5")

    # ------------------------------------------------------------------
    # rival AI
    # ------------------------------------------------------------------
    def ai_choose(self):
        r = self.rival
        own = r.body if r.grow > 0 else r.body[:-1]
        blocked = self.obstacles | set(self.player.body) | set(own)

        def neighbours(c):
            for d in DIRS:
                n = (c[0] + d[0], c[1] + d[1])
                if 0 <= n[0] < COLS and 0 <= n[1] < ROWS and n not in blocked:
                    yield n

        options = list(neighbours(r.head))
        if not options:
            return None
        if random.random() < 0.05:                      # occasional human-like wobble
            return random.choice(options)

        targets = {f.pos for f in self.foods if f.kind in ("apple", "gold")}
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
                    self.burst(move, self.theme["rival"], 10)
                    if not self.has_food("apple"):
                        self.spawn_food("apple")

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
    # end of round
    # ------------------------------------------------------------------
    def finish(self, cause, survived=False):
        self.state = "dead"
        self.cause = cause
        d = self.store.data
        d["games"] += 1
        if self.score > d["best"].get(self.best_key, 0):
            d["best"][self.best_key] = self.score
            self.new_best = self.score > 0
        if survived:
            self.unlock("survivor")
        self.store.save()

    def die(self, reason):
        self.shake = 14
        self.sound.play("die")
        for c in self.player.body:
            self.burst(c, self.theme["head"], 3)
        self.finish(f"You crashed into {reason}")

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def update(self, dt):
        self.menu_t += dt
        for d in self.dots:
            d[1] -= d[2] * dt / 1000
            if d[1] < -5:
                d[0], d[1] = random.uniform(0, W), H + 5

        if self.state == "play":
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

            # boost: hold SPACE / SHIFT, drains energy, recharges when released
            keys = pygame.key.get_pressed()
            want = keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            self.boosting = bool(want) and self.energy > (0 if self.boosting else 15)
            if self.boosting:
                self.energy = max(0.0, self.energy - 45 * dt / 1000)
                if random.random() < 0.8:
                    self.burst(self.player.body[min(2, len(self.player.body) - 1)],
                               self.theme["head"], 1)
            else:
                self.energy = min(100.0, self.energy + 18 * dt / 1000)

            iv = self.player_interval()
            while self.state == "play" and self.acc >= iv:
                self.acc -= iv
                self.step_player()
            riv = self.interval() * 1.12
            while self.state == "play" and self.rival and self.racc >= riv:
                self.racc -= riv
                self.step_rival()
            if self.racc > 1000:
                self.racc = 0

            if self.mode == "Rival" and not self.rival and self.t >= self.rival_respawn:
                self.spawn_rival()
                self.rival_respawn = self.t + 1500

            for f in self.foods[:]:
                if f.life and self.t - f.born > f.life:
                    self.foods.remove(f)

        for p in self.particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
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

    # ------------------------------------------------------------------
    # drawing helpers
    # ------------------------------------------------------------------
    def cell_rect(self, c, pad=0):
        return pygame.Rect(c[0] * CELL + pad, c[1] * CELL + HUD + pad,
                           CELL - 2 * pad, CELL - 2 * pad)

    def glow(self, color):
        if color not in self.glow_cache:
            self.glow_cache[color] = make_glow(34, color)
        return self.glow_cache[color]

    def make_vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(0, 40, 3):
            pygame.draw.rect(v, (0, 0, 0, int(95 * (1 - i / 40) ** 2)),
                             (i, i, W - 2 * i, H - 2 * i), 3)
        return v

    def move_alphas(self):
        """How far between the previous and current cell each snake is drawn (0..1)."""
        return (min(1.0, self.acc / self.player_interval()),
                min(1.0, self.racc / (self.interval() * 1.12)))

    def draw_background(self, surf):
        th = self.theme
        surf.fill((12, 14, 20))
        for x in range(COLS):
            for y in range(ROWS):
                col = th["bg1"] if (x + y) % 2 else th["bg2"]
                wave = 0.035 * (1 + math.sin(self.menu_t / 500 + (x + y) * 0.35))
                pygame.draw.rect(surf, lerp_col(col, th["accent"], wave), self.cell_rect((x, y)))
        for d in self.dots:
            pygame.draw.circle(surf, lerp_col(th["bg2"], th["dim"], 0.25),
                               (int(d[0]), int(d[1])), int(d[3]))
        if not self.wrap:
            pygame.draw.rect(surf, th["border"], (0, HUD, W, H - HUD), 3)
        else:
            for i in range(0, W, 16):
                pygame.draw.line(surf, th["border"], (i, HUD), (i + 6, HUD), 2)
                pygame.draw.line(surf, th["border"], (i, H - 2), (i + 6, H - 2), 2)

    def draw_snake(self, surf, snake, head_c, tail_c, ghost=False, slowed=False,
                   alpha=1.0, pop=0.0, player=False):
        n = len(snake.body)
        if slowed:
            head_c, tail_c = (120, 190, 255), (40, 90, 170)
        if ghost:
            head_c, tail_c = lerp_col(head_c, (210, 170, 255), 0.6), lerp_col(tail_c, (150, 110, 230), 0.6)

        # smooth pixel centres: glide from the previous cell to the current one
        prev = snake.prev
        pts = []
        for i, b in enumerate(snake.body):
            a = prev[min(i, len(prev) - 1)]
            if abs(a[0] - b[0]) > 1 or abs(a[1] - b[1]) > 1:      # wrapped around the edge
                a = b
            pts.append(((a[0] + (b[0] - a[0]) * alpha) * CELL + CELL / 2,
                        (a[1] + (b[1] - a[1]) * alpha) * CELL + HUD + CELL / 2))
        hx, hy = pts[0]
        if player:
            self.head_px = (hx, hy)
        g = self.glow(head_c)
        surf.blit(g, g.get_rect(center=(int(hx), int(hy))))

        for i in range(n - 1, -1, -1):
            t = i / max(1, n - 1)
            col = lerp_col(head_c, tail_c, t)
            rad = CELL * 0.5 - 1 - 4 * t + (3 * pop if i == 0 else 0)
            if i < n - 1:
                q = pts[i + 1]
                if abs(q[0] - pts[i][0]) < CELL * 1.5 and abs(q[1] - pts[i][1]) < CELL * 1.5:
                    pygame.draw.line(surf, col, pts[i], q, max(1, int(rad * 2)))
            c = (int(pts[i][0]), int(pts[i][1]))
            pygame.draw.circle(surf, col, c, int(rad))
            if i and i % 2 == 0:                                    # scale highlights
                pygame.draw.circle(surf, lerp_col(col, (255, 255, 255), 0.18), c,
                                   max(1, int(rad * 0.45)))

        dx, dy = snake.dir
        px, py = -dy, dx
        for side in (-1, 1):
            ex, ey = hx + dx * 5 + px * 5 * side, hy + dy * 5 + py * 5 * side
            pygame.draw.circle(surf, (250, 250, 250), (int(ex), int(ey)), 4)
            pygame.draw.circle(surf, (20, 20, 30), (int(ex + dx * 1.5), int(ey + dy * 1.5)), 2)

    def draw_food(self, surf):
        for f in self.foods:
            r = self.cell_rect(f.pos)
            cx, cy = r.center
            pulse = 1 + 0.12 * math.sin(self.t / 130 + cx)
            k = f.kind
            if k == "apple":
                pygame.draw.circle(surf, (235, 80, 65), (cx, cy), int(9 * pulse))
                pygame.draw.circle(surf, (255, 170, 160), (cx - 3, cy - 3), 3)
                pygame.draw.line(surf, (100, 70, 30), (cx, cy - 8), (cx + 2, cy - 12), 2)
                pygame.draw.ellipse(surf, (90, 200, 90), (cx + 1, cy - 12, 7, 4))
            elif k == "gold":
                pts = []
                for i in range(10):
                    ang = -math.pi / 2 + i * math.pi / 5 + self.t / 600
                    rad = (11 if i % 2 == 0 else 5) * pulse
                    pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
                pygame.draw.polygon(surf, (255, 210, 40), pts)
            elif k == "slow":
                pygame.draw.rect(surf, (90, 170, 255), (cx - 6, cy - 3, 12, 11), border_radius=4)
                pygame.draw.rect(surf, (210, 235, 255), (cx - 3, cy - 9, 6, 6))
            elif k == "shield":
                pygame.draw.polygon(surf, (120, 220, 255), [
                    (cx - 8, cy - 7), (cx + 8, cy - 7), (cx + 7, cy + 2), (cx, cy + 10), (cx - 7, cy + 2)])
                pygame.draw.polygon(surf, (220, 250, 255), [
                    (cx - 4, cy - 4), (cx + 4, cy - 4), (cx + 3, cy + 1), (cx, cy + 5), (cx - 3, cy + 1)])
            elif k == "ghost":
                col = (200, 160, 255)
                pygame.draw.circle(surf, col, (cx, cy - 2), 8)
                pygame.draw.rect(surf, col, (cx - 8, cy - 2, 16, 9))
                for i in range(3):
                    pygame.draw.circle(surf, col, (cx - 5 + i * 5, cy + 8), 3)
                pygame.draw.circle(surf, (30, 20, 50), (cx - 3, cy - 3), 2)
                pygame.draw.circle(surf, (30, 20, 50), (cx + 3, cy - 3), 2)
            elif k == "double":
                pygame.draw.circle(surf, (255, 215, 70), (cx, cy), int(10 * pulse))
                draw_text(surf, self.tiny, "x2", (90, 60, 0), (cx, cy), "center", False)
            elif k == "magnet":
                red = (235, 70, 70)
                pygame.draw.arc(surf, red, pygame.Rect(cx - 9, cy - 9, 18, 18), math.pi, math.tau, 5)
                for mx in (cx - 9, cx + 4):
                    pygame.draw.rect(surf, red, (mx, cy - 6, 5, 7))
                    pygame.draw.rect(surf, (230, 230, 240), (mx, cy - 10, 5, 4))
            elif k == "shrink":
                pygame.draw.circle(surf, (255, 150, 90), (cx, cy), 10)
                draw_text(surf, self.tiny, "-3", (80, 30, 0), (cx, cy), "center", False)
            if f.life:
                left = 1 - (self.t - f.born) / f.life
                pygame.draw.arc(surf, (255, 255, 255), r.inflate(6, 6), math.pi / 2,
                                math.pi / 2 + math.tau * max(0.01, left), 2)

    def draw_obstacles(self, surf):
        th = self.theme
        for o in self.obstacles:
            r = self.cell_rect(o, 1)
            pygame.draw.rect(surf, th["rock"], r, border_radius=4)
            pygame.draw.rect(surf, th["rock2"], r.inflate(-8, -8), border_radius=3)

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
                                 ("magnet", "MAGNET", (240, 90, 90))):
            if self.active(name):
                chips.append((f"{label} {(self.fx[name] - self.t) / 1000:.1f}s", col))
        x = W - 10
        for label, col in chips:
            img = self.tiny.render(label, True, (10, 10, 20))
            rect = pygame.Rect(0, 0, img.get_width() + 14, 20)
            rect.topright = (x, 8)
            pygame.draw.rect(surf, col, rect, border_radius=10)
            surf.blit(img, img.get_rect(center=rect.center))
            x = rect.left - 6
        draw_text(surf, self.tiny, f"{self.mode} / {self.diff}", th["dim"], (W - 10, 36), "topright", False)

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

    def draw_overlay(self, surf, alpha=150):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        surf.blit(ov, (0, 0))

    # ------------------------------------------------------------------
    # screens
    # ------------------------------------------------------------------
    def draw_play(self, surf):
        th = self.theme
        self.draw_background(surf)
        self.draw_obstacles(surf)
        self.draw_food(surf)
        pa, ra = self.move_alphas()
        if self.rival:
            self.draw_snake(surf, self.rival, th["rival"], th["rival_tail"], alpha=ra)
        self.draw_snake(surf, self.player, th["head"], th["tail"],
                        ghost=self.active("ghost"), slowed=self.active("slow"),
                        alpha=pa, pop=self.pop, player=True)
        if self.player.shield:
            c = (int(self.head_px[0]), int(self.head_px[1]))
            pygame.draw.circle(surf, (140, 230, 255), c, 17 + int(2 * math.sin(self.t / 100)), 2)
        if self.active("magnet"):
            c = (int(self.head_px[0]), int(self.head_px[1]))
            ring = int(6 * CELL * (0.85 + 0.15 * math.sin(self.t / 150)))
            pygame.draw.circle(surf, (240, 90, 90), c, ring, 1)
        for p in self.particles:
            pygame.draw.circle(surf, p[5], (int(p[0]), int(p[1])), max(1, p[4] // 12))
        for f in self.floaters:
            draw_text(surf, self.small, f[2], f[3], (f[0], f[1]), "center")
        self.draw_hud(surf)
        self.draw_toasts(surf)

    def draw_menu(self, surf):
        th = self.theme
        self.draw_background(surf)
        base = self.menu_t * 0.14
        for i in range(24):
            x = (base - i * 15) % (W + 60) - 30
            y = 108 + math.sin(x / 42 + self.menu_t / 450) * 20
            col = lerp_col(th["head"], th["tail"], i / 24)
            pygame.draw.circle(surf, col, (int(x), int(y)), 11 if i else 13)
            if i == 0:
                pygame.draw.circle(surf, (255, 255, 255), (int(x + 4), int(y - 4)), 3)
        draw_text(surf, self.big, "DYNAMIC SNAKE", th["text"], (W // 2, 40), "midtop")

        sound_txt = "On" if self.sound.enabled else "Off"
        items = [("Mode", MODES[self.mode_i]), ("Difficulty", DIFFS[self.diff_i]),
                 ("Theme", THEME_NAMES[self.theme_i]), ("Sound", sound_txt),
                 ("START GAME", None), ("Achievements", None), ("Quit", None)]
        y = 190
        for i, (label, value) in enumerate(items):
            sel = i == self.menu_sel
            col = th["accent"] if sel else th["text"]
            if sel:
                bar = pygame.Rect(0, 0, 400, 38)
                bar.center = (W // 2, y + 16)
                pygame.draw.rect(surf, lerp_col(th["bg1"], th["accent"], 0.25), bar, border_radius=12)
                pygame.draw.rect(surf, th["accent"], bar, 2, border_radius=12)
            if value is None:
                draw_text(surf, self.font, label, col, (W // 2, y), "midtop")
            else:
                draw_text(surf, self.font, label, col, (W // 2 - 180, y), "topleft")
                draw_text(surf, self.font, f"<  {value}  >" if sel else value, col,
                          (W // 2 + 180, y), "topright")
            y += 44

        n = len(self.store.data["achievements"])
        d = self.store.data
        draw_text(surf, self.small, f"Best ({self.best_key}): {self.best()}     "
                  f"Games: {d['games']}     Trophies: {n}/{len(ACHIEVEMENTS)}",
                  th["dim"], (W // 2, H - 60), "midtop")
        draw_text(surf, self.tiny, "Arrows: steer   SPACE: boost   P: pause   ESC: menu",
                  th["dim"], (W // 2, H - 34), "midtop", False)

    def draw_achievements(self, surf):
        th = self.theme
        self.draw_background(surf)
        self.draw_overlay(surf, 120)
        draw_text(surf, self.medium, "ACHIEVEMENTS", th["text"], (W // 2, 30), "midtop")
        got = self.store.data["achievements"]
        y = 95
        for key, (title, desc) in ACHIEVEMENTS.items():
            have = key in got
            col = (255, 215, 80) if have else th["dim"]
            mark = "[x]" if have else "[ ]"
            draw_text(surf, self.font, f"{mark} {title}", col, (W // 2 - 260, y))
            draw_text(surf, self.small, desc, col, (W // 2 + 20, y + 4))
            y += 42
        draw_text(surf, self.small, "Press ESC or ENTER to go back", th["dim"],
                  (W // 2, H - 40), "midtop")

    def draw_end(self, surf):
        th = self.theme
        self.draw_overlay(surf, 165)
        title = "TIME UP!" if self.mode == "Time Attack" and self.time_left <= 0 else "GAME OVER"
        draw_text(surf, self.big, title, th["text"], (W // 2, H // 2 - 130), "midtop")
        draw_text(surf, self.small, self.cause, th["dim"], (W // 2, H // 2 - 60), "midtop")
        draw_text(surf, self.medium, f"Score {self.score}", (255, 225, 120),
                  (W // 2, H // 2 - 30), "midtop")
        if self.new_best:
            draw_text(surf, self.font, "NEW BEST!", th["accent"], (W // 2, H // 2 + 18), "midtop")
        else:
            draw_text(surf, self.small, f"Best {self.best()}", th["dim"], (W // 2, H // 2 + 22), "midtop")
        draw_text(surf, self.font, "ENTER: play again     ESC: menu", th["text"],
                  (W // 2, H // 2 + 75), "midtop")

    def draw(self):
        surf = pygame.Surface((W, H))
        if self.state == "menu":
            self.draw_menu(surf)
        elif self.state == "trophies":
            self.draw_achievements(surf)
        else:
            self.draw_play(surf)
            if self.state == "pause":
                self.draw_overlay(surf)
                draw_text(surf, self.big, "PAUSED", self.theme["text"], (W // 2, H // 2 - 50), "midtop")
                draw_text(surf, self.font, "P: resume     ESC: menu", self.theme["dim"],
                          (W // 2, H // 2 + 20), "midtop")
            elif self.state == "dead":
                self.draw_end(surf)

        surf.blit(self.vignette, (0, 0))
        if self.flash > 0.03:                                   # screen flash on level-up / hits
            fl = pygame.Surface((W, H))
            fl.fill(self.theme["accent"])
            fl.set_alpha(int(70 * self.flash))
            surf.blit(fl, (0, 0))
        if self.state != self.last_state:                       # fade between screens
            if self.state in ("menu", "trophies") or \
                    (self.state == "play" and self.last_state in ("menu", "dead")):
                self.fade = 220.0
            self.last_state = self.state
        if self.fade > 1:
            fd = pygame.Surface((W, H))
            fd.set_alpha(int(self.fade))
            surf.blit(fd, (0, 0))

        ox = int(random.uniform(-1, 1) * self.shake)
        oy = int(random.uniform(-1, 1) * self.shake)
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, (ox, oy))
        pygame.display.flip()

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def start_game(self):
        self.reset()
        self.state = "play"

    def menu_change(self, delta):
        if self.menu_sel == 0:
            self.mode_i = (self.mode_i + delta) % len(MODES)
        elif self.menu_sel == 1:
            self.diff_i = (self.diff_i + delta) % len(DIFFS)
        elif self.menu_sel == 2:
            self.theme_i = (self.theme_i + delta) % len(THEME_NAMES)
            self.glow_cache.clear()
        elif self.menu_sel == 3:
            self.sound.enabled = not self.sound.enabled
        else:
            return
        self.sound.play("menu")
        self.save_settings()

    def menu_activate(self):
        if self.menu_sel == 4:
            self.start_game()
        elif self.menu_sel == 5:
            self.state = "trophies"
        elif self.menu_sel == 6:
            self.quit()
        else:
            self.menu_change(1)

    def quit(self):
        self.store.save()
        pygame.quit()
        sys.exit()

    def handle_key(self, key):
        steer = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
                 pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}
        enter = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)

        if self.state == "menu":
            if key == pygame.K_ESCAPE:
                self.quit()
            elif key in (pygame.K_UP, pygame.K_w):
                self.menu_sel = (self.menu_sel - 1) % 7
                self.sound.play("menu")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_sel = (self.menu_sel + 1) % 7
                self.sound.play("menu")
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.menu_change(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.menu_change(1)
            elif key in enter:
                self.menu_activate()
        elif self.state == "trophies":
            if key in (pygame.K_ESCAPE,) + enter:
                self.state = "menu"
        elif self.state == "play":
            if key in steer:
                self.turn(steer[key])
            elif key == pygame.K_p:
                self.state = "pause"
            elif key == pygame.K_ESCAPE:
                self.state = "menu"
        elif self.state == "pause":
            if key in (pygame.K_p,) + enter:
                self.state = "play"
            elif key == pygame.K_ESCAPE:
                self.state = "menu"
        elif self.state == "dead":
            if key in enter:
                self.start_game()
            elif key == pygame.K_ESCAPE:
                self.state = "menu"

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