"""Unit tests for the hand evaluation module."""

import pytest

from src.strategy.hand_evaluator import (
    HandTier,
    classify_hand,
    fold_equity,
    implied_odds,
    minimum_equity_to_call,
    pot_odds,
)


class TestClassifyHand:
    def test_premium_hands(self):
        for hand in ("AA", "KK", "QQ", "AKs"):
            assert classify_hand(hand) == HandTier.PREMIUM

    def test_strong_hands(self):
        for hand in ("JJ", "TT", "AJs", "KQs"):
            assert classify_hand(hand) == HandTier.STRONG

    def test_playable_hands(self):
        assert classify_hand("99") == HandTier.PLAYABLE
        assert classify_hand("JTs") == HandTier.PLAYABLE

    def test_speculative_hands(self):
        assert classify_hand("66") == HandTier.SPECULATIVE
        assert classify_hand("87s") == HandTier.SPECULATIVE

    def test_marginal_hands(self):
        assert classify_hand("22") == HandTier.MARGINAL
        assert classify_hand("T9o") == HandTier.MARGINAL

    def test_trash_fallback(self):
        assert classify_hand("72o") == HandTier.TRASH
        assert classify_hand("83o") == HandTier.TRASH

    def test_unknown_returns_trash(self):
        assert classify_hand("XY") == HandTier.TRASH


class TestPotOdds:
    def test_basic_pot_odds(self):
        result = pot_odds(50.0, 100.0)
        assert abs(result - 1 / 3) < 1e-9

    def test_zero_call(self):
        assert pot_odds(0.0, 100.0) == 0.0

    def test_small_call_large_pot(self):
        result = pot_odds(10.0, 990.0)
        assert result == pytest.approx(0.01, abs=0.001)


class TestImpliedOdds:
    def test_with_future_winnings(self):
        result = implied_odds(50.0, 100.0, 150.0)
        assert result == pytest.approx(50.0 / 300.0)

    def test_zero_future(self):
        result = implied_odds(50.0, 100.0, 0.0)
        assert result == pytest.approx(pot_odds(50.0, 100.0))

    def test_zero_call(self):
        assert implied_odds(0.0, 100.0, 200.0) == 0.0


class TestMinimumEquity:
    def test_matches_pot_odds(self):
        assert minimum_equity_to_call(50.0, 100.0) == pytest.approx(
            pot_odds(50.0, 100.0)
        )


class TestPotOddsEdgeCases:
    def test_negative_call_treated_as_zero(self):
        assert pot_odds(-10.0, 100.0) == 0.0

    def test_very_large_call_approaches_one(self):
        result = pot_odds(10_000.0, 1.0)
        assert result > 0.99

    def test_equal_call_and_pot(self):
        assert pot_odds(100.0, 100.0) == pytest.approx(0.5)


class TestImpliedOddsEdgeCases:
    def test_negative_call(self):
        assert implied_odds(-5.0, 100.0, 50.0) == 0.0

    def test_large_future_winnings_shrink_odds(self):
        normal = implied_odds(50.0, 100.0, 0.0)
        with_future = implied_odds(50.0, 100.0, 500.0)
        assert with_future < normal


class TestFoldEquity:
    def test_always_folds_is_profitable(self):
        ev = fold_equity(100.0, 50.0, 1.0)
        assert ev == pytest.approx(50.0)

    def test_never_folds_loses_shove(self):
        ev = fold_equity(100.0, 50.0, 0.0)
        assert ev == pytest.approx(-100.0)

    def test_breakeven_fold_rate(self):
        ev = fold_equity(100.0, 100.0, 0.5)
        assert ev == pytest.approx(0.0)

    def test_invalid_fold_pct_raises(self):
        with pytest.raises(ValueError):
            fold_equity(100.0, 50.0, 1.5)
