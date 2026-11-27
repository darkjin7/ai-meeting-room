"""v4.5 눈검수용 스크린샷 — 모바일 390x844 · 데스크톱 1440x900 화상 6분할(영상)."""
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL = '/workspace/downloads/'
WORK = '/workspace/work/meeting-room/'
MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },3000); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
})();
"""


def shot(b, vw, vh, dpr, mobile, out, play):
    ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=dpr,
                        is_mobile=mobile, has_touch=mobile)
    p = ctx.new_page(); p.add_init_script(MOCK)
    p.goto(URL); p.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','2')")
    p.reload(); p.wait_for_timeout(500)
    p.click('.agcard[data-id="yt-growth"]'); p.wait_for_timeout(600)
    p.click('#viewVideoBtn'); p.wait_for_timeout(1200)
    p.wait_for_function("()=>!document.getElementById('toast').classList.contains('show')", timeout=8000)
    if play:
        p.evaluate("()=>{ window.__mr4.playRound(1); }")
        p.wait_for_function("()=>!!document.querySelector('.tile.speaking')", timeout=15000)
        p.wait_for_timeout(1500)          # 영상이 실제로 흐른 뒤
    p.wait_for_function("()=>{const v=document.querySelector('video.vid'); return v && v.currentTime>0.5;}", timeout=8000)
    p.screenshot(path=out)
    info = p.evaluate("""()=>{const t=document.querySelector('.tile');const r=t.getBoundingClientRect();
      const v=document.querySelector('video.vid');const rv=v.getBoundingClientRect();
      const sp=document.querySelector('.tile.speaking');
      return {tile:[Math.round(r.width),Math.round(r.height)], aspect:+(r.width/r.height).toFixed(2),
              video:[Math.round(rv.width),Math.round(rv.height)], vw:v.videoWidth, vh:v.videoHeight,
              t:Math.round(v.currentTime*100)/100, speaking:sp?sp.dataset.id:null,
              scroll:document.documentElement.scrollHeight-innerHeight};}""")
    print(out, info)
    ctx.close()


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    shot(b, 390, 844, 2, True, DL + 'meeting_v45_mobile_video6.png', True)
    shot(b, 1440, 900, 1, False, DL + 'meeting_v45_desktop_video6.png', True)
    b.close()
