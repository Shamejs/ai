"""Tkinter human-vs-bot interface for the 15x15 Swap2 game."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Protocol

import bot
import bot_easy
import bot_smart


BOARD_SIZE = 15
EMPTY = "_"
BOARD_WOOD = "#70421f"
CELL_WOOD = "#b9824b"
CELL_WOOD_ACTIVE = "#d4a56a"
LAST_MOVE_WOOD = "#f4e7a1"
LAST_MOVE_ACTIVE = "#efdb78"
X_RED = "#d62828"
O_BLUE = "#1769d2"
BOT_OPTIONS = {
    "Standarta": bot,
    "Viegls": bot_easy,
    "Gudrais": bot_smart,
}


class GameBot(Protocol):
    BOT_NAME: str

    def get_move(self, board: list[list[str]], player: str) -> tuple[int, int]: ...

    def swap2_propose(
        self, board: list[list[str]]
    ) -> list[tuple[int, int, str]]: ...

    def swap2_respond(self, board: list[list[str]]) -> dict[str, object]: ...

    def swap2_final_choice(self, board: list[list[str]]) -> str: ...


class TicTacToeGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("5-rindu Tic-Tac-Toe (Swap2)")
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.buttons: list[list[tk.Button]] = []
        self.phase = "idle"
        self.human_color: str | None = None
        self.bot_color: str | None = None
        self.current_player: str | None = None
        self.opening_moves: list[str] = []
        self._last_move: tuple[int, int] | None = None
        self.starter = tk.StringVar(value="first")
        self.game_mode = tk.StringVar(value="Cilvēks pret botu")
        self.bot_choice = tk.StringVar(value="Gudrais")
        self.second_bot_choice = tk.StringVar(value="Standarta")
        self.bot_module: GameBot = bot
        self.player1_bot: GameBot = bot
        self.player2_bot: GameBot = bot
        self.bot_by_color: dict[str, GameBot] = {}
        self.bot_vs_bot = False

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        main_frame = ttk.Frame(root)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        controls = ttk.Frame(main_frame, padding=8)
        controls.grid(row=0, column=0, sticky=tk.EW)
        ttk.Label(controls, text="Režīms:").pack(side=tk.LEFT)
        ttk.Combobox(
            controls,
            textvariable=self.game_mode,
            values=("Cilvēks pret botu", "Boti sacenšas"),
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(controls, text="Kurš sāk:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            controls, text="Pirmais", variable=self.starter, value="first"
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Radiobutton(
            controls, text="Otrais", variable=self.starter, value="second"
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(controls, text="Bots 1:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Combobox(
            controls,
            textvariable=self.bot_choice,
            values=tuple(BOT_OPTIONS),
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)
        ttk.Label(controls, text="Bots 2:").pack(side=tk.LEFT, padx=(8, 4))
        ttk.Combobox(
            controls,
            textvariable=self.second_bot_choice,
            values=tuple(BOT_OPTIONS),
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)
        ttk.Button(controls, text="Jauna spēle", command=self.new_game).pack(
            side=tk.RIGHT
        )

        self.status = ttk.Label(
            main_frame, text="Izvēlies, kurš sāk, un nospied “Jauna spēle”."
        )
        self.status.grid(row=1, column=0, padx=8, pady=(0, 8))

        board_frame = tk.Frame(main_frame, bg=BOARD_WOOD, padx=8, pady=8)
        board_frame.grid(row=2, column=0)
        for r in range(BOARD_SIZE):
            row = []
            for c in range(BOARD_SIZE):
                button = tk.Button(
                    board_frame,
                    text="",
                    width=2,
                    height=1,
                    font=("Segoe UI", 20, "bold"),
                    bg=CELL_WOOD,
                    activebackground=CELL_WOOD_ACTIVE,
                    fg="#352313",
                    activeforeground="#352313",
                    relief=tk.RAISED,
                    borderwidth=2,
                    command=lambda rr=r, cc=c: self.on_cell_click(rr, cc),
                )
                button.grid(row=r, column=c, padx=1, pady=1)
                row.append(button)
            self.buttons.append(row)

    def new_game(self) -> None:
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.phase = "idle"
        self.human_color = None
        self.bot_color = None
        self.current_player = None
        self.opening_moves = []
        self._last_move = None
        self.bot_vs_bot = self.game_mode.get() == "Boti sacenšas"
        self.bot_module = BOT_OPTIONS[self.bot_choice.get()]
        second_module = BOT_OPTIONS[self.second_bot_choice.get()]
        if self.bot_vs_bot:
            self.player1_bot, self.player2_bot = (
                (self.bot_module, second_module)
                if self.starter.get() == "first"
                else (second_module, self.bot_module)
            )
        else:
            self.player1_bot = self.bot_module
            self.player2_bot = self.bot_module
        self.bot_by_color = {}
        self._refresh_board()

        if self.bot_vs_bot:
            self.phase = "bot_open"
            self._set_status("Boti gatavojas sacensties...")
            self.root.after(100, self._bot_propose)
        elif self.starter.get() == "first":
            self.phase = "human_open"
            self.opening_moves = ["X", "X", "O"]
            self._set_status("Atklātne: novieto divus X, pēc tam vienu O.")
        else:
            self.phase = "bot_open"
            self._set_status("Bots veido Swap2 atklātni...")
            self.root.after(100, self._bot_propose)

    def on_cell_click(self, row: int, col: int) -> None:
        if self.board[row][col] != EMPTY:
            return

        if self.phase == "human_open":
            symbol = self.opening_moves.pop(0)
            self._place(row, col, symbol)
            if self.opening_moves:
                next_symbol = self.opening_moves[0]
                self._set_status(f"Atklātne: tagad novieto {next_symbol}.")
            else:
                self.phase = "bot_respond"
                self._set_status("Bots izvērtē atklātni...")
                self.root.after(100, self._bot_respond)
            return

        if self.phase == "human_turn" and self.current_player == self.human_color:
            symbol = self.current_player
            self._place(row, col, symbol)
            self._finish_turn(symbol)

    def _bot_propose(self) -> None:
        if self.phase != "bot_open":
            return
        proposer = self.player1_bot
        responder = self.player2_bot if self.bot_vs_bot else self.bot_module
        for row, col, symbol in proposer.swap2_propose(self._copy_board()):
            self._place(row, col, symbol)
        self._set_status("Swap2 krāsu izvēle tiek veikta automātiski...")
        response = responder.swap2_respond(self._copy_board())
        if response["action"] == "PLACE_TWO":
            for row, col, symbol in response["moves"]:
                self._place(row, col, symbol)
            player1_color = proposer.swap2_final_choice(self._copy_board())
            player2_color = self._other(player1_color)
        else:
            player2_color = response["action"][-1]
            player1_color = self._other(player2_color)
        self._assign_player_colors(player1_color, player2_color)
        self._start_regular_game()

    def _bot_respond(self) -> None:
        if self.phase != "bot_respond":
            return
        response = self.bot_module.swap2_respond(self._copy_board())
        action = response["action"]
        if action == "PLACE_TWO":
            for row, col, symbol in response["moves"]:
                self._place(row, col, symbol)
            self.human_color = self.bot_module.swap2_final_choice(self._copy_board())
            self.bot_color = self._other(self.human_color)
        else:
            self.bot_color = action[-1]
            self.human_color = self._other(self.bot_color)
        self._start_regular_game()

    def _assign_player_colors(self, player1_color: str, player2_color: str) -> None:
        if self.bot_vs_bot:
            self.bot_by_color = {
                player1_color: self.player1_bot,
                player2_color: self.player2_bot,
            }
        else:
            self.bot_color = player1_color
            self.human_color = player2_color

    def _start_regular_game(self) -> None:
        self.current_player = "O"
        if self.bot_vs_bot:
            self.phase = "bot_turn"
            self._set_status(
                f"Botu spēle: {self.player1_bot.BOT_NAME} pret "
                f"{self.player2_bot.BOT_NAME}. Gājiens {self.current_player}."
            )
        else:
            self.phase = (
                "human_turn"
                if self.current_player == self.human_color
                else "bot_turn"
            )
            self._set_status(
                f"Tu spēlē ar {self.human_color}; bots ar {self.bot_color}. "
                f"Tagad gājiens {self.current_player}."
            )
        if self.phase == "bot_turn":
            self.root.after(100, self._bot_move)

    def _bot_move(self) -> None:
        if self.phase != "bot_turn" or self.current_player is None:
            return
        module = (
            self.bot_by_color[self.current_player]
            if self.bot_vs_bot
            else self.bot_module
        )
        player = self.current_player if self.bot_vs_bot else self.bot_color
        if player is None:
            raise RuntimeError("Bot color has not been assigned")
        row, col = module.get_move(self._copy_board(), player)
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            raise ValueError(f"Bots atgrieza nederīgas koordinātas: {(row, col)}")
        if self.board[row][col] != EMPTY:
            raise ValueError(f"Bots izvēlējās aizņemtu rūtiņu: {(row, col)}")
        symbol = self.current_player
        self._place(row, col, symbol)
        self._finish_turn(symbol)

    def _finish_turn(self, symbol: str) -> None:
        row, col = self._last_move
        if self._is_winner(row, col, symbol):
            if self.bot_vs_bot:
                winner = f"{self.bot_by_color[symbol].BOT_NAME} uzvarēja!"
            else:
                winner = "Tu uzvarēji!" if symbol == self.human_color else "Bots uzvarēja!"
            self.phase = "game_over"
            self._set_status(f"{winner} ({symbol})")
            messagebox.showinfo("Spēle beigusies", winner)
            return

        if all(cell != EMPTY for line in self.board for cell in line):
            self.phase = "game_over"
            self._set_status("Neizšķirts!")
            messagebox.showinfo("Spēle beigusies", "Neizšķirts!")
            return

        self.current_player = self._other(symbol)
        if self.current_player == self.human_color:
            self.phase = "human_turn"
            self._set_status(f"Tavs gājiens ({self.current_player}).")
        else:
            self.phase = "bot_turn"
            self._set_status(f"Bota gājiens ({self.current_player})...")
            self.root.after(100, self._bot_move)

    def _place(self, row: int, col: int, symbol: str) -> None:
        if self.board[row][col] != EMPTY:
            raise ValueError(f"Rūtiņa {(row, col)} jau ir aizņemta")
        self.board[row][col] = symbol
        self._last_move = (row, col)
        self._refresh_board()

    def _refresh_board(self) -> None:
        for r, line in enumerate(self.board):
            for c, value in enumerate(line):
                color = X_RED if value == "X" else O_BLUE if value == "O" else "#352313"
                self.buttons[r][c].configure(
                    text="" if value == EMPTY else value,
                    fg=color,
                    activeforeground=color,
                    bg=LAST_MOVE_WOOD if (r, c) == self._last_move else CELL_WOOD,
                    activebackground=(
                        LAST_MOVE_ACTIVE
                        if (r, c) == self._last_move
                        else CELL_WOOD_ACTIVE
                    ),
                )

    def _is_winner(self, row: int, col: int, symbol: str) -> bool:
        directions = ((0, 1), (1, 0), (1, 1), (1, -1))
        for dr, dc in directions:
            count = 1
            for sign in (-1, 1):
                r, c = row + sign * dr, col + sign * dc
                while (
                    0 <= r < BOARD_SIZE
                    and 0 <= c < BOARD_SIZE
                    and self.board[r][c] == symbol
                ):
                    count += 1
                    r += sign * dr
                    c += sign * dc
            if count >= 5:
                return True
        return False

    @staticmethod
    def _other(symbol: str) -> str:
        return "O" if symbol == "X" else "X"

    def _copy_board(self) -> list[list[str]]:
        return [row[:] for row in self.board]

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)


def main() -> None:
    root = tk.Tk()
    TicTacToeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
