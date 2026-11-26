"""Blackjack simulācija ar četru kavu skaitīšanu un sagaidāmās vērtības stratēģiju."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from math import gcd

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
CARD_VALUES = {
    **{str(value): value for value in range(2, 11)},
    "J": 10,
    "Q": 10,
    "K": 10,
    "A": 1,
}
CARD_VALUE_COUNT = 10
DEALER_BUST = 22
DEALER_NATURAL = 23


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return CARD_VALUES[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def _card_counts(cards: list[Card]) -> tuple[int, ...]:
    counts = [0] * CARD_VALUE_COUNT
    for card in cards:
        counts[card.value - 1] += 1
    return tuple(counts)


class Shoe:
    def __init__(
        self,
        num_decks: int = 4,
        *,
        rng: random.Random | None = None,
        cards: list[Card] | None = None,
    ) -> None:
        if num_decks < 1:
            raise ValueError("Kavu skaitam jābūt vismaz 1.")
        self.num_decks = num_decks
        self.rng = rng or random.Random()
        self._custom_cards = cards is not None
        self._template = (
            cards.copy()
            if cards is not None
            else [
                Card(rank, suit)
                for _ in range(num_decks)
                for suit in SUITS
                for rank in RANKS
            ]
        )
        self.shuffle()

    def shuffle(self) -> None:
        self.cards = self._template.copy()
        if not self._custom_cards:
            self.rng.shuffle(self.cards)
        self.cards_dealt = 0
        self.shuffle_after = max(1, int(len(self._template) * 0.75))
        self.unseen_counts = list(_card_counts(self.cards))
        self.running_count = 0

    def prepare_round(self) -> bool:
        if not self._custom_cards and self.cards_dealt >= self.shuffle_after:
            self.shuffle()
            return True
        return False

    @property
    def true_count(self) -> float:
        remaining_decks = max(sum(self.unseen_counts) / 52, 0.25)
        return self.running_count / remaining_decks

    def draw(self, *, visible: bool = True) -> Card:
        if not self.cards:
            raise RuntimeError("Kavā vairs nav kāršu.")
        card = self.cards.pop()
        self.cards_dealt += 1
        if visible:
            self.observe(card)
        return card

    def observe(self, card: Card) -> None:
        index = card.value - 1
        if self.unseen_counts[index] <= 0:
            raise ValueError(f"Kārts {card} jau ir ieskaitīta.")
        self.unseen_counts[index] -= 1
        if card.rank in ("2", "3", "4", "5", "6"):
            self.running_count += 1
        elif card.rank in ("10", "J", "Q", "K", "A"):
            self.running_count -= 1


@dataclass
class Hand:
    cards: list[Card]

    @property
    def total(self) -> int:
        hard_total = sum(card.value for card in self.cards)
        has_usable_ace = any(card.rank == "A" for card in self.cards)
        if has_usable_ace and hard_total + 10 <= 21:
            return hard_total + 10
        return hard_total

    @property
    def is_soft(self) -> bool:
        return (
            any(card.rank == "A" for card in self.cards)
            and sum(card.value for card in self.cards) + 10 <= 21
        )

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total == 21

    @property
    def is_bust(self) -> bool:
        return self.total > 21

    def add(self, card: Card) -> None:
        self.cards.append(card)

    def __str__(self) -> str:
        soft_label = ", mīksta summa" if self.is_soft else ""
        return f"{' '.join(map(str, self.cards))} ({self.total}{soft_label})"


class Outcome(Enum):
    BOT_WIN = "Bots uzvar!"
    DEALER_WIN = "Dīleris uzvar."
    PUSH = "Neizšķirts."


@dataclass(frozen=True)
class Decision:
    action: str
    hit_ev: float
    stand_ev: float


@dataclass(frozen=True)
class RoundResult:
    bot_hand: Hand
    dealer_hand: Hand
    outcome: Outcome
    bot_actions: tuple[str, ...]


def _hand_total(hard_total: int, ace_count: int) -> int:
    if ace_count and hard_total + 10 <= 21:
        return hard_total + 10
    return hard_total


def _normalize_weights(weights: tuple[int, ...]) -> tuple[int, ...]:
    common_divisor = 0
    for weight in weights:
        common_divisor = gcd(common_divisor, weight)
    if common_divisor > 1:
        return tuple(weight // common_divisor for weight in weights)
    return weights


@lru_cache(maxsize=100_000)
def _dealer_finish(
    hard_total: int,
    ace_count: int,
    counts: tuple[int, ...],
) -> tuple[float, ...]:
    total = _hand_total(hard_total, ace_count)
    if total >= 17 or not sum(counts):
        result = [0.0] * (DEALER_BUST + 1)
        result[min(total, DEALER_BUST)] = 1.0
        return tuple(result)

    remaining = sum(counts)
    result = [0.0] * (DEALER_BUST + 1)
    for index, count in enumerate(counts):
        if not count:
            continue
        card_value = index + 1
        next_counts = list(counts)
        next_counts[index] -= 1
        next_hard_total = hard_total + card_value
        next_ace_count = ace_count + (card_value == 1)
        next_total = _hand_total(next_hard_total, next_ace_count)
        if next_total > 21:
            result[DEALER_BUST] += count / remaining
        else:
            continuation = _dealer_finish(
                next_hard_total,
                next_ace_count,
                tuple(next_counts),
            )
            probability = count / remaining
            for terminal, chance in enumerate(continuation):
                result[terminal] += probability * chance
    return tuple(result)


@lru_cache(maxsize=100_000)
def _dealer_distribution(
    upcard_value: int,
    counts: tuple[int, ...],
    hole_weights: tuple[int, ...],
) -> tuple[float, ...]:
    """Aprēķina dīlera iznākumus, ņemot vērā nezināmo bedrītes kārti."""
    weight_total = sum(hole_weights)
    result = [0.0] * (DEALER_NATURAL + 1)
    if not weight_total:
        return tuple(result)

    for index, weight in enumerate(hole_weights):
        if not weight:
            continue
        card_value = index + 1
        next_counts = list(counts)
        next_counts[index] -= 1
        if next_counts[index] < 0:
            continue

        probability = weight / weight_total
        hard_total = upcard_value + card_value
        ace_count = (upcard_value == 1) + (card_value == 1)
        is_natural = (
            (upcard_value == 1 and card_value == 10)
            or (upcard_value == 10 and card_value == 1)
        )
        if is_natural:
            result[DEALER_NATURAL] += probability
            continue

        continuation = _dealer_finish(hard_total, ace_count, tuple(next_counts))
        for terminal, chance in enumerate(continuation):
            result[terminal] += probability * chance
    return tuple(result)


@lru_cache(maxsize=100_000)
def _stand_ev(
    player_total: int,
    upcard_value: int,
    counts: tuple[int, ...],
    hole_weights: tuple[int, ...],
) -> float:
    dealer = _dealer_distribution(upcard_value, counts, hole_weights)
    expected_value = -dealer[DEALER_NATURAL]
    for dealer_total, probability in enumerate(dealer[:DEALER_BUST]):
        if not probability:
            continue
        if dealer_total < player_total:
            expected_value += probability
        elif dealer_total > player_total:
            expected_value -= probability
    expected_value += dealer[DEALER_BUST]
    return expected_value


@lru_cache(maxsize=100_000)
def _action_values(
    hard_total: int,
    ace_count: int,
    upcard_value: int,
    counts: tuple[int, ...],
    hole_weights: tuple[int, ...],
) -> tuple[float, float]:
    total = _hand_total(hard_total, ace_count)
    stand_ev = _stand_ev(total, upcard_value, counts, hole_weights)
    unseen_total = sum(counts)
    weight_total = sum(hole_weights)
    if total >= 21 or unseen_total <= 1 or not weight_total:
        return float("-inf"), stand_ev

    hit_ev = 0.0
    denominator = weight_total * (unseen_total - 1)
    for index, count in enumerate(counts):
        if not count:
            continue
        draw_weight = sum(
            weight * (count - (index == hole_index))
            for hole_index, weight in enumerate(hole_weights)
        )
        if not draw_weight:
            continue

        card_value = index + 1
        next_counts = list(counts)
        next_counts[index] -= 1
        next_weights = tuple(
            weight * (count - (index == hole_index))
            for hole_index, weight in enumerate(hole_weights)
        )
        next_weights = _normalize_weights(next_weights)
        next_hard_total = hard_total + card_value
        next_ace_count = ace_count + (card_value == 1)
        next_total = _hand_total(next_hard_total, next_ace_count)
        value = (
            -1.0
            if next_total > 21
            else _optimal_value(
                next_hard_total,
                next_ace_count,
                upcard_value,
                tuple(next_counts),
                next_weights,
            )
        )
        hit_ev += (draw_weight / denominator) * value
    return hit_ev, stand_ev


@lru_cache(maxsize=100_000)
def _optimal_value(
    hard_total: int,
    ace_count: int,
    upcard_value: int,
    counts: tuple[int, ...],
    hole_weights: tuple[int, ...],
) -> float:
    total = _hand_total(hard_total, ace_count)
    if total > 21:
        return -1.0
    hit_ev, stand_ev = _action_values(
        hard_total,
        ace_count,
        upcard_value,
        counts,
        hole_weights,
    )
    return max(hit_ev, stand_ev)


def choose_action(
    hand: Hand,
    dealer_upcard: Card,
    shoe: Shoe,
    *,
    peeked_no_blackjack: bool,
) -> Decision:
    hard_total = sum(card.value for card in hand.cards)
    ace_count = sum(card.rank == "A" for card in hand.cards)
    upcard_value = dealer_upcard.value
    counts = tuple(shoe.unseen_counts)
    hole_weights = list(counts)

    if peeked_no_blackjack:
        if upcard_value == 1:
            hole_weights[9] = 0
        elif upcard_value == 10:
            hole_weights[0] = 0

    hit_ev, stand_ev = _action_values(
        hard_total,
        ace_count,
        upcard_value,
        counts,
        _normalize_weights(tuple(hole_weights)),
    )
    action = "hit" if hit_ev > stand_ev + 1e-12 else "stand"
    return Decision(action, hit_ev, stand_ev)


def _settle(bot_hand: Hand, dealer_hand: Hand) -> Outcome:
    if bot_hand.is_bust:
        return Outcome.DEALER_WIN
    if dealer_hand.is_bust:
        return Outcome.BOT_WIN
    if bot_hand.is_blackjack and not dealer_hand.is_blackjack:
        return Outcome.BOT_WIN
    if dealer_hand.is_blackjack and not bot_hand.is_blackjack:
        return Outcome.DEALER_WIN
    if bot_hand.total > dealer_hand.total:
        return Outcome.BOT_WIN
    if bot_hand.total < dealer_hand.total:
        return Outcome.DEALER_WIN
    return Outcome.PUSH


def play_round(shoe: Shoe) -> RoundResult:
    bot_hand = Hand([shoe.draw()])
    dealer_upcard = shoe.draw()
    dealer_hand = Hand([dealer_upcard])
    bot_hand.add(shoe.draw())
    dealer_hole = shoe.draw(visible=False)
    dealer_hand.add(dealer_hole)
    bot_actions: list[str] = []
    dealer_can_have_blackjack = dealer_upcard.value in (1, 10)

    if dealer_can_have_blackjack and dealer_hand.is_blackjack:
        shoe.observe(dealer_hole)
        return RoundResult(
            bot_hand,
            dealer_hand,
            _settle(bot_hand, dealer_hand),
            tuple(bot_actions),
        )

    if not bot_hand.is_blackjack:
        while not bot_hand.is_bust and bot_hand.total < 21:
            decision = choose_action(
                bot_hand,
                dealer_upcard,
                shoe,
                peeked_no_blackjack=dealer_can_have_blackjack,
            )
            bot_actions.append(
                f"Hi-Lo {shoe.running_count:+d}, true count "
                f"{shoe.true_count:+.2f}; {decision.action} "
                f"(hit EV {decision.hit_ev:.3f}, stand EV {decision.stand_ev:.3f})"
            )
            if decision.action == "stand":
                break
            bot_hand.add(shoe.draw())

    shoe.observe(dealer_hole)
    if not bot_hand.is_bust and not bot_hand.is_blackjack:
        while dealer_hand.total < 17:
            dealer_hand.add(shoe.draw())

    return RoundResult(
        bot_hand,
        dealer_hand,
        _settle(bot_hand, dealer_hand),
        tuple(bot_actions),
    )


def run_game(rounds: int, seed: int | None = None) -> None:
    rng = random.Random(seed)
    shoe = Shoe(num_decks=4, rng=rng)
    wins = losses = pushes = 0
    print(
        "4 kavas (208 kārtis; pārjaukšana pēc ~75% jeb 156 kārtīm); "
        "Hi-Lo skaitīšana un precīzs "
        "EV hit/stand izvēlei. Tikai hit/stand, dīleris stāv pie 17; "
        "dīleris stāv arī pie mīksta 17."
    )

    for round_number in range(1, rounds + 1):
        if shoe.prepare_round():
            print("\nKava pārjaukta pēc ~75% kāršu izspēlēšanas.")
        result = play_round(shoe)
        print(f"\nRaunds {round_number}")
        print(f"Bots: {result.bot_hand}")
        print(f"Dīleris: {result.dealer_hand}")
        for action in result.bot_actions:
            print(f"Bota skaitījums: {action}")
        print(result.outcome.value)

        if result.outcome is Outcome.BOT_WIN:
            wins += 1
        elif result.outcome is Outcome.DEALER_WIN:
            losses += 1
        else:
            pushes += 1

    print(f"\nRezultāts pēc {rounds} raundiem:")
    print(f"Uzvaras: {wins} | Zaudējumi: {losses} | Neizšķirti: {pushes}")
    print(f"Uzvaru īpatsvars: {wins / rounds:.1%}")
    print("EV izvēle optimizē vidējo iznākumu, bet negarantē uzvaru katrā raundā.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Četru kavu blackjack simulācija ar kāršu skaitīšanas botu."
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="spēlējamo raundu skaits (noklusējums: 10)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="nejaušo skaitļu sākumvērtība atkārtojamam rezultātam",
    )
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds jābūt vismaz 1")
    run_game(args.rounds, args.seed)


if __name__ == "__main__":
    main()