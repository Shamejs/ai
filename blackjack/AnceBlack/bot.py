"""Tournament bot compatible with blackjack/RULES.md."""

from __future__ import annotations

from math import floor

BOT_NAME: str = "AnceBlackCountBot"

_SUITS = frozenset("H D C S".split())
_RANKS = frozenset(("2", "3", "4", "5", "6", "7", "8", "9", "T", "10", "J", "Q", "K", "A"))
_HIGH_CARDS = frozenset(("10", "T", "J", "Q", "K", "A"))
_LOW_CARDS = frozenset(("2", "3", "4", "5", "6"))


def _rank(card: str) -> str:
    if not isinstance(card, str) or len(card) not in (2, 3):
        raise ValueError(f"Nederīga kārts: {card!r}")
    rank = card[:-1].upper()
    suit = card[-1].upper()
    if suit not in _SUITS or rank not in _RANKS:
        raise ValueError(f"Nederīga kārts: {card!r}")
    return "T" if rank == "10" else rank


def _card_value(rank: str) -> int:
    if rank == "A":
        return 1
    if rank in ("T", "J", "Q", "K"):
        return 10
    return int(rank)


def _running_count(history: list[str]) -> int:
    count = 0
    for card in history:
        rank = _rank(card)
        if rank in _LOW_CARDS:
            count += 1
        elif rank in _HIGH_CARDS:
            count -= 1
    return count


def _true_count(history: list[str], decks_remaining: float) -> float:
    return _running_count(history) / max(decks_remaining, 0.25)


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    """Bet more only when the Hi-Lo true count favors the player."""
    bankroll_limit = min(200, max(10, bankroll))
    true_count = _true_count(history, decks_remaining)
    if true_count < 2:
        bet = 10
    else:
        units = min(20, 2 ** max(0, floor(true_count) - 1))
        bet = 10 * units
    return min(bankroll_limit, bet)


def _hand_state(hand: list[str]) -> tuple[list[str], int, bool]:
    ranks = [_rank(card) for card in hand]
    hard_total = sum(_card_value(rank) for rank in ranks)
    has_ace = "A" in ranks
    soft = has_ace and hard_total + 10 <= 21
    return ranks, hard_total + (10 if soft else 0), soft


def _split_recommended(pair_value: int, dealer_value: int) -> bool:
    if pair_value in (1, 8):
        return True
    if pair_value == 9:
        return dealer_value in (2, 3, 4, 5, 6, 8, 9)
    if pair_value == 7:
        return 2 <= dealer_value <= 7
    if pair_value == 6:
        return 2 <= dealer_value <= 6
    if pair_value == 4:
        return dealer_value in (5, 6)
    if pair_value in (2, 3):
        return 2 <= dealer_value <= 7
    return False


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    """Return a legal basic-strategy action with Hi-Lo count deviations."""
    ranks, total, soft = _hand_state(hand)
    dealer_rank = _rank(dealer_upcard)
    dealer_value = 11 if dealer_rank == "A" else _card_value(dealer_rank)
    true_count = _true_count(history, max(0.25, (208 - len(history)) / 52))
    can_double = can_double and len(ranks) == 2

    if len(ranks) == 2 and can_split:
        first_value = _card_value(ranks[0])
        second_value = _card_value(ranks[1])
        if first_value == second_value and _split_recommended(first_value, dealer_value):
            return "SPLIT"

    if soft:
        if total <= 14:
            if can_double and dealer_value in (5, 6):
                return "DOUBLE"
            return "HIT"
        if total <= 16:
            if can_double and 4 <= dealer_value <= 6:
                return "DOUBLE"
            return "HIT"
        if total == 17:
            if can_double and 3 <= dealer_value <= 6:
                return "DOUBLE"
            return "HIT"
        if total == 18:
            if can_double and 3 <= dealer_value <= 6:
                return "DOUBLE"
            if dealer_value in (9, 10, 11):
                return "HIT"
            return "STAND"
        if total == 19:
            if can_double and dealer_value == 6:
                return "DOUBLE"
            return "STAND"
        return "STAND"

    if total == 16 and dealer_value == 10:
        return "STAND" if true_count >= 0 else "HIT"
    if total == 16 and dealer_value == 11:
        return "STAND" if true_count >= 3 else "HIT"
    if total == 15 and dealer_value == 10:
        return "STAND" if true_count >= 4 else "HIT"
    if total == 12 and dealer_value == 2:
        return "STAND" if true_count >= 3 else "HIT"
    if total == 12 and dealer_value == 3:
        return "STAND" if true_count >= 2 else "HIT"
    if total == 13 and dealer_value == 2 and true_count <= -1:
        return "HIT"

    if can_double and total == 9 and 3 <= dealer_value <= 6:
        return "DOUBLE"
    if can_double and total == 9 and dealer_value == 2 and true_count >= 1:
        return "DOUBLE"
    if can_double and total == 10:
        if 2 <= dealer_value <= 9 or (
            dealer_value in (10, 11) and true_count >= 4
        ):
            return "DOUBLE"
    if can_double and total == 11 and (
        dealer_value <= 10 or (dealer_value == 11 and true_count >= 1)
    ):
        return "DOUBLE"

    if total <= 11:
        return "HIT"
    if total == 12:
        return "STAND" if 4 <= dealer_value <= 6 else "HIT"
    if 13 <= total <= 16:
        return "STAND" if dealer_value <= 6 else "HIT"
    return "STAND"
