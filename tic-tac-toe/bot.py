"""A self-contained tactical bot for 15x15 five-in-a-row with Swap2."""

import random

BOT_NAME = "Swap2 Tactical"

BOARD_SIZE = 15
EMPTY, X, O = "_", "X", "O"
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
WINDOW_SCORES = (0, 2, 18, 220, 12_000, 1_000_000_000)


def _other(player: str) -> str:
    return O if player == X else X


def _is_winning_move(board: list[list[str]], row: int, col: int, player: str) -> bool:
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (-1, 1):
            r, c = row + sign * dr, col + sign * dc
            while (
                0 <= r < BOARD_SIZE
                and 0 <= c < BOARD_SIZE
                and board[r][c] == player
            ):
                count += 1
                r += sign * dr
                c += sign * dc
        if count >= 5:
            return True
    return False


def _winning_moves(board: list[list[str]], player: str) -> list[tuple[int, int]]:
    return [
        (r, c)
        for r in range(BOARD_SIZE)
        for c in range(BOARD_SIZE)
        if board[r][c] == EMPTY and _is_winning_move(board, r, c, player)
    ]


def _candidate_moves(board: list[list[str]]) -> list[tuple[int, int]]:
    occupied = [
        (r, c)
        for r in range(BOARD_SIZE)
        for c in range(BOARD_SIZE)
        if board[r][c] != EMPTY
    ]
    if not occupied:
        return [(7, 7)]

    candidates = set()
    for r, c in occupied:
        for rr in range(max(0, r - 2), min(BOARD_SIZE, r + 3)):
            for cc in range(max(0, c - 2), min(BOARD_SIZE, c + 3)):
                if board[rr][cc] == EMPTY:
                    candidates.add((rr, cc))
    return list(candidates)


def _move_score(
    board: list[list[str]], row: int, col: int, player: str
) -> int:
    opponent = _other(player)
    score = 0

    for dr, dc in DIRECTIONS:
        for offset in range(5):
            start_r = row - offset * dr
            start_c = col - offset * dc
            end_r = start_r + 4 * dr
            end_c = start_c + 4 * dc
            if not (
                0 <= start_r < BOARD_SIZE
                and 0 <= start_c < BOARD_SIZE
                and 0 <= end_r < BOARD_SIZE
                and 0 <= end_c < BOARD_SIZE
            ):
                continue

            own_count = 1
            opponent_count = 0
            for step in range(5):
                r = start_r + step * dr
                c = start_c + step * dc
                if (r, c) == (row, col):
                    continue
                if board[r][c] == player:
                    own_count += 1
                elif board[r][c] == opponent:
                    opponent_count += 1

            if opponent_count == 0:
                score += WINDOW_SCORES[own_count]
            elif own_count == 1 and opponent_count >= 2:
                score += WINDOW_SCORES[opponent_count] * 4 // 5

    score += 14 - abs(row - 7) - abs(col - 7)
    return score


def _rank_moves(
    board: list[list[str]], player: str
) -> list[tuple[int, int, int]]:
    ranked = [
        (_move_score(board, r, c, player), r, c)
        for r, c in _candidate_moves(board)
    ]
    ranked.sort(key=lambda item: (item[0], -abs(item[1] - 7) - abs(item[2] - 7)), reverse=True)
    return ranked


def _position_strength(board: list[list[str]], player: str) -> int:
    ranked = _rank_moves(board, player)
    return ranked[0][0] if ranked else 0


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    """Choose a legal move, preferring wins, urgent blocks and good lines."""
    winning = _winning_moves(board, player)
    if winning:
        return winning[0]

    blocking = _winning_moves(board, _other(player))
    if blocking:
        return blocking[0]

    ranked = _rank_moves(board, player)
    if ranked:
        return ranked[0][1], ranked[0][2]

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                return r, c
    raise ValueError("No legal moves remain")


def get_move_easy(board: list[list[str]], player: str) -> tuple[int, int]:
    """Choose a winning move or block, otherwise randomize among the five best."""
    winning = _winning_moves(board, player)
    if winning:
        return winning[0]

    blocking = _winning_moves(board, _other(player))
    if blocking:
        return blocking[0]

    ranked = _rank_moves(board, player)
    if ranked:
        _, row, col = random.choice(ranked[:5])
        return row, col

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                return r, c
    raise ValueError("No legal moves remain")


def swap2_propose(board: list[list[str]]) -> list[tuple[int, int, str]]:
    """Propose two X stones and one O stone around the center."""
    return [(7, 7, X), (7, 8, X), (8, 7, O)]


def swap2_respond(board: list[list[str]]) -> dict[str, object]:
    """Take the stronger color, or place two stones when the opening is balanced."""
    x_strength = _position_strength(board, X)
    o_strength = _position_strength(board, O)
    difference = abs(x_strength - o_strength)

    if difference > max(80, max(x_strength, o_strength) // 5):
        return {"action": "TAKE_X" if x_strength > o_strength else "TAKE_O"}

    x_moves = _rank_moves(board, X)
    o_moves = _rank_moves(board, O)
    if not x_moves or not o_moves:
        return {"action": "TAKE_X" if x_strength >= o_strength else "TAKE_O"}

    x_move = (x_moves[0][1], x_moves[0][2])
    o_move = next(
        ((move[1], move[2]) for move in o_moves if (move[1], move[2]) != x_move),
        None,
    )
    if o_move is None:
        return {"action": "TAKE_X" if x_strength >= o_strength else "TAKE_O"}

    return {
        "action": "PLACE_TWO",
        "moves": [(x_move[0], x_move[1], X), (o_move[0], o_move[1], O)],
    }


def swap2_final_choice(board: list[list[str]]) -> str:
    """Choose the color with the strongest available continuation."""
    return X if _position_strength(board, X) >= _position_strength(board, O) else O
