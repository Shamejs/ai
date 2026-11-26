"""Blackjack rules engine used by the local visual demo."""

from __future__ import annotations

import random
from dataclasses import dataclass

from bot import hand_value

SUITS = ("H", "D", "C", "S")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
DECK_COUNT = 4
RESHUFFLE_AT = 52


@dataclass
class PlayerHand:
    cards: list[str]
    bet: int
    from_split: bool = False
    split_aces: bool = False
    finished: bool = False


def create_shoe(rng: random.Random | None = None) -> list[str]:
    """Create and shuffle the four-deck shoe from the assignment rules."""
    shoe = [
        f"{rank}{suit}"
        for _ in range(DECK_COUNT)
        for suit in SUITS
        for rank in RANKS
    ]
    (rng or random.Random()).shuffle(shoe)
    return shoe


def draw_card(shoe: list[str]) -> str:
    if not shoe:
        raise RuntimeError("The shoe is empty; shuffle a new shoe before dealing.")
    return shoe.pop()


def is_natural(hand: list[str]) -> bool:
    return len(hand) == 2 and hand_value(hand) == 21


def dealer_should_hit(hand: list[str]) -> bool:
    """The local demo dealer stands on all 17s, including soft 17."""
    return hand_value(hand) < 17


def compare_hands(player: list[str], dealer: list[str]) -> str:
    """Return 'win', 'loss', or 'push' for a completed non-natural hand."""
    player_total = hand_value(player)
    dealer_total = hand_value(dealer)

    if player_total > 21:
        return "loss"
    if dealer_total > 21:
        return "win"
    if player_total > dealer_total:
        return "win"
    if player_total < dealer_total:
        return "loss"
    return "push"


def is_pair(hand: list[str]) -> bool:
    return len(hand) == 2 and hand_value([hand[0]]) == hand_value([hand[1]])
