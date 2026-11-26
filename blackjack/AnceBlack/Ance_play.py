"""Play blackjack at a shared table with the AnceBlack bot."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field
from typing import Callable

from blackjack.AnceBlack.Ance_black import Card, Hand, Shoe
from AnceBlack.bot import BOT_NAME, decide_action, place_bet

STARTING_BANKROLL = 1000
MIN_BET = 10
MAX_BET = 200
MAX_HANDS = 4
SUIT_CODES = {"♥": "H", "♦": "D", "♣": "C", "♠": "S"}


@dataclass
class WageredHand:
    hand: Hand
    wager: int
    natural_eligible: bool = True
    split_aces: bool = False
    finished: bool = False

    @property
    def is_natural(self) -> bool:
        return self.natural_eligible and self.hand.is_blackjack


@dataclass
class Player:
    name: str
    bankroll: int = STARTING_BANKROLL
    hands: list[WageredHand] = field(default_factory=list)


def _card_code(card: Card) -> str:
    rank = "T" if card.rank == "10" else card.rank
    return f"{rank}{SUIT_CODES[card.suit]}"


def _draw_visible(shoe: Shoe, history: list[str]) -> Card:
    card = shoe.draw()
    history.append(_card_code(card))
    return card


def _is_pair(hand: Hand) -> bool:
    return len(hand.cards) == 2 and hand.cards[0].value == hand.cards[1].value


def _can_split(player: Player, wagered_hand: WageredHand) -> bool:
    return (
        len(player.hands) < MAX_HANDS
        and player.bankroll >= wagered_hand.wager
        and not wagered_hand.split_aces
        and _is_pair(wagered_hand.hand)
    )


def calculate_payout(
    wagered_hand: WageredHand,
    dealer_hand: Hand,
) -> int:
    """Return the total amount credited back, including any returned stake."""
    player_hand = wagered_hand.hand
    wager = wagered_hand.wager

    if player_hand.is_bust:
        return 0
    if dealer_hand.is_blackjack:
        return wager if wagered_hand.is_natural else 0
    if wagered_hand.is_natural:
        return wager * 5 // 2
    if dealer_hand.is_bust or player_hand.total > dealer_hand.total:
        return wager * 2
    if player_hand.total == dealer_hand.total:
        return wager
    return 0


def _split_hand(
    player: Player,
    hand_index: int,
    shoe: Shoe,
    history: list[str],
) -> None:
    wagered_hand = player.hands[hand_index]
    first, second = wagered_hand.hand.cards
    split_aces = first.rank == "A" and second.rank == "A"
    player.bankroll -= wagered_hand.wager

    left = WageredHand(Hand([first]), wagered_hand.wager, False, split_aces)
    right = WageredHand(Hand([second]), wagered_hand.wager, False, split_aces)
    left.hand.add(_draw_visible(shoe, history))
    right.hand.add(_draw_visible(shoe, history))
    if split_aces:
        left.finished = True
        right.finished = True
    player.hands[hand_index : hand_index + 1] = [left, right]


def _play_human_turn(
    player: Player,
    dealer_upcard: Card,
    shoe: Shoe,
    history: list[str],
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    hand_index = 0
    while hand_index < len(player.hands):
        wagered_hand = player.hands[hand_index]
        hand = wagered_hand.hand
        if wagered_hand.finished or hand.is_bust or hand.total >= 21:
            wagered_hand.finished = True
            hand_index += 1
            continue

        output_fn(f"\nTava roka: {hand} | Likme: {wagered_hand.wager}")
        output_fn(f"Dīlera atklātā kārts: {dealer_upcard}")
        options = ["HIT", "STAND"]
        can_double = len(hand.cards) == 2 and player.bankroll >= wagered_hand.wager
        can_split = _can_split(player, wagered_hand)
        if can_double:
            options.append("DOUBLE")
        if can_split:
            options.append("SPLIT")
        prompt = f"Izvēlies {', '.join(options)} (H/S/D/P): "

        while True:
            choice = input_fn(prompt).strip().upper()
            actions = {
                "H": "HIT",
                "HIT": "HIT",
                "S": "STAND",
                "STAND": "STAND",
                "D": "DOUBLE",
                "DOUBLE": "DOUBLE",
                "P": "SPLIT",
                "SPLIT": "SPLIT",
            }
            action = actions.get(choice)
            if action in options:
                break
            output_fn("Nederīga izvēle; izvēlies kādu no piedāvātajām darbībām.")

        if action == "HIT":
            hand.add(_draw_visible(shoe, history))
            if hand.is_bust or hand.total >= 21:
                wagered_hand.finished = True
                hand_index += 1
        elif action == "DOUBLE":
            player.bankroll -= wagered_hand.wager
            wagered_hand.wager *= 2
            hand.add(_draw_visible(shoe, history))
            wagered_hand.finished = True
            hand_index += 1
        elif action == "SPLIT":
            _split_hand(player, hand_index, shoe, history)
        else:
            wagered_hand.finished = True
            hand_index += 1


def _play_bot_turn(
    player: Player,
    dealer_upcard: Card,
    shoe: Shoe,
    history: list[str],
    output_fn: Callable[[str], None],
) -> None:
    hand_index = 0
    while hand_index < len(player.hands):
        wagered_hand = player.hands[hand_index]
        hand = wagered_hand.hand
        if wagered_hand.finished or hand.is_bust or hand.total >= 21:
            wagered_hand.finished = True
            hand_index += 1
            continue

        can_double = len(hand.cards) == 2 and player.bankroll >= wagered_hand.wager
        can_split = _can_split(player, wagered_hand)
        action = decide_action(
            [_card_code(card) for card in hand.cards],
            _card_code(dealer_upcard),
            history,
            can_double,
            can_split,
        )
        output_fn(f"{player.name} izvēlas {action} ar roku {hand}.")

        if action == "HIT":
            hand.add(_draw_visible(shoe, history))
            if hand.is_bust or hand.total >= 21:
                wagered_hand.finished = True
                hand_index += 1
        elif action == "DOUBLE" and can_double:
            player.bankroll -= wagered_hand.wager
            wagered_hand.wager *= 2
            hand.add(_draw_visible(shoe, history))
            wagered_hand.finished = True
            hand_index += 1
        elif action == "SPLIT" and can_split:
            _split_hand(player, hand_index, shoe, history)
        else:
            wagered_hand.finished = True
            hand_index += 1


def _reveal_hole_card(
    hole_card: Card,
    shoe: Shoe,
    history: list[str],
) -> None:
    shoe.observe(hole_card)
    history.append(_card_code(hole_card))


def _settle_player(
    player: Player,
    dealer_hand: Hand,
    output_fn: Callable[[str], None],
) -> None:
    for index, wagered_hand in enumerate(player.hands, start=1):
        payout = calculate_payout(wagered_hand, dealer_hand)
        player.bankroll += payout
        if wagered_hand.is_natural and not dealer_hand.is_blackjack:
            result = "Blackjack! Izmaksa 3:2."
        elif wagered_hand.hand.is_bust:
            result = "Pārsniegti 21 punkti; likme zaudēta."
        elif payout > wagered_hand.wager:
            result = "Roka uzvar."
        elif payout == wagered_hand.wager:
            result = "Neizšķirts; likme atgriezta."
        else:
            result = "Dīleris uzvar."
        output_fn(
            f"{player.name}, roka {index}: {wagered_hand.hand}. "
            f"{result} Atgriezts: {payout}."
        )
    output_fn(f"{player.name} atlikums: {player.bankroll} žetoni.")


def _read_bet(
    player: Player,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> int | None:
    maximum = min(MAX_BET, player.bankroll)
    while True:
        raw_bet = input_fn(
            f"Tava likme {MIN_BET}-{maximum} (10 žetonu solis; Enter=10, Q=iziet): "
        ).strip()
        if raw_bet.lower() in ("q", "quit"):
            return None
        if raw_bet == "":
            bet = MIN_BET
        else:
            try:
                bet = int(raw_bet)
            except ValueError:
                output_fn("Ievadi veselu skaitli vai Q.")
                continue
        if MIN_BET <= bet <= maximum and bet % MIN_BET == 0:
            return bet
        output_fn(f"Likmei jābūt no {MIN_BET} līdz {maximum} ar soli {MIN_BET}.")


def _play_round(
    human: Player,
    bot: Player,
    shoe: Shoe,
    history: list[str],
    human_bet: int,
    bot_bet: int,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    human.bankroll -= human_bet
    bot.bankroll -= bot_bet
    human.hands = [WageredHand(Hand([]), human_bet)]
    bot.hands = [WageredHand(Hand([]), bot_bet)]

    human.hands[0].hand.add(_draw_visible(shoe, history))
    bot.hands[0].hand.add(_draw_visible(shoe, history))
    dealer_upcard = _draw_visible(shoe, history)
    human.hands[0].hand.add(_draw_visible(shoe, history))
    bot.hands[0].hand.add(_draw_visible(shoe, history))
    hole_card = shoe.draw(visible=False)
    dealer_hand = Hand([dealer_upcard, hole_card])

    output_fn(f"\nDīlera atklātā kārts: {dealer_upcard}")
    output_fn(f"Tava sākuma roka: {human.hands[0].hand}")
    output_fn(f"{BOT_NAME} sākuma roka: {bot.hands[0].hand}")

    dealer_has_natural = (
        dealer_upcard.value in (1, 10) and dealer_hand.is_blackjack
    )
    if dealer_has_natural:
        _reveal_hole_card(hole_card, shoe, history)
        output_fn(f"Dīlerim ir blackjack: {dealer_hand}.")
    else:
        if not human.hands[0].is_natural:
            _play_human_turn(
                human,
                dealer_upcard,
                shoe,
                history,
                input_fn,
                output_fn,
            )
        if not bot.hands[0].is_natural:
            _play_bot_turn(bot, dealer_upcard, shoe, history, output_fn)

        _reveal_hole_card(hole_card, shoe, history)
        if any(
            not wagered_hand.hand.is_bust and not wagered_hand.is_natural
            for player in (human, bot)
            for wagered_hand in player.hands
        ):
            while dealer_hand.total < 17:
                dealer_hand.add(_draw_visible(shoe, history))
        output_fn(f"Dīlera roka: {dealer_hand}")

    _settle_player(human, dealer_hand, output_fn)
    _settle_player(bot, dealer_hand, output_fn)


def play_game(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    seed: int | None = None,
) -> tuple[int, int]:
    rng = random.Random(seed)
    shoe = Shoe(num_decks=4, rng=rng)
    history: list[str] = []
    human = Player("Tu")
    bot = Player(BOT_NAME)
    round_number = 0

    output_fn("Blackjack: tu un bots spēlējat pret dīleri.")
    output_fn("Katram sākumā ir 1000 žetoni; dīleris stāv pie 17, arī soft 17.")
    output_fn("Likmes ir 10-200, blackjack izmaksā 3:2. Ievadi Q, lai izietu.")

    while human.bankroll >= MIN_BET and bot.bankroll >= MIN_BET:
        if shoe.prepare_round():
            history.clear()
            output_fn("\nKava pārjaukta pēc aptuveni 75% izspēlēšanas.")

        human_bet = _read_bet(human, input_fn, output_fn)
        if human_bet is None:
            break
        decks_remaining = max(len(shoe.cards) / 52, 0.25)
        bot_bet = place_bet(bot.bankroll, history, decks_remaining)
        round_number += 1
        output_fn(f"\nRaunds {round_number}")
        output_fn(f"{BOT_NAME} liek {bot_bet} žetonus.")
        _play_round(
            human,
            bot,
            shoe,
            history,
            human_bet,
            bot_bet,
            input_fn,
            output_fn,
        )

    if human.bankroll < MIN_BET:
        output_fn("Tev vairs nepietiek žetonu minimālajai likmei.")
    if bot.bankroll < MIN_BET:
        output_fn(f"{BOT_NAME} vairs nepietiek žetonu minimālajai likmei.")
    output_fn(
        f"\nSpēle beigusies. Tavs atlikums: {human.bankroll}; "
        f"{BOT_NAME} atlikums: {bot.bankroll}."
    )
    return human.bankroll, bot.bankroll


def main() -> None:
    parser = argparse.ArgumentParser(description="Spēlē blackjack kopā ar AnceBlack botu.")
    parser.add_argument("--seed", type=int, default=None, help="atkārtojamai kavai")
    args = parser.parse_args()
    play_game(seed=args.seed)


if __name__ == "__main__":
    main()
