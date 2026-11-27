"""v4.6.1 모바일(390x844) 스크린샷 — 새로 넣은 인트로 1번(전원 셀카)·2번(일렬 정면)"""
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

want = {1: DL + 'meeting_v461_intro1.png', 2: DL + 'meeting_v461_intro2.png'}
got = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                        is_mobile=True, has_touch=True)
    p = ctx.new_page(); p.add_init_script(MOCK)
    p.goto(URL); p.evaluate("()=>localStorage.clear()")
    p.reload(); p.wait_for_timeout(900)
    ids = [a['id'] for a in p.evaluate("()=>window.__mr4.lobby()")['agendas']]
    prev = None
    for n in range(1, 13):
        target = [a for a in ids if a != prev][0] if len(ids) > 1 else ids[0]
        p.evaluate("()=>window.__mr4.showLobby()"); p.wait_for_timeout(150)
        p.click('#lobbyAgList .agdoc-item[data-id="%s"]' % target); p.wait_for_timeout(150)
        p.click('#enterBtn')
        p.wait_for_function("()=>document.body.classList.contains('intro-on')", timeout=3000)
        p.wait_for_timeout(1500)                 # 영상이 어느 정도 진행된 장면
        idx = int(p.get_attribute('#intro', 'data-intro') or '0')
        st = p.evaluate("()=>window.__mr4.introState()")
        print(n, 'intro', idx, st['clip'], '%.2fs' % st['time'], 'readyState', st['readyState'], 'paused', st['paused'])
        if idx in want and idx not in got:
            path = want[idx]
            p.screenshot(path=path)
            got[idx] = path
            big = p.locator('#introVid').bounding_box()
            print('  saved', path, big)
        prev = target
        if len(got) == len(want):
            break
        p.click('#introSkip')
        p.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=3000)
        p.wait_for_timeout(300)
    b.close()
print('done', got)
if len(got) != len(want):
    sys.exit('두 클립을 다 못 찍음: %s' % got)
