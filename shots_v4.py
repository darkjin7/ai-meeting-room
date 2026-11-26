"""v4 보고용 스크린샷 (downloads/) — 최종 빌드 기준으로 새로 찍는다."""
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL  = '/workspace/downloads/'

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])

    # ── 데스크톱 ──
    ctx = b.new_context(viewport={'width':1440,'height':900})
    p = ctx.new_page()
    p.goto(URL); p.evaluate("localStorage.setItem('darkjin_mr4_speed','4')")
    p.reload(); p.wait_for_timeout(400)
    p.wait_for_timeout(2300)
    p.screenshot(path=DL+'meeting_v4_1_desktop_prep.png')

    p.click('.agcard[data-id="yt-growth"]'); p.wait_for_timeout(700)
    p.evaluate("window.scrollTo(0,0)"); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_2_desktop_materials.png')

    p.click('.tile[data-id="cue"] .matbtn'); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_3_desktop_material_detail.png')
    p.click('#matModal .foot button[data-close]'); p.wait_for_timeout(250)

    p.click('#rebutBtn'); p.wait_for_timeout(3200)
    p.fill('#interjectInput','이번 주는 제목 실험만 하자'); p.click('#interjectSend')
    p.wait_for_timeout(1500)
    p.evaluate("document.getElementById('stageHd').scrollIntoView({block:'start'})"); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_4_desktop_discussion.png')

    p.click('#toConfirmBtn'); p.wait_for_timeout(700)
    p.screenshot(path=DL+'meeting_v4_5_desktop_confirm.png')

    p.click('#optList .opt[data-id="A"]'); p.wait_for_timeout(200)
    p.fill('#ownerDirection','A로 가고 제목 교체는 내가 직접 한다')
    p.click('#confirmRoleBtn'); p.wait_for_timeout(900)
    p.evaluate("document.getElementById('stageHd').scrollIntoView({block:'start'})"); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_6_desktop_roles.png')
    p.evaluate("document.getElementById('rolePanel').scrollIntoView({block:'start'})"); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_7_desktop_roles_panel.png')

    # ── 두 번째 안건 (자료가 다르다) ──
    p.click('#newMeeting'); p.wait_for_timeout(400)
    p.click('.agcard[data-id="ldp-workflow"]'); p.wait_for_timeout(700)
    p.evaluate("window.scrollTo(0,0)"); p.wait_for_timeout(400)
    p.screenshot(path=DL+'meeting_v4_8_desktop_agenda2.png')

    # ── 모바일 390x844 ──
    m = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(URL); mp.evaluate("localStorage.setItem('darkjin_mr4_speed','4')")
    mp.reload(); mp.wait_for_timeout(400)
    mp.wait_for_timeout(2300)
    mp.screenshot(path=DL+'meeting_v4_9_mobile_prep.png')
    mp.click('.agcard[data-id="yt-growth"]'); mp.wait_for_timeout(700)
    mp.evaluate("window.scrollTo(0,0)"); mp.wait_for_timeout(400)
    mp.screenshot(path=DL+'meeting_v4_10_mobile_materials.png')
    mp.click('#toConfirmBtn'); mp.wait_for_timeout(600)
    mp.screenshot(path=DL+'meeting_v4_11_mobile_confirm.png')
    mp.click('#optList .opt[data-id="A"]'); mp.wait_for_timeout(200)
    mp.click('#confirmRoleBtn'); mp.wait_for_timeout(900)
    mp.evaluate("document.getElementById('rolePanel').scrollIntoView({block:'start'})"); mp.wait_for_timeout(400)
    mp.screenshot(path=DL+'meeting_v4_12_mobile_roles.png')
    b.close()
print('shots done')
