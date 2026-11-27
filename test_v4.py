"""v4.2.1 검증 — 화상 자막 높이 고정·글로 보기 자동 스크롤 복원 (v4.2 검증에 추가)
- 안건 목록(✅ 준비 완료 / ⏳ 준비 중) → 4라운드 심화 토론 → 결론 확정 → 역할 분담 (v4.1 유지)
- 🎥 화상 6분할 ↔ 📝 글로 보기 토글이 되고, 모바일(390x844) 한 화면에 6타일이 스크롤 없이 꽉 차는지
- v4.2.1) 화상 모드 자막 바 높이 68px 고정 — 1줄/2줄 자막이 바뀌어도 6분할 grid top 불변
- v4.2.1) 화상 모드에서는 캐릭터 바운스 transform·점 웨이브 애니메이션 없음(정적), 자동 스크롤 0
- v4.2.1) 📝 글로 보기에서만 발언 카드로 smooth 자동 스크롤(focusTile) 복원
- 발언 전환 시 카드 높이 변화 0 (iOS 떨림 원인 제거)
- 발언 순서가 고정 [0,1,2,3,4,5]가 아니라 라운드마다 섞이는지
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
  // v4.2 — scrollIntoView(smooth) 호출 감시 (iOS 떨림 원인 제거 확인용)
  window.__siv=[];
  const __siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(o){ window.__siv.push((o&&o.behavior)||"auto"); return __siv.apply(this, arguments); };
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

def tile_heights(p):
    return p.eval_on_selector_all('.tile','e=>e.map(x=>Math.round(x.getBoundingClientRect().height))')

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

        # 3-b) v4.3/v4.5 — 비서실 8인 캐릭터 아바타(512x478 webp)가 실제로 로드되는지
        def face_report(page):
            return page.evaluate("""()=>[...document.querySelectorAll('img.face')].map(i=>({src:i.getAttribute('src'),nw:i.naturalWidth,nh:i.naturalHeight,
                w:Math.round(i.getBoundingClientRect().width),h:Math.round(i.getBoundingClientRect().height)}))""")
        p.wait_for_function("()=>[...document.querySelectorAll('img.face')].every(i=>i.complete && i.naturalWidth>0)", timeout=15000)
        fr = face_report(p)
        bad = [f for f in fr if not (f['nw'] == 512 and f['nh'] == 478)]
        assert not bad, '아바타 이미지 로드 실패/크기 이상: %s' % bad[:4]
        srcs = sorted(set(f['src'] for f in fr))
        assert all('/avatars/' in s for s in srcs), '아바타가 상대경로가 아님: %s' % srcs
        assert len(srcs) == 8, '8인 아바타가 다 안 쓰임: %d %s' % (len(srcs), srcs)
        tile_faces = p.eval_on_selector_all('.tile .avatar img.face','e=>e.length')
        vbob_faces = p.eval_on_selector_all('.tile .vstage .vbob img.face','e=>e.length')
        vbob_vids = p.eval_on_selector_all('.tile .vstage .vbob video.face','e=>e.length')
        guest_faces = p.eval_on_selector_all('#guestBar .gi .gie img.face','e=>e.length')
        assert tile_faces == 6 and vbob_faces == 5, '타일 아바타 6개 아님: %d / %d' % (tile_faces, vbob_faces)
        assert vbob_vids == 1, '화상 얼굴 자리에 피클 영상 1개가 없음: %d' % vbob_vids
        assert guest_faces == 2, '참관 게스트 썸네일 2개 아님: %d' % guest_faces
        assert p.eval_on_selector_all('.tile .vstage .vbob','e=>e.filter(x=>x.textContent.trim()).length') == 0, '화상 타일에 이모지가 남아 있음'
        print('OK 8인 캐릭터 아바타 로드 — naturalWidth 512x478 %d장 · 타일 6 · 게스트 2 · 상대경로 ./avatars/*.webp' % len(srcs))

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

        # 7-b) v4.2 — 발언 순서가 고정 1~6번이 아니라 매번 섞인다 (다시 틀어도 매번 다르게)
        ids_all = ['pickle','gemini','cue','hark','chatgpt','claude']
        orders = [p.evaluate("()=>window.__mr4.lastOrder()")]
        for _ in range(4):
            p.evaluate("(n)=>window.__mr4.playRound(n)", 3)
            orders.append(p.evaluate("()=>window.__mr4.lastOrder()"))
        for o in orders:
            assert sorted(o) == sorted(ids_all), '발언 순서가 6인 전체가 아님: %s' % o
        assert any(o != ids_all for o in orders), '발언 순서가 고정 6인 순서 그대로: %s' % orders
        assert len(set(tuple(o) for o in orders)) >= 2, '다시 틀어도 순서가 그대로: %s' % orders
        assert p.evaluate("()=>window.__mr4.orderLog().length") >= 5, '순서 기록이 없음'
        print('OK 랜덤 발언 순서 — 재생 5회 중 %d가지 순서 · 고정 순서 아님' % len(set(tuple(o) for o in orders)))

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

        # 말하는 카드 강조(테두리·배경만) + 카드 높이 불변 + 📝 글로 보기 자동 스크롤 복원 (v4.2.1)
        base_h = tile_heights(mp)
        # v4.4 — 발언 카드가 화면 '세로 중앙'으로 와야 한다.
        #   (v4.2.1 은 카드가 화면에 걸치기만 하면 안 움직여서, 아래·위 가장자리에 걸친 채 발언이 넘어갔다)
        #   매 프레임 지금 말하는 카드의 중앙 오차(err = 카드 중심 − 보이는 영역 중심)를 기록한다.
        mp.evaluate("""()=>{
            window.__center = [];
            (function loop(){
              const t = document.querySelector('.tile.speaking');
              if(t && window.__mr4){
                const b = window.__mr4.visibleCenter();
                const r = t.getBoundingClientRect();
                window.__center.push({id:t.dataset.id, err:Math.round(r.top + r.height/2 - b.center),
                                      top:Math.round(r.top), bottom:Math.round(r.bottom),
                                      bandTop:Math.round(b.top), bandBottom:Math.round(b.bottom),
                                      y:Math.round(window.pageYOffset)});
              }
              requestAnimationFrame(loop);
            })();
        }""")
        # 발언 간격을 실제 음성 속도(≈0.7초)에 가깝게 해 자동 스크롤이 안착하는지 보게 한다
        mp.evaluate("()=>{ localStorage.setItem('darkjin_mr4_speed','0.25'); window.__mr4.state.speed=0.25; }")
        mp.evaluate("()=>window.scrollTo(0, document.documentElement.scrollHeight)")   # 발언 카드가 화면 밖에 있도록 아래로 내려 둔다
        mp.wait_for_timeout(200)
        mp.click('#nextRoundBtn')
        mp.wait_for_function("() => !!document.querySelector('.tile.speaking')", timeout=8000)
        sp = mp.evaluate("""()=>{const t=document.querySelector('.tile.speaking');if(!t)return null;const s=getComputedStyle(t);return {border:s.borderTopColor, shadow:s.boxShadow, bg:s.backgroundImage, id:t.dataset.id}}""")
        assert sp and sp['border'].replace(' ','') == 'rgb(46,224,106)', '말하는 카드 테두리 강조 없음: %s' % (sp and sp['border'])
        assert sp['shadow'] == 'none', '발언 카드에 boxShadow 변화가 남아 있음: %s' % sp['shadow']
        assert 'rgb' in sp['bg'], '말하는 카드 배경 강조 없음'
        hs = []
        while mp.evaluate("()=>window.__mr4.state.busy"):
            hs.append(tile_heights(mp))
            mp.wait_for_timeout(70)
        bad = [h for h in hs if h != base_h]
        assert not bad, '발언 전환 중 카드 높이가 변함(iOS 떨림): %s' % bad[:2]
        mp.wait_for_timeout(500)
        log = mp.evaluate("()=>window.__center")
        per = []
        for s in log:
            if not per or per[-1]['id'] != s['id']: per.append(dict(s))
            else: per[-1].update(s)
        assert len(per) >= 5, '발언자 순서 기록이 부족: %s' % [x['id'] for x in per]
        max_scroll = mp.evaluate("()=>Math.round(document.documentElement.scrollHeight - innerHeight)")
        stuck = []
        for x in per:
            if abs(x['err']) <= 12: continue
            # 문서 끝/처음에 걸려 더 못 올리는 경우는 카드 전체가 보이면 통과
            at_edge = x['y'] <= 2 or x['y'] >= max_scroll - 2
            if at_edge and x['top'] >= x['bandTop'] - 1 and x['bottom'] <= x['bandBottom'] + 1: continue
            stuck.append(x)
        assert not stuck, '발언 카드가 화면 세로 중앙에 오지 않음: %s' % stuck
        sv = per[-1]
        mp.evaluate("()=>{ localStorage.setItem('darkjin_mr4_speed','2'); window.__mr4.state.speed=2; }")
        print('OK 발언 떨림 없음 — 카드 높이 %s 일정 · 글로 보기 발언 카드 세로 중앙(보이는 영역 %d~%d 중심 %d) · %d명 순서대로 중앙 오차(px) %s' % (base_h[:2], per[0]['bandTop'], per[0]['bandBottom'], (per[0]['bandTop']+per[0]['bandBottom'])//2, len(per), [(x['id'], x['err']) for x in per]))

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

        # ═════════ v4.2 — 🎥 화상 6분할 ↔ 📝 글로 보기 ═════════
        assert mp.is_visible('#viewBar'), '보기 전환 토글이 없음'
        assert mp.inner_text('#viewTextBtn').strip().endswith('글로 보기'), '글로 보기 버튼 문구 이상'
        mp.click('#viewVideoBtn'); mp.wait_for_timeout(450)
        assert mp.evaluate("()=>document.body.classList.contains('view-video')"), '화상 6분할 모드 클래스 없음'
        assert mp.is_visible('#vsub'), '화상 모드 자막 바 없음'
        assert not mp.is_visible('.talk'), '화상 모드에 논의 기록이 남아 있음'
        cols = mp.evaluate("getComputedStyle(document.getElementById('stage')).gridTemplateColumns")
        rows = mp.evaluate("getComputedStyle(document.getElementById('stage')).gridTemplateRows")
        assert len(cols.split()) == 2, '모바일 화상 모드 2열 아님: ' + cols
        assert len(rows.split()) == 3, '모바일 화상 모드 3행 아님: ' + rows
        ih = mp.evaluate("()=>window.innerHeight"); iw = mp.evaluate("()=>window.innerWidth")
        rects = mp.eval_on_selector_all('.tile', """els=>els.map(e=>{const r=e.getBoundingClientRect();return {t:Math.round(r.top),b:Math.round(r.bottom),l:Math.round(r.left),rr:Math.round(r.right),h:Math.round(r.height)}})""")
        assert len(rects) == 6, '화상 모드 타일 6개 아님: %d' % len(rects)
        assert all(r['t'] >= -1 and r['b'] <= ih+1 and r['l'] >= -1 and r['rr'] <= iw+1 for r in rects), '화상 모드에서 타일이 화면 밖: %s (뷰포트 %dx%d)' % (rects, iw, ih)
        assert all(r['h'] >= 90 for r in rects), '화상 타일이 너무 납작함: %s' % [r['h'] for r in rects]
        sh = mp.evaluate("()=>document.documentElement.scrollHeight")
        assert sh <= ih + 2, '화상 모드에서 세로 스크롤이 생김: %d > %d' % (sh, ih)
        # 타일엔 긴 본문 대신 캐릭터·이름·상태만, 한 줄 자막은 전용 바 1곳에
        assert mp.evaluate("()=>{const w=document.querySelector('.tile .stagewrap');return Math.round(w.getBoundingClientRect().height)}") == 0, '화상 모드에 본문 글이 남아 있음'
        assert mp.evaluate("()=>{const v=document.querySelector('.tile .vstage');return Math.round(v.getBoundingClientRect().height)}") > 40, '화상 모드 캐릭터 영역 없음'
        vn = mp.eval_on_selector_all('.tile .vnm','e=>e.map(x=>x.textContent)')
        assert len(vn) == 6 and 'Gemini' in vn and 'Claude' in vn, '화상 타일 이름 이상: %s' % vn
        assert mp.inner_text('#vsTx').strip(), '자막 바가 비어 있음'
        # v4.3 — 6분할 얼굴 자리에 실제 캐릭터 사진이 원형 프레임을 꽉 채운다(정사각 유지·object-fit:cover)
        VFACE = "els=>els.map(i=>({src:i.getAttribute('src'),nw:i.naturalWidth,w:Math.round(i.getBoundingClientRect().width),h:Math.round(i.getBoundingClientRect().height),fit:getComputedStyle(i).objectFit,rad:getComputedStyle(i).borderRadius}))"
        # v4.4 — 피클 얼굴 자리는 정지 이미지 대신 움직이는 영상(videos → 5장 + video 1)
        vface = mp.eval_on_selector_all('.tile .vstage .vbob img.face', VFACE)
        assert len(vface) == 5, '화상 타일 얼굴 5개(피클은 영상) 아님: %d' % len(vface)
        assert all(f['nw'] == 512 for f in vface), '화상 타일 아바타 로드 실패: %s' % [f['src'] for f in vface if f['nw'] != 512]
        assert all(f['fit'] == 'cover' for f in vface), '화상 타일 얼굴 object-fit 이 cover 아님: %s' % set(f['fit'] for f in vface)
        # v4.5 — 풀블리드: 타일 안 미디어가 타일 전체(테두리 안쪽)를 꽉 채운다
        bleed = mp.evaluate("""()=>[...document.querySelectorAll('.tile')].map(t=>{
            const r=t.getBoundingClientRect(), b=t.querySelector('.vbob').getBoundingClientRect();
            const m=t.querySelector('.vbob img.face, .vbob video.face');
            const mr=m.getBoundingClientRect(), s=getComputedStyle(m);
            return {id:t.dataset.id, tile:[Math.round(r.width),Math.round(r.height)],
                    media:[Math.round(mr.width),Math.round(mr.height)], frame:[Math.round(b.width),Math.round(b.height)],
                    fit:s.objectFit, pos:s.objectPosition, rad:s.borderRadius};})""")
        assert len(bleed) == 6, '화상 타일 6개 아님: %d' % len(bleed)
        assert all(abs(x['media'][0]-x['frame'][0]) <= 1 and abs(x['media'][1]-x['frame'][1]) <= 1 for x in bleed), '미디어가 프레임과 크기가 다름: %s' % bleed
        assert all(x['frame'][0] >= x['tile'][0]-6 and x['frame'][1] >= x['tile'][1]-6 for x in bleed), '미디어가 타일을 꽉 채우지 않음: %s' % bleed
        assert all(x['fit'] == 'cover' and x['rad'] == '0px' and x['pos'].endswith('45%') for x in bleed), '풀블리드 속성 이상: %s' % bleed
        # 화상 모드 타일 상태는 화상통화처럼 '듣는 중 / 발언 중'
        vstates = set(mp.eval_on_selector_all('.tile .vstate','e=>e.map(x=>x.textContent)'))
        assert vstates <= {'듣는 중','발언 중','배정','대기','조용'}, '화상 타일 상태 문구 이상: %s' % vstates
        # v4.2.1 — 화상 모드에서는 캐릭터 바운스·점 웨이브 모션이 없다(정적 상태 + 테두리·배경색만)
        mp.wait_for_timeout(2500)
        mp.evaluate("()=>{ window.__siv = []; }")
        mp.evaluate("()=>{ window.__mr4.playRound(2); }")
        mp.wait_for_function("()=>!!document.querySelector('.tile.speaking')", timeout=8000)
        vsp = mp.evaluate("""()=>{const t=document.querySelector('.tile.speaking');const b=t.querySelector('.vbob');const w=t.querySelector('.vw');const i=w.querySelector('i');const bs=getComputedStyle(b), is=getComputedStyle(i);
            return {id:t.dataset.id, anim:bs.animationName, tf:bs.transform, wc:bs.willChange, tr:bs.transitionDuration, vw:getComputedStyle(w).display, dot:is.animationName, dotH:is.height}}""")
        assert vsp['anim'] == 'none', '화상 발언 캐릭터에 바운스 애니메이션이 남아 있음: ' + vsp['anim']
        assert vsp['tf'] == 'none', '발언 캐릭터에 transform이 걸려 있음: ' + vsp['tf']
        assert vsp['wc'] == 'auto', '발언 캐릭터에 will-change(컴포짓 레이어)가 남아 있음: ' + vsp['wc']
        assert vsp['tr'].split(',')[0].strip() in ('0s',), '발언 캐릭터 transition이 남아 있음: ' + vsp['tr']
        assert vsp['vw'] == 'flex', '발언 캐릭터 웨이브 없음'
        assert vsp['dot'] == 'none', '점 웨이브 애니메이션이 남아 있음: ' + vsp['dot']
        react_on = mp.evaluate("()=>Array.from(document.querySelectorAll('.tile .react.on')).map(x=>x.textContent)")
        assert len(react_on) >= 1, '옆 캐릭터 리액션 배지가 없음'
        sub_txt = mp.inner_text('#vsub')
        assert '라운드' in sub_txt and len(sub_txt) > 10, '자막 바에 발언이 안 나옴: ' + sub_txt[:60]
        mp.wait_for_timeout(180)
        mp.screenshot(path=DL+'meeting_v42_mobile_video6.png', full_page=False)

        # 자막 바 높이 고정(68px) — 1줄↔2줄 자막이 바뀌어도 위 6분할 grid가 1px도 밀리지 않는다
        cap_h, stage_t, tx_h, ys, scrolls = [], [], [], [], []
        while mp.evaluate("()=>window.__mr4.state.busy"):
            s = mp.evaluate("""()=>{const v=document.getElementById('vsub');const tx=document.getElementById('vsTx');const st=document.getElementById('stage');
                return {h:Math.round(v.getBoundingClientRect().height), t:Math.round(st.getBoundingClientRect().top), b:Math.round(st.getBoundingClientRect().bottom),
                        tx:Math.round(tx.scrollHeight), y:Math.round(window.scrollY), vt:Math.round(v.getBoundingClientRect().top)}}""")
            cap_h.append(s['h']); stage_t.append(s['t']); tx_h.append(s['tx']); ys.append(s['y'])
            scrolls.append(s['b'] - s['vt'])
            mp.wait_for_timeout(60)
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=30000)
        assert cap_h and all(h == 68 for h in cap_h), '화상 모드 자막 바 높이가 변함: %s' % sorted(set(cap_h))
        assert len(set(stage_t)) == 1, '자막 줄 수에 따라 6분할 grid가 밀림: %s' % sorted(set(stage_t))
        assert max(scrolls) <= 1, '자막 바와 6분할 사이가 벌어짐: %s' % max(scrolls)
        assert set(ys) == {0}, '화상 모드에서 페이지가 스크롤됨: %s' % sorted(set(ys))
        # 자막을 1줄/2줄/3줄로 갈아 끼워도 자막 바·6분할 top이 1px도 안 변한다
        cap_fix = []
        for who, tag, txt in [
            ('claude', '1라운드', '짧게.'),
            ('gemini', '1라운드', '한 줄짜리 자막입니다. 높이는 그대로여야 합니다.'),
            ('hark', '2라운드 · → Gemini에게', '두 줄로 접히는 긴 자막입니다. 두 번째 줄까지 들어가고도 자막 바 높이는 68px 그대로여야 합니다. 카드가 밀리면 안 됩니다.'),
            ('cue', '3라운드', '아주 긴 자막. ' * 12),
        ]:
            mp.evaluate("(a)=>window.__mr4.sub(a[0], a[1], a[2])", [who, tag, txt])
            mp.wait_for_timeout(120)
            m = mp.evaluate("""()=>{const v=document.getElementById('vsub');const tx=document.getElementById('vsTx');const st=document.getElementById('stage');const cb=document.getElementById('stage1Bar');
                return {h:Math.round(v.getBoundingClientRect().height), st:Math.round(st.getBoundingClientRect().top),
                        sb:Math.round(st.getBoundingClientRect().bottom), vt:Math.round(v.getBoundingClientRect().top),
                        txh:Math.round(tx.getBoundingClientRect().height), cb:Math.round(cb.getBoundingClientRect().top)}}""")
            cap_fix.append(m)
        assert all(m['h'] == 68 for m in cap_fix), '자막 길이에 따라 자막 바 높이가 변함: %s' % [m['h'] for m in cap_fix]
        assert all(m['txh'] == 38 for m in cap_fix), '자막 본문 높이가 변함: %s' % [m['txh'] for m in cap_fix]
        assert len(set((m['st'], m['sb'], m['vt'], m['cb']) for m in cap_fix)) == 1, '자막 길이에 따라 6분할 grid가 밀림: %s' % [(m['st'], m['sb'], m['vt'], m['cb']) for m in cap_fix]
        mp.evaluate("()=>window.__mr4.sub(null, '', '', true)")
        print('OK 자막 바 68px 고정 — 1줄/2줄/3줄·아주 긴 자막 4종 모두 높이 %s · grid top %s 불변(재생 중 %d샘플도 동일)' % ([m['h'] for m in cap_fix], cap_fix[0]['st'], len(cap_h)))
        smv = [b for b in mp.evaluate("()=>window.__siv") if b == 'smooth']
        assert not smv, '화상 모드에서 scrollIntoView(smooth)가 호출됨: %s' % mp.evaluate("()=>window.__siv")
        # focusTile을 직접 불러도 화상 모드에서는 스크롤하지 않는다
        mp.evaluate("()=>{ window.__siv = []; }")
        mp.evaluate("()=>window.__mr4.focusTile('gemini')")
        assert mp.evaluate("()=>window.__siv") == [], '화상 모드에서 focusTile이 스크롤을 시도함: %s' % mp.evaluate("()=>window.__siv")
        print('OK 화상 6분할 — 390x844 한 화면 2x3 · 스크롤 없음 · 캐릭터 %s 발언 · 리액션 %s · 모션 0 · 자막 바 %dpx 고정(%d샘플·자막높이 %s)' % (vsp['id'], react_on, cap_h[0], len(cap_h), sorted(set(tx_h))))

        # 다시 글로 보기
        mp.click('#viewTextBtn'); mp.wait_for_timeout(450)
        assert not mp.evaluate("()=>document.body.classList.contains('view-video')"), '글로 보기로 안 돌아옴'
        assert mp.is_visible('.talk'), '글로 보기에서 논의 기록이 안 보임'
        cols2 = mp.evaluate("getComputedStyle(document.getElementById('stage')).gridTemplateColumns")
        assert len(cols2.split()) == 1, '글로 보기 1열 아님: ' + cols2
        assert mp.evaluate("()=>{const b=document.querySelector('.tile .bubble');return Math.round(b.getBoundingClientRect().height)}") > 100, '글로 보기인데 본문이 숨겨져 있음'
        mp.wait_for_timeout(2500)
        mp.evaluate("document.getElementById('stageHd').scrollIntoView({block:'start'})")
        mp.wait_for_timeout(400)
        mp.screenshot(path=DL+'meeting_v42_mobile_text.png', full_page=False)
        print('OK 글로 보기 복귀 — 1열 큰 카드(%.1fpx) · 본문 복원' % mp.evaluate("parseFloat(getComputedStyle(document.querySelector('.tile .bubble')).fontSize)"))

        # 결론 선택 → 참관 게스트 최종 조언
        mp.click('#toConfirmBtn'); mp.wait_for_timeout(500)
        mp.screenshot(path=DL+'meeting_v41_mobile_confirm.png')
        assert mp.is_visible('#guestAdviceBox'), '모바일 게스트 조언 섹션 없음'
        assert mp.eval_on_selector_all('#guestAdvice .gcard','e=>e.length') == 2, '모바일 게스트 조언 2건 아님'
        assert mp.eval_on_selector_all('#guestAdvice .gcard .gce img.face','e=>e.length') == 2, '게스트 최종 조언에 캐릭터 썸네일 없음'
        assert mp.evaluate("()=>[...document.querySelectorAll('#guestAdvice .gce img.face')].every(i=>i.naturalWidth===512)"), '게스트 조언 썸네일 로드 실패'
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
        # v4.3 — 역할 분담 카드도 이모지 대신 캐릭터 썸네일
        assert mp.eval_on_selector_all('#actionList .ac .em img.face','e=>e.length') == 6, '역할 분담 카드에 캐릭터 썸네일 6개 아님'
        assert mp.evaluate("()=>[...document.querySelectorAll('#actionList .ac .em img.face')].every(i=>i.naturalWidth===512)"), '역할 카드 썸네일 로드 실패'
        print('OK 모바일 390x844 · 1열 큰 카드(%.0fpx, 줄간격 %.2f) · 말하는 카드 테두리 강조·자막 바 68px 고정 · 게스트 조언 · 역할 카드 썸네일' % (fs, lh))
        b.close()

    if errs:
        print('ERRORS:'); [print(' ', e) for e in errs]
        sys.exit(1)
    print('ALL PASS')

main()
