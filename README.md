# PokerNow SNG Agent

An autonomous agent that plays Friendly Sit & Go tournaments on
[PokerNow](https://network.pokernow.com/sng_tournaments) using
[Browser-Use](https://docs.browser-use.com/) for browser automation
and a configurable poker strategy engine for decision-making.

The goal is to **consistently finish in the top 3** of 8-player tables
by following a tight-aggressive, ICM-aware strategy that adjusts to
tournament stage and table dynamics.

## How it works

1. The agent opens a Chromium browser, navigates to the PokerNow SNG
   lobby, and joins the next available tournament.
2. During play, it reads the table state (cards, pot, stacks, blinds)
   through the DOM and makes decisions guided by a multi-layered
   strategy system:
   - **Hand evaluation** -- tier-based starting hand classification
   - **Positional ranges** -- tighter in early position, wider on the
     button
   - **Tournament stage awareness** -- early, middle, bubble, ITM,
     heads-up
   - **ICM adjustments** -- tightens calling ranges on the bubble,
     widens in the money
   - **Push-fold logic** -- correct shove-or-fold play under 15 BB
3. Captchas are handled automatically via CapSolver, with a
   human-in-the-loop fallback when the solver fails.

## Project structure

```
run_agent.py              Entrypoint
config/
  settings.py             Centralized configuration from .env
src/
  agent.py                Agent lifecycle and task prompt assembly
  browser.py              Playwright browser setup
  tools.py                Browser-Use action registrations
  captcha/
    solver.py             CapSolver reCAPTCHA integration
    human.py              Human fallback for unsupported captchas
  strategy/
    hand_evaluator.py     Hand tiers, pot odds, implied odds
    position.py           Opening ranges by table position
    tournament.py         Stage detection, ICM push-fold ranges
    sng_strategy.py       Strategy engine and prompt generation
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/PokerNow-Agent.git
cd PokerNow-Agent

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Set at least one LLM API key in `.env`:

| Variable | Provider |
|---|---|
| `BROWSER_USE_API_KEY` | Browser-Use Cloud (recommended) |
| `OPENAI_API_KEY` | OpenAI |
| `GOOGLE_API_KEY` | Google Gemini |
| `ANTHROPIC_API_KEY` | Anthropic Claude |

### 3. CapSolver (optional)

For automatic captcha solving, sign up at
[capsolver.com](https://www.capsolver.com/) and add your key:

```
CAPSOLVER_API_KEY=your_key_here
```

Without this key the agent will pause and ask you to solve captchas
manually.

## Usage

```bash
python run_agent.py
```

Close any existing Chrome instances before running if you want the
agent to reuse your logged-in PokerNow session.

When a captcha appears the agent will:
1. Attempt to solve it via CapSolver.
2. If that fails, prompt you to solve it in the browser and press
   Enter.

## Strategy overview

The strategy module (`src/strategy/`) is fully decoupled from the
browser automation code. It generates a natural-language strategy
prompt that the LLM agent follows during gameplay. This makes it easy
to tweak ranges, adjust ICM parameters, or swap in an entirely
different strategy without touching the automation layer.

### Tournament stages

| Stage | Players | Approach |
|---|---|---|
| Early | 7-8 | Tight, survival mode. Premium and strong hands only. |
| Middle | 5-6 | Start stealing blinds. Apply pressure from late position. |
| Bubble | 4 | ICM dominates. Short stacks shove/fold. Medium stacks fold wide. Big stacks attack. |
| In the money | 3 | Loosen up. Target the short stack for elimination. |
| Heads-up | 2 | Maximum aggression. Raise most buttons. |

### Key concepts

- **Hand tiers**: 6 tiers from Premium (AA, KK, QQ, AKs) down to
  Trash. Each position maps to a set of openable tiers.
- **ICM risk premium**: Near the bubble, calling an all-in costs more
  equity than the chips are worth. The engine tightens calling ranges
  by 25-65% depending on stack size.
- **Push-fold**: Below 15 BB the agent switches to shove-or-fold mode,
  referencing stage-specific hand ranges.

## Disclaimer

Automation may violate PokerNow's terms of service. Review
[their policies](https://network.pokernow.com/service_terms) before
using this in any capacity beyond personal experimentation.
