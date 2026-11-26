from __future__ import annotations

import random
import unittest
from unittest.mock import Mock

import bot as bot_module
from app import BlackjackApp
from bot import (
    BOT_NAME,
    analyze_bet,
    analyze_decision,
    audit_public_shoe,
    card_value,
    decide_action,
    estimate_true_count,
    hand_value,
    is_early_shuffle,
    place_bet,
    running_count,
)
from game import (
    PlayerHand,
    compare_hands,
    create_shoe,
    dealer_should_hit,
    draw_card,
    is_natural,
    is_pair,
)


class BlackjackBotTests(unittest.TestCase):
    def test_bot_name_matches_assignment_name(self) -> None:
        self.assertEqual(BOT_NAME, "klavs_bot")

    def test_card_format_uses_t_for_ten(self) -> None:
        self.assertEqual(card_value("TH"), 10)
        with self.assertRaises(ValueError):
            card_value("10H")

    def test_hi_lo_count_and_true_count(self) -> None:
        history = ["2H", "6D", "9C", "TS", "AH"]
        self.assertEqual(running_count(history), 0)
        self.assertEqual(estimate_true_count(history, 2.0), 0.0)

        low_cards = [f"{rank}{suit}" for rank in "23456" for suit in "HDCS"]
        self.assertEqual(running_count(low_cards), 20)
        self.assertGreater(estimate_true_count(low_cards), 5.0)

    def test_action_count_uses_inferred_decks_and_hidden_dealer_card(self) -> None:
        initial_deck_count = bot_module._SHOE_DECK_COUNT
        history_before_deal = [
            f"{rank}{suit}"
            for rank in "23456"
            for suit in "HDCS"
        ] + ["7H", "8H", "9H", "TH", "JH", "QH"]

        try:
            analyze_bet(1000, history_before_deal, 1.5)
            self.assertEqual(bot_module._SHOE_DECK_COUNT, 2)

            visible_history = history_before_deal + ["AS", "7D", "6C"]
            expected_decks_remaining = 2 - (len(visible_history) + 1) / 52
            expected_true_count = (
                running_count(visible_history) / expected_decks_remaining
            )
            insight = analyze_decision(
                ["AS", "7D"],
                "6C",
                visible_history,
                can_double=False,
                can_split=False,
            )
            self.assertAlmostEqual(insight.true_count, expected_true_count)
        finally:
            bot_module._SHOE_DECK_COUNT = initial_deck_count

    def test_bet_spread_increases_when_count_is_favorable(self) -> None:
        low_cards = [f"{rank}{suit}" for rank in "23456" for suit in "HDCS"]
        neutral_bet = place_bet(10000, [], 4.0)
        favorable_bet = place_bet(10000, low_cards, 3.6)
        self.assertEqual(neutral_bet, 10)
        self.assertEqual(favorable_bet, 43)
        self.assertLessEqual(place_bet(35, low_cards, 3.6), 35)

    def test_bets_without_estimated_edge_stay_at_minimum(self) -> None:
        self.assertEqual(place_bet(1000, ["TH", "AS"], 4.0), 10)
        self.assertEqual(place_bet(1000, ["2H", "3H"], 4.0), 10)
        self.assertEqual(place_bet(1000, ["2H", "3H", "4H", "5H"], 4.0), 10)

    def test_bankroll_drawdown_reduces_aggressive_bet_limit(self) -> None:
        low_cards = [f"{rank}{suit}" for rank in "23456" for suit in "HDCS"]
        for bankroll, expected_bet in (
            (10000, 43),
            (8000, 35),
            (5000, 21),
            (1000, 10),
            (49, 10),
        ):
            with self.subTest(bankroll=bankroll):
                self.assertEqual(
                    place_bet(bankroll, low_cards, 3.6),
                    expected_bet,
                )
        self.assertIn("estimated edge", analyze_bet(1000, low_cards, 3.6).reason)
        self.assertIn("quarter-Kelly", analyze_bet(1000, low_cards, 3.6).reason)

    def test_public_shoe_audit_flags_extreme_or_impossible_data(self) -> None:
        normal_sample = [
            f"{rank}{suit}"
            for rank in "23456789TJQKA"
            for suit in "HDCS"
        ]
        biased_sample = [
            f"2{suit}"
            for _ in range(4)
            for suit in "HDCS"
        ] + [
            f"{rank}{suit}"
            for rank in "3456789TJQKA"
            for suit in "HDC"
        ]

        self.assertTrue(audit_public_shoe([]).startswith("COLLECTING:"))
        self.assertTrue(audit_public_shoe(normal_sample).startswith("OK:"))
        self.assertTrue(audit_public_shoe(biased_sample).startswith("CHECK:"))
        self.assertTrue(audit_public_shoe(["2H"] * 5).startswith("ALERT:"))
        self.assertTrue(audit_public_shoe(["2H"] * 3, 2).startswith("ALERT:"))
        self.assertTrue(is_early_shuffle(53))
        self.assertFalse(is_early_shuffle(52))
        self.assertTrue(is_early_shuffle(27, deck_count=2))
        self.assertFalse(is_early_shuffle(26, deck_count=2))

    def test_suspicious_shoe_uses_minimum_bet_and_conservative_actions(self) -> None:
        biased_sample = [
            f"2{suit}"
            for _ in range(4)
            for suit in "HDCS"
        ] + [
            f"{rank}{suit}"
            for rank in "3456789TJQKA"
            for suit in "HDC"
        ]

        self.assertEqual(place_bet(1000, biased_sample, 3.0), 10)
        insight = analyze_decision(
            ["TS", "6D"],
            "TH",
            biased_sample,
            can_double=True,
            can_split=False,
        )
        self.assertEqual(insight.action, "HIT")
        self.assertIn("conservative action", insight.reason)
        self.assertEqual(
            decide_action(["TS", "6D"], "6C", biased_sample, False, False),
            "STAND",
        )

    def test_pair_splitting_and_double_decisions(self) -> None:
        self.assertEqual(decide_action(["8S", "8D"], "6C", [], False, True), "SPLIT")
        self.assertEqual(decide_action(["5S", "5D"], "6C", [], True, True), "DOUBLE")
        self.assertEqual(decide_action(["5S", "6D"], "9C", [], True, False), "DOUBLE")

    def test_soft_eighteen_does_not_double_against_dealer_two(self) -> None:
        self.assertEqual(decide_action(["AS", "7D"], "2C", [], True, False), "STAND")
        self.assertEqual(decide_action(["AS", "7D"], "3C", [], True, False), "DOUBLE")
        self.assertEqual(decide_action(["AS", "7D"], "9C", [], True, False), "HIT")

    def test_hi_lo_deviation_is_explained(self) -> None:
        low_cards = [f"{rank}{suit}" for rank in "23456" for suit in "HDCS"]
        insight = analyze_bet(1000, low_cards, 3.6)
        self.assertEqual(insight.running_count, 20)
        self.assertIn("true count", insight.reason)

        decision = analyze_decision(["TS", "6D"], "TH", low_cards, False, False)
        self.assertEqual(decision.action, "STAND")
        self.assertIn("Hi-Lo deviation", decision.reason)

    def test_aces_reduce_to_one_when_hand_would_bust(self) -> None:
        self.assertEqual(hand_value(["AS", "AH", "9C"]), 21)
        self.assertEqual(hand_value(["AS", "9H", "5C"]), 15)

    def test_four_deck_shoe_contains_208_cards(self) -> None:
        shoe = create_shoe(random.Random(7))
        self.assertEqual(len(shoe), 208)
        self.assertEqual(len(set(shoe)), 52)
        self.assertTrue(all(shoe.count(card) == 4 for card in set(shoe)))

    def test_draw_removes_one_card_and_empty_shoe_fails(self) -> None:
        shoe = ["AS"]
        self.assertEqual(draw_card(shoe), "AS")
        self.assertEqual(shoe, [])
        with self.assertRaises(RuntimeError):
            draw_card(shoe)

    def test_natural_dealer_rule_and_pair_detection(self) -> None:
        self.assertTrue(is_natural(["AS", "KH"]))
        self.assertFalse(is_natural(["AS", "7H", "3C"]))
        self.assertFalse(dealer_should_hit(["AS", "6H"]))
        self.assertFalse(dealer_should_hit(["TS", "7D"]))
        self.assertTrue(is_pair(["TS", "KH"]))

    def test_hand_comparison_covers_wins_losses_pushes_and_busts(self) -> None:
        self.assertEqual(compare_hands(["TS", "8D"], ["TH", "7C"]), "win")
        self.assertEqual(compare_hands(["TS", "6D"], ["TH", "7C"]), "loss")
        self.assertEqual(compare_hands(["TS", "7D"], ["TH", "7C"]), "push")
        self.assertEqual(compare_hands(["TS", "8D", "5C"], ["TH", "7C"]), "loss")


class BlackjackAppTests(unittest.TestCase):
    def test_splitting_pair_draws_cards_and_schedules_next_bot_turn(self) -> None:
        app = BlackjackApp.__new__(BlackjackApp)
        hand = PlayerHand(["2D", "2H"], 10)
        app.player_hands = [hand]
        app.active_hand_index = 0
        app.bankroll = 990
        app.shoe = ["3C", "4D"]
        app.history = []
        app.last_action = ""
        app.last_reason = ""
        app.current_bet = 0
        app.root = Mock()
        app._set_status = Mock()
        app._record_event = Mock()
        app._refresh_analysis = Mock()
        app._render_table = Mock()
        app._display_card = lambda card: card

        app._split_active_hand(hand)

        self.assertEqual(
            [item.cards for item in app.player_hands],
            [["2D", "4D"], ["2H", "3C"]],
        )
        self.assertEqual(app.history, ["4D", "3C"])
        self.assertEqual(app.bankroll, 980)
        app.root.after.assert_called_once_with(550, app._bot_turn)


if __name__ == "__main__":
    unittest.main()
