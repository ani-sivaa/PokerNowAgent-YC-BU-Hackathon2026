"""
In-browser overlay for toggling the poker agent on and off.

Injects a sleek floating panel (Shadow-DOM isolated) into the
Playwright page so the operator can pause the bot -- e.g. to log in
or handle something manually -- then resume with one click.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from browser_use import Browser


# ------------------------------------------------------------------
# JavaScript — single self-contained snippet used for BOTH
# context.add_init_script (runs on every navigation) AND
# page.evaluate (on-demand re-injection).
# ------------------------------------------------------------------

_OVERLAY_JS = r"""
(function(){
  /* restore toggle state */
  try{window.__pokerAgentActive__=localStorage.getItem('__pokerAgentActive__')==='true'}
  catch(e){window.__pokerAgentActive__=false}

  function __pao_inject(){
    if(document.getElementById('__poker-agent-overlay__'))return;
    if(!document.body){setTimeout(__pao_inject,100);return}

    var host=document.createElement('div');
    host.id='__poker-agent-overlay__';
    host.style.cssText='position:fixed;bottom:20px;right:20px;z-index:2147483647;';

    var shadow=host.attachShadow({mode:'open'});
    shadow.innerHTML='\
<style>\
*{margin:0;padding:0;box-sizing:border-box}\
.panel{\
  background:rgba(10,10,15,.88);\
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);\
  border:1px solid rgba(255,255,255,.06);\
  border-radius:14px;\
  padding:14px 18px;\
  display:flex;align-items:center;gap:14px;\
  box-shadow:0 4px 24px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.03);\
  user-select:none;cursor:default;\
  transition:border-color .3s,box-shadow .3s;\
  font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif;\
}\
.panel:hover{border-color:rgba(255,255,255,.1)}\
.panel.on{border-color:rgba(34,197,94,.15)}\
.info{display:flex;flex-direction:column;gap:3px}\
.label{\
  font-size:9px;font-weight:700;letter-spacing:1.8px;\
  text-transform:uppercase;color:rgba(255,255,255,.35);line-height:1;\
}\
.status{\
  font-size:13px;font-weight:500;color:rgba(255,255,255,.9);\
  display:flex;align-items:center;gap:7px;line-height:1;\
}\
.dot{\
  width:7px;height:7px;border-radius:50%;\
  background:#f59e0b;flex-shrink:0;\
  transition:background .3s,box-shadow .3s;\
}\
.dot.on{\
  background:#22c55e;\
  box-shadow:0 0 6px 2px rgba(34,197,94,.5);\
  animation:pulse 2s infinite;\
}\
@keyframes pulse{\
  0%,100%{box-shadow:0 0 6px 2px rgba(34,197,94,.35)}\
  50%{box-shadow:0 0 12px 4px rgba(34,197,94,.7)}\
}\
.toggle{\
  position:relative;width:42px;height:24px;\
  background:rgba(255,255,255,.08);border-radius:12px;\
  cursor:pointer;border:none;outline:none;\
  transition:background .3s;flex-shrink:0;\
}\
.toggle.on{background:rgba(34,197,94,.25)}\
.knob{\
  position:absolute;top:3px;left:3px;width:18px;height:18px;\
  background:#fff;border-radius:50%;\
  transition:transform .25s cubic-bezier(.4,0,.2,1);\
  box-shadow:0 1px 3px rgba(0,0,0,.3);\
}\
.toggle.on .knob{transform:translateX(18px)}\
</style>\
<div class="panel">\
  <div class="info">\
    <div class="label">Poker Agent</div>\
    <div class="status">\
      <span class="dot"></span>\
      <span class="text">Paused</span>\
    </div>\
  </div>\
  <button class="toggle"><div class="knob"></div></button>\
</div>';

    document.body.appendChild(host);

    var dot=shadow.querySelector('.dot');
    var text=shadow.querySelector('.text');
    var toggle=shadow.querySelector('.toggle');
    var panel=shadow.querySelector('.panel');

    function update(){
      var on=!!window.__pokerAgentActive__;
      dot.classList.toggle('on',on);
      toggle.classList.toggle('on',on);
      panel.classList.toggle('on',on);
      text.textContent=on?'Active':'Paused';
    }
    toggle.addEventListener('click',function(){
      window.__pokerAgentActive__=!window.__pokerAgentActive__;
      try{localStorage.setItem('__pokerAgentActive__',String(window.__pokerAgentActive__))}catch(e){}
      update();
    });
    update();
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',__pao_inject);
  }else{
    __pao_inject();
  }
})();
"""


# ------------------------------------------------------------------
# Python helper
# ------------------------------------------------------------------

class AgentOverlay:
    """Manages the in-browser toggle overlay and pause / resume lifecycle."""

    def __init__(self, browser: Browser) -> None:
        self._browser = browser
        self._init_script_added = False

    # -- setup --------------------------------------------------------

    async def setup(self, url: str) -> None:
        """Start the browser, navigate to *url*, and inject the overlay."""
        await self._browser.start()

        page = await self._browser.get_current_page()
        if page is None:
            await self._browser.new_page(url)
        else:
            await self._browser.navigate_to(url)

        # Let the page settle (PokerNow is slow to load).
        await asyncio.sleep(3)

        page = await self._browser.must_get_current_page()

        # Init script runs the full overlay JS on every future navigation.
        if not self._init_script_added:
            try:
                await page.context.add_init_script(_OVERLAY_JS)
                self._init_script_added = True
            except Exception:
                pass

        # Inject right now on the current page too.
        await self._inject_with_retry(page, attempts=5)

    # -- overlay injection -------------------------------------------

    async def _inject(self, page: Any | None = None) -> None:
        if page is None:
            page = await self._browser.get_current_page()
        if page is None:
            return
        try:
            exists = await page.evaluate(
                "() => !!document.getElementById('__poker-agent-overlay__')"
            )
            if not exists:
                await page.evaluate(_OVERLAY_JS)
        except Exception:
            pass

    async def _inject_with_retry(
        self, page: Any | None = None, attempts: int = 3
    ) -> None:
        for _ in range(attempts):
            await self._inject(page)
            try:
                if page and await page.evaluate(
                    "() => !!document.getElementById('__poker-agent-overlay__')"
                ):
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)

    # -- state queries -----------------------------------------------

    async def _read_active(self) -> bool:
        try:
            page = await self._browser.get_current_page()
            if page:
                return await page.evaluate(
                    "() => window.__pokerAgentActive__ === true"
                )
        except Exception:
            pass
        return False

    async def check_active(self) -> bool:
        """Return the current toggle state without side-effects."""
        return await self._read_active()

    # -- agent callbacks ---------------------------------------------

    async def should_stop(self) -> bool:
        """``register_should_stop_callback`` — True when the bot is paused."""
        await self._inject()
        return not await self._read_active()

    async def on_new_step(self, _state: Any, _output: Any, _n: int) -> None:
        """``register_new_step_callback`` — re-injects overlay each step."""
        await self._inject()

    # -- blocking wait -----------------------------------------------

    async def wait_for_activation(self) -> None:
        """Block until the operator toggles the bot *on*."""
        while True:
            await self._inject()
            if await self._read_active():
                return
            await asyncio.sleep(0.5)
