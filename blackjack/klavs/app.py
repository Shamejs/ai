"""Polished local Blackjack table for testing the official bot callbacks."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from bot import (
    BOT_NAME,
    analyze_bet,
    analyze_decision,
    audit_public_shoe,
    card_value,
    decide_action,
    estimate_true_count,
    hand_value,
    is_early_shuffle,
    place_bet,
    running_count,
)
from game import (
    RESHUFFLE_AT,
    PlayerHand,
    compare_hands,
    create_shoe,
    dealer_should_hit,
    draw_card,
    is_natural,
    is_pair,
)

COLORS = {
    "background": "#0B1110",
    "panel": "#121C19",
    "panel_light": "#192722",
    "felt": "#0B5A43",
    "felt_dark": "#084634",
    "wood": "#57351F",
    "wood_light": "#9B6938",
    "gold": "#D9B66F",
    "navy": "#163C58",
    "text": "#F4F1E8",
    "muted": "#A8B7AE",
    "red": "#C84B50",
    "green": "#54D39A",
    "blue": "#8DB8FF",
    "card": "#F8F6EF",
    "card_ink": "#17221E",
}

SUIT_SYMBOLS = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}


class BlackjackApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Blackjack | klavs_bot")
        self.root.geometry("1180x850")
        self.root.minsize(940, 720)
        self.root.configure(bg=COLORS["background"])

        self.shoe = create_shoe()
        self.history: list[str] = []
        self.player_hands: list[PlayerHand] = []
        self.dealer_hand: list[str] = []
        self.dealer_hole_revealed = False
        self.round_active = False
        self.auto_remaining = 0
        self.auto_after_id: str | None = None
        self.round_number = 0
        self.bankroll = 1000
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self.shuffle_count = 0
        self.early_shuffle_count = 0
        self.active_hand_index = 0
        self.current_bet = 0
        self.last_action = "READY"
        self.last_reason = "The running count starts at zero for a fresh four-deck shoe."
        self.status = "Choose DEAL NEXT HAND or AUTO 10 HANDS to start watching."
        self.log_entries: list[str] = []

        self._configure_styles()
        self._build_layout()
        self._record_event("Fresh four-deck shoe. Running count: +0.")
        self._refresh_analysis()
        self._render_table()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Table.TFrame", background=COLORS["background"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "StatTitle.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
        )
        style.configure(
            "StatValue.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Segoe UI", 17, "bold"),
        )
        style.configure(
            "MetricTitle.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 8, "bold"),
        )
        style.configure(
            "MetricValue.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["gold"],
            font=("Segoe UI", 14, "bold"),
        )
        style.configure(
            "Reason.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["green"],
            foreground="#0C2118",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#78E0AD"), ("disabled", "#53665C")],
            foreground=[("disabled", "#D7D1C0")],
        )
        style.configure(
            "Secondary.TButton",
            background=COLORS["navy"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padding=(10, 8),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#285E7E"), ("disabled", "#26333A")],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Danger.TButton",
            background=COLORS["red"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padding=(10, 8),
            borderwidth=0,
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#E06A6E"), ("disabled", "#6A4849")],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="Table.TFrame", padding=(20, 12, 20, 10))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Table.TFrame")
        header.pack(fill="x", pady=(0, 8))
        title_block = ttk.Frame(header, style="Table.TFrame")
        title_block.pack(side="left", fill="x", expand=True)
        ttk.Label(title_block, text="BLACKJACK", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text=f"AI CARD-COUNTING TABLE  /  {BOT_NAME}",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        self.shoe_label = ttk.Label(header, text="", style="Subtitle.TLabel")
        self.shoe_label.pack(side="right", anchor="e", padx=(12, 0))

        stats = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 7))
        stats.pack(fill="x", pady=(0, 8))
        self.stat_labels: dict[str, ttk.Label] = {}
        stat_items = (
            ("bankroll", "BANKROLL"),
            ("wins", "WINS"),
            ("losses", "LOSSES"),
            ("pushes", "PUSHES"),
        )
        for column, (key, title) in enumerate(stat_items):
            stats.columnconfigure(column, weight=1)
            cell = ttk.Frame(stats, style="Panel.TFrame")
            cell.grid(row=0, column=column, sticky="nsew")
            ttk.Label(cell, text=title, style="StatTitle.TLabel").pack()
            label = ttk.Label(cell, text="0", style="StatValue.TLabel")
            label.pack(pady=(2, 0))
            self.stat_labels[key] = label

        self.canvas = tk.Canvas(
            outer,
            background=COLORS["background"],
            highlightthickness=0,
            height=340,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._render_table())

        analysis = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 6))
        analysis.pack(side="bottom", fill="x", pady=(6, 0))
        self.metric_labels: dict[str, ttk.Label] = {}
        metric_items = (
            ("running", "RUNNING COUNT"),
            ("true", "TRUE COUNT"),
            ("bet", "NEXT BET"),
            ("decision", "BOT DECISION"),
        )
        for column, (key, title) in enumerate(metric_items):
            analysis.columnconfigure(column, weight=1)
            cell = ttk.Frame(analysis, style="Panel.TFrame")
            cell.grid(row=0, column=column, sticky="nsew")
            ttk.Label(cell, text=title, style="MetricTitle.TLabel").pack()
            label = ttk.Label(cell, text="—", style="MetricValue.TLabel")
            label.pack(pady=(2, 0))
            self.metric_labels[key] = label
        self.reason_label = ttk.Label(
            analysis,
            text="",
            style="Reason.TLabel",
            wraplength=950,
            justify="left",
        )
        self.reason_label.grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(5, 0)
        )
        self.audit_label = ttk.Label(
            analysis,
            text="",
            style="Reason.TLabel",
            wraplength=950,
            justify="left",
        )
        self.audit_label.grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(4, 0)
        )
        ttk.Label(
            analysis,
            text="LIVE PLAY LOG",
            style="MetricTitle.TLabel",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(7, 3))
        self.log_text = tk.Text(
            analysis,
            height=3,
            wrap="word",
            state="disabled",
            background=COLORS["panel_light"],
            foreground=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 8),
            padx=8,
            pady=4,
        )
        self.log_text.grid(row=4, column=0, columnspan=3, sticky="nsew")
        log_scrollbar = ttk.Scrollbar(
            analysis,
            orient="vertical",
            command=self.log_text.yview,
        )
        log_scrollbar.grid(row=4, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        analysis.rowconfigure(4, weight=1)

        footer = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 7))
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        self.status_label = ttk.Label(
            footer,
            text=self.status,
            style="Status.TLabel",
            wraplength=1100,
        )
        self.status_label.pack(fill="x", pady=(0, 6))

        buttons = ttk.Frame(footer, style="Panel.TFrame")
        buttons.pack(fill="x")
        self.deal_button = ttk.Button(
            buttons,
            text="DEAL NEXT HAND",
            style="Primary.TButton",
            command=self._start_round,
        )
        self.deal_button.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.auto_button = ttk.Button(
            buttons,
            text="AUTO 10 HANDS",
            style="Secondary.TButton",
            command=self._start_auto,
        )
        self.auto_button.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.stop_button = ttk.Button(
            buttons,
            text="STOP AUTO",
            style="Danger.TButton",
            command=self._stop_auto,
            state="disabled",
        )
        self.stop_button.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.reset_button = ttk.Button(
            buttons,
            text="RESET TABLE",
            style="Secondary.TButton",
            command=self._reset_table,
        )
        self.reset_button.pack(side="left", expand=True, fill="x")

    def _decks_remaining(self) -> float:
        hidden_cards = 1 if self.round_active and not self.dealer_hole_revealed else 0
        return max(0.25, (len(self.shoe) + hidden_cards) / 52.0)

    def _refresh_analysis(self) -> None:
        running = running_count(self.history)
        true = estimate_true_count(self.history, self._decks_remaining())
        bet_insight = analyze_bet(
            self.bankroll,
            self.history,
            self._decks_remaining(),
        )
        self.metric_labels["running"].configure(text=f"{running:+d}")
        self.metric_labels["true"].configure(text=f"{true:+.1f}")
        if self.round_active:
            self.metric_labels["bet"].configure(text=f"{self.current_bet} chips")
        else:
            self.metric_labels["bet"].configure(text=f"{bet_insight.amount} chips")
        self.metric_labels["decision"].configure(text=self.last_action)
        self.reason_label.configure(text=self.last_reason)
        self.audit_label.configure(text=self._shoe_audit_text())
        self.stat_labels["bankroll"].configure(text=f"{self.bankroll} chips")
        self.stat_labels["wins"].configure(text=str(self.wins))
        self.stat_labels["losses"].configure(text=str(self.losses))
        self.stat_labels["pushes"].configure(text=str(self.pushes))
        self.shoe_label.configure(
            text=f"4-DECK SHOE  {len(self.shoe)} / 208   •   HAND {self.round_number}"
        )

    def _shoe_audit_text(self) -> str:
        audit = audit_public_shoe(self.history)
        return (
            f"PUBLIC SHOE AUDIT: {audit}  |  Shuffles: {self.shuffle_count} "
            f"(before 75% dealt: {self.early_shuffle_count}). "
            "This checks visible cards only and does not prove manipulation."
        )

    def _set_status(self, message: str) -> None:
        self.status = message
        self.status_label.configure(text=message)

    def _record_event(self, message: str) -> None:
        self.log_entries.append(message)
        self.log_entries = self.log_entries[-40:]
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(self.log_entries))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _update_controls(self) -> None:
        blocked = self.round_active or self.auto_remaining > 0
        self.deal_button.configure(
            state="disabled" if blocked or self.bankroll < 10 else "normal"
        )
        self.auto_button.configure(
            state="disabled" if blocked or self.bankroll < 10 else "normal"
        )
        self.stop_button.configure(
            state="normal" if self.auto_remaining else "disabled"
        )
        self.reset_button.configure(
            state="disabled" if blocked else "normal"
        )

    def _start_auto(self) -> None:
        if not self.round_active and self.bankroll >= 10:
            self.auto_remaining = 10
            self._start_round()

    def _stop_auto(self) -> None:
        self.auto_remaining = 0
        if self.auto_after_id is not None:
            self.root.after_cancel(self.auto_after_id)
            self.auto_after_id = None
        self._update_controls()
        self._set_status("Auto-play will stop after the current hand.")

    def _start_round(self) -> None:
        if self.round_active:
            return
        if self.bankroll < 10:
            self._set_status("The bankroll is below the 10-chip minimum. Reset the table.")
            return

        if len(self.shoe) <= RESHUFFLE_AT:
            cards_dealt = 208 - len(self.shoe)
            shuffled_early = is_early_shuffle(len(self.shoe))
            self.shuffle_count += 1
            if shuffled_early:
                self.early_shuffle_count += 1
            self.shoe = create_shoe()
            self.history.clear()
            self.last_reason = "Shoe reshuffled: the Hi-Lo running count resets to zero."
            self._record_event(
                f"Shoe reshuffled after {cards_dealt}/208 cards were dealt"
                f"{' (before the 75% threshold)' if shuffled_early else ''}. "
                "Running count reset to +0."
            )

        bet_insight = analyze_bet(
            self.bankroll,
            self.history,
            len(self.shoe) / 52.0,
        )
        bet = place_bet(self.bankroll, self.history, len(self.shoe) / 52.0)
        if bet != bet_insight.amount:
            raise RuntimeError("The betting API and its explanation disagree.")

        self.bankroll -= bet
        self.current_bet = bet
        self.round_number += 1
        player_cards = [draw_card(self.shoe), draw_card(self.shoe)]
        dealer_upcard = draw_card(self.shoe)
        dealer_hole = draw_card(self.shoe)
        self.player_hands = [PlayerHand(player_cards, bet)]
        self.dealer_hand = [dealer_upcard, dealer_hole]
        self.history.extend((player_cards[0], dealer_upcard, player_cards[1]))
        self.dealer_hole_revealed = False
        self.active_hand_index = 0
        self.round_active = True
        self.last_action = "BET"
        self.last_reason = bet_insight.reason
        self._record_event(
            f"Hand {self.round_number}: {BOT_NAME} bets {bet} chips. "
            f"Running {bet_insight.running_count:+d}, true {bet_insight.true_count:+.1f}."
        )
        self._record_event(
            f"Initial deal: {BOT_NAME} gets "
            f"{self._display_card(player_cards[0])}, {self._display_card(player_cards[1])}; "
            f"dealer shows {self._display_card(dealer_upcard)}."
        )
        if self.auto_remaining:
            self.auto_remaining -= 1
        self._set_status(
            f"Hand {self.round_number}: bot bets {bet} chips. Cards are being dealt."
        )
        self._update_controls()
        self._refresh_analysis()
        self._render_table()

        if is_natural(player_cards) or is_natural(self.dealer_hand):
            self.root.after(650, self._settle_naturals)
        else:
            self.root.after(650, self._bot_turn)

    def _settle_naturals(self) -> None:
        self._reveal_dealer_hole()
        player_natural = is_natural(self.player_hands[0].cards)
        dealer_natural = is_natural(self.dealer_hand)
        bet = self.player_hands[0].bet

        if player_natural and dealer_natural:
            self.bankroll += bet
            self.pushes += 1
            result = "push"
            message = "Both sides have Blackjack. The bet is returned."
        elif player_natural:
            self.bankroll += bet * 5 // 2
            self.wins += 1
            result = "win"
            message = "Blackjack! The bot receives the 3:2 payout."
        else:
            self.losses += 1
            result = "loss"
            message = "Dealer has Blackjack. The bot loses this hand."
        self._finish_round(result, message)

    def _bot_turn(self) -> None:
        hand = self.player_hands[self.active_hand_index]
        can_double = len(hand.cards) == 2 and self.bankroll >= hand.bet
        can_split = (
            len(hand.cards) == 2
            and is_pair(hand.cards)
            and self.bankroll >= hand.bet
            and not hand.split_aces
        )
        insight = analyze_decision(
            hand.cards,
            self.dealer_hand[0],
            self.history,
            can_double,
            can_split,
        )
        action = decide_action(
            hand.cards,
            self.dealer_hand[0],
            self.history,
            can_double,
            can_split,
        )
        if action != insight.action:
            raise RuntimeError("The bot action and its explanation disagree.")

        self.last_action = action
        self.last_reason = insight.reason
        visible_hand = ", ".join(self._display_card(card) for card in hand.cards)
        self._record_event(
            f"{BOT_NAME}: {action} with {visible_hand} vs "
            f"{self._display_card(self.dealer_hand[0])}. "
            f"Running {insight.running_count:+d}, true {insight.true_count:+.1f}. "
            f"{insight.reason}"
        )
        self.current_bet = sum(player_hand.bet for player_hand in self.player_hands)
        self._refresh_analysis()
        self._render_table()

        if action == "HIT":
            self._hit(hand)
        elif action == "STAND":
            hand.finished = True
            self._advance_hand()
        elif action == "DOUBLE":
            self.bankroll -= hand.bet
            hand.bet *= 2
            card = draw_card(self.shoe)
            hand.cards.append(card)
            self.history.append(card)
            self._record_event(
                f"{BOT_NAME} doubles and draws {self._display_card(card)}."
            )
            hand.finished = True
            self._set_status(f"Bot doubles, draws {self._display_card(card)}, then stands.")
            self._advance_hand()
        elif action == "SPLIT":
            self._split_active_hand(hand)
        else:
            raise ValueError(f"Unknown bot action: {action!r}")

    def _hit(self, hand: PlayerHand) -> None:
        card = draw_card(self.shoe)
        hand.cards.append(card)
        self.history.append(card)
        total = hand_value(hand.cards)
        self._set_status(f"Bot hits {self._display_card(card)}. Hand total: {total}.")
        self._record_event(
            f"{BOT_NAME} draws {self._display_card(card)}; hand total {total}."
        )
        self._refresh_analysis()
        self._render_table()
        if total > 21:
            hand.finished = True
            self.root.after(450, self._advance_hand)
        else:
            self.root.after(550, self._bot_turn)

    def _split_active_hand(self, hand: PlayerHand) -> None:
        first_card, second_card = hand.cards
        self.bankroll -= hand.bet
        hand.cards = [first_card]
        hand.from_split = True
        second_hand = PlayerHand([second_card], hand.bet, from_split=True)
        self.player_hands.insert(self.active_hand_index + 1, second_hand)

        first_draw = draw_card(self.shoe)
        second_draw = draw_card(self.shoe)
        hand.cards.append(first_draw)
        second_hand.cards.append(second_draw)
        self.history.extend((first_draw, second_draw))
        hand.split_aces = card_value(first_card) == 11
        second_hand.split_aces = hand.split_aces
        if hand.split_aces:
            hand.finished = True
            second_hand.finished = True

        self.last_action = "SPLIT"
        self.last_reason = (
            f"Split pair into two hands. New cards: {self._display_card(first_draw)} "
            f"and {self._display_card(second_draw)}."
        )
        self.current_bet = sum(player_hand.bet for player_hand in self.player_hands)
        self._set_status("Bot splits the pair and plays each hand separately.")
        self._record_event(
            f"{BOT_NAME} splits; new cards are {self._display_card(first_draw)} "
            f"and {self._display_card(second_draw)}."
        )
        self._refresh_analysis()
        self._render_table()
        if hand.split_aces:
            self.root.after(550, self._advance_hand)
        else:
            self.root.after(550, self._bot_turn)

    def _advance_hand(self) -> None:
        for index in range(self.active_hand_index + 1, len(self.player_hands)):
            if not self.player_hands[index].finished:
                self.active_hand_index = index
                self.last_action = "NEXT HAND"
                self.last_reason = "The bot is now evaluating the next split hand."
                self._set_status(f"Playing split hand {index + 1}.")
                self._refresh_analysis()
                self._render_table()
                self.root.after(450, self._bot_turn)
                return

        if all(hand.finished for hand in self.player_hands):
            self.root.after(450, self._dealer_turn)

    def _reveal_dealer_hole(self) -> None:
        if not self.dealer_hole_revealed and len(self.dealer_hand) > 1:
            self.history.append(self.dealer_hand[1])
            self.dealer_hole_revealed = True
            self._record_event(
                f"Dealer reveals {self._display_card(self.dealer_hand[1])}."
            )

    def _dealer_turn(self) -> None:
        self._reveal_dealer_hole()
        if all(hand_value(hand.cards) > 21 for hand in self.player_hands):
            self._settle_hands()
            return
        if dealer_should_hit(self.dealer_hand):
            card = draw_card(self.shoe)
            self.dealer_hand.append(card)
            self.history.append(card)
            self._set_status(
                f"Dealer draws {self._display_card(card)}. "
                f"Dealer total: {hand_value(self.dealer_hand)}."
            )
            self._record_event(
                f"Dealer draws {self._display_card(card)}; "
                f"dealer total {hand_value(self.dealer_hand)}."
            )
            self._refresh_analysis()
            self._render_table()
            self.root.after(550, self._dealer_turn)
            return
        self._settle_hands()

    def _settle_hands(self) -> None:
        results: list[str] = []
        net = 0
        for hand in self.player_hands:
            result = compare_hands(hand.cards, self.dealer_hand)
            if result == "win":
                self.bankroll += hand.bet * 2
                self.wins += 1
                net += hand.bet
            elif result == "push":
                self.bankroll += hand.bet
                self.pushes += 1
            else:
                self.losses += 1
                net -= hand.bet
            results.append(result)

        summary = f"Round complete: {results.count('win')} win, "
        summary += f"{results.count('loss')} loss, {results.count('push')} push."
        if net > 0:
            summary += f" Net +{net} chips."
        elif net < 0:
            summary += f" Net {net} chips."
        else:
            summary += " Even result."
        self._finish_round(" / ".join(results), summary)

    def _finish_round(self, result: str, message: str) -> None:
        self.round_active = False
        self.last_action = f"ROUND {result.upper()}"
        self.last_reason = message
        self.current_bet = 0
        self._record_event(message)
        self._set_status(message)
        self._update_controls()
        self._refresh_analysis()
        self._render_table()
        if self.auto_remaining:
            self.auto_after_id = self.root.after(850, self._continue_auto)

    def _continue_auto(self) -> None:
        self.auto_after_id = None
        if self.auto_remaining and not self.round_active:
            self._start_round()

    def _reset_table(self) -> None:
        if self.round_active:
            return
        if self.auto_after_id is not None:
            self.root.after_cancel(self.auto_after_id)
            self.auto_after_id = None
        self.shoe = create_shoe()
        self.history.clear()
        self.player_hands.clear()
        self.dealer_hand.clear()
        self.dealer_hole_revealed = False
        self.round_number = 0
        self.bankroll = 1000
        self.wins = self.losses = self.pushes = 0
        self.shuffle_count = self.early_shuffle_count = 0
        self.auto_remaining = 0
        self.last_action = "READY"
        self.last_reason = "Fresh shoe: running count reset to zero."
        self.log_entries.clear()
        self._record_event("Fresh four-deck shoe. Running count: +0.")
        self._set_status("Table reset. The bot is ready for a new shoe.")
        self._update_controls()
        self._refresh_analysis()
        self._render_table()

    @staticmethod
    def _display_card(card: str) -> str:
        rank = "10" if card[:-1] == "T" else card[:-1]
        return f"{rank}{SUIT_SYMBOLS[card[-1]]}"

    def _render_table(self) -> None:
        if not hasattr(self, "canvas"):
            return
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 760)
        height = max(canvas.winfo_height(), 300)
        canvas.create_oval(
            15,
            8,
            width - 15,
            height - 8,
            fill=COLORS["wood"],
            outline=COLORS["gold"],
            width=4,
        )
        canvas.create_oval(
            28,
            19,
            width - 28,
            height - 19,
            fill=COLORS["felt"],
            outline=COLORS["wood_light"],
            width=3,
        )
        canvas.create_oval(
            41,
            31,
            width - 41,
            height - 31,
            outline="#177458",
            width=1,
        )
        canvas.create_text(
            width // 2,
            37,
            text="DEALER",
            fill=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        )

        dealer_total = "—"
        if self.dealer_hand:
            visible_cards = (
                self.dealer_hand
                if self.dealer_hole_revealed
                else self.dealer_hand[:1]
            )
            dealer_total = str(hand_value(visible_cards))
        canvas.create_text(
            width - 108,
            38,
            text=f"TOTAL  {dealer_total}",
            fill=COLORS["gold"],
            font=("Segoe UI", 9, "bold"),
        )
        self._draw_cards(
            self.dealer_hand,
            y=58,
            hide_second=bool(self.dealer_hand) and not self.dealer_hole_revealed,
            area_width=width - 150,
            card_height=78,
        )
        self._draw_chip_stack(76, height * 0.30)
        self._draw_chip_stack(width - 110, height * 0.30)

        canvas.create_line(
            width * 0.28,
            height * 0.45,
            width * 0.72,
            height * 0.45,
            fill="#8C7147",
            width=1,
        )
        canvas.create_text(
            width // 2,
            height * 0.41,
            text=f"HI-LO COUNT  {running_count(self.history):+d}",
            fill=COLORS["gold"],
            font=("Segoe UI", 9, "bold"),
        )
        canvas.create_text(
            width // 2,
            height * 0.50,
            text=self.status,
            fill=COLORS["text"],
            font=("Segoe UI", 9),
            width=width - 180,
        )

        if not self.player_hands:
            canvas.create_text(
                width // 2,
                height * 0.68,
                text="DEAL NEXT HAND TO WATCH ONE ROUND",
                fill="#C5D8CD",
                font=("Segoe UI", 10, "bold"),
            )
            canvas.create_text(
                width // 2,
                height * 0.73,
                text="OR START AUTO 10 HANDS",
                fill="#C5D8CD",
                font=("Segoe UI", 8, "bold"),
            )
            canvas.create_oval(
                width // 2 - 62,
                height * 0.79,
                width // 2 + 62,
                height * 0.79 + 30,
                outline=COLORS["gold"],
                width=2,
            )
            canvas.create_text(
                width // 2,
                height * 0.79 + 15,
                text="BOT BET",
                fill=COLORS["gold"],
                font=("Segoe UI", 8, "bold"),
            )
        else:
            available_height = max(92, int(height * 0.40))
            row_height = max(47, available_height // len(self.player_hands))
            card_height = min(72, max(42, row_height - 18))
            for index, hand in enumerate(self.player_hands):
                y = int(height * 0.57) + index * row_height
                active = self.round_active and index == self.active_hand_index
                title_color = COLORS["gold"] if active else "#C5D8CD"
                hand_total = hand_value(hand.cards)
                canvas.create_text(
                    72,
                    y + card_height / 2,
                    text=f"HAND {index + 1}\n{hand_total}  /  {hand.bet}",
                    fill=title_color,
                    font=("Segoe UI", 8, "bold"),
                    justify="center",
                )
                self._draw_cards(
                    hand.cards,
                    y=y,
                    hide_second=False,
                    area_width=width - 230,
                    card_height=card_height,
                    center_x=(width + 105) / 2,
                )

        canvas.create_text(
            width // 2,
            height - 35,
            text="BLACKJACK PAYS 3:2     •     DEALER STANDS ON SOFT 17",
            fill="#E5D2A2",
            font=("Segoe UI", 8, "bold"),
        )

    def _draw_chip_stack(self, x: float, y: float) -> None:
        chip_colors = ("#F2EBDD", "#C84B50", "#244F78")
        for stack, color in enumerate(chip_colors):
            left = x + stack * 12
            for level in range(3):
                top = y - level * 5
                self.canvas.create_oval(
                    left,
                    top,
                    left + 28,
                    top + 12,
                    fill=color,
                    outline="#E5C982",
                    width=1,
                )

    def _draw_cards(
        self,
        cards: list[str],
        y: float,
        hide_second: bool,
        area_width: float,
        card_height: int,
        center_x: float | None = None,
    ) -> None:
        if not cards:
            return
        card_width = max(34, int(card_height * 0.68))
        gap = 9
        total_width = len(cards) * card_width + (len(cards) - 1) * gap
        if total_width > area_width:
            gap = max(2, int((area_width - len(cards) * card_width) / max(1, len(cards) - 1)))
            total_width = len(cards) * card_width + (len(cards) - 1) * gap
        if center_x is None:
            center_x = max(self.canvas.winfo_width(), 760) / 2
        start_x = center_x - total_width / 2
        for index, card in enumerate(cards):
            x = start_x + index * (card_width + gap)
            if hide_second and index == 1:
                self._draw_card_back(x, y, card_width, card_height)
            else:
                self._draw_card(x, y, card, card_width, card_height)

    def _draw_card(
        self,
        x: float,
        y: float,
        card: str,
        width: int,
        height: int,
    ) -> None:
        rank = "10" if card[:-1] == "T" else card[:-1]
        suit = card[-1]
        symbol = SUIT_SYMBOLS[suit]
        color = COLORS["red"] if suit in ("H", "D") else COLORS["card_ink"]
        canvas = self.canvas
        canvas.create_rectangle(
            x + 2, y + 3, x + width + 2, y + height + 3,
            fill="#123E31", outline="",
        )
        canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=COLORS["card"], outline="#D5D1C6", width=1,
        )
        font_size = max(7, int(height * 0.12))
        canvas.create_text(
            x + 7, y + 6, text=f"{rank}\n{symbol}", anchor="nw",
            fill=color, font=("Segoe UI", font_size, "bold"), justify="left",
        )
        canvas.create_text(
            x + width / 2, y + height / 2,
            text=symbol, fill=color,
            font=("Segoe UI Symbol", max(16, int(height * 0.34))),
        )

    def _draw_card_back(
        self,
        x: float,
        y: float,
        width: int,
        height: int,
    ) -> None:
        canvas = self.canvas
        canvas.create_rectangle(
            x + 2, y + 3, x + width + 2, y + height + 3,
            fill="#123E31", outline="",
        )
        canvas.create_rectangle(
            x, y, x + width, y + height,
            fill="#183E67", outline=COLORS["gold"], width=2,
        )
        canvas.create_rectangle(
            x + 5, y + 5, x + width - 5, y + height - 5,
            outline="#8DB8FF", width=1,
        )
        canvas.create_text(
            x + width / 2, y + height / 2,
            text="♠", fill=COLORS["gold"],
            font=("Segoe UI Symbol", max(15, int(height * 0.32))),
        )


def main() -> None:
    root = tk.Tk()
    BlackjackApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
