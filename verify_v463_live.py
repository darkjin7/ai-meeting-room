"""배포된 Pages(v4.6.3) 실제 동작 확인 — sleepy 는 3초 뒤 눈 감은 프레임에서 멈추고, phone 은 풀블리드로 돈다."""
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'https://darkjin7.github.io/ai-meeting-room/'
MOCK = open('mock_speech.js').read()

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    p = c.new_page(); p.add_init_script(MOCK)
    errs = []; p.on('pageerror', lambda e: errs.append(str(e)))
    p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
    p.goto(URL, wait_until='load'); p.wait_for_timeout(1200)
    print('title:', p.title())
    p.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); p.wait_for_timeout(700)
    p.click('#viewVideoBtn'); p.wait_for_timeout(900)

    # sleepy — 3초를 틀고 마지막 프레임에서 멈춘다
    p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m && m.sleep && m.sleep.t > 0.3;}""", timeout=9000)
    s0 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('sleepy 재생 중:', {k: s0['sleep'][k] for k in ('t', 'rs', 'loop', 'op', 'w', 'h')}, '| 문구', s0['vstate'])
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m && m.sleep && m.sleep.paused && m.sleep.ended;}""", timeout=9000)
    p.wait_for_timeout(1500)
    s1 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('sleepy 끝:', {k: s1['sleep'][k] for k in ('t', 'dur', 'paused', 'done', 'op')})
    p.screenshot(path='/workspace/work/meeting-room/live_v463_sleepy.png')

    # phone — 풀블리드 루프 + 이름·상태 하단
    p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m && m.phon && !m.phon.paused && m.phon.t > 0.3;}""", timeout=9000)
    ph = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    box = p.evaluate("""()=>{const t=document.querySelector('.tile[data-id="pickle"]');
        const v=t.querySelector('video.vlay[data-state="phone"]');
        const o=t.querySelector('.vov'); const rt=t.getBoundingClientRect(), ro=o.getBoundingClientRect();
        const rv=v.getBoundingClientRect();
        return {tile:[Math.round(rt.width),Math.round(rt.height)], video:[Math.round(rv.width),Math.round(rv.height)],
                vovBottom:Math.round(rt.bottom-ro.bottom), name:o.textContent.trim()};}""")
    print('phone:', {k: ph['phon'][k] for k in ('t', 'rs', 'loop', 'op')}, '| 문구', ph['vstate'], '|', box)
    p.screenshot(path='/workspace/work/meeting-room/live_v463_phone.png')

    # 발언 차례 → 즉시 깨어남
    p.evaluate("()=>{ window.__mr4.playRound(1); }")
    p.wait_for_function("()=>window.__mr4.state.busy===false && window.__mr4.state.round>=1", timeout=90000)
    p.wait_for_timeout(500)
    aw = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('라운드 후:', aw['vstate'], '| mood', repr(aw['mood']), '| speak paused', aw['speak']['paused'], 'op', aw['speak']['op'],
          '| sleep', {k: aw['sleep'][k] for k in ('paused', 'done', 't')})
    print('errors:', errs)
    b.close()
