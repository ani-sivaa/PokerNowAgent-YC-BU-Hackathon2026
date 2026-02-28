"""
In-browser overlay for toggling the poker agent on and off.

Uses browser-use's lifecycle hooks (on_step_start) and the built-in
agent.pause() / agent.resume() API.  The overlay is a Shadow-DOM
isolated floating panel injected via page.evaluate().
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_use import Agent


# ------------------------------------------------------------------
# JavaScript — self-contained overlay injection.
# Persists toggle state in localStorage so it survives navigations.
# ------------------------------------------------------------------

OVERLAY_JS = r"""
(function(){
  if(document.getElementById('__poker-agent-overlay__'))return;
  if(!document.body){setTimeout(arguments.callee,100);return}

  try{window.__pokerAgentActive__=localStorage.getItem('__pokerAgentActive__')==='true'}
  catch(e){window.__pokerAgentActive__=false}

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
})();
"""


# ------------------------------------------------------------------
# Hook factory
# ------------------------------------------------------------------

def create_overlay_hook():
    """Return an ``on_step_start`` hook that injects the overlay and
    pauses / resumes the agent based on the toggle state.

    Usage::

        hook = create_overlay_hook()
        await agent.run(on_step_start=hook)
    """
    _init_script_added = False

    async def _ensure_overlay(agent: Agent) -> None:
        """Inject the overlay into the current page if missing."""
        nonlocal _init_script_added
        try:
            page = await agent.browser_session.must_get_current_page()

            if not _init_script_added:
                await page.context.add_init_script(OVERLAY_JS)
                _init_script_added = True

            exists = await page.evaluate(
                "() => !!document.getElementById('__poker-agent-overlay__')"
            )
            if not exists:
                await page.evaluate(OVERLAY_JS)
        except Exception:
            pass

    async def _is_active(agent: Agent) -> bool:
        try:
            page = await agent.browser_session.must_get_current_page()
            return await page.evaluate(
                "() => window.__pokerAgentActive__ === true"
            )
        except Exception:
            return True

    async def hook(agent: Agent) -> None:
        await _ensure_overlay(agent)

        if await _is_active(agent):
            return

        # User toggled the bot off — pause until they turn it back on.
        agent.pause()
        print("\n  Bot PAUSED — toggle the overlay to resume.\n")

        while True:
            await asyncio.sleep(0.5)
            await _ensure_overlay(agent)
            if await _is_active(agent):
                break

        agent.resume()
        print("  Bot RESUMED\n")

    return hook
