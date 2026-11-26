import copy
import glob
import importlib.util
import os
import threading
import tkinter as tk
from tkinter import ttk

SIZE = 15
EMPTY = "_"
HUMAN = "Cilvēks"
CELL = 36
MARGIN = 24

COLORS = {
    "window": "#F4F1EA",
    "panel": "#FFFFFF",
    "panel_border": "#DDD8CD",
    "board": "#E8C989",
    "board_alt": "#E2BE75",
    "grid": "#7A6342",
    "grid_light": "#987C54",
    "x": "#20262D",
    "o": "#F7F4EC",
    "o_outline": "#A89F90",
    "accent": "#4F6F52",
    "accent_hover": "#415F44",
    "status": "#30362F",
    "muted": "#777B75",
}


def opponent(player):
    return "O" if player == "X" else "X"


def discover_bots():
    here = os.path.dirname(os.path.abspath(__file__))
    bots = {}
    bot_paths = [os.path.join(here, "bot.py")]
    bot_paths += glob.glob(os.path.join(here, "studenti", "*", "bot.py"))

    for path in sorted(set(bot_paths)):
        try:
            spec = importlib.util.spec_from_file_location(
                "bot_" + str(abs(hash(os.path.abspath(path)))), path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            name = getattr(module, "BOT_NAME", os.path.basename(os.path.dirname(path)))
            bots[f"{name}"] = module
        except Exception as exc:
            print(f"Nespēja ielādēt botu {path}: {exc}")
    return bots


def is_free(board, r, c):
    return (0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == EMPTY)


def winning_line(board, r, c):
    player = board[r][c]
    for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
        cells = [(r, c)]
        for sign in (1, -1):
            rr, cc = r + sign * dr, c + sign * dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and board[rr][cc] == player:
                cells.append((rr, cc))
                rr += sign * dr
                cc += sign * dc
        if len(cells) >= 5:
            return cells
    return None


class App:
    def __init__(self, root):
        self.root = root
        root.title("5-rindu Tic-Tac-Toe (Swap2)")
        root.configure(bg=COLORS["window"])
        root.resizable(False, False)
        self.bots = discover_bots()
        options = [HUMAN] + list(self.bots)

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=COLORS["panel"])
        style.configure("Title.TLabel", background=COLORS["panel"],
                        foreground=COLORS["status"],
                        font=("Arial", 13))
        style.configure("Section.TLabel", background=COLORS["panel"],
                        foreground=COLORS["muted"],
                        font=("Arial", 9))
        style.configure("Status.TLabel", background=COLORS["panel"],
                        foreground=COLORS["status"],
                        font=("Arial", 10))
        style.configure("App.TCombobox", padding=7, font=("Arial", 10))
        style.map("App.TCombobox",
                  fieldbackground=[("readonly", "#F9F8F4")],
                  selectbackground=[("readonly", "#F9F8F4")],
                  selectforeground=[("readonly", COLORS["status"])])
        style.configure("App.TButton", padding=(12, 8),
                        font=("Arial", 10),
                        foreground="white", background=COLORS["accent"],
                        borderwidth=0)
        style.map("App.TButton",
                  background=[("active", COLORS["accent_hover"]),
                              ("pressed", "#354F38")])

        side = ttk.Frame(root, padding=14, style="App.TFrame")
        side.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(side, text="Spēles iestatījumi",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        ttk.Label(side, text="Pirmais spēlētājs", style="Section.TLabel").pack(anchor="w")
        self.p1 = tk.StringVar(value=HUMAN)
        ttk.Combobox(side, textvariable=self.p1, values=options,
                     state="readonly", width=24,
                     style="App.TCombobox").pack(anchor="w", pady=(4, 12))
        ttk.Label(side, text="Otrais spēlētājs", style="Section.TLabel").pack(anchor="w")
        self.p2 = tk.StringVar(value=options[1] if len(options) > 1 else HUMAN)
        ttk.Combobox(side, textvariable=self.p2, values=options,
                     state="readonly", width=24,
                     style="App.TCombobox").pack(anchor="w", pady=(4, 12))
        ttk.Button(side, text="Jauna spēle", command=self.new_game,
                   style="App.TButton").pack(fill=tk.X, pady=(2, 14))

        self.colors = tk.Label(side, text="", justify="left", anchor="w",
                               bg=COLORS["panel"], fg=COLORS["status"],
                               font=("Arial", 10), padx=12, pady=9,
                               relief="solid", bd=1,
                               highlightbackground=COLORS["panel_border"])
        self.colors.pack(fill=tk.X, pady=(0, 10))
        self.status = tk.Label(side, text="", wraplength=245, justify="left", anchor="w",
                               bg="#F2F5EF", fg=COLORS["status"],
                               font=("Arial", 10), padx=12, pady=10,
                               relief="solid", bd=1,
                               highlightbackground="#CFD8CA")
        self.status.pack(fill=tk.X, pady=(0, 8))
        self.actions = tk.Frame(side, bg=COLORS["panel"])
        self.actions.pack(fill=tk.X, pady=(0, 6))

        px = MARGIN * 2 + CELL * SIZE
        board_frame = tk.Frame(root, bg=COLORS["window"], padx=14, pady=14)
        board_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        self.canvas = tk.Canvas(board_frame, width=px, height=px,
                                bg=COLORS["board"], highlightthickness=1,
                                highlightbackground=COLORS["panel_border"])
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self.game_id = 0
        self.new_game()

    def clear_actions(self):
        for widget in self.actions.winfo_children():
            widget.destroy()

    def add_action(self, text, command):
        ttk.Button(self.actions, text=text, command=command,
                   style="App.TButton").pack(fill=tk.X, pady=2)

    def set_status(self, text):
        self.status.configure(text=text)

    def is_human(self, index):
        return self.players[index] is None

    def xy(self, r, c):
        return (MARGIN + c * CELL + CELL // 2,
                MARGIN + r * CELL + CELL // 2)

    def draw(self):
        cv = self.canvas
        cv.delete("all")
        left = MARGIN
        right = MARGIN + CELL * SIZE
        bottom = MARGIN + CELL * SIZE
        for i in range(SIZE):
            pos = MARGIN + i * CELL
            cv.create_line(pos, MARGIN, pos, bottom,
                           fill=COLORS["grid_light"], width=1)
            cv.create_line(MARGIN, pos, right, pos,
                           fill=COLORS["grid_light"], width=1)
            cv.create_text(pos + CELL // 2, MARGIN - 18, text=str(i),
                           fill=COLORS["muted"], font=("Segoe UI", 8))
            cv.create_text(MARGIN - 18, pos + CELL // 2, text=str(i),
                           fill=COLORS["muted"], font=("Segoe UI", 8))
        cv.create_line(right, MARGIN, right, bottom,
                       fill=COLORS["grid"], width=2)
        cv.create_line(MARGIN, bottom, right, bottom,
                       fill=COLORS["grid"], width=2)

        for r in range(SIZE):
            for c in range(SIZE):
                x, y = self.xy(r, c)
                cv.create_oval(x - 1.5, y - 1.5, x + 1.5, y + 1.5,
                               fill=COLORS["grid"], outline="")

        for r in range(SIZE):
            for c in range(SIZE):
                symbol = self.board[r][c]
                if symbol == EMPTY:
                    continue
                x, y = self.xy(r, c)
                radius = CELL // 2 - 3
                if symbol == "X":
                    cv.create_oval(x - radius + 2, y - radius + 3,
                                   x + radius + 2, y + radius + 3,
                                   fill="#C7A96A", outline="")
                    cv.create_oval(x - radius, y - radius,
                                   x + radius, y + radius,
                                   fill=COLORS["x"], outline="#151A1F", width=1)
                    cv.create_line(x - 8, y - 8, x + 8, y + 8,
                                   fill="#F2F0EA", width=2)
                    cv.create_line(x + 8, y - 8, x - 8, y + 8,
                                   fill="#F2F0EA", width=2)
                else:
                    cv.create_oval(x - radius + 2, y - radius + 3,
                                   x + radius + 2, y + radius + 3,
                                   fill="#C7A96A", outline="")
                    cv.create_oval(x - radius, y - radius,
                                   x + radius, y + radius,
                                   fill=COLORS["o"], outline=COLORS["o_outline"], width=1)
        if self.last:
            x, y = self.xy(*self.last)
            cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="red", outline="red")
        if self.win_cells:
            for r, c in self.win_cells:
                x, y = self.xy(r, c)
                cv.create_rectangle(x - CELL // 2 + 3, y - CELL // 2 + 3,
                                    x + CELL // 2 - 3, y + CELL // 2 - 3,
                                    outline="red", width=3)

    def new_game(self):
        self.game_id += 1
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        names = [self.p1.get(), self.p2.get()]
        self.names = names
        self.players = [None if name == HUMAN else self.bots[name] for name in names]
        self.color = {0: None, 1: None}
        self.pending = []
        self.last = None
        self.win_cells = None
        self.phase = "propose"
        self.busy = False
        self.clear_actions()
        self.update_colors()
        self.draw()
        self.advance()

    def update_colors(self):
        self.colors.configure(
            text=f"1. {self.names[0]}: {self.color[0] or '?'}\n"
                 f"2. {self.names[1]}: {self.color[1] or '?'}"
        )

    def turn_index(self):
        x_count = sum(cell == "X" for row in self.board for cell in row)
        o_count = sum(cell == "O" for row in self.board for cell in row)
        symbol = "X" if x_count == o_count else "O"
        index = 0 if self.color[0] == symbol else 1
        return symbol, index

    def advance(self):
        self.clear_actions()
        self.update_colors()
        if self.phase == "propose":
            if self.is_human(0):
                self.pending = ["X", "X", "O"]
                self.set_status("1. spēlētājs: novietojiet 2× X un 1× O.")
            else:
                self.set_status("1. spēlētājs (bots) novieto atklātni...")
                self.run_bot(0, "swap2_propose", self.apply_propose)
        elif self.phase == "respond":
            if self.is_human(1):
                self.set_status("2. spēlētājs: izvēlieties darbību.")
                self.add_action("Ņemt X (TAKE_X)", lambda: self.apply_response({"action": "TAKE_X"}))
                self.add_action("Ņemt O (TAKE_O)", lambda: self.apply_response({"action": "TAKE_O"}))
                self.add_action("Novietot vēl divas (PLACE_TWO)", self.human_place_two)
            else:
                self.set_status("2. spēlētājs (bots) izvēlas...")
                self.run_bot(1, "swap2_respond", self.apply_response)
        elif self.phase == "place_two":
            self.set_status(f"2. spēlētājs: novietojiet {self.pending[0]}.")
        elif self.phase == "final":
            if self.is_human(0):
                self.set_status("1. spēlētājs: izvēlieties krāsu.")
                self.add_action("Spēlēt ar X", lambda: self.apply_final("X"))
                self.add_action("Spēlēt ar O", lambda: self.apply_final("O"))
            else:
                self.set_status("1. spēlētājs (bots) izvēlas krāsu...")
                self.run_bot(0, "swap2_final_choice", self.apply_final)
        elif self.phase == "play":
            symbol, index = self.turn_index()
            if self.is_human(index):
                self.set_status(f"Jūsu gājiens ({symbol}).")
            else:
                self.set_status(f"{self.names[index]} domā ({symbol})...")
                self.run_bot(index, "get_move", self.apply_move, symbol)

    def run_bot(self, index, function_name, callback, *extra):
        module = self.players[index]
        board = copy.deepcopy(self.board)
        game_id = self.game_id
        result = {}

        def work():
            try:
                result["value"] = getattr(module, function_name)(board, *extra)
            except Exception as exc:
                result["error"] = exc

        threading.Thread(target=work, daemon=True).start()

        def poll():
            if game_id != self.game_id:
                return
            if "value" not in result and "error" not in result:
                self.root.after(30, poll)
                return
            self.busy = False
            if "error" in result:
                self.phase = "over"
                self.set_status(f"Kļūda: {result['error']}")
                return
            callback(result["value"])

        self.busy = True
        self.root.after(30, poll)

    def apply_propose(self, moves):
        try:
            assert isinstance(moves, (list, tuple)) and len(moves) == 3
            assert sorted(str(move[2]) for move in moves) == ["O", "X", "X"]
            seen = set()
            for r, c, symbol in moves:
                assert is_free(self.board, r, c)
                assert (r, c) not in seen
                seen.add((r, c))
        except Exception:
            self.phase = "over"
            self.set_status("Nederīgs botu atklātnes atbildes rezultāts.")
            return
        for r, c, symbol in moves:
            self.board[r][c] = symbol
        self.phase = "respond"
        self.draw()
        self.advance()

    def apply_response(self, response):
        if isinstance(response, dict) and response.get("action") in ("TAKE_X", "TAKE_O"):
            chosen = response["action"].replace("TAKE_", "")
            self.color[1] = chosen
            self.color[0] = opponent(chosen)
            self.phase = "play"
            self.update_colors()
            self.draw()
            self.advance()
        elif isinstance(response, dict) and response.get("action") == "PLACE_TWO":
            try:
                moves = response["moves"]
                assert len(moves) == 2
                assert sorted(symbol for _, _, symbol in moves) == ["O", "X"]
                assert len({(r, c) for r, c, _ in moves}) == 2
                assert all(is_free(self.board, r, c) for r, c, _ in moves)
            except Exception:
                self.phase = "over"
                self.set_status("Nederīgs botu PLACE_TWO rezultāts.")
                return
            for r, c, symbol in moves:
                self.board[r][c] = symbol
            self.phase = "final"
            self.draw()
            self.advance()
        else:
            self.phase = "over"
            self.set_status("Nederīga botu atbildes darbība.")

    def human_place_two(self):
        self.pending = ["X", "O"]
        self.phase = "place_two"
        self.advance()

    def apply_final(self, symbol):
        if symbol not in ("X", "O"):
            self.phase = "over"
            self.set_status("Nederīga krāsas izvēle.")
            return
        self.color[0] = symbol
        self.color[1] = opponent(symbol)
        self.phase = "play"
        self.update_colors()
        self.draw()
        self.advance()

    def apply_move(self, move):
        symbol, index = self.turn_index()
        try:
            r, c = int(move[0]), int(move[1])
            assert is_free(self.board, r, c)
        except Exception:
            self.phase = "over"
            self.set_status("Nederīgs gājiens.")
            return
        self.make_move(r, c, symbol)

    def make_move(self, r, c, symbol):
        self.board[r][c] = symbol
        self.last = (r, c)
        line = winning_line(self.board, r, c)
        if line:
            self.win_cells = line
            self.phase = "over"
            self.draw()
            self.set_status("Uzvarēja 5 vienādās figūras.")
            return
        if all(EMPTY not in row for row in self.board):
            self.phase = "over"
            self.draw()
            self.set_status("Neizšķirts.")
            return
        self.draw()
        self.advance()

    def on_click(self, event):
        if self.busy or self.phase == "over":
            return
        c = (event.x - MARGIN) // CELL
        r = (event.y - MARGIN) // CELL
        if not is_free(self.board, r, c):
            return

        if self.phase == "propose" and self.is_human(0) and self.pending:
            symbol = self.pending.pop(0)
            self.board[r][c] = symbol
            self.draw()
            if not self.pending:
                self.phase = "respond"
            self.advance()
        elif self.phase == "place_two" and self.is_human(1) and self.pending:
            symbol = self.pending.pop(0)
            self.board[r][c] = symbol
            self.draw()
            if not self.pending:
                self.phase = "final"
            self.advance()
        elif self.phase == "play":
            symbol, index = self.turn_index()
            if self.is_human(index):
                self.make_move(r, c, symbol)


def run_gui():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
