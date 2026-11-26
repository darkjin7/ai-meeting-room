"""v4.3 최종 보고용 스크린샷 — 화상 6분할 / 글로 보기 (모바일 390x844)"""
from playwright.sync_api import sync_playwright
EXE='/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL='file:///workspace/work/meeting-room/index.v4.html'
DL='/workspace/downloads/'
MOCK = open('/workspace/work/meeting-room/mock_speech.js').read()
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=EXE,args=['--no-sandbox'])
    c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True)
    p=c.new_page(); p.add_init_script(MOCK); p.goto(URL)
    p.evaluate("localStorage.clear();localStorage.setItem('darkjin_mr4_speed','2')"); p.reload(); p.wait_for_timeout(400)
    p.click('.agcard[data-id="yt-growth"]'); p.wait_for_timeout(600)
    p.evaluate("(n)=>window.__mr4.playRound(n)",1); p.wait_for_timeout(300)
    p.evaluate("(n)=>window.__mr4.playRound(n)",2); p.wait_for_timeout(300)
    # 화상 6분할 — 발언 중 장면
    p.click('#viewVideoBtn'); p.wait_for_timeout(2900)
    p.evaluate("()=>{window.__mr4.playRound(3);}")
    p.wait_for_function("()=>!!document.querySelector('.tile.speaking')",timeout=8000)
    p.wait_for_timeout(120)
    p.screenshot(path=DL+'meeting_v43_mobile_video6.png')
    p.wait_for_function("()=>window.__mr4.state.busy===false",timeout=60000)
    # 글로 보기
    p.click('#viewTextBtn'); p.wait_for_timeout(3000)
    p.evaluate("document.getElementById('stageHd').scrollIntoView({block:'start'})")
    p.wait_for_timeout(400)
    p.evaluate("()=>{window.__mr4.playRound(4);}")
    p.wait_for_function("()=>!!document.querySelector('.tile.speaking')",timeout=8000)
    p.wait_for_timeout(120)
    p.screenshot(path=DL+'meeting_v43_mobile_text.png')
    p.screenshot(path='/workspace/work/meeting-room/v43_mobile_text_full.png', full_page=True)
    # 데스크톱 화상 (보고 참고)
    c2=b.new_context(viewport={'width':1440,'height':900}); q=c2.new_page(); q.add_init_script(MOCK); q.goto(URL)
    q.evaluate("localStorage.clear();localStorage.setItem('darkjin_mr4_speed','2')"); q.reload(); q.wait_for_timeout(400)
    q.click('.agcard[data-id="yt-growth"]'); q.wait_for_timeout(500)
    q.evaluate("(n)=>window.__mr4.playRound(n)",1)
    q.click('#viewVideoBtn'); q.wait_for_timeout(2900)
    q.evaluate("()=>{window.__mr4.playRound(2);}")
    q.wait_for_function("()=>!!document.querySelector('.tile.speaking')",timeout=8000)
    q.wait_for_timeout(120)
    q.screenshot(path='/workspace/work/meeting-room/v43_desktop_video6.png')
    b.close()
print('shots v4.3 done')
