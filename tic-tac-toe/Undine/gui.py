"""Tkinter GUI 15×15 tic-tac-toe spēlei ar Swap2 atklātni."""

import tkinter as tk
from tkinter import messagebox, ttk

try:
    from bot import BOT_NAME, get_move, swap2_propose, swap2_respond, swap2_final_choice
except ImportError:
    BOT_NAME = "Bota nav"

SIZE = 15
EMPTY = "_"


class GomokuGame:
    def __init__(self, root):
        self.root = root
        root.title("5-rindu Tic-Tac-Toe — Swap2")
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.phase = "setup"
        self.player1 = "X"
        self.player2 = "O"
        self.current = "X"
        self.human = "X"
        self.finished = False
        self.swap_pending = ["X", "X", "O"]
        self.swap_place_pending = []
        self.name1 = "Spēlētājs 1"
        self.name2 = "Spēlētājs 2"
        self.starting_player = 1

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Jauna spēle", command=self.new_game).pack(side="left", padx=5)

        self.status = ttk.Label(root, text="Spied \"Jauna spēle\"", font=("Segoe UI", 11))
        self.status.pack(pady=(0, 6))

        board_frame = tk.Frame(root)
        board_frame.pack()
        self.canvas = tk.Canvas(board_frame, width=660, height=660, bg="#DDAA55", highlightthickness=1,
                                highlightbackground="#5A3A20")
        self.canvas.pack()
        self.cell = 44
        self.origin = 0
        self.canvas.bind("<Button-1>", self.on_click)
        self.draw_board()

    def new_game(self):
        setup = tk.Toplevel(self.root)
        setup.title("Cilvēks pret botu")

        ttk.Label(setup, text="Tavs vārds:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        human_name = tk.StringVar(value=self.name1)
        ttk.Entry(setup, textvariable=human_name, width=24).grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(setup, text="Kurš sāk Swap2:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        starter = tk.StringVar(value="human")
        ttk.Radiobutton(setup, text="Es", variable=starter, value="human").grid(row=1, column=1, sticky="w", padx=10)
        ttk.Radiobutton(setup, text="Bots", variable=starter, value="bot").grid(row=2, column=1, sticky="w", padx=10)

        def start():
            self.name1 = human_name.get().strip() or "Spēlētājs"
            self.name2 = BOT_NAME
            self.starting_player = starter.get()
            setup.destroy()

            self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
            self.finished = False
            self.swap_pending = ["X", "X", "O"]
            self.swap_place_pending = []
            self.draw_board()

            if self.starting_player == "human":
                self.phase = "swap_propose"
                self.status.configure(text=f"{self.name1}: novieto 3 figūras — X, X, O")
            else:
                proposal = swap2_propose(self.board)
                for r, c, symbol in proposal:
                    self.board[r][c] = symbol
                self.phase = "human_swap_choice"
                self.draw_board()
                self.status.configure(text="Bots novietoja 3 figūras. Izvēlies TAKE_X, TAKE_O vai PLACE_TWO")
                self.show_human_swap_choice()

        ttk.Button(setup, text="Sākt spēli", command=start).grid(row=3, column=0, columnspan=2, pady=12)

    def draw_board(self):
        self.canvas.delete("all")
        for i in range(SIZE):
            x = i * self.cell
            self.canvas.create_line(x, 0, x, SIZE * self.cell, fill="#5A3A20")
            self.canvas.create_line(0, x, SIZE * self.cell, x, fill="#5A3A20")
        for r in range(SIZE):
            for c in range(SIZE):
                value = self.board[r][c]
                if value == EMPTY:
                    continue
                x1 = c * self.cell + 5
                y1 = r * self.cell + 5
                x2 = x1 + self.cell - 10
                y2 = y1 + self.cell - 10
                if value == "X":
                    text_color = "#B91C1C"
                else:
                    text_color = "#1D4ED8"
                self.canvas.create_text(
                    c * self.cell + self.cell // 2,
                    r * self.cell + self.cell // 2,
                    text=value,
                    fill=text_color,
                    font=("Segoe UI", 23, "bold"),
                )

    def on_click(self, event):
        if self.finished:
            return
        c = event.x // self.cell
        r = event.y // self.cell
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            return

        if self.phase in ("swap_response", "swap_choice_manual", "swap_final"):
            return

        if self.phase == "swap_propose":
            if self.board[r][c] == EMPTY:
                symbol = self.swap_pending.pop(0)
                self.board[r][c] = symbol
                self.draw_board()
                if self.swap_pending:
                    self.status.configure(text=f"Novieto nākamo figūru: {self.swap_pending[0]}")
                else:
                    self.phase = "swap_choice_manual"
                    self.status.configure(text="Otrā spēlētāja izvēle: TAKE_X, TAKE_O vai PLACE_TWO")
                    self.show_manual_choice()
            return

        if self.phase == "swap_place_two":
            if self.board[r][c] == EMPTY:
                symbol = self.swap_place_pending.pop(0)
                self.board[r][c] = symbol
                self.draw_board()
                if self.swap_place_pending:
                    self.status.configure(text=f"Novieto otro papildfigūru: {self.swap_place_pending[0]}")
                else:
                    self.phase = "swap_final"
                    self.status.configure(text="Pirmais spēlētājs izvēlas X vai O")
                    final = tk.Toplevel(self.root)
                    final.title("Krāsas izvēle")
                    ttk.Button(final, text="Spēlēt ar X", command=lambda: self.manual_final_choice(final, "X")).pack(padx=20, pady=5)
                    ttk.Button(final, text="Spēlēt ar O", command=lambda: self.manual_final_choice(final, "O")).pack(padx=20, pady=5)
            return

        if self.phase == "human_place_two":
            if self.board[r][c] == EMPTY:
                symbol = self.swap_place_pending.pop(0)
                self.board[r][c] = symbol
                self.draw_board()
                if self.swap_place_pending:
                    self.status.configure(text=f"Novieto {self.swap_place_pending[0]} — klikšķini uz brīva lauciņa")
                else:
                    final = tk.Toplevel(self.root)
                    final.title("Izvēlies savu krāsu")
                    ttk.Button(final, text="Spēlēt ar X", command=lambda: self.finish_human_place_two(final, "X")).pack(padx=20, pady=5)
                    ttk.Button(final, text="Spēlēt ar O", command=lambda: self.finish_human_place_two(final, "O")).pack(padx=20, pady=5)
            return

        if (self.phase == "playing"
                and getattr(self, "human_symbol", None) == self.current
                and self.board[r][c] == EMPTY):
            self.play_move(r, c, self.current)

    def play_move(self, r, c, player):
        self.board[r][c] = player
        self.draw_board()
        if self.has_five(r, c, player):
            self.finished = True
            self.status.configure(text=f"Uzvar {player}!")
            messagebox.showinfo("Spēles beigas", f"Uzvar {player}")
            return
        if all(value != EMPTY for row in self.board for value in row):
            self.finished = True
            self.status.configure(text="Neizšķirts")
            messagebox.showinfo("Spēles beigas", "Neizšķirts")
            return

        opponent = "O" if player == "X" else "X"
        self.current = opponent
        opponent_name = self.name1 if opponent == getattr(self, "human_symbol", "") else self.name2
        self.status.configure(text=f"Gājiens: {opponent_name} ({opponent})")

        if opponent == getattr(self, "bot_symbol", None):
            self.root.after(300, lambda: self.bot_move(self.bot_symbol))

    def bot_move(self, player):
        if self.finished:
            return
        r, c = get_move(self.board, player)
        if self.board[r][c] != EMPTY:
            return
        self.play_move(r, c, player)

    def bot_swap_response_human_start(self):
        response = swap2_respond(self.board)
        action = response["action"]

        if action == "TAKE_X":
            self.human_symbol = "O"
            self.bot_symbol = "X"
            self.current = "X"
        elif action == "TAKE_O":
            self.human_symbol = "X"
            self.bot_symbol = "O"
            self.current = "O"
        else:
            for r, c, symbol in response["moves"]:
                if self.board[r][c] == EMPTY:
                    self.board[r][c] = symbol
            choice = swap2_final_choice(self.board)
            self.human_symbol = choice
            self.bot_symbol = "O" if choice == "X" else "X"
            self.current = "O" if choice == "X" else "X"

        self.player1 = self.human_symbol
        self.player2 = self.bot_symbol
        self.phase = "playing"
        self.draw_board()
        next_name = self.name1 if self.current == self.human_symbol else self.name2
        self.status.configure(text=f"Bots izvēlējās {action}. Gājiens: {next_name} ({self.current})")
        if self.current == self.bot_symbol:
            self.root.after(300, lambda: self.bot_move(self.bot_symbol))

    def bot_swap_response(self):
        response = swap2_respond(self.board)
        action = response["action"]
        if action == "TAKE_X":
            self.human = "O"
            self.current = "O"
            self.finish_swap(action)
        elif action == "TAKE_O":
            self.human = "X"
            self.current = "O"
            self.finish_swap(action)
        else:
            for r, c, symbol in response["moves"]:
                if self.board[r][c] == EMPTY:
                    self.board[r][c] = symbol
            choice = swap2_final_choice(self.board)
            self.human = choice
            self.current = "O" if choice == "X" else "X"
            self.finish_swap("PLACE_TWO")

    def finish_swap(self, action):
        self.phase = "playing"
        self.status.configure(text=f"Atklātne: {action}. Gājiens: {self.current}. Tu spēlē: {self.human}")
        self.draw_board()
        if self.mode.get() == "Cilvēks pret botu" and self.current != self.human:
            self.root.after(250, lambda: self.bot_move(self.current))

    def show_manual_choice(self):
        window = tk.Toplevel(self.root)
        window.title("Swap2 izvēle")
        ttk.Label(window, text="Otrā spēlētāja darbība:").pack(padx=20, pady=10)
        ttk.Button(window, text="TAKE_X", command=lambda: self.manual_take(window, "X")).pack(fill="x", padx=20, pady=3)
        ttk.Button(window, text="TAKE_O", command=lambda: self.manual_take(window, "O")).pack(fill="x", padx=20, pady=3)
        ttk.Button(window, text="PLACE_TWO", command=lambda: self.manual_place_two(window)).pack(fill="x", padx=20, pady=3)

    def manual_take(self, window, symbol):
        window.destroy()
        proposer = self.starting_player
        responder = 2 if proposer == 1 else 1
        other_symbol = "O" if symbol == "X" else "X"

        if proposer == 1:
            self.player1 = other_symbol
            self.player2 = symbol
        else:
            self.player1 = symbol
            self.player2 = other_symbol

        responder_name = self.name1 if responder == 1 else self.name2
        next_name = self.name1 if self.player1 == "O" else self.name2
        self.phase = "playing"
        self.current = "O"
        self.status.configure(text=f"Gājiens: {next_name} (O) — {responder_name} pārņēma {symbol}")

    def manual_place_two(self, window):
        window.destroy()
        self.phase = "swap_place_two"
        self.swap_place_pending = ["X", "O"]
        self.status.configure(text="Novieto vēl X — klikšķini uz brīva lauciņa")

    def manual_final_choice(self, window, symbol):
        window.destroy()
        self.phase = "playing"
        chooser = self.starting_player
        other = 2 if chooser == 1 else 1
        if symbol == "X":
            self.player1 = "X" if chooser == 1 else "O"
            self.player2 = "X" if chooser == 2 else "O"
        else:
            self.player1 = "O" if chooser == 1 else "X"
            self.player2 = "O" if chooser == 2 else "X"

        chooser_name = self.name1 if chooser == 1 else self.name2
        self.current = "O" if symbol == "X" else "X"
        next_name = self.name1 if self.player1 == self.current else self.name2
        self.status.configure(text=f"{chooser_name} izvēlējās {symbol}. Gājiens: {next_name} ({self.current})")

    def run_swap2_bot(self):
        try:
            proposal = swap2_propose(self.board)
            for r, c, symbol in proposal:
                self.board[r][c] = symbol
            response = swap2_respond(self.board)
            action = response["action"]
            if action == "TAKE_X":
                self.current = "O"
            elif action == "TAKE_O":
                self.current = "O"
            else:
                for r, c, symbol in response["moves"]:
                    self.board[r][c] = symbol
                choice = swap2_final_choice(self.board)
                self.current = "O" if choice == "X" else "X"
            self.phase = "playing"
            self.status.configure(text=f"Swap2: {action}; gājiens: {self.current}")
            self.draw_board()
            self.root.after(300, lambda: self.bot_move(self.current))
        except Exception as exc:
            messagebox.showerror("Kļūda", str(exc))

    def has_five(self, row, col, player):
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < SIZE and 0 <= c < SIZE and self.board[r][c] == player:
                count += 1
                r += dr
                c += dc
            r, c = row - dr, col - dc
            while 0 <= r < SIZE and 0 <= c < SIZE and self.board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if count >= 5:
                return True
        return False

    def show_human_swap_choice(self):
        window = tk.Toplevel(self.root)
        window.title("Mana Swap2 izvēle")
        ttk.Label(window, text="Izvēlies, kā pārņemt atklātni:").pack(padx=20, pady=10)
        ttk.Button(window, text="TAKE_X", command=lambda: self.human_take(window, "X")).pack(fill="x", padx=20, pady=3)
        ttk.Button(window, text="TAKE_O", command=lambda: self.human_take(window, "O")).pack(fill="x", padx=20, pady=3)
        ttk.Button(window, text="PLACE_TWO", command=lambda: self.human_place_two(window)).pack(fill="x", padx=20, pady=3)

    def human_take(self, window, symbol):
        window.destroy()
        self.human_symbol = symbol
        self.bot_symbol = "O" if symbol == "X" else "X"
        self.player1 = self.bot_symbol
        self.player2 = self.human_symbol
        self.phase = "playing"
        self.current = "O"
        self.draw_board()
        next_name = self.name1 if self.current == self.human_symbol else self.name2
        self.status.configure(text=f"Gājiens: {next_name} ({self.current})")
        if self.current == self.bot_symbol:
            self.root.after(300, lambda: self.bot_move(self.bot_symbol))

    def human_place_two(self, window):
        window.destroy()
        self.phase = "human_place_two"
        self.swap_place_pending = ["X", "O"]
        self.status.configure(text="Novieto X — klikšķini uz brīva lauciņa")

    def finish_human_place_two(self, window, symbol):
        window.destroy()
        self.human_symbol = symbol
        self.bot_symbol = "O" if symbol == "X" else "X"
        self.player1 = self.bot_symbol
        self.player2 = self.human_symbol
        self.phase = "playing"
        self.current = "O" if symbol == "X" else "X"
        self.draw_board()
        next_name = self.name1 if self.current == self.human_symbol else self.name2
        self.status.configure(text=f"Gājiens: {next_name} ({self.current})")
        if self.current == self.bot_symbol:
            self.root.after(300, lambda: self.bot_move(self.bot_symbol))


if __name__ == "__main__":
    root = tk.Tk()
    GomokuGame(root)
    root.mainloop()
