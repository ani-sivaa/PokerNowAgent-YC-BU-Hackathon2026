"""
Main SNG strategy engine.

Combines hand evaluation, positional awareness, and tournament stage
logic into a single strategy prompt that the browser-use agent follows
during gameplay. The prompt is regenerated for each hand based on
current table conditions.

Design rationale: the agent perceives the table through screenshots and
DOM reads -- it cannot call Python functions mid-hand. So we compile all
strategic guidance into a natural-language prompt that the LLM can
reason about while choosing actions.
"""

from __future__ import annotations

import textwrap

from src.strategy.hand_evaluator import (
    HAND_TIERS,
    HandTier,
    classify_hand,
)
from src.strategy.position import (
    OPENING_RANGE,
    Position,
    is_steal_position,
)
from src.strategy.tournament import (
    PUSH_FOLD_RANGES,
    StackCategory,
    TournamentStage,
    classify_stack,
    detect_stage,
    push_fold_tiers,
)


class SNGStrategy:
    """
    Generates context-aware strategy instructions for the LLM agent.

    Instantiate once and call build_prompt() to get the full strategy
    text that is appended to the agent's task description.
    """

    def __init__(self, table_size: int = 8):
        self.table_size = table_size

    def build_prompt(self) -> str:
        """Return the complete strategy prompt for the agent task."""
        sections = [
            self._objective(),
            self._general_principles(),
            self._preflop_guide(),
            self._postflop_guide(),
            self._stage_guide(),
            self._push_fold_guide(),
            self._common_mistakes(),
        ]
        return "\n\n".join(sections)

    @staticmethod
    def hand_tier_names(tiers: set[HandTier]) -> str:
        """Format a set of tiers as a readable comma-separated string."""
        ordered = sorted(tiers, key=lambda t: t.value)
        return ", ".join(t.name.lower() for t in ordered)

    @staticmethod
    def hands_in_tier(tier: HandTier) -> list[str]:
        """List all starting hands belonging to a tier."""
        return [h for h, t in HAND_TIERS.items() if t == tier]

    def _objective(self) -> str:
        return textwrap.dedent("""\
            POKER STRATEGY GUIDE -- {n}-Player Sit & Go
            ============================================
            Primary objective: finish in the top 3 consistently.
            This is a survival-first strategy. Preserving chips is more
            important than accumulating them, especially near the bubble."""
        ).format(n=self.table_size)

    def _general_principles(self) -> str:
        return textwrap.dedent("""\
            GENERAL PRINCIPLES
            ------------------
            1. Play tight-aggressive (TAG). Enter few pots but play them hard.
            2. Position is paramount -- act last whenever possible.
            3. Avoid coin-flip situations early; let weaker players bust each other.
            4. Protect your stack on the bubble -- fold marginal hands.
            5. Open up significantly once in the money or heads-up.
            6. Never slow-play premium hands multi-way; always build the pot.
            7. Pay attention to stack sizes at the table -- they dictate your range.""")

    def _preflop_guide(self) -> str:
        lines = [
            "PREFLOP OPENING RANGES (by position)",
            "-" * 40,
        ]
        for pos in Position:
            tiers = OPENING_RANGE.get(pos, set())
            tier_str = self.hand_tier_names(tiers)
            lines.append(f"  {pos.name:<5}  open: {tier_str}")

        lines.append("")
        lines.append("Hand tier reference:")
        for tier in HandTier:
            hands = self.hands_in_tier(tier)
            if hands:
                lines.append(f"  {tier.name:<12} {', '.join(hands)}")

        lines.append("")
        lines.append(
            "Three-bet for value with PREMIUM and STRONG hands. "
            "Flat-call with PLAYABLE hands that have good implied odds. "
            "Fold everything weaker to a raise unless you are on the button "
            "and getting a great price."
        )
        return "\n".join(lines)

    def _postflop_guide(self) -> str:
        return textwrap.dedent("""\
            POSTFLOP GUIDELINES
            -------------------
            - Continuation bet (c-bet) 50-70% of the pot when you were the
              preflop raiser, especially on dry boards (no flush/straight draws).
            - Check-fold on wet boards when you missed entirely.
            - With strong made hands (top pair+), bet for value -- do not
              slow-play in multi-way pots.
            - With draws, calculate pot odds before calling:
                pot_odds = amount_to_call / (pot + amount_to_call)
              Call only if your estimated equity exceeds the pot odds.
            - On the river, value-bet thinly when ahead and check behind
              with marginal hands to avoid getting raised off your equity.
            - Bluff sparingly -- only when the board texture supports a
              credible story and you have blockers to strong hands.""")

    def _stage_guide(self) -> str:
        lines = [
            "TOURNAMENT STAGE ADJUSTMENTS",
            "-" * 40,
        ]
        stage_advice = {
            TournamentStage.EARLY: (
                "7-8 players. Play tight, avoid marginal spots. Let weaker "
                "players eliminate each other. Only commit chips with premium "
                "or strong hands. Do not bluff into multi-way pots."
            ),
            TournamentStage.MIDDLE: (
                "5-6 players. Start stealing blinds from late position. "
                "Apply pressure on medium stacks. Look for spots to accumulate "
                "chips but avoid flipping against big stacks."
            ),
            TournamentStage.BUBBLE: (
                "4 players (1 away from money). ICM pressure is extreme. "
                "Short stacks: shove or fold with a narrow range. "
                "Medium stacks: play very tight, avoid confrontations. "
                "Big stacks: attack medium stacks relentlessly, but respect "
                "other big stacks. NEVER bust on the bubble with a marginal hand."
            ),
            TournamentStage.IN_THE_MONEY: (
                "3 players. You are in the money. Open up your ranges "
                "significantly. Steal blinds aggressively. Target the short "
                "stack and try to eliminate them for a higher payout."
            ),
            TournamentStage.HEADS_UP: (
                "2 players. Widen to nearly any two cards from the button. "
                "Aggression wins heads-up. Raise most buttons, three-bet "
                "liberally, and apply maximum pressure."
            ),
        }
        for stage, advice in stage_advice.items():
            lines.append(f"\n  [{stage.name}]")
            lines.append(f"  {advice}")
        return "\n".join(lines)

    def _push_fold_guide(self) -> str:
        lines = [
            "PUSH-FOLD REFERENCE (when stack <= 15 BB)",
            "-" * 40,
            "When your stack is 15 big blinds or less, the correct play is "
            "almost always all-in or fold. Do not limp or min-raise.",
            "",
        ]
        for stage in TournamentStage:
            lines.append(f"  [{stage.name}]")
            for stack_cat in StackCategory:
                tiers = push_fold_tiers(stage, stack_cat)
                hands = []
                for tier in sorted(tiers, key=lambda t: t.value):
                    hands.extend(self.hands_in_tier(tier))
                tier_str = self.hand_tier_names(tiers)
                lines.append(
                    f"    {stack_cat.name:<7} push tiers: {tier_str}"
                )
            lines.append("")
        return "\n".join(lines)

    def _common_mistakes(self) -> str:
        return textwrap.dedent("""\
            COMMON MISTAKES TO AVOID
            ------------------------
            - Calling all-ins on the bubble with medium-strength hands.
            - Open-limping instead of raising or folding.
            - Slow-playing big hands and letting opponents draw for free.
            - Ignoring position -- playing the same range from UTG and BTN.
            - Tilting after a bad beat -- stick to the strategy.
            - Over-bluffing in multi-way pots where someone always calls.
            - Min-raising with a short stack (just shove or fold).""")


def build_strategy_task_prompt(table_size: int = 8) -> str:
    """Convenience function to generate the full strategy prompt."""
    return SNGStrategy(table_size=table_size).build_prompt()
