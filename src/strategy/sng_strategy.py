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
        itm = 4 if self.table_size >= 8 else 3
        return textwrap.dedent("""\
            POKER STRATEGY GUIDE -- {n}-Player Sit & Go
            ============================================
            Primary objective: SURVIVE to the top {itm} to earn points.
            You earn points when {itm} or fewer players remain.

            KEY PRINCIPLE: Survival does NOT mean folding everything.
            If you fold every hand, the blinds will eat your stack and you
            will be eliminated. You must pick up blinds and win small pots
            to stay alive. The strategy changes based on your stack size:

            STACK SIZE RULES (before the money, >{itm} players left):
              BIG STACK (15+ BB):
                - Play tight. Enter pots with strong hands only.
                - Avoid unnecessary all-ins. You can afford to wait.
              MEDIUM STACK (8-14 BB):
                - Steal blinds from late position with decent hands.
                - Avoid calling all-ins without premium hands.
                - You can raise/fold but avoid committing your whole stack.
              SHORT STACK (4-7 BB):
                - Shove or fold. Do NOT limp or min-raise.
                - Shove with: any pair, any Ace, KQ, KJ, KTs, QJs.
                - You MUST pick up blinds or you will die. Do not wait
                  for AA/KK -- you will blind out before seeing them.
              DESPERATE STACK (1-3 BB):
                - Shove with ANY two cards from late position.
                - Shove with any Ace, any King, any pair, any suited
                  connectors from any position.
                - At this stack you WILL be eliminated by blinds if you
                  fold. ANY hand is better than being blinded out.

            AFTER you are in the money ({itm} or fewer players remain):
              - Open up. Steal aggressively. Target short stacks.
              - Play to WIN and climb the payout ladder."""
        ).format(n=self.table_size, itm=itm)

    def _general_principles(self) -> str:
        itm = 4 if self.table_size >= 8 else 3
        return textwrap.dedent("""\
            GENERAL PRINCIPLES
            ------------------
            1. Count remaining players EVERY hand to know your stage.
            2. Check your stack in BB EVERY hand to pick the right mode.
            3. With 15+ BB: play tight, avoid unnecessary confrontations.
            4. With 8-14 BB: steal blinds from late position, avoid calling shoves.
            5. With 4-7 BB: shove-or-fold only. Shove any pair, any Ace, KQ/KJ/KT.
            6. With 1-3 BB: shove almost anything. You WILL die to blinds otherwise.
            7. Position matters -- steal from the button and cutoff, fold from UTG.
            8. NEVER fold a strong made hand postflop to a small bet. If you have
               two pair or better and the bet is less than half the pot, CALL.
            9. SEE MORE FLOPS: If you hold a broadway card (A/K/Q/J/10) suited
               with any other card, call cheap preflop bets to see the flop.
               Evaluate the flop -- continue if you hit a pair or flush draw,
               fold if you miss completely. Do NOT auto-fold playable suited hands.
            10. After the money ({itm} or fewer players): play aggressively to win."""
        ).format(itm=itm)

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

        lines.append("")
        lines.append("SUITED ROYALS RULE (see cheap flops with these):")
        lines.append(
            "  If you hold one broadway card (A, K, Q, J, or 10) plus any\n"
            "  other card of the SAME SUIT, this is a suited royal hand.\n"
            "  Examples: Kh 7h, Qs 4s, Jd 3d, Ah 6h, Ts 2s.\n"
            "  These hands have flush potential and high-card value.\n"
            "  RULE: Do NOT auto-fold suited royals. Instead:\n"
            "    - If you can CHECK for free: always check and see the flop.\n"
            "    - If the call price is cheap (1 BB or less, or under 15%\n"
            "      of your stack): CALL and see the flop.\n"
            "    - If the price is expensive (a big raise): fold.\n"
            "  AFTER THE FLOP with suited royals, evaluate:\n"
            "    - Did you hit a flush draw (2 of your suit on board)? CALL\n"
            "      reasonable bets to see the turn/river.\n"
            "    - Did you make a flush (3+ of your suit on board)? BET/RAISE.\n"
            "    - Did you hit top pair with your broadway card? CALL or BET.\n"
            "    - Did you completely miss (no pair, no draw)? CHECK or FOLD.\n"
            "  This lets you see more flops cheaply and win big pots when\n"
            "  you connect, instead of folding every hand preflop."
        )
        return "\n".join(lines)

    def _postflop_guide(self) -> str:
        return textwrap.dedent("""\
            POSTFLOP GUIDELINES
            -------------------
            CRITICAL: Do NOT fold strong hands to small bets. The old
            strategy was folding two-pair to 1 BB bets -- that is WRONG.

            When to CALL (even before the money):
            - You have top pair + good kicker or better: ALWAYS call
              reasonable bets (up to pot-sized).
            - You have two pair or better: ALWAYS call. Only fold two pair
              to an all-in if the board is extremely dangerous (4 to a
              flush/straight you don't have).
            - You have a flush or straight: ALWAYS call or raise.
            - Getting great pot odds (calling < 25% of the pot): call
              with any pair or draw.

            When to FOLD postflop:
            - You completely missed the board (no pair, no draw, no
              flush draw, no straight draw) AND face a bet.
            - You have bottom pair with no kicker and face aggression.
            - You called preflop with a suited royal hand and the flop
              gave you NOTHING (no pair, no flush draw). Cut your losses.

            When to BET/RAISE postflop:
            - C-bet 50-70% of pot as preflop raiser on dry boards.
            - Bet for value with top pair or better.
            - Do NOT slow-play big hands. Bet them.

            When to CHECK:
            - You missed the board and are first to act.
            - You have a marginal hand and want a free card.
            - Check is FREE -- always check rather than fold when no bet
              is facing you.""")

    def _stage_guide(self) -> str:
        lines = [
            "TOURNAMENT STAGE ADJUSTMENTS",
            "-" * 40,
        ]
        stage_advice = {
            TournamentStage.EARLY: (
                "7-8 players. Not in the money yet. "
                "With 15+ BB: play tight, enter pots with premium/strong hands, "
                "avoid big all-in confrontations. "
                "With 8-14 BB: steal blinds from BTN/CO, fold from early position. "
                "With <8 BB: shove-or-fold with any pair, any Ace, KQ, KJ. "
                "Let weaker players bust each other, but do NOT fold yourself "
                "into oblivion -- pick up blinds to stay alive."
            ),
            TournamentStage.MIDDLE: (
                "5-6 players. Getting closer to the money. "
                "With 15+ BB: tighten up slightly, steal from late position. "
                "With 8-14 BB: actively steal blinds. Shove over limpers with "
                "strong hands. "
                "With <8 BB: shove-or-fold. Any pair, any Ace, any two Broadway. "
                "You MUST pick up blinds at this stage or you will blind out."
            ),
            TournamentStage.BUBBLE: (
                "4 players (1 from the money). Almost there! "
                "Big stack: pressure the medium stacks. Raise their blinds. "
                "Medium stack: play carefully but still steal when unopened. "
                "Short stack: shove wider -- any pair, any Ace, KQ, KJ, QJ. "
                "You are so close. Avoid calling someone else's all-in "
                "without a real hand, but DO shove yourself to stay alive."
            ),
            TournamentStage.IN_THE_MONEY: (
                "3 players. Points SECURED! Now play to win. "
                "Steal blinds aggressively. Shove on short stacks. "
                "Open your range wide from the button. "
                "Target the shortest stack for elimination."
            ),
            TournamentStage.HEADS_UP: (
                "2 players. Points secured. Maximum aggression. "
                "Raise nearly every button. Shove with any decent hand. "
                "Three-bet liberally. Apply relentless pressure."
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
            "all-in or fold. Do NOT limp or min-raise.",
            "",
            "CRITICAL: These ranges apply at ALL stages. If you are short-"
            "stacked, you MUST shove with these hands or you will blind out.",
            "",
            "  1-3 BB:  Shove almost any hand. Any Ace, any pair, any King,",
            "           any suited connector, any two Broadway cards.",
            "  4-7 BB:  Shove any pair, any Ace, KQ, KJ, KTs, QJs, JTs.",
            "  8-10 BB: Shove pairs 55+, ATo+, A8s+, KQo, KJs+, QJs.",
            "  11-15 BB: Shove pairs 77+, AJo+, ATs+, KQs. Or raise/fold.",
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
            - #1 MISTAKE: Folding EVERYTHING and blinding out. If your stack
              is short (under 8 BB), you MUST shove with decent hands. Waiting
              for AA/KK with 3 BB will guarantee elimination.
            - Folding strong made hands to small bets. If you have two pair
              and someone bets 1 BB into a 4 BB pot, CALL. That is free money.
            - Calling someone else's all-in on the bubble with a mediocre hand.
              Shove yourself, but be cautious about calling others' shoves.
            - Open-limping instead of raising or folding.
            - Slow-playing big hands and letting opponents draw for free.
            - Ignoring position -- play tighter from UTG, wider from BTN.
            - Clicking the same button repeatedly when it doesn't respond.
              Click ONCE. If no response after 2 seconds, the action went
              through or it is not your turn. Wait for the next hand.
            - Waiting 5+ seconds between observations. Use short waits (2s).
            - Auto-folding suited broadway hands preflop when the price is
              cheap. A hand like Kh 7h or Qs 4s can make a flush. See the
              flop cheaply, THEN decide. Only fold these to big raises.""")


def build_strategy_task_prompt(table_size: int = 8) -> str:
    """Convenience function to generate the full strategy prompt."""
    return SNGStrategy(table_size=table_size).build_prompt()
