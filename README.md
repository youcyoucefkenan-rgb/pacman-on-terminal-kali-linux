# Terminal Pac-Man

A Pac-Man game that runs entirely in your terminal, written in pure Python 3 with the built-in `curses` library. No extra packages needed, so it works out of the box on Kali Linux and most other Linux/macOS terminals.

```
██████████████████████████████████████
██ · · · · · · · ·██· · · · · · · ·██
██●████ ·██████ ·██ ·██████ ·████●██
██ · · · · · · · · · · · · · · · · ██
```

## Requirements

- Python 3.6 or newer
- A terminal at least **40 columns x 24 rows**
- A UTF-8 terminal for the nicest graphics (or use `--ascii`)

## How to run

```bash
cd ~/Downloads        # or wherever you saved the file
python3 pacman.py
```

Optional: run it as a command.

```bash
chmod +x pacman.py
./pacman.py
```

If the walls look garbled, use plain ASCII graphics:

```bash
python3 pacman.py --ascii
```

## Controls

| Key              | Action        |
|------------------|---------------|
| Arrow keys / WASD | Move          |
| `P`              | Pause / resume |
| `Q`              | Quit          |
| `Enter` / `Space` | Start (title screen) |
| `R`              | Retry (game over screen) |

## How to play

- Eat every dot in the maze to clear the level.
- Avoid the four ghosts (`MM`). Touching one costs a life.
- Eat a power pellet (`●` or `O`) and the ghosts turn blue (`mm`). While they are blue you can eat them. They flash shortly before the effect ends.
- Eaten ghosts turn into eyes (`''`), run back to their house, and come back out.
- Use the side tunnel in the middle row to wrap around to the other side. Ghosts can use it too.
- You start with 3 lives.

## Scoring

| Item                 | Points               |
|----------------------|----------------------|
| Dot                  | 10                   |
| Power pellet         | 50                   |
| Ghosts (one pellet)  | 200, 400, 800, 1600  |

Your high score is saved automatically to `~/.pacman_highscore`.

## The ghosts

Each ghost has its own personality:

| Ghost  | Color   | Behavior                                              |
|--------|---------|-------------------------------------------------------|
| Blinky | Red     | Chases you directly                                   |
| Pinky  | Magenta | Aims a few tiles ahead of where you are heading       |
| Inky   | Cyan    | Uses Blinky's position to set up pincer attacks       |
| Clyde  | Green   | Chases when far away, retreats to his corner when close |

Ghosts alternate between **scatter** (heading to their corners) and **chase** modes, and leave the ghost house one at a time.

## Levels

Each new level makes the game harder: ghosts get faster, leave the house sooner, and power pellets last a shorter time.

## Troubleshooting

| Problem                         | Fix                                                        |
|---------------------------------|------------------------------------------------------------|
| "Terminal too small" message    | Enlarge or maximize the window (40x24 minimum)             |
| Broken or strange wall characters | Run with `--ascii`                                       |
| Colors look wrong               | Try `TERM=xterm-256color python3 pacman.py`                |
| `python3: command not found`    | `sudo apt install python3`                                 |

## Project layout

```
pacman.py   # the whole game
README.md   # this file
```

The code is split into game logic (the `Game` class, no drawing code) and the `curses` screens and drawing functions, so it is easy to modify or port to another UI such as Pygame.

## Ideas to extend it

- Bonus fruit
- Extra life at 10,000 points
- Sound effects through the terminal bell
- A different maze (edit the `MAZE` list at the top of `pacman.py`)

Have fun!
