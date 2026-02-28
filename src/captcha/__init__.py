"""
Captcha-handling subsystem.

Provides two strategies: automatic solving via CapSolver and a
human-in-the-loop fallback that pauses until the operator confirms.
"""

from src.captcha.human import prompt_human_solve
from src.captcha.solver import solve_captcha

__all__ = ["solve_captcha", "prompt_human_solve"]
