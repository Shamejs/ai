"""A tactical alpha-beta search bot for 15x15 five-in-a-row."""

import time

import bot as base_bot


BOT_NAME = "Gudrais bots"
BOARD_SIZE = base_bot.BOARD_SIZE
EMPTY = base_bot.EMPTY
X, O = base_bot.X, base_bot.O
WIN_SCORE = 1_000_000_000
TIME_LIMIT = 0.78
MAX_DEPTH = 4
ROOT_WIDTH = 9
SEARCH_WIDTH = 6


class _SearchTimeout(Exception):
    pass


def _evaluate(board: list[list[str]], player: str) -> int:
    opponent = O if player == X else X
    own_wins = base_bot._winning_moves(board, player)
    if own_wins:
        return WIN_SCORE

    opponent_wins = base_bot._winning_moves(board, opponent)
    if opponent_wins:
        return -WIN_SCORE // (2 if len(opponent_wins) == 1 else 1)

    own_moves = base_bot._rank_moves(board, player)
    opponent_moves = base_bot._rank_moves(board, opponent)
    own_score = own_moves[0][0] if own_moves else 0
    opponent_score = opponent_moves[0][0] if opponent_moves else 0
    own_threat = own_moves[1][0] if len(own_moves) > 1 else 0
    opponent_threat = opponent_moves[1][0] if len(opponent_moves) > 1 else 0
    return own_score + own_threat // 4 - opponent_score - opponent_threat // 4


def _ordered_moves(
    board: list[list[str]], player: str, width: int
) -> list[tuple[int, int]]:
    opponent = O if player == X else X
    ranked = base_bot._rank_moves(board, player)
    moves = [(row, col) for _, row, col in ranked[:width]]
    for row, col in base_bot._winning_moves(board, opponent):
        if (row, col) not in moves:
            moves.append((row, col))
    return moves


def _search(
    board: list[list[str]],
    player: str,
    depth: int,
    alpha: int,
    beta: int,
    deadline: float,
) -> int:
    if time.perf_counter() >= deadline:
        raise _SearchTimeout

    opponent = O if player == X else X
    if base_bot._winning_moves(board, player):
        return WIN_SCORE

    opponent_wins = base_bot._winning_moves(board, opponent)
    if len(opponent_wins) > 1:
        return -WIN_SCORE
    if depth <= 0:
        return _evaluate(board, player)

    moves = _ordered_moves(board, player, SEARCH_WIDTH)
    if not moves:
        return 0

    best = -WIN_SCORE
    for row, col in moves:
        board[row][col] = player
        try:
            if base_bot._is_winning_move(board, row, col, player):
                score = WIN_SCORE
            else:
                score = -_search(
                    board, opponent, depth - 1, -beta, -alpha, deadline
                )
        finally:
            board[row][col] = EMPTY
        if score > best:
            best = score
        if score > alpha:
            alpha = score
        if alpha >= beta:
            break
    return best


def get_move(board: list[list[str]], player: str) -> tuple[int, int]:
    """Search forcing lines with alpha-beta under the per-move time limit."""
    winning = base_bot._winning_moves(board, player)
    if winning:
        return winning[0]

    opponent = O if player == X else X
    ranked = base_bot._rank_moves(board, player)
    if not ranked:
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if board[row][col] == EMPTY:
                    return row, col
        raise ValueError("No legal moves remain")

    best_move = (ranked[0][1], ranked[0][2])
    root_moves = [(row, col) for _, row, col in ranked[:ROOT_WIDTH]]
    for move in base_bot._winning_moves(board, opponent):
        if move not in root_moves:
            root_moves.append(move)

    deadline = time.perf_counter() + TIME_LIMIT
    for depth in range(1, MAX_DEPTH + 1):
        depth_best_move = best_move
        depth_best_score = -WIN_SCORE
        alpha = -WIN_SCORE
        try:
            for row, col in root_moves:
                if time.perf_counter() >= deadline:
                    raise _SearchTimeout
                board[row][col] = player
                try:
                    if base_bot._is_winning_move(board, row, col, player):
                        score = WIN_SCORE
                    else:
                        score = -_search(
                            board,
                            opponent,
                            depth - 1,
                            -WIN_SCORE,
                            -alpha,
                            deadline,
                        )
                finally:
                    board[row][col] = EMPTY
                if score > depth_best_score:
                    depth_best_score = score
                    depth_best_move = (row, col)
                if score > alpha:
                    alpha = score
        except _SearchTimeout:
            break
        best_move = depth_best_move

    return best_move


swap2_propose = base_bot.swap2_propose
swap2_respond = base_bot.swap2_respond
swap2_final_choice = base_bot.swap2_final_choice
