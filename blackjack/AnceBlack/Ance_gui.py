"""Tkinter blackjack game: play at a shared table with the AnceBlack bot."""

from __future__ import annotations

import argparse
import random
import tkinter as tk
from collections.abc import Callable

from blackjack.AnceBlack.Ance_black import Card, Hand, Shoe
from AnceBlack.bot import BOT_NAME, place_bet
from play import (
    MAX_BET,
    MIN_BET,
    STARTING_BANKROLL,
    Player,
    WageredHand,
    _can_split,
    _draw_visible,
    _play_bot_turn,
    _reveal_hole_card,
    _settle_player,
    _split_hand,
)

TABLE_GREEN = "#0b573d"
CARD_WIDTH = 66
CARD_HEIGHT = 90
CARD_GAP = 10
RED_SUITS = frozenset(("♥", "♦"))


def validate_bet(raw_bet: str, bankroll: int) -> int:
    """Return a valid table wager or raise ValueError with a user-facing reason."""
    try:
        bet = int(raw_bet)
    except ValueError:
        raise ValueError("Likmei jābūt veselam skaitlim.") from None

    maximum = min(MAX_BET, bankroll)
    if not MIN_BET <= bet <= maximum or bet % MIN_BET:
        raise ValueError(
            f"Likmei jābūt no {MIN_BET} līdz {maximum} ar soli {MIN_BET}."
        )
    return bet


class BlackjackApp:
    def __init__(self, root: tk.Tk, seed: int | None = None) -> None:
        self.root = root
        self.root.title("Blackjack — Tu pret botu")
        self.root.configure(bg=TABLE_GREEN)
        self.root.minsize(900, 760)

        self.shoe = Shoe(num_decks=4, rng=random.Random(seed))
        self.history: list[str] = []
        self.human = Player("Tu")
        self.bot = Player(BOT_NAME)
        self.round_number = 0
        self.in_round = False
        self.current_hand_index = 0
        self.dealer_upcard: Card | None = None
        self.hole_card: Card | None = None
        self.dealer_hand: Hand | None = None
        self.dealer_revealed = False

        self.bet_var = tk.StringVar(value=str(MIN_BET))
        self.status_var = tk.StringVar(
            value="Ievadi likmi un sāc raundu. Tu un bots spēlējat pret dīleri."
        )
        self.balance_var = tk.StringVar()

        self._build_ui()
        self._render()
        self._log("Kopīga četru kavu kurpe; pārjaukšana pēc aptuveni 75%.")
        self._log("Dīleris stāv pie 17, ieskaitot soft 17. Blackjack maksā 3:2.")

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=TABLE_GREEN, padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(
            header,
            text="BLACKJACK",
            font=("Segoe UI", 24, "bold"),
            fg="#f7f4e8",
            bg=TABLE_GREEN,
        ).pack(side="left")
        tk.Label(
            header,
            textvariable=self.balance_var,
            font=("Segoe UI", 12, "bold"),
            fg="#f4d35e",
            bg=TABLE_GREEN,
        ).pack(side="right", padx=8)

        self.table = tk.Canvas(
            self.root,
            width=1000,
            height=750,
            bg=TABLE_GREEN,
            highlightthickness=0,
        )
        self.table.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
            fg="#fff5c3",
            bg=TABLE_GREEN,
            anchor="w",
            padx=24,
            pady=6,
        ).pack(fill="x")

        controls = tk.Frame(self.root, bg=TABLE_GREEN, padx=20, pady=10)
        controls.pack(fill="x")

        tk.Label(
            controls,
            text="Tava likme:",
            font=("Segoe UI", 11),
            fg="white",
            bg=TABLE_GREEN,
        ).pack(side="left", padx=(0, 6))
        self.bet_entry = tk.Spinbox(
            controls,
            from_=MIN_BET,
            to=MAX_BET,
            increment=MIN_BET,
            textvariable=self.bet_var,
            width=7,
            font=("Segoe UI", 11),
        )
        self.bet_entry.pack(side="left", padx=(0, 12))

        self.start_button = self._button(controls, "Sākt raundu", self._start_round)
        self.hit_button = self._button(controls, "Ņemt kārti", self._hit)
        self.stand_button = self._button(controls, "Palikt", self._stand)
        self.double_button = self._button(controls, "Dubultot", self._double)
        self.split_button = self._button(controls, "Dalīt", self._split)

        log_frame = tk.Frame(self.root, bg=TABLE_GREEN, padx=20)
        log_frame.pack(fill="x", pady=(0, 12))
        self.log_text = tk.Text(
            log_frame,
            height=6,
            wrap="word",
            state="disabled",
            bg="#073b2a",
            fg="#f4f4e9",
            insertbackground="white",
            font=("Segoe UI", 9),
            relief="flat",
        )
        self.log_text.pack(fill="x")

    @staticmethod
    def _button(
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg="#f4d35e",
            fg="#17382b",
            activebackground="#ffe98a",
            relief="flat",
            padx=12,
            pady=7,
            disabledforeground="#777777",
        )
        button.pack(side="left", padx=4)
        return button

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _draw_card(
        self,
        x: int,
        y: int,
        card: Card | None,
        hidden: bool = False,
    ) -> None:
        if hidden:
            self.table.create_rectangle(
                x, y, x + CARD_WIDTH, y + CARD_HEIGHT,
                fill="#173e64", outline="#e8e4cf", width=2,
            )
            self.table.create_text(
                x + CARD_WIDTH / 2,
                y + CARD_HEIGHT / 2,
                text="?",
                fill="white",
                font=("Segoe UI", 25, "bold"),
            )
            return

        if card is None:
            return
        color = "#c0392b" if card.suit in RED_SUITS else "#20252a"
        self.table.create_rectangle(
            x, y, x + CARD_WIDTH, y + CARD_HEIGHT,
            fill="#f8f6ed", outline="#e8e4cf", width=2,
        )
        self.table.create_text(
            x + 8,
            y + 7,
            text=card.rank,
            fill=color,
            anchor="nw",
            font=("Segoe UI", 12, "bold"),
        )
        self.table.create_text(
            x + CARD_WIDTH / 2,
            y + CARD_HEIGHT / 2 + 6,
            text=card.suit,
            fill=color,
            font=("Segoe UI Symbol", 28, "bold"),
        )

    def _draw_hand(
        self,
        cards: list[Card],
        x: int,
        y: int,
        hidden_second_card: bool = False,
    ) -> None:
        for index, card in enumerate(cards):
            self._draw_card(
                x + index * (CARD_WIDTH + CARD_GAP),
                y,
                card,
                hidden=hidden_second_card and index == 1,
            )

    def _render(self) -> None:
        self.balance_var.set(
            f"Atlikums — Tu: {self.human.bankroll}   |   "
            f"{BOT_NAME}: {self.bot.bankroll}   |   Raunds: {self.round_number}"
        )
        self.table.delete("all")
        bot_rows = max(1, len(self.bot.hands))
        human_y = 190 + bot_rows * 98 + 60
        canvas_height = max(
            750,
            human_y + max(1, len(self.human.hands)) * 98 + 25,
        )
        self.table.configure(height=canvas_height)
        self.table.create_oval(
            12, 12, 988, canvas_height - 12, outline="#73a88c", width=3
        )

        dealer_y = 48
        self.table.create_text(
            34, dealer_y + 18, text="DĪLERIS", fill="white",
            anchor="w", font=("Segoe UI", 12, "bold"),
        )
        if self.dealer_hand is None:
            self.table.create_text(
                34, dealer_y + 48, text="Gatavs izdalīt kārtis",
                fill="#d2e6d9", anchor="w", font=("Segoe UI", 10),
            )
        else:
            self._draw_hand(
                self.dealer_hand.cards,
                225,
                dealer_y,
                hidden_second_card=not self.dealer_revealed,
            )
            shown_total = (
                str(self.dealer_hand.total)
                if self.dealer_revealed
                else str(self.dealer_upcard.value if self.dealer_upcard else "?")
                + " + ?"
            )
            self.table.create_text(
                850, dealer_y + 45, text=f"Punkti: {shown_total}",
                fill="white", anchor="w", font=("Segoe UI", 10, "bold"),
            )

        bot_y = 190
        self.table.create_text(
            34, bot_y + 18, text=BOT_NAME, fill="white",
            anchor="w", font=("Segoe UI", 12, "bold"),
        )
        for index, wagered_hand in enumerate(self.bot.hands):
            row_y = bot_y + index * 98
            self._draw_hand(wagered_hand.hand.cards, 225, row_y)
            self.table.create_text(
                850,
                row_y + 42,
                text=f"{wagered_hand.hand.total} p. | likme {wagered_hand.wager}",
                fill="#e0eee5",
                anchor="w",
                font=("Segoe UI", 10),
            )

        self.table.create_text(
            34, human_y + 18, text="TAVA ROKA", fill="#f4d35e",
            anchor="w", font=("Segoe UI", 12, "bold"),
        )
        for index, wagered_hand in enumerate(self.human.hands):
            row_y = human_y + index * 98
            active = self.in_round and index == self.current_hand_index
            self.table.create_text(
                34,
                row_y + 45,
                text=f"Roka {index + 1}" + (" ▶" if active else ""),
                fill="#f4d35e" if active else "#e0eee5",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            self._draw_hand(wagered_hand.hand.cards, 225, row_y)
            self.table.create_text(
                850,
                row_y + 42,
                text=f"{wagered_hand.hand.total} p. | likme {wagered_hand.wager}",
                fill="#e0eee5",
                anchor="w",
                font=("Segoe UI", 10),
            )

        self._update_controls()

    def _update_controls(self) -> None:
        active = (
            self.in_round
            and self.current_hand_index < len(self.human.hands)
        )
        self.start_button.configure(
            state="disabled" if self.in_round
            or min(self.human.bankroll, self.bot.bankroll) < MIN_BET
            else "normal"
        )
        self.bet_entry.configure(state="disabled" if self.in_round else "normal")
        for button in (self.hit_button, self.stand_button, self.double_button, self.split_button):
            button.configure(state="disabled")
        if not active:
            return

        wagered_hand = self.human.hands[self.current_hand_index]
        self.hit_button.configure(state="normal")
        self.stand_button.configure(state="normal")
        can_double = (
            len(wagered_hand.hand.cards) == 2
            and self.human.bankroll >= wagered_hand.wager
        )
        self.double_button.configure(state="normal" if can_double else "disabled")
        can_split = _can_split(self.human, wagered_hand)
        self.split_button.configure(state="normal" if can_split else "disabled")

    def _start_round(self) -> None:
        if self.in_round:
            return
        if min(self.human.bankroll, self.bot.bankroll) < MIN_BET:
            self.status_var.set("Kādam spēlētājam nepietiek žetonu minimālajai likmei.")
            return
        try:
            human_bet = validate_bet(self.bet_var.get(), self.human.bankroll)
        except ValueError as error:
            self.status_var.set(str(error))
            return

        if self.shoe.prepare_round():
            self.history.clear()
            self._log("Kava pārjaukta pēc aptuveni 75% izspēlēšanas.")

        decks_remaining = max(len(self.shoe.cards) / 52, 0.25)
        bot_bet = place_bet(self.bot.bankroll, self.history, decks_remaining)
        self.human.bankroll -= human_bet
        self.bot.bankroll -= bot_bet
        self.human.hands = [WageredHand(Hand([]), human_bet)]
        self.bot.hands = [WageredHand(Hand([]), bot_bet)]
        self.dealer_upcard = None
        self.dealer_revealed = False

        self.human.hands[0].hand.add(_draw_visible(self.shoe, self.history))
        self.bot.hands[0].hand.add(_draw_visible(self.shoe, self.history))
        dealer_upcard = _draw_visible(self.shoe, self.history)
        self.human.hands[0].hand.add(_draw_visible(self.shoe, self.history))
        self.bot.hands[0].hand.add(_draw_visible(self.shoe, self.history))
        hole_card = self.shoe.draw(visible=False)
        dealer_hand = Hand([dealer_upcard, hole_card])
        self.dealer_upcard = dealer_upcard
        self.hole_card = hole_card
        self.dealer_hand = dealer_hand
        self.round_number += 1
        self.in_round = True
        self.current_hand_index = 0

        self._log(f"Raunds {self.round_number}: tava likme {human_bet}; botam {bot_bet}.")
        dealer_has_natural = dealer_upcard.value in (1, 10) and dealer_hand.is_blackjack
        if dealer_has_natural:
            _reveal_hole_card(hole_card, self.shoe, self.history)
            self.dealer_revealed = True
            self._log(f"Dīlerim ir blackjack: {dealer_hand}.")
            self._settle_round()
            return

        self._continue_human_turn()

    def _continue_human_turn(self) -> None:
        while self.current_hand_index < len(self.human.hands):
            wagered_hand = self.human.hands[self.current_hand_index]
            if (
                wagered_hand.finished
                or wagered_hand.is_natural
                or wagered_hand.hand.is_bust
                or wagered_hand.hand.total >= 21
            ):
                wagered_hand.finished = True
                self.current_hand_index += 1
                continue
            self.status_var.set(
                f"Tavs gājiens — roka {self.current_hand_index + 1}: "
                f"{wagered_hand.hand.total} punkti."
            )
            self._render()
            return

        self._play_bot_and_dealer()

    def _hit(self) -> None:
        wagered_hand = self.human.hands[self.current_hand_index]
        card = _draw_visible(self.shoe, self.history)
        wagered_hand.hand.add(card)
        self._log(f"Tu paņem {card}.")
        if wagered_hand.hand.is_bust or wagered_hand.hand.total >= 21:
            wagered_hand.finished = True
            self.current_hand_index += 1
            self._continue_human_turn()
        else:
            self.status_var.set(f"Rokā {wagered_hand.hand.total} punkti.")
            self._render()

    def _stand(self) -> None:
        wagered_hand = self.human.hands[self.current_hand_index]
        wagered_hand.finished = True
        self._log(f"Tu paliec pie {wagered_hand.hand.total} punktiem.")
        self.current_hand_index += 1
        self._continue_human_turn()

    def _double(self) -> None:
        wagered_hand = self.human.hands[self.current_hand_index]
        if len(wagered_hand.hand.cards) != 2 or self.human.bankroll < wagered_hand.wager:
            return
        self.human.bankroll -= wagered_hand.wager
        wagered_hand.wager *= 2
        card = _draw_visible(self.shoe, self.history)
        wagered_hand.hand.add(card)
        wagered_hand.finished = True
        self._log(f"Tu dubulto un paņem vienu kārti: {card}.")
        self.current_hand_index += 1
        self._continue_human_turn()

    def _split(self) -> None:
        wagered_hand = self.human.hands[self.current_hand_index]
        if not _can_split(self.human, wagered_hand):
            return
        _split_hand(
            self.human,
            self.current_hand_index,
            self.shoe,
            self.history,
        )
        self._log(f"Tu sadali roku {self.current_hand_index + 1}.")
        self._continue_human_turn()

    def _play_bot_and_dealer(self) -> None:
        assert self.dealer_upcard is not None
        assert self.hole_card is not None
        assert self.dealer_hand is not None
        if not self.bot.hands[0].is_natural:
            self._log(f"{BOT_NAME} sāk savu gājienu.")
            _play_bot_turn(
                self.bot,
                self.dealer_upcard,
                self.shoe,
                self.history,
                self._log,
            )

        _reveal_hole_card(self.hole_card, self.shoe, self.history)
        self.dealer_revealed = True
        if any(
            not hand.hand.is_bust and not hand.is_natural
            for player in (self.human, self.bot)
            for hand in player.hands
        ):
            while self.dealer_hand.total < 17:
                card = _draw_visible(self.shoe, self.history)
                self.dealer_hand.add(card)
                self._log(f"Dīleris paņem {card}.")
        self._log(f"Dīlera roka: {self.dealer_hand}.")
        self._settle_round()

    def _settle_round(self) -> None:
        assert self.dealer_hand is not None
        _settle_player(self.human, self.dealer_hand, self._log)
        _settle_player(self.bot, self.dealer_hand, self._log)
        self.in_round = False
        self.status_var.set(
            f"Raunds {self.round_number} pabeigts. Sāc nākamo, kad esi gatavs."
        )
        if min(self.human.bankroll, self.bot.bankroll) < MIN_BET:
            self.status_var.set("Spēle beigusies — kādam spēlētājam nepietiek žetonu.")
        self._render()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tkinter blackjack spēle ar AnceBlack botu.")
    parser.add_argument("--seed", type=int, default=None, help="atkārtojamai kavai")
    args = parser.parse_args()

    root = tk.Tk()
    BlackjackApp(root, seed=args.seed)
    root.mainloop()


if __name__ == "__main__":
    main()
