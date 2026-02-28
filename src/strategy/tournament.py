"""
Tournament stage detection and ICM-aware adjustments.

Tracks where we are in a Sit & Go lifecycle (early / middle / bubble /
in-the-money) and adjusts strategic parameters accordingly. The ICM
model approximates the equity risk premium that makes chip preservation
more valuable than chip accumulation near the payout threshold.
"""

from __future__ import annotations

from enum import Enum, auto

from src.strategy.hand_evaluator import HandTier


class TournamentStage(Enum):
    EARLY = auto()
    MIDDLE = auto()
    BUBBLE = auto()
    IN_THE_MONEY = auto()
    HEADS_UP = auto()


class StackCategory(Enum):
    SHORT = auto()
    MEDIUM = auto()
    BIG = auto()


# Thresholds expressed in big blinds
SHORT_STACK_BB = 10
MEDIUM_STACK_BB = 25

# 8-player SNG: top 3 pay, so bubble is at 4 players
PAID_POSITIONS = 3


def classify_stack(chips: int, big_blind: int) -> StackCategory:
    """Classify a stack relative to the current blind level."""
    bb_count = chips / big_blind if big_blind > 0 else 0
    if bb_count <= SHORT_STACK_BB:
        return StackCategory.SHORT
    if bb_count <= MEDIUM_STACK_BB:
        return StackCategory.MEDIUM
    return StackCategory.BIG


def detect_stage(players_remaining: int) -> TournamentStage:
    """Determine the tournament stage from the number of active players."""
    if players_remaining <= 1:
        return TournamentStage.HEADS_UP
    if players_remaining == 2:
        return TournamentStage.HEADS_UP
    if players_remaining <= PAID_POSITIONS:
        return TournamentStage.IN_THE_MONEY
    if players_remaining == PAID_POSITIONS + 1:
        return TournamentStage.BUBBLE
    if players_remaining >= 7:
        return TournamentStage.EARLY
    return TournamentStage.MIDDLE


# ---- ICM-adjusted opening range modifiers ----
#
# Each stage/stack combination maps to a set of hand tiers the player
# should be willing to open-shove with. Tighter sets reflect higher ICM
# risk premiums (e.g. medium stacks on the bubble fold much wider).

PUSH_FOLD_RANGES: dict[TournamentStage, dict[StackCategory, set[HandTier]]] = {
    TournamentStage.EARLY: {
        StackCategory.SHORT:  {HandTier.PREMIUM, HandTier.STRONG},
        StackCategory.MEDIUM: {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
        StackCategory.BIG:    {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
    },
    TournamentStage.MIDDLE: {
        StackCategory.SHORT:  {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
        StackCategory.MEDIUM: {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
        StackCategory.BIG:    {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
    },
    TournamentStage.BUBBLE: {
        StackCategory.SHORT:  {HandTier.PREMIUM, HandTier.STRONG},
        StackCategory.MEDIUM: {HandTier.PREMIUM},
        StackCategory.BIG:    {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
    },
    TournamentStage.IN_THE_MONEY: {
        StackCategory.SHORT:  {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
        StackCategory.MEDIUM: {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
        StackCategory.BIG:    {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE, HandTier.MARGINAL},
    },
    TournamentStage.HEADS_UP: {
        StackCategory.SHORT:  {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
        StackCategory.MEDIUM: {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE, HandTier.MARGINAL},
        StackCategory.BIG:    {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE, HandTier.MARGINAL},
    },
}

# How much to tighten calling ranges relative to opening ranges on the
# bubble. A multiplier of 1 means "call with the same range as open".
# Lower values force tighter calls.
ICM_CALL_TIGHTNESS: dict[StackCategory, float] = {
    StackCategory.SHORT: 0.50,
    StackCategory.MEDIUM: 0.35,
    StackCategory.BIG: 0.75,
}


def push_fold_tiers(
    stage: TournamentStage, stack: StackCategory
) -> set[HandTier]:
    """Return the set of hand tiers eligible for open-shoving."""
    return PUSH_FOLD_RANGES.get(stage, {}).get(
        stack, {HandTier.PREMIUM, HandTier.STRONG}
    )


def icm_call_adjustment(stack: StackCategory) -> float:
    """
    Return a multiplier (0-1) representing how much to tighten calling ranges.

    Lower values mean the player should demand stronger hands before
    calling an all-in, reflecting the ICM penalty for risking elimination.
    """
    return ICM_CALL_TIGHTNESS.get(stack, 0.5)
