"""배포된 Pages(v4.7.1) 실제 동작 확인 — 딴짓(phone)은 한 번만 재생하고 곧바로 경청(listening)으로 돌아온다."""
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
    p.goto(URL, wait_until='load'); p.wait_for_timeout(1400)
    print('title:', p.title())
    p.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); p.wait_for_timeout(700)
    p.click('#viewVideoBtn')
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m && m.listen && !m.listen.paused && m.listen.t > 0.3 && m.listen.rs >= 2;}""", timeout=12000)
    base = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('기본:', base['moodNow'], '| 문구', base['vstate'], '| loop(phone/sleepy)', base['phon']['loop'], base['sleep']['loop'],
          '| dur(phone)', base['phon']['dur'])

    # 딴짓 켜기 → 1.6초 부근 '들킨' 표정 스크린샷
    p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m.mood==='phone' && m.phon && !m.phon.paused && m.phon.t >= 1.45 && m.phon.t <= 2.20;}""", timeout=8000)
    ph = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('딴짓 중: mood', ph['mood'], '| phone t %.2fs' % ph['phon']['t'], '| loop', ph['phon']['loop'],
          '| listening paused/op', ph['listen']['paused'], ph['listen']['op'], '| 문구', ph['vstate'])
    p.screenshot(path='/workspace/work/meeting-room/live_v471_phone.png')

    # 끝나면 곧바로 경청 복귀 — 마지막 프레임에 머물지 않는다
    p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
        return m.mood==='' && m.moodNow==='listening' && m.listen && !m.listen.paused && m.listen.op==='1';}""",
                        timeout=8000)
    p.wait_for_timeout(500)
    back = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('딴짓 종료: mood %r' % back['mood'], '| phone paused/done/t', back['phon']['paused'], back['phon']['done'], back['phon']['t'],
          '| listening t %.2fs op %s' % (back['listen']['t'], back['listen']['op']), '| 문구', back['vstate'])
    p.screenshot(path='/workspace/work/meeting-room/live_v471_back_to_listening.png')

    # 6초 지켜도 다시 켜지지 않는다
    t0 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    p.wait_for_timeout(6000)
    t1 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
    print('6초 뒤: mood %r' % t1['mood'], '| phone t %.2f→%.2f' % (t0['phon']['t'], t1['phon']['t']),
          '| listening t %.2f→%.2f' % (t0['listen']['t'], t1['listen']['t']), '| 문구', t1['vstate'])
    print('errors:', errs)
    b.close()
