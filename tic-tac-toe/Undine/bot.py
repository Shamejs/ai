"""5-rindu Tic-Tac-Toe bota un Swap2 atvērtnes ieviešana."""

from __future__ import annotations

BOT_NAME = "Strategiskais Zirneklis"
SIZE = 15
EMPTY = "_"


def _copy_board(board):
    return [list(row) for row in board]


def _winner(board, row, col, player):
    for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        r, c = row + dr, col + dc
        while 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == player:
            count += 1
            r += dr
            c += dc
        r, c = row - dr, col - dc
        while 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == player:
            count += 1
            r -= dr
            c -= dc
        if count >= 5:
            return True
    return False


def _winning_moves(board, player):
    work = _copy_board(board)
    result = []
    for r in range(SIZE):
        for c in range(SIZE):
            if work[r][c] == EMPTY:
                work[r][c] = player
                if _winner(work, r, c, player):
                    result.append((r, c))
                work[r][c] = EMPTY
    return result


def _line_score(board, row, col, player):
    opponent = "O" if player == "X" else "X"
    score = 0
    for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
        for symbol, weight in ((player, 1), (opponent, 1.35)):
            own = 0
            open_ends = 0
            r, c = row - dr, col - dc
            while 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == symbol:
                own += 1
                r -= dr
                c -= dc
            if 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == EMPTY:
                open_ends += 1
            r, c = row + dr, col + dc
            while 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == symbol:
                own += 1
                r += dr
                c += dc
            if 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == EMPTY:
                open_ends += 1
            if own:
                score += weight * (10 ** max(0, own - 1)) * (1 + open_ends)
    return score + max(0, 30 - abs(row - 7) - abs(col - 7))


def get_move(board, player):
    """Izvēlas nākamo gājienu, vispirms pārbaudot uzvaras un bloķēšanu."""
    if player not in ("X", "O"):
        raise ValueError("player must be 'X' or 'O'")

    work = _copy_board(board)
    opponent = "O" if player == "X" else "X"

    wins = _winning_moves(work, player)
    if wins:
        return wins[0]

    blocks = _winning_moves(work, opponent)
    if blocks:
        return blocks[0]

    best_move = None
    best_score = float("-inf")
    for r in range(SIZE):
        for c in range(SIZE):
            if work[r][c] != EMPTY:
                continue
            work[r][c] = player
            score = _line_score(work, r, c, player)
            work[r][c] = EMPTY
            if score > best_score:
                best_score = score
                best_move = (r, c)

    return best_move if best_move is not None else (7, 7)


def swap2_propose(board):
    """Izveido pieņemamu sākuma pozīciju: divi X un viens O."""
    candidates = [(7, 7), (7, 8), (8, 7), (7, 6), (6, 7), (8, 8), (6, 6), (7, 9), (9, 7)]
    free = [(r, c) for r, c in candidates if board[r][c] == EMPTY]
    if len(free) < 3:
        free = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == EMPTY][:3]
    if len(free) < 3:
        return []
    return [(free[0][0], free[0][1], "X"),
            (free[1][0], free[1][1], "X"),
            (free[2][0], free[2][1], "O")]


def swap2_respond(board):
    """Novērtē atvērtni: ar 2 pret 1 figūrām parasti paņem spēcīgāko krāsu."""
    x_count = sum(value == "X" for row in board for value in row)
    o_count = sum(value == "O" for row in board for value in row)

    for player in ("X", "O"):
        winning = _winning_moves(board, player)
        if winning:
            return {"action": "TAKE_X" if player == "X" else "TAKE_O"}

    if x_count > o_count:
        return {"action": "TAKE_O"}

    # Neitrāla pozīcija: papildina ar vienu X un vienu O, nododot izvēli.
    work = _copy_board(board)
    moves = []
    candidates = [(7, 6), (7, 8), (6, 7), (8, 7), (6, 6), (8, 8), (7, 9), (9, 7)]
    for r, c in candidates:
        if work[r][c] == EMPTY:
            moves.append((r, c, "X" if len(moves) == 0 else "O"))
            if len(moves) == 2:
                break
    if len(moves) != 2:
        moves = []
        for r in range(SIZE):
            for c in range(SIZE):
                if work[r][c] == EMPTY:
                    moves.append((r, c, "X" if len(moves) == 0 else "O"))
                    if len(moves) == 2:
                        break
            if len(moves) == 2:
                break
    return {"action": "PLACE_TWO", "moves": moves}


def swap2_final_choice(board):
    """Pēc PLACE_TWO izvēlas krāsu, kas uzreiz var uzvarēt vai bloķēt uzvaru."""
    for player in ("X", "O"):
        if _winning_moves(board, player):
            return player

    x_score = sum(_line_score(board, r, c, "X") for r in range(SIZE) for c in range(SIZE) if board[r][c] == "X")
    o_score = sum(_line_score(board, r, c, "O") for r in range(SIZE) for c in range(SIZE) if board[r][c] == "O")
    return "X" if x_score >= o_score else "O"
