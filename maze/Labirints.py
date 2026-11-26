import time
import tkinter as tk


TILE_SIZE = 26
MAP_WIDTH = 31
MAP_HEIGHT = 19
MAP_LEFT = 42
MAP_TOP = 126
BACKGROUND = "#101923"
FLOOR = "#e7eceb"
HALL = "#d5dfdc"
WALL = "#35434a"
PLAYER = "#1676d2"
EXIT = "#16a05a"
HAZARD = "#d94b45"
TEXT = "#f3f6f7"
MUTED = "#b8c5c8"

START = (15, 2)
EXITS = {(0, 9), (30, 9), (15, 18)}
HAZARDS = {(11, 6), (20, 13), (8, 14)}
KEYS = {
    (2, 2): ("1", "#f0b429"),
    (28, 2): ("2", "#58a6ff"),
    (2, 16): ("3", "#f07167"),
    (28, 16): ("4", "#b28dff"),
}


def build_floor() -> set[tuple[int, int]]:
    floor: set[tuple[int, int]] = set()

    def rectangle(x1: int, y1: int, x2: int, y2: int) -> None:
        floor.update((x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1))

    rectangle(1, 9, 29, 10)
    rectangle(15, 0, 15, 17)
    rectangle(1, 1, 13, 7)
    rectangle(17, 1, 29, 7)
    rectangle(1, 12, 13, 17)
    rectangle(17, 12, 29, 17)
    rectangle(13, 4, 17, 4)
    rectangle(13, 14, 17, 14)
    rectangle(5, 7, 5, 9)
    rectangle(25, 7, 25, 9)
    rectangle(5, 10, 5, 12)
    rectangle(25, 10, 25, 12)
    floor.update(EXITS)
    return floor


FLOOR_CELLS = build_floor()

# Short interior partitions turn the rooms into a maze while leaving door gaps.
PARTITIONS = {
    *((3, y) for y in range(1, 7) if y != 4),
    *((5, y) for y in range(1, 7) if y not in (2, 5)),
    *((7, y) for y in range(1, 7) if y not in (2, 5)),
    *((9, y) for y in range(1, 7) if y != 3),
    *((11, y) for y in range(1, 7) if y != 3),
    *((x, 4) for x in range(1, 5) if x != 2),
    *((x, 2) for x in range(1, 6) if x != 2),
    *((x, 6) for x in range(7, 13) if x != 10),
    *((19, y) for y in range(1, 7) if y != 3),
    *((21, y) for y in range(1, 7) if y not in (2, 5)),
    *((23, y) for y in range(1, 7) if y not in (2, 5)),
    *((25, y) for y in range(1, 7) if y != 3),
    *((27, y) for y in range(1, 7) if y not in (2, 5)),
    *((x, 4) for x in range(25, 30) if x != 28),
    *((x, 2) for x in range(18, 23) if x != 20),
    *((x, 6) for x in range(23, 29) if x != 26),
    *((4, y) for y in range(12, 18) if y not in (14, 16)),
    *((6, y) for y in range(12, 18) if y not in (13, 16)),
    *((9, y) for y in range(12, 18) if y not in (13, 16)),
    *((11, y) for y in range(12, 18) if y not in (14, 16)),
    *((x, 13) for x in range(1, 6) if x not in (3, 5)),
    *((x, 15) for x in range(5, 13) if x != 10),
    *((x, 16) for x in range(7, 13) if x != 9),
    *((19, y) for y in range(12, 18) if y not in (14, 16)),
    *((22, y) for y in range(12, 18) if y not in (14, 16)),
    *((24, y) for y in range(12, 18) if y not in (13, 16)),
    *((27, y) for y in range(12, 18) if y not in (13, 16)),
    *((x, 13) for x in range(25, 30) if x not in (25, 27)),
    *((x, 15) for x in range(18, 22) if x != 19),
    *((x, 16) for x in range(18, 24) if x != 20),
}


class EvacuationMaze:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Evakuācijas labirints")
        root.configure(bg=BACKGROUND)
        root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=MAP_WIDTH * TILE_SIZE + 2 * MAP_LEFT,
            height=MAP_HEIGHT * TILE_SIZE + MAP_TOP + 30,
            bg=BACKGROUND,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.status = tk.StringVar()
        tk.Label(
            root,
            text="EVAKUĀCIJAS LABIRINTS",
            font=("Segoe UI", 22, "bold"),
            bg=BACKGROUND,
            fg=TEXT,
        ).place(x=MAP_LEFT, y=16)
        tk.Label(
            root,
            text="Savāc visas 4 atslēgas, apiej bīstamās zonas un atrodi vienu no 3 izejām.",
            font=("Segoe UI", 11),
            bg=BACKGROUND,
            fg=MUTED,
        ).place(x=MAP_LEFT, y=55)
        tk.Label(
            root,
            textvariable=self.status,
            font=("Segoe UI", 11, "bold"),
            bg=BACKGROUND,
            fg="#88d8aa",
        ).place(x=MAP_LEFT, y=83)

        self.player = START
        self.moves = 0
        self.collected_keys: set[tuple[int, int]] = set()
        self.started_at = time.monotonic()
        self.finished = False
        self.message = ""
        self.draw_map()
        root.bind("<KeyPress>", self.on_key)
        self.update_status()
        self.root.after(250, self.update_clock)

    def draw_map(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                x1 = MAP_LEFT + x * TILE_SIZE
                y1 = MAP_TOP + y * TILE_SIZE
                x2, y2 = x1 + TILE_SIZE, y1 + TILE_SIZE
                if (x, y) not in FLOOR_CELLS:
                    canvas.create_rectangle(x1, y1, x2, y2, fill=WALL, outline="#202d32")
                    continue
                color = HALL if y in (9, 10) or x == 15 else FLOOR
                canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#c4cfcc")
                if (x, y) in PARTITIONS:
                    canvas.create_rectangle(x1, y1, x2, y2, fill=WALL, outline=WALL)
                elif (x, y) in HAZARDS:
                    canvas.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3, fill=HAZARD, outline="#9c302d")
                    canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="!",
                        fill="white",
                        font=("Segoe UI", 14, "bold"),
                    )

        for key_cell, (key_number, key_color) in KEYS.items():
            if key_cell in self.collected_keys:
                continue
            cx, cy = self.cell_center(key_cell)
            canvas.create_oval(
                cx - 9,
                cy - 9,
                cx + 9,
                cy + 9,
                fill=key_color,
                outline="#30343b",
                width=2,
            )
            canvas.create_text(cx, cy, text=key_number, fill="#17202a", font=("Segoe UI", 9, "bold"))

        for exit_x, exit_y in EXITS:
            cx, cy = self.cell_center((exit_x, exit_y))
            unlocked = len(self.collected_keys) == len(KEYS)
            exit_color = EXIT if unlocked else "#8b3c3a"
            canvas.create_rectangle(
                cx - TILE_SIZE * 0.39,
                cy - TILE_SIZE * 0.39,
                cx + TILE_SIZE * 0.39,
                cy + TILE_SIZE * 0.39,
                fill=exit_color,
                outline="#087641" if unlocked else "#542927",
                width=2,
            )
            canvas.create_text(
                cx,
                cy,
                text="IZEJA" if unlocked else "SLĒGTS",
                fill="white",
                font=("Segoe UI", 6, "bold"),
            )

        canvas.create_text(
            *self.cell_center(START),
            text="SĀKUMS",
            fill="#243c50",
            font=("Segoe UI", 7, "bold"),
        )
        self.draw_player()
        self.draw_legend()

    def draw_player(self) -> None:
        cx, cy = self.cell_center(self.player)
        radius = TILE_SIZE * 0.34
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=PLAYER,
            outline="white",
            width=2,
        )

    def draw_legend(self) -> None:
        y = MAP_TOP + MAP_HEIGHT * TILE_SIZE + 16
        self.canvas.create_oval(MAP_LEFT, y, MAP_LEFT + 16, y + 16, fill=PLAYER, outline="white")
        self.canvas.create_text(MAP_LEFT + 23, y + 8, text="Tu", anchor="w", fill=TEXT, font=("Segoe UI", 9))
        self.canvas.create_rectangle(MAP_LEFT + 90, y, MAP_LEFT + 106, y + 16, fill=EXIT, outline="")
        self.canvas.create_text(MAP_LEFT + 113, y + 8, text="Izeja", anchor="w", fill=TEXT, font=("Segoe UI", 9))
        self.canvas.create_rectangle(MAP_LEFT + 190, y, MAP_LEFT + 206, y + 16, fill=HAZARD, outline="")
        self.canvas.create_text(MAP_LEFT + 213, y + 8, text="Bīstama zona", anchor="w", fill=TEXT, font=("Segoe UI", 9))
        self.canvas.create_oval(MAP_LEFT + 335, y, MAP_LEFT + 351, y + 16, fill="#f0b429", outline="#30343b")
        self.canvas.create_text(MAP_LEFT + 343, y + 8, text="K", fill="#17202a", font=("Segoe UI", 8, "bold"))
        self.canvas.create_text(MAP_LEFT + 358, y + 8, text="Atslēga", anchor="w", fill=TEXT, font=("Segoe UI", 9))
        self.canvas.create_text(
            MAP_LEFT + 485,
            y + 8,
            text="Bultiņas/WASD: kustība  |  R: no jauna",
            anchor="w",
            fill=MUTED,
            font=("Segoe UI", 9),
        )

    def cell_center(self, cell: tuple[int, int]) -> tuple[float, float]:
        x, y = cell
        return (
            MAP_LEFT + (x + 0.5) * TILE_SIZE,
            MAP_TOP + (y + 0.5) * TILE_SIZE,
        )

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "r":
            self.reset()
            return
        if self.finished:
            return

        directions = {
            "up": (0, -1), "w": (0, -1),
            "down": (0, 1), "s": (0, 1),
            "left": (-1, 0), "a": (-1, 0),
            "right": (1, 0), "d": (1, 0),
        }
        if key not in directions:
            return
        dx, dy = directions[key]
        next_cell = (self.player[0] + dx, self.player[1] + dy)
        if next_cell not in FLOOR_CELLS or next_cell in PARTITIONS:
            self.message = "Tur ir siena — izmēģini citu ceļu."
            self.update_status()
            return
        if next_cell in HAZARDS:
            self.message = "Bīstama zona! Atrodi citu maršrutu."
            self.update_status()
            return
        if next_cell in EXITS and len(self.collected_keys) < len(KEYS):
            self.message = f"Izeja slēgta — vajag visas {len(KEYS)} atslēgas."
            self.update_status()
            return

        self.player = next_cell
        self.moves += 1
        if self.player in KEYS:
            self.collected_keys.add(self.player)
            remaining = len(KEYS) - len(self.collected_keys)
            self.message = "Visas atslēgas savāktas — izejas atslēgtas!" if not remaining else f"Atslēga savākta! Atlikušas {remaining}."
        else:
            self.message = ""
        if self.player in EXITS:
            self.finished = True
            elapsed = int(time.monotonic() - self.started_at)
            self.message = f"Tu sasniedzi izeju {elapsed // 60:02}:{elapsed % 60:02} laikā! Spied R, lai spēlētu vēlreiz."
        self.draw_map()
        self.update_status()

    def update_status(self) -> None:
        elapsed = int(time.monotonic() - self.started_at)
        details = f"Atslēgas: {len(self.collected_keys)}/{len(KEYS)}    Gājieni: {self.moves}    Laiks: {elapsed // 60:02}:{elapsed % 60:02}"
        if self.message:
            details += f"    |    {self.message}"
        self.status.set(details)

    def update_clock(self) -> None:
        if not self.finished:
            self.update_status()
        self.root.after(250, self.update_clock)

    def reset(self) -> None:
        self.player = START
        self.moves = 0
        self.collected_keys.clear()
        self.started_at = time.monotonic()
        self.finished = False
        self.message = ""
        self.draw_map()
        self.update_status()


def main() -> None:
    root = tk.Tk()
    EvacuationMaze(root)
    root.mainloop()


if __name__ == "__main__":
    main()
