BOT_NAME = "ZanesBlackjack"

# Turnira noteikumi: 4 kavas, dileris apstasjas uz soft 17, blackjack maksā 3:2.
BLACKJACK_PAYS = 1.5
DEALER_HITS_SOFT_17 = False

SOFT_ACTIONS = {
    13: ("HIT", (5, 6)),
    14: ("HIT", (5, 6)),
    15: ("HIT", (4, 6)),
    16: ("HIT", (4, 6)),
    17: ("HIT", (3, 6)),
}

HARD_DOUBLE = {
    9: (3, 6),
    10: (2, 9),
    11: (2, 10),
}

PAIR_ACTIONS = {
    "A": "always",
    "T": "never",
    "9": (2, 6, 8, 9),
    "8": "always",
    "7": (2, 7),
    "6": (2, 6),
    "5": "never",
    "4": (5, 6),
    "3": (2, 7),
    "2": (2, 7),
}


def _hand_value(hand):
    total = 0
    aces = 0
    for card in hand:
        rank = card[:-1]
        if rank == "A":
            aces += 1
            total += 11
        elif rank in ("T", "J", "Q", "K"):
            total += 10
        else:
            total += int(rank)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total, aces > 0


def _dealer_value(card):
    rank = card[:-1]
    if rank in ("T", "J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def _running_count(history):
    count = 0
    for card in history:
        rank = card[:-1]
        if rank in ("2", "3", "4", "5", "6"):
            count += 1
        elif rank in ("T", "J", "Q", "K", "A"):
            count -= 1
    return count


def place_bet(bankroll: int, history: list[str], decks_remaining: float) -> int:
    if bankroll <= 0:
        return 10

    running = _running_count(history)
    decks = max(float(decks_remaining), 0.5)
    true_count = running / decks

    if true_count >= 5:
        bet = 200
    elif true_count >= 4:
        bet = 150
    elif true_count >= 3:
        bet = 100
    elif true_count >= 2:
        bet = 60
    elif true_count >= 1:
        bet = 30
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
    dealer = _dealer_value(dealer_upcard)

    if can_split and len(hand) == 2:
        ranks = []
        for card in hand:
            rank = card[:-1]
            ranks.append("T" if rank in ("J", "Q", "K") else rank)

        if ranks[0] == ranks[1]:
            pair_rule = PAIR_ACTIONS.get(ranks[0])
            split = pair_rule == "always"
            if isinstance(pair_rule, tuple):
                if len(pair_rule) == 4:
                    split = dealer in pair_rule
                else:
                    split = pair_rule[0] <= dealer <= pair_rule[1]
            if split:
                return "SPLIT"

    total, soft = _hand_value(hand)

    if soft:
        soft_rule = SOFT_ACTIONS.get(total)
        if soft_rule is not None:
            fallback, double_range = soft_rule
            if double_range[0] <= dealer <= double_range[1] and can_double:
                return "DOUBLE"
            return fallback
        if total == 18:
            if 3 <= dealer <= 6:
                return "DOUBLE" if can_double else "STAND"
            if dealer in (2, 7, 8):
                return "STAND"
            return "HIT"
        if total >= 19:
            return "STAND"

    if total <= 8:
        return "HIT"
    double_range = HARD_DOUBLE.get(total)
    if double_range is not None:
        if double_range[0] <= dealer <= double_range[1] and can_double:
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