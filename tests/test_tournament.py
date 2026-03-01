"""Unit tests for tournament stage detection and ICM logic."""

from src.strategy.hand_evaluator import HandTier
from src.strategy.tournament import (
    StackCategory,
    TournamentStage,
    classify_stack,
    detect_stage,
    icm_call_adjustment,
    push_fold_tiers,
)


class TestDetectStage:
    def test_early_stage(self):
        assert detect_stage(8) == TournamentStage.EARLY
        assert detect_stage(7) == TournamentStage.EARLY

    def test_middle_stage(self):
        assert detect_stage(6) == TournamentStage.MIDDLE
        assert detect_stage(5) == TournamentStage.MIDDLE

    def test_bubble(self):
        assert detect_stage(4) == TournamentStage.BUBBLE

    def test_in_the_money(self):
        assert detect_stage(3) == TournamentStage.IN_THE_MONEY

    def test_heads_up(self):
        assert detect_stage(2) == TournamentStage.HEADS_UP
        assert detect_stage(1) == TournamentStage.HEADS_UP


class TestClassifyStack:
    def test_short_stack(self):
        assert classify_stack(500, 100) == StackCategory.SHORT

    def test_medium_stack(self):
        assert classify_stack(1500, 100) == StackCategory.MEDIUM

    def test_big_stack(self):
        assert classify_stack(5000, 100) == StackCategory.BIG

    def test_zero_blind(self):
        assert classify_stack(1000, 0) == StackCategory.SHORT


class TestPushFoldTiers:
    def test_bubble_medium_very_tight(self):
        tiers = push_fold_tiers(TournamentStage.BUBBLE, StackCategory.MEDIUM)
        assert tiers == {HandTier.PREMIUM}

    def test_heads_up_big_stack_wide(self):
        tiers = push_fold_tiers(TournamentStage.HEADS_UP, StackCategory.BIG)
        assert HandTier.MARGINAL in tiers

    def test_early_short_conservative(self):
        tiers = push_fold_tiers(TournamentStage.EARLY, StackCategory.SHORT)
        assert tiers == {HandTier.PREMIUM, HandTier.STRONG}

    def test_unknown_stage_defaults(self):
        tiers = push_fold_tiers(TournamentStage.EARLY, StackCategory.SHORT)
        assert len(tiers) >= 2


class TestICMCallAdjustment:
    def test_short_stack_loose(self):
        adj = icm_call_adjustment(StackCategory.SHORT)
        assert adj == 0.50

    def test_medium_tightest(self):
        adj = icm_call_adjustment(StackCategory.MEDIUM)
        assert adj < icm_call_adjustment(StackCategory.SHORT)

    def test_big_stack_loosest(self):
        adj = icm_call_adjustment(StackCategory.BIG)
        assert adj == 0.75
