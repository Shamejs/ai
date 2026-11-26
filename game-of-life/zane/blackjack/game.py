import random
import tkinter as tk
from tkinter import messagebox, ttk

import bot


SUITS = ("H", "D", "C", "S")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")


def card_value(card):
    rank = card[:-1]
    if rank in ("T", "J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(cards):
    total = sum(card_value(card) for card in cards)
    aces = sum(card[:-1] == "A" for card in cards)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_soft(cards):
    total = sum(card_value(card) for card in cards)
    aces = sum(card[:-1] == "A" for card in cards)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return aces > 0


def normalized_rank(card):
    rank = card[:-1]
    return "T" if rank in ("T", "J", "Q", "K") else rank


def card_label(card):
    rank = card[:-1]
    suit = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}[card[-1]]
    return f"{rank}{suit}"


class BlackjackGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackjack - cilveks pret ZanesBlackjack")
        self.root.geometry("980x700")
        self.root.configure(bg="#123524")

        self.player_bankroll = 1000
        self.bot_bankroll = 1000
        self.history = []
        self.shoe = []
        self.dealt = 0
        self.player_hands = []
        self.bot_hands = []
        self.dealer = []
        self.current_hand = 0
        self.round_active = False

        self._build_ui()
        self._reset_shoe()
        self.update_status("Izvelies likmi un saki raundu.")

    def _build_ui(self):
        title = tk.Label(
            self.root,
            text="BLACKJACK",
            font=("Segoe UI", 28, "bold"),
            fg="#f4d35e",
            bg="#123524",
        )
        title.pack(pady=(8, 2))

        table = tk.Frame(self.root, bg="#123524")
        table.pack(fill="both", expand=True, padx=20)

        self.dealer_label = tk.Label(
            table, text="DILERIS", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#123524",
        )
        self.dealer_label.pack(pady=(4, 2))
        self.dealer_cards = tk.Frame(table, bg="#123524")
        self.dealer_cards.pack(pady=4)

        info = tk.Frame(table, bg="#123524")
        info.pack(pady=8)
        self.player_money = tk.Label(
            info, text="", font=("Segoe UI", 12), fg="white", bg="#123524"
        )
        self.player_money.grid(row=0, column=0, padx=20)
        self.bot_money = tk.Label(
            info, text="", font=("Segoe UI", 12), fg="white", bg="#123524"
        )
        self.bot_money.grid(row=0, column=1, padx=20)

        self.bot_label = tk.Label(
            table, text=f"{bot.BOT_NAME}", font=("Segoe UI", 14, "bold"),
            fg="#7ee8fa", bg="#123524",
        )
        self.bot_label.pack(pady=(5, 2))
        self.bot_cards = tk.Frame(table, bg="#123524")
        self.bot_cards.pack(pady=4)

        self.player_label = tk.Label(
            table, text="TAVA ROKA", font=("Segoe UI", 14, "bold"),
            fg="white", bg="#123524",
        )
        self.player_label.pack(pady=(5, 2))
        self.player_cards = tk.Frame(table, bg="#123524")
        self.player_cards.pack(pady=4)

        self.status = tk.Label(
            table, text="", font=("Segoe UI", 12),
            fg="#dff3ff", bg="#123524", wraplength=850,
        )
        self.status.pack(pady=8)

        controls = tk.Frame(self.root, bg="#123524")
        controls.pack(pady=8)

        tk.Label(
            controls, text="Likme:", font=("Segoe UI", 11),
            fg="white", bg="#123524",
        ).grid(row=0, column=0, padx=5)
        self.bet_var = tk.StringVar(value="10")
        self.bet_entry = ttk.Spinbox(
            controls, textvariable=self.bet_var, from_=10, to=200,
            increment=10, width=8,
        )
        self.bet_entry.grid(row=0, column=1, padx=5)

        self.bet_button = tk.Button(
            controls, text="Likme un raunds", command=self.start_round,
            font=("Segoe UI", 11, "bold"), width=16, bg="#f4d35e",
        )
        self.bet_button.grid(row=0, column=2, padx=8)

        self.hit_button = tk.Button(
            controls, text="VELT KARTI", command=lambda: self.player_action("HIT"),
            font=("Segoe UI", 11, "bold"), width=12,
        )
        self.stand_button = tk.Button(
            controls, text="STAVET", command=lambda: self.player_action("STAND"),
            font=("Segoe UI", 11, "bold"), width=12,
        )
        self.double_button = tk.Button(
            controls, text="DUBULTOT", command=lambda: self.player_action("DOUBLE"),
            font=("Segoe UI", 11, "bold"), width=12,
        )
        self.split_button = tk.Button(
            controls, text="SADALIT", command=lambda: self.player_action("SPLIT"),
            font=("Segoe UI", 11, "bold"), width=12,
        )
        for column, button in enumerate(
            (self.hit_button, self.stand_button, self.double_button, self.split_button),
            start=3,
        ):
            button.grid(row=0, column=column, padx=4)
        self.disable_actions()
        self.update_bankrolls()

    def update_bankrolls(self):
        self.player_money.config(text=f"Tu: {self.player_bankroll} zetes")
        self.bot_money.config(
            text=f"{bot.BOT_NAME}: {self.bot_bankroll} zetes"
        )

    def update_status(self, text):
        self.status.config(text=text)

    def disable_actions(self):
        for button in (
            self.hit_button,
            self.stand_button,
            self.double_button,
            self.split_button,
        ):
            button.config(state="disabled")

    def enable_actions(self):
        self.hit_button.config(state="normal")
        self.stand_button.config(state="normal")
        hand = self.player_hands[self.current_hand]
        if len(hand["cards"]) == 2 and self.player_bankroll >= hand["bet"]:
            self.double_button.config(state="normal")
        else:
            self.double_button.config(state="disabled")
        if (
            len(hand["cards"]) == 2
            and normalized_rank(hand["cards"][0]) == normalized_rank(hand["cards"][1])
            and self.player_bankroll >= hand["bet"]
            and len(self.player_hands) < 2
        ):
            self.split_button.config(state="normal")
        else:
            self.split_button.config(state="disabled")

    def _reset_shoe(self):
        self.shoe = [rank + suit for _ in range(4) for suit in SUITS for rank in RANKS]
        random.shuffle(self.shoe)
        self.dealt = 0
        self.history = []

    def draw_card(self):
        if self.dealt >= 156 or not self.shoe:
            self._reset_shoe()
            self.update_status("Kurpe jau ir samaisita.")
        card = self.shoe.pop()
        self.dealt += 1
        return card

    def visible_history_card(self, card):
        self.history.append(card)

    def clear_cards(self):
        for frame in (self.dealer_cards, self.bot_cards, self.player_cards):
            for child in frame.winfo_children():
                child.destroy()

    def render_card(self, parent, card, hidden=False):
        text = "?" if hidden else card_label(card)
        label = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 15, "bold"),
            width=5,
            height=3,
            relief="raised",
            bd=2,
            fg="#1a1a1a",
            bg="#e9e9e9" if not hidden else "#6e1a1a",
        )
        label.pack(side="left", padx=5)

    def render_hands(self, hide_dealer_hole=False):
        self.clear_cards()
        for index, card in enumerate(self.dealer):
            self.render_card(
                self.dealer_cards,
                card,
                hidden=(hide_dealer_hole and index == 1),
            )
        if self.dealer:
            dealer_total = hand_value([card for i, card in enumerate(self.dealer) if not (hide_dealer_hole and i == 1)])
            shown = f"Dileris: {dealer_total}" if hide_dealer_hole else f"Dileris: {hand_value(self.dealer)}"
            self.dealer_label.config(text=shown)
        else:
            self.dealer_label.config(text="DILERIS")

        for index, hand in enumerate(self.bot_hands):
            prefix = "  " if index else ""
            frame_label = tk.Label(
                self.bot_cards,
                text=f"{prefix}{bot.BOT_NAME}: {hand_value(hand['cards'])}",
                font=("Segoe UI", 11),
                fg="#7ee8fa",
                bg="#123524",
            )
            frame_label.pack(side="left", padx=8)
            cards_frame = tk.Frame(self.bot_cards, bg="#123524")
            cards_frame.pack(side="left", padx=8)
            for card in hand["cards"]:
                self.render_card(cards_frame, card)

        for index, hand in enumerate(self.player_hands):
            prefix = "ROKA 1" if index == 0 else f"ROKA {index + 1}"
            if len(self.player_hands) > 1:
                prefix += "  " + ("- GAISI" if index == self.current_hand else "")
            frame_label = tk.Label(
                self.player_cards,
                text=f"{prefix}: {hand_value(hand['cards'])} (likme {hand['bet']})",
                font=("Segoe UI", 11),
                fg="#f4d35e" if index == self.current_hand else "white",
                bg="#123524",
            )
            frame_label.pack(side="left", padx=8)
            cards_frame = tk.Frame(self.player_cards, bg="#123524")
            cards_frame.pack(side="left", padx=8)
            for card in hand["cards"]:
                self.render_card(cards_frame, card)
        self.update_bankrolls()

    def start_round(self):
        if self.round_active:
            return
        if self.player_bankroll < 10:
            messagebox.showinfo("Speles beigas", "Tu zaudeji visus zetonus.")
            return

        try:
            player_bet = int(self.bet_var.get())
        except ValueError:
            update_status = "Ievadi veselu likmes skaitli."
            self.update_status(update_status)
            return
        player_bet = max(10, min(200, player_bet, self.player_bankroll))
        self.bet_var.set(str(player_bet))

        if self.bot_bankroll < 10:
            messagebox.showinfo("Speles beigas", f"{bot.BOT_NAME} zaudeja.")
            return

        bot_bet = bot.place_bet(
            self.bot_bankroll,
            list(self.history),
            max(0.5, (208 - self.dealt) / 52),
        )
        bot_bet = max(10, min(200, int(bot_bet), self.bot_bankroll))

        self.player_bankroll -= player_bet
        self.bot_bankroll -= bot_bet
        self.player_hands = [{"cards": [], "bet": player_bet, "doubled": False, "stood": False}]
        self.bot_hands = [{"cards": [], "bet": bot_bet, "doubled": False, "stood": False}]
        self.dealer = []
        self.current_hand = 0
        self.round_active = True
        self.bet_button.config(state="disabled")
        self.bet_entry.config(state="disabled")

        for owner in ("player", "bot", "dealer", "player", "bot", "dealer"):
            card = self.draw_card()
            if owner == "player":
                self.player_hands[0]["cards"].append(card)
                self.visible_history_card(card)
            elif owner == "bot":
                self.bot_hands[0]["cards"].append(card)
                self.visible_history_card(card)
            else:
                self.dealer.append(card)
                if len(self.dealer) == 1:
                    self.visible_history_card(card)

        self.render_hands(hide_dealer_hole=True)
        self.update_status(
            f"Tava likme {player_bet}; {bot.BOT_NAME} likme {bot_bet}. Tavs gajienjs."
        )
        player_blackjack = (
            len(self.player_hands[0]["cards"]) == 2
            and hand_value(self.player_hands[0]["cards"]) == 21
        )
        if player_blackjack:
            self.disable_actions()
            self.update_status(
                f"Tavs blackjack! {bot.BOT_NAME} tagad izlemj savu gajienju."
            )
            self.root.after(350, self.play_bot)
        else:
            self.enable_actions()

    def player_action(self, action):
        if not self.round_active:
            return
        hand = self.player_hands[self.current_hand]

        if action == "HIT":
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
            if hand_value(hand["cards"]) >= 21:
                hand["stood"] = True
                self.next_player_hand()
            else:
                self.render_hands(hide_dealer_hole=True)
                self.enable_actions()
            return

        if action == "DOUBLE":
            if len(hand["cards"]) != 2 or self.player_bankroll < hand["bet"]:
                return
            self.player_bankroll -= hand["bet"]
            hand["bet"] *= 2
            hand["doubled"] = True
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
            hand["stood"] = True
            self.next_player_hand()
            return

        if action == "SPLIT":
            if (
                len(hand["cards"]) == 2
                and normalized_rank(hand["cards"][0]) == normalized_rank(hand["cards"][1])
                and self.player_bankroll >= hand["bet"]
                and len(self.player_hands) < 2
            ):
                self.player_bankroll -= hand["bet"]
                first = {"cards": [hand["cards"][0], self.draw_card()], "bet": hand["bet"], "doubled": False, "stood": False}
                second = {"cards": [hand["cards"][1], self.draw_card()], "bet": hand["bet"], "doubled": False, "stood": False}
                self.visible_history_card(first["cards"][1])
                self.visible_history_card(second["cards"][1])
                self.player_hands = [first, second]
                self.current_hand = 0
                self.render_hands(hide_dealer_hole=True)
                self.enable_actions()
            return

        hand["stood"] = True
        self.next_player_hand()

    def next_player_hand(self):
        self.current_hand += 1
        if self.current_hand >= len(self.player_hands):
            self.disable_actions()
            self.render_hands(hide_dealer_hole=True)
            self.update_status("Bota gajienjs.")
            self.root.after(350, self.play_bot)
        else:
            self.render_hands(hide_dealer_hole=True)
            self.enable_actions()

    def play_bot(self):
        hand = self.bot_hands[0]
        dealer_upcard = self.dealer[0]

        if hand_value(hand["cards"]) == 21:
            self.update_status(f"{bot.BOT_NAME}: blackjack vai 21; dileris atver karti.")
            self.root.after(350, self.play_dealer)
            return

        can_double = len(hand["cards"]) == 2 and self.bot_bankroll >= hand["bet"]
        can_split = (
            len(hand["cards"]) == 2
            and normalized_rank(hand["cards"][0]) == normalized_rank(hand["cards"][1])
            and self.bot_bankroll >= hand["bet"]
        )

        action = bot.decide_action(
            list(hand["cards"]),
            dealer_upcard,
            list(self.history),
            can_double,
            can_split,
        )

        if action == "SPLIT" and can_split:
            self.bot_bankroll -= hand["bet"]
            first_card = hand["cards"][0]
            second_card = hand["cards"][1]
            first_card_new = self.draw_card()
            second_card_new = self.draw_card()
            self.visible_history_card(first_card_new)
            self.visible_history_card(second_card_new)
            self.bot_hands = [
                {"cards": [first_card, first_card_new], "bet": hand["bet"], "doubled": False, "stood": False},
                {"cards": [second_card, second_card_new], "bet": hand["bet"], "doubled": False, "stood": False},
            ]
            self.render_hands(hide_dealer_hole=True)
            self.root.after(350, lambda: self.play_bot_hands(0))
            return

        if action == "DOUBLE" and can_double:
            self.bot_bankroll -= hand["bet"]
            hand["bet"] *= 2
            hand["doubled"] = True
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
            hand["stood"] = True
        elif action == "HIT":
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
            self.render_hands(hide_dealer_hole=True)
            if hand_value(hand["cards"]) < 21:
                self.root.after(350, self.play_bot)
                return

        self.root.after(350, self.play_dealer)

    def play_bot_hands(self, index):
        if index >= len(self.bot_hands):
            self.root.after(350, self.play_dealer)
            return
        hand = self.bot_hands[index]
        dealer_upcard = self.dealer[0]
        can_double = len(hand["cards"]) == 2 and self.bot_bankroll >= hand["bet"]
        action = bot.decide_action(
            list(hand["cards"]),
            dealer_upcard,
            list(self.history),
            can_double,
            False,
        )
        if action == "DOUBLE" and can_double:
            self.bot_bankroll -= hand["bet"]
            hand["bet"] *= 2
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
        elif action == "HIT":
            card = self.draw_card()
            hand["cards"].append(card)
            self.visible_history_card(card)
            self.render_hands(hide_dealer_hole=True)
            if hand_value(hand["cards"]) < 21:
                self.root.after(350, lambda: self.play_bot_hands(index))
                return
        self.root.after(350, lambda: self.play_bot_hands(index + 1))

    def play_dealer(self):
        self.disable_actions()
        while hand_value(self.dealer) < 17:
            card = self.draw_card()
            self.dealer.append(card)
        if is_soft(self.dealer) and hand_value(self.dealer) == 17:
            pass

        if len(self.dealer) == 2:
            self.history.append(self.dealer[1])
        self.render_hands(hide_dealer_hole=False)
        self.settle_round()

    def settle_round(self):
        dealer_total = hand_value(self.dealer)
        dealer_blackjack = len(self.dealer) == 2 and dealer_total == 21
        messages = []

        for hand in self.player_hands:
            player_total = hand_value(hand["cards"])
            player_blackjack = len(hand["cards"]) == 2 and player_total == 21
            bet = hand["bet"]
            if player_total > 21:
                messages.append(f"Spelētāja roka {player_total}: PARSKATS.")
            elif dealer_blackjack and not player_blackjack:
                messages.append("Dilerim blackjack; zaudēts.")
            elif player_blackjack and not dealer_blackjack:
                self.player_bankroll += int(bet * 2.5)
                messages.append(f"Blackjack! Uzvara {int(bet * 1.5)}.")
            elif dealer_total > 21 or player_total > dealer_total:
                self.player_bankroll += bet * 2
                messages.append(f"Roka {player_total}: uzvara.")
            elif player_total == dealer_total:
                self.player_bankroll += bet
                messages.append(f"Roka {player_total}: push.")
            else:
                messages.append(f"Roka {player_total}: zaudējums.")

        bot_dealer_total = dealer_total
        for hand in self.bot_hands:
            bot_total = hand_value(hand["cards"])
            bot_blackjack = len(hand["cards"]) == 2 and bot_total == 21
            bet = hand["bet"]
            if bot_total > 21:
                messages.append(f"{bot.BOT_NAME}: pārskats.")
            elif dealer_blackjack and not bot_blackjack:
                messages.append(f"{bot.BOT_NAME}: zaudēja pret dīlera blackjack.")
            elif bot_blackjack and not dealer_blackjack:
                self.bot_bankroll += int(bet * 2.5)
                messages.append(f"{bot.BOT_NAME}: blackjack.")
            elif bot_dealer_total > 21 or bot_total > bot_dealer_total:
                self.bot_bankroll += bet * 2
                messages.append(f"{bot.BOT_NAME}: uzvara.")
            elif bot_total == bot_dealer_total:
                self.bot_bankroll += bet
                messages.append(f"{bot.BOT_NAME}: push.")
            else:
                messages.append(f"{bot.BOT_NAME}: zaudējums.")

        self.round_active = False
        self.bet_button.config(state="normal")
        self.bet_entry.config(state="normal")
        self.disable_actions()
        self.update_bankrolls()
        self.update_status(" | ".join(messages))

        if self.player_bankroll < 10:
            messagebox.showinfo("Speles beigas", "Tu zaudeji visus zetonus.")
        elif self.bot_bankroll < 10:
            messagebox.showinfo("Speles beigas", f"{bot.BOT_NAME} zaudeja visus zetonus.")


def main():
    root = tk.Tk()
    BlackjackGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
