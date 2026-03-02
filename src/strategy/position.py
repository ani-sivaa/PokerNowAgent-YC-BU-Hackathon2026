"""
Position-based preflop opening ranges for 8-max tables.

Each seat maps to a set of hand tiers that can be opened from that
position. The ranges tighten in early position and widen on the button,
following standard tight-aggressive (TAG) opening theory.
"""

from __future__ import annotations

from enum import Enum, auto

from src.strategy.hand_evaluator import HandTier


class Position(Enum):
    """Seats at an 8-max table, ordered from earliest to latest."""

    UTG = auto()
    UTG1 = auto()
    MP = auto()
    MP1 = auto()
    HJ = auto()
    CO = auto()
    BTN = auto()
    SB = auto()
    BB = auto()


OPENING_RANGE: dict[Position, set[HandTier]] = {
    Position.UTG:  {HandTier.PREMIUM},
    Position.UTG1: {HandTier.PREMIUM, HandTier.STRONG},
    Position.MP:   {HandTier.PREMIUM, HandTier.STRONG},
    Position.MP1:  {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
    Position.HJ:   {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE},
    Position.CO:   {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
    Position.BTN:  {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE, HandTier.MARGINAL},
    Position.SB:   {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE},
    Position.BB:   {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE, HandTier.SPECULATIVE, HandTier.MARGINAL},
}

STEAL_POSITIONS = {Position.CO, Position.BTN, Position.SB}

THREE_BET_TIERS = {HandTier.PREMIUM, HandTier.STRONG}

BB_DEFENSE_VS_STEAL = {
    HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE,
    HandTier.SPECULATIVE, HandTier.MARGINAL,
}


def should_defend_bb(tier: HandTier, raiser_position: Position) -> bool:
    """Return True if the BB should defend this hand against a steal."""
    if raiser_position not in STEAL_POSITIONS:
        return tier in {HandTier.PREMIUM, HandTier.STRONG, HandTier.PLAYABLE}
    return tier in BB_DEFENSE_VS_STEAL


def can_open(position: Position, tier: HandTier) -> bool:
    """Return True if this hand tier is in the opening range for the position."""
    return tier in OPENING_RANGE.get(position, set())


def is_steal_position(position: Position) -> bool:
    """Return True if the seat is typically used for blind stealing."""
    return position in STEAL_POSITIONS


def should_three_bet(tier: HandTier) -> bool:
    """Return True if the hand is strong enough to three-bet for value."""
    return tier in THREE_BET_TIERS


def position_from_seat_index(seat: int, num_players: int, dealer: int) -> Position:
    """
    Map a raw seat number to a Position enum for the current hand.

    Seat indices and dealer button position are zero-based. The mapping
    adjusts dynamically as players bust out.
    """
    positions_by_size = {
        2: [Position.SB, Position.BB],
        3: [Position.BTN, Position.SB, Position.BB],
        4: [Position.CO, Position.BTN, Position.SB, Position.BB],
        5: [Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
        6: [Position.MP1, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
        7: [Position.MP, Position.MP1, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
        8: [Position.UTG, Position.MP, Position.MP1, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
        9: [Position.UTG, Position.UTG1, Position.MP, Position.MP1, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
    }
    order = positions_by_size.get(min(num_players, 9), positions_by_size[8])
    offset = (seat - dealer - 1) % num_players
    if offset < len(order):
        return order[offset]
    return Position.UTG
