"""
Automatic reCAPTCHA solver using the CapSolver API.

Workflow:
  1. Detect a reCAPTCHA v2 widget on the current page.
  2. Submit a solve task to CapSolver.
  3. Poll until the solution is ready (or timeout).
  4. Inject the token into the page so the form can proceed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from browser_use.browser.session import BrowserSession

if TYPE_CHECKING:
    from playwright.async_api import Page

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


async def detect_recaptcha(page: Page) -> dict | None:
    """Look for a reCAPTCHA v2 element and return its sitekey + page URL."""
    js = """() => {
        const el = document.querySelector('.g-recaptcha')
                || document.querySelector('[data-sitekey]');
        if (!el) return JSON.stringify({found: false});
        return JSON.stringify({
            found: true,
            sitekey: el.getAttribute('data-sitekey') || '',
            url: window.location.href
        });
    }"""
    raw = await page.evaluate(js)
    data = json.loads(raw) if isinstance(raw, str) else raw
    if data.get("found") and data.get("sitekey"):
        return data
    return None


async def create_solve_task(
    client: "httpx.AsyncClient",
    api_url: str,
    api_key: str,
    sitekey: str,
    page_url: str,
) -> str | None:
    """Submit a reCAPTCHA v2 task to CapSolver and return the task ID."""
    payload = {
        "clientKey": api_key,
        "task": {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": sitekey,
        },
    }
    resp = await client.post(f"{api_url}/createTask", json=payload)
    resp.raise_for_status()
    body = resp.json()
    return body.get("taskId")


async def poll_solution(
    client: "httpx.AsyncClient",
    api_url: str,
    api_key: str,
    task_id: str,
    interval: int,
    timeout: int,
) -> str | None:
    """Block until CapSolver returns a token or the timeout expires."""
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval
        resp = await client.post(
            f"{api_url}/getTaskResult",
            json={"clientKey": api_key, "taskId": task_id},
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("status") == "ready":
            return (result.get("solution") or {}).get("gRecaptchaResponse")
        if result.get("status") == "failed":
            return None
    return None


async def inject_token(page: Page, token: str) -> None:
    """Write the solved token into the reCAPTCHA response fields on the page."""
    safe = token.replace("\\", "\\\\").replace("'", "\\'")
    safe = safe.replace("\n", "\\n").replace("\r", "\\r")
    js = f"""() => {{
        const token = '{safe}';
        const fields = [
            document.getElementById('g-recaptcha-response'),
            document.getElementById('recaptcha-token'),
        ];
        for (const el of fields) {{
            if (!el) continue;
            el.innerHTML = token;
            el.value = token;
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
        }}
    }}"""
    await page.evaluate(js)


async def solve_captcha(
    browser_session: BrowserSession,
    api_key: str,
    api_url: str = "https://api.capsolver.com",
    poll_interval: int = 2,
    poll_timeout: int = 120,
) -> tuple[bool, str]:
    """
    End-to-end captcha solve attempt.

    Returns (success, message) so the caller can decide on fallback.
    """
    if httpx is None:
        return False, "httpx is not installed (pip install httpx)"

    try:
        page = await browser_session.must_get_current_page()
    except Exception as exc:
        return False, f"Could not access page: {exc}"

    try:
        recaptcha = await detect_recaptcha(page)
    except Exception as exc:
        return False, f"Detection script failed: {exc}"

    if recaptcha is None:
        logger.debug("no recaptcha element found on current page")
        return False, "No reCAPTCHA element found on this page"

    sitekey = recaptcha["sitekey"]
    page_url = recaptcha.get("url", "")
    logger.info("recaptcha detected – sitekey=%s url=%s", sitekey[:12], page_url)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            task_id = await create_solve_task(
                client, api_url, api_key, sitekey, page_url
            )
            if not task_id:
                logger.warning("capsolver returned no task id")
                return False, "CapSolver did not return a task ID"

            logger.info("capsolver task created – id=%s", task_id)
            token = await poll_solution(
                client, api_url, api_key, task_id, poll_interval, poll_timeout
            )
    except Exception as exc:
        return False, f"CapSolver request failed: {exc}"

    if not token:
        logger.warning("capsolver failed to produce a solution")
        return False, "CapSolver could not produce a solution"

    try:
        await inject_token(page, token)
    except Exception as exc:
        logger.error("token injection failed: %s", exc)
        return False, f"Token injection failed: {exc}"

    logger.info("captcha solved successfully via capsolver")
    await asyncio.sleep(1)
    return True, "CAPTCHA solved via CapSolver"
