"""v4.1 검증 — 안건 목록(✅ 준비 완료 / ⏳ 준비 중) → 4라운드 심화 토론 → 결론 확정 → 역할 분담
- 안건 1·2 전환 시 6인 자료와 라운드 발언이 완전히 달라지는지
- 라운드가 1→2→3→4로 이어지고, 각 라운드 발언이 서로 다른지 (반박 1회로 끝나지 않는지)
- ⏳ 예정 안건은 예약만 되고 회의에 들어갈 수 없는지 (가짜 답변 방지)
- 데스크톱/모바일(390x844) 화면 + 스크린샷
"""
import json, sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL  = '/workspace/downloads/'
WORK = '/workspace/work/meeting-room/'

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

def tiles(p):
    return p.eval_on_selector_all('.tile', """els=>els.map(e=>({
        id:e.dataset.id,
        state:(e.querySelector('.state')||{}).textContent||'',
        text:(e.querySelector('.bubble')||{}).innerText||''
    }))""")

def by_id(lst):
    return {t['id']: t['text'] for t in lst}

def wait_idle(p, timeout=25000):
    p.wait_for_function("() => window.__mr4 && window.__mr4.state && window.__mr4.state.busy === false", timeout=timeout)

def play(p, n, timeout=30000):
    """다음 라운드 버튼을 눌러 n라운드까지 진행하고 끝날 때까지 기다린다."""
    p.click('#nextRoundBtn')
    p.wait_for_function("(n) => window.__mr4.state.round >= n && window.__mr4.state.busy === false", arg=n, timeout=timeout)
    p.wait_for_timeout(120)

def chips(p):
    return p.eval_on_selector_all('#roundBar .rchip', "els=>els.map(e=>({t:e.textContent, d:e.disabled}))")

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
        p.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','4')")
        p.reload(); p.wait_for_timeout(400)

        # 1) 초기: 안건 목록 (✅ / ⏳)
        assert p.eval_on_selector_all('.tile','e=>e.length') == 6, '타일 6개 아님'
        ready = p.eval_on_selector_all('#agList .agcard','e=>e.length')
        waits = p.eval_on_selector_all('#planList .wcard','e=>e.length')
        assert ready >= 2, '✅ 준비 완료 안건 2개 미만: %d' % ready
        assert waits >= 1, '⏳ 준비 중 슬롯 없음'
        assert p.inner_text('#readyCnt').startswith('✅'), '#readyCnt 표기 아님'
        assert p.inner_text('#waitCnt').startswith('⏳'), '#waitCnt 표기 아님'
        assert not p.is_visible('#stage1Bar'), '초기인데 라운드 바가 보임'
        assert not p.is_visible('#rolePanel'), '초기인데 역할 패널이 보임'
        assert p.eval_on_selector_all('#actionList .ac','e=>e.length') == 0
        # 옛 큐 UI(주제 입력 + 요청문 복사 버튼)는 목록 중심으로 축소됨
        assert p.eval_on_selector_all('#reqTopic','e=>e.length') == 0, '옛 주제 입력창이 남아 있음'
        assert p.is_visible('#planAddBtn'), '안건 예약 버튼 없음'
        print('OK 초기 안건 목록 · ✅%d · ⏳%d · 옛 입력창 없음' % (ready, waits))

        # 2) ⏳ 카드는 회의에 못 들어간다
        p.click('#planList .wcard')
        p.wait_for_timeout(300)
        assert not p.is_visible('#stage1Bar'), '⏳ 카드를 눌렀는데 회의가 열림'
        assert p.eval_on_selector_all('.tile[data-id="pickle"] .bubble.empty','e=>e.length') == 1, '⏳ 카드 클릭에 자료가 열림'
        print('OK ⏳ 안건은 열리지 않음 (가짜 답변 없음)')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_prep.png', full_page=False)

        # 3) 안건 1 열기 → 라운드 4개 · 2~4 잠김
        p.click('.agcard[data-id="yt-growth"]')
        p.wait_for_timeout(500)
        t1 = tiles(p)
        a1 = by_id(t1)
        assert all(a1[k].strip() for k in a1), '자료 없는 타일 있음'
        assert '구독자 4명' in a1['pickle'] or '구독자' in a1['pickle']
        assert p.is_visible('#stage1Bar'), '라운드 바 안 보임'
        assert not p.is_visible('#rolePanel'), '1단계인데 역할 패널 보임'
        cs = chips(p)
        assert len(cs) == 4, '라운드 칩 4개 아님: %s' % cs
        assert cs[0]['d'] is False and cs[1]['d'] is True and cs[3]['d'] is True, '라운드 잠금 상태 이상: %s' % cs
        assert '1라운드' in p.inner_text('#nextRoundBtn'), '다음 라운드 버튼 문구 이상'
        ids1 = p.eval_on_selector_all('.tile','e=>e.map(x=>x.dataset.id)')
        assert ids1 == ['pickle','gemini','cue','hark','chatgpt','claude'], '안건1 주전 6인 아님: %s' % ids1
        assert p.is_visible('#guestBar'), '참관 게스트 표시 없음'
        gb = p.inner_text('#guestBar')
        assert '참관 게스트 2인' in gb and 'Meta Muse' in gb and 'Keyring' in gb, '게스트 표시 이상: ' + gb
        assert p.eval_on_selector_all('.tile','e=>e.length') == 6, '게스트가 타일로 들어감'
        print('OK 안건1 자료 6개 · 라운드 칩 4개 · 2~4 잠김')

        # 4) 잠긴 4라운드를 건너뛰려 하면 막힌다
        p.evaluate("()=>window.__mr4.playRound(4)")
        p.wait_for_timeout(250)
        assert p.evaluate("()=>window.__mr4.state.round") == 0, '잠긴 라운드가 실행됨'
        print('OK 라운드 건너뛰기 차단')

        # 5) 1라운드 자료 발표
        play(p, 1)
        r1 = by_id(tiles(p))
        assert '1라운드' in r1['pickle'], '1라운드 표기 없음: ' + r1['pickle'][:40]
        cs = chips(p)
        assert cs[0]['d'] is False and cs[1]['d'] is False and cs[2]['d'] is True, '1라운드 후 잠금 이상: %s' % cs
        assert p.inner_text('#talkCount') == '6건', '1라운드 기록: ' + p.inner_text('#talkCount')
        assert '2라운드' in p.inner_text('#nextRoundBtn'), '다음 버튼이 2라운드가 아님'
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_round1.png')

        # 6) 2라운드 정면 반박 — 1라운드와 다른 발언, 상대를 지목
        play(p, 2)
        r2 = by_id(tiles(p))
        for k in r1:
            assert r1[k][:30] != r2[k][:30], '2라운드가 1라운드와 같은 발언: '+k
        assert '→' in r2['pickle'] and '2라운드' in r2['pickle'], '반박 대상 표기 없음'
        assert 'Hark' in r2['pickle'], '반박 대상 이름 없음'
        assert p.inner_text('#talkCount') == '12건', '2라운드 기록: ' + p.inner_text('#talkCount')
        pills = p.eval_on_selector_all('.talk-item .pill','e=>e.map(x=>x.textContent)')
        assert any('2R' in x for x in pills), '2라운드 기록 표기 없음'
        print('OK 2라운드 정면 반박 · 6인 전부 다른 발언 · 기록 12건')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_round2.png')

        # 7) 3·4라운드 — 서로 다른 발언이 이어지고, 라운드 칩이 모두 완료
        play(p, 3)
        r3 = by_id(tiles(p))
        for k in r2:
            assert r2[k][:30] != r3[k][:30], '3라운드가 2라운드와 같은 발언: '+k
        assert p.inner_text('#talkCount') == '18건', '3라운드 기록: ' + p.inner_text('#talkCount')
        print('OK 3라운드 대안·절충 · 기록 18건')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_round3.png')

        play(p, 4)
        r4 = by_id(tiles(p))
        for k in r3:
            assert r3[k][:30] != r4[k][:30], '4라운드가 3라운드와 같은 발언: '+k
        assert p.inner_text('#talkCount') == '24건', '4라운드 기록: ' + p.inner_text('#talkCount')
        cs = chips(p)
        assert all(not c['d'] for c in cs), '4라운드 후 칩이 잠겨 있음: %s' % cs
        assert '다시 보기' in p.inner_text('#nextRoundBtn'), '마지막 라운드 후 버튼 문구: ' + p.inner_text('#nextRoundBtn')
        # 자료 상세에서 누적 라운드 발언을 볼 수 있다
        p.click('.tile[data-id="hark"] .matbtn'); p.wait_for_timeout(300)
        mr = p.inner_text('#matRounds')
        assert '2R' in mr and '3R' in mr and '4R' in mr, '자료 상세에 라운드 발언 누적 없음'
        p.click('#matModal .foot button[data-close]'); p.wait_for_timeout(200)
        print('OK 4라운드 최종 정리 · 기록 24건 · 누적 열람')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_round4.png')

        # 8) 오너 코멘트 → 6인 반응 (라운드 중에도 유지)
        p.fill('#interjectInput','이번 주는 제목 실험만 하자')
        p.click('#interjectSend')
        p.wait_for_timeout(700)
        c1 = by_id(tiles(p))
        assert '코멘트 반영' in c1['claude'], '오너 코멘트 반영 안 됨'
        assert any('제목 실험만' in x for x in p.eval_on_selector_all('.talk-item','e=>e.map(x=>x.innerText)')), '코멘트가 기록에 없음'
        print('OK 오너 코멘트 → 6인 반응')

        # 9) 결론 확정 — 라운드 진행 상황이 보인다
        p.click('#toConfirmBtn'); p.wait_for_timeout(500)
        assert p.is_visible('#confirmPanel'), '결론 패널 안 보임'
        assert not p.is_visible('#rolePanel'), '결론 확정 전인데 역할 패널 보임'
        assert p.eval_on_selector_all('#optList .opt','e=>e.length') == 3, '결론 후보 3개 아님'
        meta = p.inner_text('#cfMeta')
        assert '4/4' in meta, '결론 패널에 라운드 진행 표시 없음: ' + meta
        assert '4라운드까지' in p.inner_text('#cfHint'), '결론 힌트 없음'
        assert p.is_visible('#guestAdviceBox'), '게스트 조언 섹션 없음'
        gcards = p.eval_on_selector_all('#guestAdvice .gcard','e=>e.length')
        assert gcards == 2, '게스트 조언 2건 아님: %d' % gcards
        gt = p.inner_text('#guestAdvice')
        assert '추천 A' in gt and '놓친 포인트' in gt, '게스트 추천/놓친 포인트 없음'
        assert 'Meta Muse' in gt and 'Keyring' in gt, '게스트 이름 없음'
        print('OK 참관 게스트 최종 조언 2건 (추천·놓친 포인트)')
        p.screenshot(path=DL+'meeting_v41_desktop_guests.png')
        p.screenshot(path=DL+'meeting_v41_desktop_confirm.png')

        # 10) 결론 확정 → 역할 분담 (라운드 기록 포함)
        p.click('#optList .opt[data-id="A"]'); p.wait_for_timeout(200)
        p.fill('#ownerDirection','A로 가고 제목 교체는 내가 직접 한다')
        p.click('#confirmRoleBtn'); p.wait_for_timeout(800)
        assert p.is_visible('#rolePanel'), '역할 패널 안 보임'
        acs = p.eval_on_selector_all('#actionList .ac','e=>e.map(x=>x.innerText)')
        assert len(acs) == 6, '역할 카드 6개 아님: %d' % len(acs)
        assert '오너 추가 지시' in p.inner_text('#conclText')
        rt = p.evaluate("()=>window.__mr4.rolesText()")
        assert '### 논의 라운드' in rt and '2라운드' in rt, '복사용 회의록에 라운드 기록 없음'
        assert '참관 게스트 최종 조언' in rt, '복사용 회의록에 게스트 조언 없음'
        print('OK 결론 A → 역할 6건 · 복사록에 라운드 포함')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_roles.png')
        p.screenshot(path=WORK+'v41_desktop_roles.png')

        # 11) 결론 다시 고르기
        p.click('#changeOption'); p.wait_for_timeout(400)
        assert p.is_visible('#confirmPanel') and not p.is_visible('#rolePanel'), '결론 다시 고르기 안 됨'
        p.click('#optList .opt[data-id="C"]'); p.wait_for_timeout(150)
        p.click('#confirmRoleBtn'); p.wait_for_timeout(600)
        assert '이어보기' in p.inner_text('#conclText'), 'C 결론 반영 안 됨'
        print('OK 결론 다시 고르기 → C 재확정')

        # 12) 안건 2 → 자료·라운드 발언이 안건 1과 전부 다르다
        p.click('#newMeeting'); p.wait_for_timeout(400)
        p.click('.agcard[data-id="ldp-workflow"]'); p.wait_for_timeout(500)
        b2 = by_id(tiles(p))
        common = [k for k in a1 if k in b2]
        assert len(common) == 5, '두 안건 공통 주전 5인 아님: %s' % common
        same = [k for k in common if a1[k] == b2[k]]
        assert not same, '두 안건 자료가 동일: %s' % same
        ids2 = p.eval_on_selector_all('.tile','e=>e.map(x=>x.dataset.id)')
        assert 'meta_muse' in ids2 and 'chatgpt' not in ids2, '안건2 주전 교체 안 됨: %s' % ids2
        assert len(ids2) == 6, '안건2 주전 6인 아님: %s' % ids2
        gb2 = p.inner_text('#guestBar')
        assert 'ChatGPT' in gb2 and 'Keyring' in gb2, '안건2 게스트 교체 안 됨: ' + gb2
        print('OK 안건2 주전: Meta Muse 참가 / ChatGPT·Keyring 게스트')
        play(p, 1); play(p, 2)
        s2 = by_id(tiles(p))
        assert s2['pickle'][:30] != r2['pickle'][:30], '안건2 2라운드가 안건1과 같음'
        assert 'Gemini' in s2['pickle'], '안건2 반박 대상이 Gemini가 아님: ' + s2['pickle'][:50]
        play(p, 3); play(p, 4)
        assert p.inner_text('#talkCount') == '24건', '안건2 라운드 기록: ' + p.inner_text('#talkCount')
        print('OK 안건2 자료·4라운드 전부 다름 · 기록 24건')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_agenda2.png')

        # 13) 안건 예약(⏳) 추가 → 목록에 쌓이고, 새로고침해도 남는다
        p.click('#prepToggle'); p.wait_for_timeout(300)
        assert p.is_visible('#planList'), '준비실을 펼쳤는데 ⏳ 목록이 안 보임'
        before = p.eval_on_selector_all('#planList .wcard','e=>e.length')
        p.click('#planAddBtn'); p.wait_for_timeout(300)
        assert p.is_visible('#planModal'), '안건 예약 모달 안 열림'
        assert p.input_value('#planDate') == p.evaluate("()=>{const d=new Date();d.setDate(d.getDate()+1);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}"), '기본 예정일이 내일이 아님'
        p.fill('#planTopic','겨울 방한 장비 교체')
        p.click('#planSave'); p.wait_for_timeout(500)
        after = p.eval_on_selector_all('#planList .wcard','e=>e.length')
        assert after == before + 1, '예약 카드가 안 늘어남: %d → %d' % (before, after)
        assert not p.is_visible('#planModal'), '예약 후 모달이 안 닫힘'
        assert p.inner_text('#waitCnt') == '⏳ %d' % after, '⏳ 카운트 불일치'
        assert any('겨울 방한 장비 교체' in x for x in p.eval_on_selector_all('#planList .wcard','e=>e.map(x=>x.innerText)')), '예약 주제가 목록에 없음'
        p.reload(); p.wait_for_timeout(500)
        assert p.eval_on_selector_all('#planList .wcard','e=>e.length') == after, '새로고침 후 예약이 사라짐'
        # 같은 주제 중복 예약은 막힌다
        p.click('#planAddBtn'); p.wait_for_timeout(250)
        p.fill('#planTopic','겨울 방한 장비 교체'); p.click('#planSave'); p.wait_for_timeout(400)
        assert p.eval_on_selector_all('#planList .wcard','e=>e.length') == after, '중복 예약이 추가됨'
        print('OK ⏳ 안건 예약 · 새로고침 유지 · 중복 차단')
        p.wait_for_timeout(2200)
        p.screenshot(path=DL+'meeting_v41_desktop_plan.png')

        # 14) 이미 ✅인 주제를 예약하면 목록에서 열린다
        p.click('#planAddBtn'); p.wait_for_timeout(250)
        p.fill('#planTopic','LDP 롱보드 촬영·편집 워크플로우 효율화')
        p.click('#planSave'); p.wait_for_timeout(600)
        assert p.is_visible('#stage1Bar'), '이미 준비된 주제 예약 시 안건이 안 열림'
        print('OK 이미 ✅인 주제는 예약 대신 안건 열기')

        # 15) URL 파라미터
        qctx = b.new_context(viewport={'width':1440,'height':900})
        qp = qctx.new_page(); qp.add_init_script(MOCK)
        qp.goto(URL + '?agenda=ldp-workflow'); qp.wait_for_timeout(500)
        assert qp.is_visible('#stage1Bar'), '?agenda= 로 안 열림'
        assert 'LDP' in qp.inner_text('#readyTitle')
        print('OK URL 파라미터 ?agenda=ldp-workflow')

        # ═════════ 모바일 390x844 — 1열 큰 카드 ═════════
        m = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = m.new_page(); mp.add_init_script(MOCK)
        mp.on('pageerror', lambda e: errs.append('mobile-pageerror:'+str(e)))
        mp.goto(URL); mp.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','2')")
        mp.reload(); mp.wait_for_timeout(500)
        mp.wait_for_timeout(2200)
        mp.screenshot(path=DL+'meeting_v41_mobile_prep.png')
        ov = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov <= 1, '가로 스크롤(준비실): %d' % ov
        mp.click('.agcard[data-id="yt-growth"]')
        mp.wait_for_timeout(700)

        # 1열 배치
        cols = mp.evaluate("getComputedStyle(document.getElementById('stage')).gridTemplateColumns")
        assert len(cols.split()) == 1, '모바일 1열 아님: ' + cols
        # 본문 글자 15~16px · 줄간격 1.55 이상
        fs = mp.evaluate("parseFloat(getComputedStyle(document.querySelector('.tile .bubble')).fontSize)")
        assert 15 <= fs <= 16.5, '모바일 본문 글자 크기 %.1fpx' % fs
        lh = mp.evaluate("()=>{const s=getComputedStyle(document.querySelector('.tile .bubble'));return parseFloat(s.lineHeight)/parseFloat(s.fontSize)}")
        assert lh >= 1.55, '모바일 줄간격 %.2f' % lh
        heights = mp.eval_on_selector_all('.tile','e=>e.map(x=>Math.round(x.getBoundingClientRect().height))')
        assert all(h >= 140 for h in heights), '타일 높이 이상: %s' % heights
        widths = mp.eval_on_selector_all('.tile','e=>e.map(x=>Math.round(x.getBoundingClientRect().width))')
        assert min(widths) > 300, '카드 폭이 1열이 아님: %s' % widths
        ov = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov <= 1, '가로 스크롤(1라운드): %d' % ov
        mp.wait_for_timeout(2200)
        mp.screenshot(path=DL+'meeting_v41_mobile_round1.png')

        # 라운드 바가 한 줄로 보이고 넘치지 않는지
        bar_ov = mp.evaluate("()=>{const b=document.getElementById('roundBar');return b.scrollWidth-b.clientWidth}")
        assert bar_ov <= 1, '라운드 바 내부 가로 스크롤: %d' % bar_ov

        # 말하는 카드 강조 + 자동 스크롤
        mp.click('#nextRoundBtn')
        mp.wait_for_function("() => !!document.querySelector('.tile.speaking')", timeout=8000)
        sp = mp.evaluate("()=>{const t=document.querySelector('.tile.speaking');if(!t)return null;const s=getComputedStyle(t);return {shadow:s.boxShadow, bg:s.backgroundImage, id:t.dataset.id}}")
        assert sp and sp['shadow'] and sp['shadow'] != 'none', '말하는 카드 강조 없음'
        assert 'rgb' in sp['bg'], '말하는 카드 배경 강조 없음'
        mp.wait_for_function("(n) => window.__mr4.state.round >= n && window.__mr4.state.busy === false", arg=1, timeout=30000)
        scrolled = mp.evaluate("()=>window.scrollY")
        assert scrolled > 0, '말하는 카드로 자동 스크롤되지 않음: %d' % scrolled

        for n in (2, 3):
            mp.click('#nextRoundBtn')
            mp.wait_for_function("(n) => window.__mr4.state.round >= n && window.__mr4.state.busy === false", arg=n, timeout=30000)
            mp.wait_for_timeout(150)
        ov = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov <= 1, '가로 스크롤(3라운드): %d' % ov
        mp.evaluate("document.getElementById('stageHd').scrollIntoView({block:'start'})")
        mp.wait_for_timeout(400)
        mp.screenshot(path=DL+'meeting_v41_mobile_rounds.png')
        mp.screenshot(path=WORK+'v41_mobile_rounds.png')
        mp.screenshot(path=DL+'meeting_v41_mobile_rounds_full.png', full_page=True)

        # 결론 선택 → 참관 게스트 최종 조언
        mp.click('#toConfirmBtn'); mp.wait_for_timeout(500)
        mp.screenshot(path=DL+'meeting_v41_mobile_confirm.png')
        assert mp.is_visible('#guestAdviceBox'), '모바일 게스트 조언 섹션 없음'
        assert mp.eval_on_selector_all('#guestAdvice .gcard','e=>e.length') == 2, '모바일 게스트 조언 2건 아님'
        gfs = mp.evaluate("parseFloat(getComputedStyle(document.querySelector('#guestAdvice .gcw')).fontSize)")
        assert gfs >= 13, '게스트 조언 글자 %.1fpx' % gfs
        ov = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov <= 1, '가로 스크롤(결론): %d' % ov
        mp.evaluate("document.getElementById('guestAdviceBox').scrollIntoView({block:'start'})")
        mp.wait_for_timeout(400)
        mp.screenshot(path=DL+'meeting_v41_mobile_guests.png')

        mp.click('#optList .opt[data-id="B"]'); mp.wait_for_timeout(150)
        mp.click('#confirmRoleBtn'); mp.wait_for_timeout(700)
        mp.evaluate("document.getElementById('rolePanel').scrollIntoView({block:'start'})")
        mp.wait_for_timeout(400)
        mp.screenshot(path=DL+'meeting_v41_mobile_roles.png')
        print('OK 모바일 390x844 · 1열 큰 카드(%.0fpx, 줄간격 %.2f) · 말하는 카드 강조·자동스크롤 · 게스트 조언' % (fs, lh))
        b.close()

    if errs:
        print('ERRORS:'); [print(' ', e) for e in errs]
        sys.exit(1)
    print('ALL PASS')

main()
