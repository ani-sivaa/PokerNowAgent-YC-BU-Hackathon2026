"""Unit tests for position-based opening ranges."""

from src.strategy.hand_evaluator import HandTier
from src.strategy.position import (
    OPENING_RANGE,
    Position,
    can_open,
    is_steal_position,
    position_from_seat_index,
    should_defend_bb,
    should_three_bet,
)


class TestCanOpen:
    def test_utg_only_premium(self):
        assert can_open(Position.UTG, HandTier.PREMIUM)
        assert not can_open(Position.UTG, HandTier.STRONG)

    def test_button_opens_wide(self):
        for tier in (HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE,
                     HandTier.SPECULATIVE, HandTier.MARGINAL):
            assert can_open(Position.BTN, tier)

    def test_trash_never_opened(self):
        for pos in Position:
            assert not can_open(pos, HandTier.TRASH)


class TestStealPositions:
    def test_steal_seats(self):
        assert is_steal_position(Position.CO)
        assert is_steal_position(Position.BTN)
        assert is_steal_position(Position.SB)

    def test_non_steal(self):
        assert not is_steal_position(Position.UTG)
        assert not is_steal_position(Position.BB)


class TestThreeBet:
    def test_premium_three_bets(self):
        assert should_three_bet(HandTier.PREMIUM)

    def test_playable_does_not(self):
        assert not should_three_bet(HandTier.PLAYABLE)


class TestPositionFromSeat:
    def test_heads_up(self):
        pos = position_from_seat_index(0, 2, dealer=1)
        assert pos in (Position.SB, Position.BB)

    def test_full_table_dealer(self):
        pos = position_from_seat_index(1, 8, dealer=0)
        assert pos == Position.UTG

    def test_three_handed(self):
        pos = position_from_seat_index(1, 3, dealer=0)
        assert pos in (Position.BTN, Position.SB, Position.BB)

    def test_all_positions_mapped(self):
        for n in range(2, 10):
            for seat in range(n):
                pos = position_from_seat_index(seat, n, dealer=0)
                assert isinstance(pos, Position)

    def test_nine_player_has_utg1(self):
        positions = [
            position_from_seat_index(seat, 9, dealer=0) for seat in range(9)
        ]
        assert Position.UTG1 in positions

    def test_different_dealer_rotates_positions(self):
        pos_d0 = position_from_seat_index(0, 6, dealer=0)
        pos_d1 = position_from_seat_index(0, 6, dealer=1)
        assert pos_d0 != pos_d1

    def test_wraparound_seat(self):
        pos = position_from_seat_index(7, 8, dealer=6)
        assert isinstance(pos, Position)


class TestBBDefense:
    def test_defend_vs_button_steal(self):
        assert should_defend_bb(HandTier.MARGINAL, Position.BTN)
        assert should_defend_bb(HandTier.SPECULATIVE, Position.CO)

    def test_tighter_vs_early_position(self):
        assert not should_defend_bb(HandTier.MARGINAL, Position.UTG)
        assert should_defend_bb(HandTier.PLAYABLE, Position.UTG)

    def test_always_defend_premium(self):
        for pos in Position:
            assert should_defend_bb(HandTier.PREMIUM, pos)

    def test_trash_never_defended(self):
        assert not should_defend_bb(HandTier.TRASH, Position.BTN)
