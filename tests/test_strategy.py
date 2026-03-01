"""Unit tests for the SNG strategy prompt builder."""

from src.strategy.hand_evaluator import HandTier
from src.strategy.sng_strategy import SNGStrategy, build_strategy_task_prompt


class TestSNGStrategy:
    def setup_method(self):
        self.strategy = SNGStrategy(table_size=8)

    def test_build_prompt_not_empty(self):
        prompt = self.strategy.build_prompt()
        assert len(prompt) > 500

    def test_prompt_contains_all_sections(self):
        prompt = self.strategy.build_prompt()
        assert "POKER STRATEGY GUIDE" in prompt
        assert "GENERAL PRINCIPLES" in prompt
        assert "PREFLOP OPENING RANGES" in prompt
        assert "POSTFLOP GUIDELINES" in prompt
        assert "TOURNAMENT STAGE ADJUSTMENTS" in prompt
        assert "PUSH-FOLD REFERENCE" in prompt
        assert "COMMON MISTAKES" in prompt

    def test_table_size_in_header(self):
        prompt = self.strategy.build_prompt()
        assert "8-Player" in prompt

    def test_different_table_size(self):
        s = SNGStrategy(table_size=6)
        prompt = s.build_prompt()
        assert "6-Player" in prompt

    def test_hand_tier_names(self):
        tiers = {HandTier.PREMIUM, HandTier.STRONG}
        names = SNGStrategy.hand_tier_names(tiers)
        assert "premium" in names
        assert "strong" in names

    def test_hands_in_tier(self):
        premium = SNGStrategy.hands_in_tier(HandTier.PREMIUM)
        assert "AA" in premium
        assert "KK" in premium
        assert "72o" not in premium


class TestConvenienceFunction:
    def test_build_strategy_task_prompt(self):
        prompt = build_strategy_task_prompt(table_size=8)
        assert "POKER STRATEGY GUIDE" in prompt
        assert len(prompt) > 500
