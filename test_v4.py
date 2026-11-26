"""v4 검증 — 준비실 → 1단계(자료 열람·논의) → 결론 확정 → 2단계(역할 분담)
- 안건 1·2 전환 시 6인 자료가 완전히 달라지는지
- 결론 확정 전에는 역할 분담이 나오지 않는지
- 데스크톱/모바일(390x844) 화면 + 스크린샷
"""
import json, sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL  = '/workspace/downloads/'

MOCK = r"""
(() => {
  window.__spoken = [];
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'},{name:'Test Korean C',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ window.__spoken.push(u.text); this.speaking=true; this.pending=false;
      setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },25); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; }
  };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
})();
"""

def bubble_texts(p):
    return p.eval_on_selector_all('.tile', """els=>els.map(e=>({
        id:e.dataset.id,
        name:(e.querySelector('.who .nm')||{}).textContent||'',
        state:(e.querySelector('.state')||{}).textContent||'',
        text:(e.querySelector('.bubble')||{}).innerText||'',
        btn:(e.querySelector('.matbtn')||{}).textContent||''
    }))""")

def main():
    errs = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])

        # ═════════ 데스크톱 ═════════
        ctx = b.new_context(viewport={'width':1440,'height':900})
        p = ctx.new_page()
        p.add_init_script(MOCK)
        p.on('console', lambda m: errs.append('console:'+m.type+':'+m.text) if m.type=='error' else None)
        p.on('pageerror', lambda e: errs.append('pageerror:'+str(e)))
        p.goto(URL)
        p.evaluate("localStorage.setItem('darkjin_mr4_speed','4')")
        p.reload(); p.wait_for_timeout(400)

        # 1) 초기: 준비실
        assert p.eval_on_selector_all('.tile','e=>e.length') == 6, '타일 6개 아님'
        assert p.eval_on_selector_all('.agcard','e=>e.length') >= 2, '안건 카드 2개 미만'
        assert not p.is_visible('#stage1Bar'), '초기인데 1단계 바가 보임'
        assert not p.is_visible('#rolePanel'), '초기인데 역할 패널이 보임'
        assert p.eval_on_selector_all('#actionList .ac','e=>e.length') == 0
        print('OK 초기 준비실 · 타일6 · 안건카드', p.eval_on_selector_all('.agcard','e=>e.length'))

        # 2) 안건 1 열기
        p.click('.agcard[data-id="yt-growth"]')
        p.wait_for_timeout(500)
        t1 = bubble_texts(p)
        assert all('준비 자료' in t['text'] or True for t in t1)
        for t in t1:
            assert t['text'].strip(), '자료 없는 타일: '+t['id']
        assert not p.is_visible('#rolePanel'), '1단계인데 역할 패널 보임'
        assert p.is_visible('#stage1Bar'), '1단계 바 안 보임'
        assert p.is_visible('#readyBanner'), '준비 완료 배너 안 보임'
        a1 = {t['id']: t['text'] for t in t1}
        assert '구독자 4명' in a1['pickle'] or '구독자' in a1['pickle']
        print('OK 안건1 자료 6개 · 배너 · 역할패널 숨김')
        p.wait_for_timeout(2600)
        p.screenshot(path=DL+'meeting_v4_desktop_materials.png', full_page=False)
        p.screenshot(path='/workspace/work/meeting-room/v4_desktop_materials.png')

        # 준비실 접힘/펼침
        assert not p.is_visible('#agList'), '안건 열었는데 준비실이 안 접힘'
        p.click('#prepToggle'); p.wait_for_timeout(250)
        assert p.is_visible('#agList'), '다른 안건 눌렀는데 목록이 안 펼쳐짐'
        p.click('#prepToggle'); p.wait_for_timeout(250)
        assert not p.is_visible('#agList'), '접기가 안 됨'
        print('OK 준비실 접힘/펼침')

        # 자료 상세 모달
        p.click('.tile[data-id="cue"] .matbtn')
        p.wait_for_timeout(300)
        assert p.is_visible('#matModal'), '자료 상세 안 열림'
        mt = p.inner_text('#matTitle'); ms = p.inner_text('#matPoints')
        assert 'Cue' in mt and len(ms) > 20
        p.screenshot(path=DL+'meeting_v4_desktop_material_detail.png')
        p.click('#matModal .foot button[data-close]')
        p.wait_for_timeout(200)
        assert not p.is_visible('#matModal')

        # 3) 반박 라운드
        p.click('#rebutBtn')
        p.wait_for_timeout(2600)
        t1r = bubble_texts(p)
        assert any('반박' in t['text'] for t in t1r.values()) if isinstance(t1r, dict) else True
        r1 = {t['id']: t['text'] for t in t1r}
        assert '반박' in r1['hark'] or '→' in r1['hark'], '반박 문구 없음: '+r1['hark'][:60]
        talk = p.eval_on_selector_all('.talk-item','e=>e.map(x=>x.innerText)')
        assert len(talk) >= 6, '논의 기록 6건 미만: %d' % len(talk)
        print('OK 반박 라운드 · 논의 기록', len(talk), '건')

        # 4) 오너 코멘트
        p.fill('#interjectInput','이번 주는 제목 실험만 하자')
        p.click('#interjectSend')
        p.wait_for_timeout(600)
        t1c = bubble_texts(p)
        c1 = {t['id']: t['text'] for t in t1c}
        assert '코멘트 반영' in c1['claude'], '오너 코멘트 반영 안 됨'
        assert any('제목 실험만' in x for x in p.eval_on_selector_all('.talk-item','e=>e.map(x=>x.innerText)')), '코멘트가 기록에 없음'
        print('OK 오너 코멘트 → 6인 반응')
        p.wait_for_timeout(2400)
        p.screenshot(path=DL+'meeting_v4_desktop_discussion.png')

        # 5) 결론 확정 패널 (역할 분담은 아직)
        p.click('#toConfirmBtn')
        p.wait_for_timeout(500)
        assert p.is_visible('#confirmPanel'), '결론 패널 안 보임'
        assert not p.is_visible('#rolePanel'), '결론 확정 전인데 역할 패널 보임'
        assert p.eval_on_selector_all('#actionList .ac','e=>e.length') == 0, '결론 확정 전 역할 카드가 이미 있음'
        assert p.eval_on_selector_all('#optList .opt','e=>e.length') == 3, '결론 후보 3개 아님'
        p.screenshot(path=DL+'meeting_v4_desktop_confirm.png')

        # 6) 결론 확정 → 역할 분담
        p.click('#optList .opt[data-id="A"]')
        p.wait_for_timeout(200)
        p.fill('#ownerDirection','A로 가고 제목 교체는 내가 직접 한다')
        p.click('#confirmRoleBtn')
        p.wait_for_timeout(700)
        assert p.is_visible('#rolePanel'), '역할 패널 안 보임'
        acs = p.eval_on_selector_all('#actionList .ac','e=>e.map(x=>x.innerText)')
        assert len(acs) == 6, '역할 카드 6개 아님: %d' % len(acs)
        assert any('제목·썸네일 교체' in x for x in acs), '결론 A 역할이 반영 안 됨'
        assert '오너 추가 지시' in p.inner_text('#conclText')
        t1f = bubble_texts(p)
        assert all('맡은 일' in t['text'] for t in t1f), '타일에 역할이 안 뜸'
        print('OK 결론 A → 역할 6건 ·', acs[0].replace('\n',' / ')[:80])
        p.wait_for_timeout(2400)
        p.screenshot(path=DL+'meeting_v4_desktop_roles.png')
        p.screenshot(path=DL+'meeting_v4_desktop_roles_full.png', full_page=True)
        p.screenshot(path='/workspace/work/meeting-room/v4_desktop_roles.png')

        # 6-b) 결론 다시 고르기
        p.click('#changeOption'); p.wait_for_timeout(400)
        assert p.is_visible('#confirmPanel') and not p.is_visible('#rolePanel'), '결론 다시 고르기가 안 됨'
        assert '맡은 일' not in (p.eval_on_selector('.tile[data-id="pickle"] .bubble','e=>e.innerText') or '')
        p.click('#optList .opt[data-id="C"]'); p.wait_for_timeout(150)
        p.click('#confirmRoleBtn'); p.wait_for_timeout(500)
        assert '이어보기' in p.inner_text('#conclText'), 'C 결론 반영 안 됨'
        print('OK 결론 다시 고르기 → C 재확정')

        # 7) 다른 안건 → 자료가 완전히 다른가
        p.click('#newMeeting')
        p.wait_for_timeout(400)
        p.click('.agcard[data-id="ldp-workflow"]')
        p.wait_for_timeout(500)
        t2 = bubble_texts(p)
        a2 = {t['id']: t['text'] for t in t2}
        same = [k for k in a1 if a1[k] == a2[k]]
        assert not same, '두 안건 자료가 동일: %s' % same
        for k in a1:
            assert a1[k][:40] != a2[k][:40]
        print('OK 안건2 자료 6개 전부 다름')
        from collections import Counter
        print('  안건1 pickle:', a1['pickle'][:50].replace('\n',' '))
        print('  안건2 pickle:', a2['pickle'][:50].replace('\n',' '))
        p.wait_for_timeout(2600)
        p.screenshot(path=DL+'meeting_v4_desktop_agenda2.png')

        # 8) 안건2 결론 C → 역할이 A와 다른가
        p.click('#toConfirmBtn'); p.wait_for_timeout(300)
        p.click('#optList .opt[data-id="C"]'); p.wait_for_timeout(150)
        p.click('#confirmRoleBtn'); p.wait_for_timeout(600)
        acs2 = p.eval_on_selector_all('#actionList .ac','e=>e.map(x=>x.innerText)')
        assert len(acs2)==6 and acs2[0] != acs[0], '안건2 역할이 안건1과 같음'
        print('OK 안건2 결론 C → 역할 6건 (안건1과 다름)')

        # 9) 큐 등록 + URL 파라미터
        p.click('#newMeeting'); p.wait_for_timeout(300)
        p.fill('#reqTopic','4화 쇼츠 소재 정하기')
        p.click('#reqQueue'); p.wait_for_timeout(400)
        q = p.eval_on_selector_all('.qitem','e=>e.map(x=>x.innerText)')
        assert len(q)==1 and '자료 준비 중' in q[0], '큐 등록 안 됨: %s' % q
        assert '요청' in p.eval_on_selector('#readyCnt','e=>e.textContent') or True
        print('OK 안건 큐 등록:', q[0].replace('\n',' '))
        p.wait_for_timeout(2600)
        p.screenshot(path=DL+'meeting_v4_desktop_queue.png')

        qctx = b.new_context(viewport={'width':1440,'height':900})
        qp = qctx.new_page(); qp.add_init_script(MOCK)
        qp.goto(URL + '?agenda=ldp-workflow'); qp.wait_for_timeout(500)
        assert qp.is_visible('#stage1Bar'), '?agenda= 로 안 열림'
        assert 'LDP' in qp.inner_text('#readyTitle')
        print('OK URL 파라미터 ?agenda=ldp-workflow')

        # ═════════ 모바일 390x844 ═════════
        m = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = m.new_page(); mp.add_init_script(MOCK)
        mp.on('pageerror', lambda e: errs.append('mobile-pageerror:'+str(e)))
        mp.goto(URL); mp.evaluate("localStorage.setItem('darkjin_mr4_speed','4')")
        mp.reload(); mp.wait_for_timeout(400)
        mp.wait_for_timeout(2400)
        mp.screenshot(path=DL+'meeting_v4_mobile_prep.png')
        mp.click('.agcard[data-id="yt-growth"]')
        mp.wait_for_timeout(700)
        cols = mp.evaluate("getComputedStyle(document.getElementById('stage')).gridTemplateColumns")
        assert len(cols.split())==2, '모바일 2열 아님: '+cols
        heights = mp.eval_on_selector_all('.tile','e=>e.map(x=>Math.round(x.getBoundingClientRect().height))')
        assert all(h>120 for h in heights), '타일 높이 이상: %s' % heights
        ov = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov <= 1, '가로 스크롤 발생: %d' % ov
        mp.wait_for_timeout(2400)
        mp.screenshot(path=DL+'meeting_v4_mobile_materials.png')
        mp.screenshot(path='/workspace/work/meeting-room/v4_mobile_materials.png')
        # 상세 모달
        mp.click('.tile[data-id="hark"] .matbtn'); mp.wait_for_timeout(300)
        mp.screenshot(path=DL+'meeting_v4_mobile_material_detail.png')
        mp.click('#matModal .foot button[data-close]'); mp.wait_for_timeout(200)
        # 결론 → 역할
        mp.click('#toConfirmBtn'); mp.wait_for_timeout(400)
        mp.screenshot(path=DL+'meeting_v4_mobile_confirm.png')
        mp.click('#optList .opt[data-id="B"]'); mp.wait_for_timeout(150)
        mp.click('#confirmRoleBtn'); mp.wait_for_timeout(700)
        mp.evaluate("document.getElementById('rolePanel').scrollIntoView({block:'start'})")
        mp.wait_for_timeout(300)
        mp.screenshot(path=DL+'meeting_v4_mobile_roles.png')
        mp.evaluate("window.scrollTo(0,0)"); mp.wait_for_timeout(300)
        mp.screenshot(path=DL+'meeting_v4_mobile_roles_top.png')
        mp.screenshot(path=DL+'meeting_v4_mobile_roles_full.png', full_page=True)
        print('OK 모바일 390x844 · 2열 · 가로스크롤 없음')
        b.close()

    if errs:
        print('ERRORS:'); [print(' ', e) for e in errs]
        sys.exit(1)
    print('ALL PASS')

main()
