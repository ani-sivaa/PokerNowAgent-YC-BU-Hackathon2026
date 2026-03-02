"""
Texas Hold'em hand strength evaluation.

Provides a tier-based ranking system for starting hands and utility
functions for pot-odds and implied-odds calculations that the strategy
engine uses to make preflop and postflop decisions.
"""

from __future__ import annotations

from enum import IntEnum


class HandTier(IntEnum):
    """
    Six-tier classification based on expected preflop equity.

    Tier 1 hands are profitable from every position. Tier 6 hands
    should almost never be opened.
    """

    PREMIUM = 1
    STRONG = 2
    PLAYABLE = 3
    SPECULATIVE = 4
    MARGINAL = 5
    TRASH = 6


HAND_TIERS: dict[str, HandTier] = {}

_TIER_DEFINITIONS: dict[HandTier, list[str]] = {
    HandTier.PREMIUM: [
        "AA", "KK", "QQ", "AKs", "AQs", "AKo",
    ],
    HandTier.STRONG: [
        "JJ", "TT", "AJs", "ATs", "KQs", "KJs", "QJs", "AQo", "AJo",
    ],
    HandTier.PLAYABLE: [
        "99", "88", "77",
        "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
        "KTs", "QTs", "JTs", "T9s",
        "ATo", "KQo", "KJo",
    ],
    HandTier.SPECULATIVE: [
        "66", "55", "44",
        "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
        "Q9s", "J9s", "98s", "87s", "76s", "65s", "54s",
        "KTo", "QJo", "JTo",
    ],
    HandTier.MARGINAL: [
        "33", "22",
        "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
        "J8s", "T8s", "97s", "86s", "75s", "64s", "53s",
        "QTo", "J9o", "T9o",
    ],
}

for _tier, _hands in _TIER_DEFINITIONS.items():
    for _hand in _hands:
        HAND_TIERS[_hand] = _tier


def classify_hand(hand: str) -> HandTier:
    """
    Return the tier for a two-card starting hand.

    Accepts formats like "AKs", "AKo", "AA". Hands not found in the
    lookup table are classified as TRASH.
    """
    return HAND_TIERS.get(hand, HandTier.TRASH)


def pot_odds(call_amount: float, pot_size: float) -> float:
    """
    Calculate pot odds as the ratio of call cost to total pot after calling.

    Returns a value between 0 and 1. Compare against estimated hand equity
    to decide whether a call is profitable.
    """
    if call_amount <= 0:
        return 0.0
    total = pot_size + call_amount
    return call_amount / total


def implied_odds(
    call_amount: float, pot_size: float, expected_future_winnings: float
) -> float:
    """
    Extend pot odds with estimated future value.

    Useful for speculative hands (suited connectors, small pairs) where
    the real payoff comes on later streets.
    """
    if call_amount <= 0:
        return 0.0
    total = pot_size + call_amount + expected_future_winnings
    return call_amount / total


def minimum_equity_to_call(call_amount: float, pot_size: float) -> float:
    """Return the minimum hand equity needed for a break-even call."""
    return pot_odds(call_amount, pot_size)


def fold_equity(
    shove_size: float, pot_size: float, villain_fold_pct: float
) -> float:
    """
    Estimate the expected value of a shove considering fold equity.

    Returns the EV in chips. Positive means profitable even if the
    hand has zero showdown equity -- the opponent folds often enough.
    """
    if villain_fold_pct < 0 or villain_fold_pct > 1:
        raise ValueError("villain_fold_pct must be between 0 and 1")
    ev_when_fold = villain_fold_pct * pot_size
    ev_when_call = (1 - villain_fold_pct) * (-shove_size)
    return ev_when_fold + ev_when_call
