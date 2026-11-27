"""v4.5.1 눈검수용 스크린샷 — 모바일 390x844 (피클 듣는 중 / 피클 발언 중 / 글로 보기) · 데스크톱"""
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL = '/workspace/downloads/'
WORK = '/workspace/work/meeting-room/'
MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'}];
  /* 발언을 3.2초로 늘려 '발언 중' 순간을 잡기 쉽게 */
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },3200); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
})();
"""


def shot(b, vw, vh, dpr, mobile, prefix):
    ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=dpr,
                        is_mobile=mobile, has_touch=mobile)
    p = ctx.new_page(); p.add_init_script(MOCK)
    p.goto(URL); p.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','4')")
    p.reload(); p.wait_for_timeout(400)
    p.click('.agcard[data-id="yt-growth"]'); p.wait_for_timeout(600)
    p.click('#viewVideoBtn'); p.wait_for_timeout(900)
    # 듣는 중 — 피클 타일은 정지 이미지
    p.wait_for_function("()=>!document.getElementById('toast').classList.contains('show')", timeout=8000)
    p.screenshot(path=DL + '%s_video_idle.png' % prefix)
    p.screenshot(path=WORK + '%s_video_idle.png' % prefix)
    print('idle ', p.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle')"))
    # 피클 발언 중 — 영상 재생
    p.evaluate("()=>{ window.__mr4.playRound(1); }")
    p.wait_for_function("""()=>{const v=document.querySelector('video.vid');
        return document.querySelector('.tile[data-id="pickle"]').classList.contains('speaking') && v && !v.paused && v.currentTime>0.6;}""",
        timeout=60000)
    p.screenshot(path=DL + '%s_video_pickle_speaking.png' % prefix)
    p.screenshot(path=WORK + '%s_video_pickle_speaking.png' % prefix)
    print('speaking', p.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle')"))
    # 글로 보기 — 발언 카드가 세로 중앙
    p.wait_for_function("()=>window.__mr4.state.busy===false", timeout=90000)
    p.click('#viewTextBtn'); p.wait_for_timeout(300)
    p.evaluate("()=>{ window.__mr4.playRound(1); }")
    p.wait_for_function("""()=>{const t=document.querySelector('.tile.speaking'); if(!t) return false;
        const b=window.__mr4.visibleCenter(); const r=t.getBoundingClientRect();
        return Math.abs(r.top+r.height/2-b.center) <= 8;}""", timeout=60000)
    p.screenshot(path=DL + '%s_text.png' % prefix)
    p.screenshot(path=WORK + '%s_text.png' % prefix)
    print('text  ', p.evaluate("()=>window.__mr4.centerOf(window.__mr4.state.activeSpeaker||'pickle')"))
    ctx.close()


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    shot(b, 390, 844, 2, True, 'meeting_v451_mobile')
    shot(b, 1440, 900, 1, False, 'meeting_v451_desktop')
    b.close()
print('done')
