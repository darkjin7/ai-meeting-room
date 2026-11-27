"""v4.6 빠른 확인 — 로비 렌더 · 입장 인트로 · 회의실 진입 (눈검수용 스크린샷)"""
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    p = ctx.new_page()
    errs = []
    p.on('console', lambda m: errs.append(m.type + ':' + m.text) if m.type in ('error',) else None)
    p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
    p.goto(URL); p.wait_for_timeout(700)
    print('lobby', p.evaluate("()=>window.__mr4.lobby()"))
    print('errors', errs[:10])
    p.screenshot(path='/workspace/work/meeting-room/smoke_lobby.png')
    p.click('#enterBtn'); p.wait_for_timeout(900)
    print('intro', p.evaluate("()=>window.__mr4.lobby()"))
    p.screenshot(path='/workspace/work/meeting-room/smoke_intro.png')
    p.wait_for_timeout(4200)
    print('after', p.evaluate("()=>window.__mr4.state.phase"), p.evaluate("()=>window.__mr4.view()"))
    print('tiles', p.evaluate("()=>document.querySelectorAll('.stage > .tile').length"))
    p.screenshot(path='/workspace/work/meeting-room/smoke_room.png')
    print('errors2', errs[:10])
    b.close()
