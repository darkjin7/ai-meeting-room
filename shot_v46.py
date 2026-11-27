"""v4.6 모바일(390x844) 스크린샷 3장 — 로비 · 입장 인트로 · 6분할 회의실"""
import sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL = '/workspace/downloads/'

MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },520); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
})();
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                        is_mobile=True, has_touch=True)
    p = ctx.new_page(); p.add_init_script(MOCK)
    p.goto(URL); p.evaluate("localStorage.clear()")
    p.reload(); p.wait_for_timeout(900)
    p.screenshot(path=DL + 'meeting_v46_mobile_lobby.png')
    print('lobby', p.evaluate("()=>window.__mr4.lobby()"))

    p.click('#enterBtn'); p.wait_for_timeout(1300)
    p.screenshot(path=DL + 'meeting_v46_mobile_intro.png')
    print('introTime', p.evaluate("()=>document.getElementById('introVid').currentTime"),
          'title', p.inner_text('#introPickTitle'))

    p.click('#introSkip')
    p.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=2500)
    p.wait_for_function("()=>[...document.querySelectorAll('img.face')].every(i=>i.complete && i.naturalWidth>0)", timeout=10000)
    p.wait_for_timeout(2200)
    p.screenshot(path=DL + 'meeting_v46_mobile_room.png')
    print('room', p.evaluate("""()=>({view:window.__mr4.view(), phase:window.__mr4.state.phase,
        agenda:window.__mr4.state.agenda&&window.__mr4.state.agenda.id,
        tiles:document.querySelectorAll('.stage > .tile').length,
        heights:[...document.querySelectorAll('.stage > .tile')].map(t=>Math.round(t.getBoundingClientRect().height))})"""))
    b.close()
