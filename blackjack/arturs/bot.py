BOT_NAME: str = "Arturs"


def _card_rank(card: str) -> str:
    return card[:-1]


def _rank_value(rank: str) -> int:
    if rank in ("T", "J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def _hand_value(hand: list[str]) -> tuple[int, bool]:
    total = 0
    aces = 0

    for card in hand:
        rank = _card_rank(card)
        if rank == "A":
            aces += 1
            total += 11
        else:
            total += _rank_value(rank)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total, aces > 0


def _dealer_upcard_value(card: str) -> int:
    rank = _card_rank(card)
    if rank == "A":
        return 11
    return _rank_value(rank)


def _pair_rank(hand: list[str]) -> str | None:
    if len(hand) != 2:
        return None

    rank1 = _card_rank(hand[0])
    rank2 = _card_rank(hand[1])
    if rank1 in ("T", "J", "Q", "K"):
        rank1 = "T"
    if rank2 in ("T", "J", "Q", "K"):
        rank2 = "T"

    if rank1 == rank2:
        return rank1
    return None


def place_bet(
    bankroll: int,
    history: list[str],
    decks_remaining: float,
) -> int:
    if bankroll <= 0:
        return 10

    running_count = 0
    for card in history:
        rank = _card_rank(card)
        if rank in ("2", "3", "4", "5", "6"):
            running_count += 1
        elif rank in ("T", "J", "Q", "K", "A"):
            running_count -= 1

    decks = max(float(decks_remaining), 0.5)
    true_count = running_count / decks

    if true_count >= 4:
        bet = 200
    elif true_count >= 3:
        bet = 160
    elif true_count >= 2:
        bet = 100
    elif true_count >= 1:
        bet = 50
    else:
        bet = 10

    maximum = min(200, bankroll)
    return max(10, min(bet, maximum))


def decide_action(
    hand: list[str],
    dealer_upcard: str,
    history: list[str],
    can_double: bool,
    can_split: bool,
) -> str:
    dealer = _dealer_upcard_value(dealer_upcard)

    if can_split:
        pair = _pair_rank(hand)

        if pair == "A" or pair == "8":
            return "SPLIT"
        if pair == "T":
            return "STAND"
        if pair == "9":
            if 2 <= dealer <= 6 or dealer in (8, 9):
                return "SPLIT"
        if pair == "7":
            if 2 <= dealer <= 7:
                return "SPLIT"
        if pair == "6":
            if 2 <= dealer <= 6:
                return "SPLIT"
        if pair == "4":
            if 5 <= dealer <= 6:
                return "SPLIT"
        if pair in ("2", "3"):
            if 2 <= dealer <= 7:
                return "SPLIT"

    total, soft = _hand_value(hand)

    if soft:
        if total <= 17:
            if 3 <= dealer <= 6 and can_double:
                return "DOUBLE"
            return "HIT"
        if total == 18:
            if 3 <= dealer <= 6:
                return "DOUBLE" if can_double else "STAND"
            if dealer in (2, 7, 8):
                return "STAND"
            return "HIT"
        return "STAND"

    if total <= 8:
        return "HIT"
    if total == 9:
        if 3 <= dealer <= 6 and can_double:
            return "DOUBLE"
        return "HIT"
    if total == 10:
        if dealer <= 9 and can_double:
            return "DOUBLE"
        return "HIT"
    if total == 11:
        if dealer <= 10 and can_double:
            return "DOUBLE"
        return "HIT"
    if total == 12:
        if 4 <= dealer <= 6:
            return "STAND"
        return "HIT"
    if 13 <= total <= 16:
        if 2 <= dealer <= 6:
            return "STAND"
        return "HIT"
    return "STAND"


if __name__ == "__main__":
    pass
