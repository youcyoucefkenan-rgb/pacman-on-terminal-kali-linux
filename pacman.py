#!/usr/bin/env python3
"""
PAC-MAN for the terminal  (pure Python 3, no extra packages needed)

Run:      python3 pacman.py
ASCII:    python3 pacman.py --ascii      (if the walls look broken)

Controls: Arrow keys or WASD = move | P = pause | Q = quit
Terminal: at least 40 columns x 24 rows
"""

import argparse
import curses
import locale
import os
import random
import time
from collections import deque

# ----------------------------------------------------------------------------
# Maze:  # wall   . dot   o power pellet   - ghost door   (space) empty/tunnel
# ----------------------------------------------------------------------------
MAZE = [
    "###################",
    "#........#........#",
    "#o##.###.#.###.##o#",
    "#.................#",
    "#.##.#.#####.#.##.#",
    "#....#...#...#....#",
    "####.###.#.###.####",
    "####.#.......#.####",
    "####.#.##-##.#.####",
    "    .  #   #  .    ",
    "####.#.#####.#.####",
    "####.#.......#.####",
    "#........#........#",
    "#.##.###.#.###.##.#",
    "#o.#...........#.o#",
    "##.#.#.#####.#.#.##",
    "#....#...#...#....#",
    "#.######.#.######.#",
    "#.................#",
    "###################",
]
H, W = len(MAZE), len(MAZE[0])

DIRS = {"U": (-1, 0), "L": (0, -1), "D": (1, 0), "R": (0, 1)}
OPP = {"U": "D", "D": "U", "L": "R", "R": "L"}

KEYMAP = {
    curses.KEY_UP: "U", ord("w"): "U", ord("W"): "U",
    curses.KEY_DOWN: "D", ord("s"): "D", ord("S"): "D",
    curses.KEY_LEFT: "L", ord("a"): "L", ord("A"): "L",
    curses.KEY_RIGHT: "R", ord("d"): "R", ord("D"): "R",
}

TICK = 0.11
PAC_START = (14, 9)
HOUSE_CENTER = (9, 9)
HOUSE_EXIT = (7, 9)
SKIP = [5, 7, 10, 0]            # ghosts skip every Nth tick (0 = never) per level
HI_FILE = os.path.expanduser("~/.pacman_highscore")

# name, colour pair, start (r, c), start state, release tick, scatter corner
GHOST_DEFS = [
    ("Blinky", 4, (7, 9), "normal", 0, (0, 17)),
    ("Pinky", 5, (9, 9), "house", 20, (0, 1)),
    ("Inky", 6, (9, 8), "house", 50, (19, 17)),
    ("Clyde", 7, (9, 10), "house", 80, (19, 1)),
]


# ----------------------------------------------------------------------------
# Game logic (no curses in here)
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, hi=0):
        self.hi = hi
        self.score = 0
        self.lives = 3
        self.level = 1
        self.load_level()

    def load_level(self):
        self.grid = [list(row) for row in MAZE]
        self.grid[PAC_START[0]][PAC_START[1]] = " "
        self.dots = sum(row.count(".") + row.count("o") for row in self.grid)
        self.reset_positions()

    def reset_positions(self):
        self.pr, self.pc = PAC_START
        self.ppr, self.ppc = PAC_START
        self.dir = None
        self.want = None
        self.face = "L"
        self.tick = 0
        self.fright = 0
        self.combo = 0
        scale = max(0.3, 1 - 0.15 * (self.level - 1))
        self.ghosts = []
        for name, color, (r, c), state, rel, corner in GHOST_DEFS:
            self.ghosts.append(dict(
                name=name, color=color, r=r, c=c, pr=r, pc=c, dir="L",
                state=state, release=int(rel * scale), corner=corner,
                fright=False,
            ))

    # -- helpers -------------------------------------------------------------
    def walk(self, r, c):
        return 0 <= r < H and self.grid[r][c] not in "#-"

    def add_score(self, n):
        self.score += n
        self.hi = max(self.hi, self.score)

    # -- one game tick -------------------------------------------------------
    def step(self):
        """Advance one tick. Returns None, 'dead' or 'win'."""
        self.tick += 1
        self.ppr, self.ppc = self.pr, self.pc
        for g in self.ghosts:
            g["pr"], g["pc"] = g["r"], g["c"]
            if g["state"] == "house" and self.tick >= g["release"]:
                g["state"] = "exit"

        self.move_pac()
        if self.dots == 0:
            return "win"
        if self.collide():
            return "dead"

        if self.fright > 0:
            self.fright -= 1
            if self.fright == 0:
                for g in self.ghosts:
                    g["fright"] = False

        for g in self.ghosts:
            if self.ghost_moves(g):
                self.move_ghost(g)
        if self.collide():
            return "dead"
        return None

    # -- pac-man -------------------------------------------------------------
    def move_pac(self):
        if self.want:
            dr, dc = DIRS[self.want]
            if self.walk(self.pr + dr, (self.pc + dc) % W):
                self.dir = self.want
        if not self.dir:
            return
        dr, dc = DIRS[self.dir]
        nr, nc = self.pr + dr, (self.pc + dc) % W
        if not self.walk(nr, nc):
            return
        self.face = self.dir
        self.pr, self.pc = nr, nc
        cell = self.grid[nr][nc]
        if cell == ".":
            self.add_score(10)
            self.dots -= 1
        elif cell == "o":
            self.add_score(50)
            self.dots -= 1
            self.fright = max(25, 70 - 8 * (self.level - 1))
            self.combo = 0
            for g in self.ghosts:
                if g["state"] == "normal":
                    g["fright"] = True
                    g["dir"] = OPP[g["dir"]]
        self.grid[nr][nc] = " "

    # -- ghosts --------------------------------------------------------------
    def ghost_moves(self, g):
        if g["state"] == "eaten":
            return True
        if g["state"] == "house":
            return False
        if g["fright"]:
            return self.tick % 2 == 0
        skip = SKIP[min(self.level - 1, len(SKIP) - 1)]
        return not (skip and self.tick % skip == 0)

    def options(self, g):
        opts = []
        for d, (dr, dc) in DIRS.items():
            nr, nc = g["r"] + dr, (g["c"] + dc) % W
            if not (0 <= nr < H):
                continue
            ch = self.grid[nr][nc]
            if ch == "#":
                continue
            if ch == "-" and g["state"] not in ("exit", "eaten"):
                continue
            opts.append((d, nr, nc))
        return opts

    def bfs_dir(self, start, goal):
        if start == goal:
            return None
        q = deque([start])
        prev = {start: None}
        while q:
            cur = q.popleft()
            if cur == goal:
                break
            for d, (dr, dc) in DIRS.items():
                nxt = (cur[0] + dr, (cur[1] + dc) % W)
                if 0 <= nxt[0] < H and self.grid[nxt[0]][nxt[1]] != "#" and nxt not in prev:
                    prev[nxt] = (cur, d)
                    q.append(nxt)
        if goal not in prev:
            return None
        cur = goal
        while prev[cur][0] != start:
            cur = prev[cur][0]
        return prev[cur][1]

    def target(self, g):
        if (self.tick % 160) < 40:          # scatter phase
            return g["corner"]
        pr, pc = self.pr, self.pc
        dr, dc = DIRS[self.dir or self.face]
        n = g["name"]
        if n == "Blinky":
            return (pr, pc)
        if n == "Pinky":
            return (pr + 4 * dr, pc + 4 * dc)
        if n == "Inky":
            b = self.ghosts[0]
            ar, ac = pr + 2 * dr, pc + 2 * dc
            return (2 * ar - b["r"], 2 * ac - b["c"])
        if (g["r"] - pr) ** 2 + (g["c"] - pc) ** 2 > 64:   # Clyde
            return (pr, pc)
        return g["corner"]

    def move_ghost(self, g):
        if g["state"] == "eaten":
            d = self.bfs_dir((g["r"], g["c"]), HOUSE_CENTER)
            if d is None:                   # back home -> revive
                g["state"] = "exit"
                g["fright"] = False
                g["dir"] = "U"
                return
            dr, dc = DIRS[d]
            g["r"], g["c"], g["dir"] = g["r"] + dr, (g["c"] + dc) % W, d
            return

        opts = self.options(g)
        if not opts:
            return
        rev = OPP[g["dir"]]
        fwd = [o for o in opts if o[0] != rev] or opts

        if g["state"] == "exit":
            tgt = HOUSE_EXIT
        elif g["fright"]:
            tgt = None
        else:
            tgt = self.target(g)

        if tgt is None:
            d, nr, nc = random.choice(fwd)
        else:
            d, nr, nc = min(fwd, key=lambda o: (o[1] - tgt[0]) ** 2 + (o[2] - tgt[1]) ** 2)
        g["r"], g["c"], g["dir"] = nr, nc, d
        if g["state"] == "exit" and g["r"] <= HOUSE_EXIT[0]:
            g["state"] = "normal"

    def collide(self):
        """Handle ghost/pac contact. True if pac-man died."""
        for g in self.ghosts:
            if g["state"] in ("house", "eaten"):
                continue
            same = (g["r"], g["c"]) == (self.pr, self.pc)
            swap = ((g["pr"], g["pc"]) == (self.pr, self.pc)
                    and (g["r"], g["c"]) == (self.ppr, self.ppc))
            if same or swap:
                if g["fright"] and g["state"] == "normal":
                    g["state"] = "eaten"
                    g["fright"] = False
                    self.add_score(200 * (2 ** self.combo))
                    self.combo = min(self.combo + 1, 3)
                else:
                    return True
        return False


# ----------------------------------------------------------------------------
# High score
# ----------------------------------------------------------------------------
def load_hi():
    try:
        with open(HI_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_hi(v):
    try:
        with open(HI_FILE, "w") as f:
            f.write(str(int(v)))
    except OSError:
        pass


# ----------------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------------
def put(scr, y, x, s, attr=0):
    try:
        scr.addstr(y, x, s, attr)
    except curses.error:
        pass


def too_small(scr):
    h, w = scr.getmaxyx()
    return h < H + 4 or w < W * 2 + 2


def draw(scr, game, ascii_mode, banner=None):
    scr.erase()
    cp = curses.color_pair
    wall = "##" if ascii_mode else "\u2588\u2588"
    dot = " ." if ascii_mode else " \u00b7"
    pellet = " O" if ascii_mode else " \u25cf"
    heart = "@ " if ascii_mode else "\u2665 "

    hud = f" SCORE {game.score:<6} HI {game.hi:<6} LVL {game.level}"
    put(scr, 0, 0, hud, cp(2) | curses.A_BOLD)
    put(scr, 1, 0, " LIVES ", cp(2))
    put(scr, 1, 7, heart * max(game.lives - 0, 0), cp(4) | curses.A_BOLD)

    top = 2
    for r in range(H):
        for c in range(W):
            ch = game.grid[r][c]
            x, y = c * 2, top + r
            if ch == "#":
                put(scr, y, x, wall, cp(1) | curses.A_BOLD)
            elif ch == ".":
                put(scr, y, x, dot, cp(2))
            elif ch == "o":
                put(scr, y, x, pellet, cp(2) | curses.A_BOLD)
            elif ch == "-":
                put(scr, y, x, "--" if ascii_mode else "\u2500\u2500", cp(5))

    # ghosts
    for g in game.ghosts:
        if g["state"] == "eaten":
            glyph, attr = "''", cp(2)
        elif g["fright"]:
            flash = game.fright <= 15 and game.fright % 2 == 0
            glyph = "mm"
            attr = (cp(9) if flash else cp(8)) | curses.A_BOLD
        else:
            glyph, attr = "MM", cp(g["color"]) | curses.A_BOLD
        put(scr, top + g["r"], g["c"] * 2, glyph, attr)

    # pac-man
    open_mouth = (game.tick // 2) % 2 == 0
    mouth = {"L": ">", "R": "<", "U": "v", "D": "^"}[game.face]
    glyph = (mouth if open_mouth else "O") + " "
    put(scr, top + game.pr, game.pc * 2, glyph, cp(3) | curses.A_BOLD)

    put(scr, top + H + 1, 0, " Arrows/WASD move  P pause  Q quit", cp(2))

    if banner:
        y = top + H // 2
        text = f" {banner} "
        x = max(0, (W * 2 - len(text)) // 2)
        put(scr, y, x, text, curses.A_REVERSE | curses.A_BOLD)
    scr.refresh()


def show_message(scr, lines):
    scr.erase()
    for i, ln in enumerate(lines):
        put(scr, 1 + i, 1, ln)
    scr.refresh()


# ----------------------------------------------------------------------------
# Screens
# ----------------------------------------------------------------------------
def title_screen(scr, hi):
    art = [
        r" ___   _   ___   __  __   _   _  _ ",
        r"| _ \ /_\ / __| |  \/  | /_\ | \| |",
        r"|  _// _ \ (__  | |\/| |/ _ \| .` |",
        r"|_| /_/ \_\___| |_|  |_/_/ \_\_|\_|",
    ]
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        y = max(0, h // 2 - 7)
        for i, ln in enumerate(art):
            put(scr, y + i, max(0, (w - len(ln)) // 2), ln, curses.color_pair(3) | curses.A_BOLD)
        info = [
            "",
            f"HIGH SCORE: {hi}",
            "",
            "Arrow keys / WASD  - move",
            "P - pause    Q - quit",
            "",
            "Eat all dots. Power pellets (O) let you eat ghosts.",
            "",
            "Press ENTER or SPACE to start",
        ]
        for i, ln in enumerate(info):
            put(scr, y + 5 + i, max(0, (w - len(ln)) // 2), ln, curses.color_pair(2))
        scr.refresh()
        scr.timeout(200)
        k = scr.getch()
        if k in (10, 13, 32, curses.KEY_ENTER):
            return True
        if k in (ord("q"), ord("Q")):
            return False


def game_over_screen(scr, game, ascii_mode):
    while True:
        draw(scr, game, ascii_mode, banner="GAME OVER  -  R: retry  Q: quit")
        scr.timeout(200)
        k = scr.getch()
        if k in (ord("r"), ord("R")):
            return True
        if k in (ord("q"), ord("Q")):
            return False


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------
def game_loop(scr, game, ascii_mode):
    """Play until death / level clear / quit. Returns 'dead', 'win' or 'quit'."""
    draw(scr, game, ascii_mode, banner="READY!")
    curses.napms(900)
    scr.nodelay(True)
    while scr.getch() != -1:        # flush buffered keys
        pass

    while True:
        if too_small(scr):
            show_message(scr, ["Terminal too small!", f"Need {W * 2 + 2}x{H + 4}.", "Resize or press Q."])
            scr.timeout(200)
            if scr.getch() in (ord("q"), ord("Q")):
                return "quit"
            continue

        res = game.step()
        draw(scr, game, ascii_mode)
        if res:
            return res

        deadline = time.time() + TICK
        while True:
            rem = deadline - time.time()
            if rem <= 0:
                break
            scr.timeout(max(1, int(rem * 1000)))
            k = scr.getch()
            if k == -1:
                continue
            if k in KEYMAP:
                game.want = KEYMAP[k]
            elif k in (ord("q"), ord("Q")):
                return "quit"
            elif k in (ord("p"), ord("P")):
                draw(scr, game, ascii_mode, banner="PAUSED - press P")
                scr.timeout(-1)
                while True:
                    k2 = scr.getch()
                    if k2 in (ord("p"), ord("P")):
                        break
                    if k2 in (ord("q"), ord("Q")):
                        return "quit"
                deadline = time.time() + TICK


def run(scr, ascii_mode):
    curses.curs_set(0)
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    colors = {1: curses.COLOR_BLUE, 2: curses.COLOR_WHITE, 3: curses.COLOR_YELLOW,
              4: curses.COLOR_RED, 5: curses.COLOR_MAGENTA, 6: curses.COLOR_CYAN,
              7: curses.COLOR_GREEN, 8: curses.COLOR_BLUE, 9: curses.COLOR_WHITE}
    for i, col in colors.items():
        curses.init_pair(i, col, bg)

    hi = load_hi()
    if too_small(scr):
        pass  # handled inside the loops
    if not title_screen(scr, hi):
        return

    game = Game(hi)
    try:
        while True:
            status = game_loop(scr, game, ascii_mode)
            if status == "quit":
                break
            if status == "win":
                game.level += 1
                game.load_level()
                draw(scr, game, ascii_mode, banner=f"LEVEL {game.level}!")
                curses.napms(1200)
                continue
            # died
            game.lives -= 1
            draw(scr, game, ascii_mode, banner="OUCH!")
            curses.napms(1200)
            if game.lives <= 0:
                save_hi(game.hi)
                if not game_over_screen(scr, game, ascii_mode):
                    break
                game = Game(game.hi)
            else:
                game.reset_positions()
    finally:
        save_hi(game.hi)


def main():
    ap = argparse.ArgumentParser(description="Pac-Man for the terminal")
    ap.add_argument("--ascii", action="store_true", help="use plain ASCII graphics")
    args = ap.parse_args()
    locale.setlocale(locale.LC_ALL, "")
    ascii_mode = args.ascii or "utf" not in locale.getpreferredencoding().lower()
    try:
        curses.wrapper(run, ascii_mode)
    except KeyboardInterrupt:
        pass
    print("Thanks for playing! High score saved to", HI_FILE)


if __name__ == "__main__":
    main()
