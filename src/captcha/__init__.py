from src.captcha.human import prompt_human_solve
from src.captcha.solver import solve_captcha

solve_captcha_via_api = solve_captcha

request_human_solve_captcha = prompt_human_solve

__all__ = ["solve_captcha", "solve_captcha_via_api", "request_human_solve_captcha", "prompt_human_solve"]
