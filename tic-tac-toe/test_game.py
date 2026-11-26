import unittest

from bot import (
    BOT_NAME,
    get_move,
    swap2_propose,
    swap2_respond,
    swap2_final_choice,
)

SIZE = 15
EMPTY = "_"


class TicTacToeBotTests(unittest.TestCase):
    def setUp(self):
        self.board = [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]

    def test_bot_contracts_and_swap2_shape(self):
        proposal = swap2_propose(self.board)
        self.assertEqual(len(proposal), 3)
        self.assertEqual(sum(symbol == "X" for _, _, symbol in proposal), 2)
        self.assertEqual(sum(symbol == "O" for _, _, symbol in proposal), 2 - 1)
        positions = {(r, c) for r, c, _ in proposal}
        self.assertEqual(len(positions), 3)

    def test_propose_does_not_modify_board(self):
        before = [row[:] for row in self.board]
        swap2_propose(self.board)
        self.assertEqual(self.board, before)

    def test_move_does_not_modify_board(self):
        before = [row[:] for row in self.board]
        move = get_move(self.board, "X")
        self.assertEqual(self.board, before)
        self.assertTrue(0 <= move[0] < SIZE)
        self.assertTrue(0 <= move[1] < SIZE)

    def test_get_move_takes_winning_move(self):
        for c in range(4):
            self.board[7][c] = "X"
        move = get_move(self.board, "X")
        self.assertEqual(move, (7, 4))

    def test_get_move_blocks_opponent(self):
        for c in range(4):
            self.board[3][c] = "O"
        move = get_move(self.board, "X")
        self.assertEqual(move, (3, 4))

    def test_swap2_response_formats(self):
        proposal = swap2_propose(self.board)
        for r, c, symbol in proposal:
            self.board[r][c] = symbol
        response = swap2_respond(self.board)
        self.assertIn(response["action"], ("TAKE_X", "TAKE_O", "PLACE_TWO"))
        if response["action"] == "PLACE_TWO":
            self.assertEqual(len(response["moves"]), 2)
            positions = {(r, c) for r, c, _ in response["moves"]}
            self.assertEqual(len(positions), 2)

    def test_final_choice_is_valid(self):
        for r, c, symbol in [(7, 7, "X"), (7, 8, "X"), (8, 7, "O")]:
            self.board[r][c] = symbol
        choice = swap2_final_choice(self.board)
        self.assertIn(choice, ("X", "O"))

    def test_bot_name(self):
        self.assertIsInstance(BOT_NAME, str)
        self.assertTrue(BOT_NAME)


if __name__ == "__main__":
    unittest.main()
