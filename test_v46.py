"""v4.6 검증 — 회의 서류철 로비 · 입장 인트로 · 6분할 본방 진입

성진님 지시
  "들어가면 준비된 회의 안건 고르는 거랑 다음에 회의를 할 안건을 적고 입장..
   영상이 있으면 다들 의자에 앉거나 화상회의 준비하는 그런 영상 나오고 우리가 만든 페이지 로딩 되면 좋겠어"

무엇을 재는가
① 로비(첫 화면) — 📁 회의 브리핑 서류가 뜨고, ✅ 준비 완료 안건만 라디오로 고를 수 있다.
   · 기본 선택 1건 · 고른 안건 이름이 하단 '선택한 안건'과 일치 · 선택은 localStorage 에 남는다
   · 🚪 회의실 입장 버튼이 토스트에 가리지 않는다(첫 화면에서 자료 준비 토스트를 띄우지 않음)
② 다음 회의 안건 메모 — 저장(누적·새로고침 유지) · 복사(피클에게 보내는 요청문) · 삭제
③ 입장 인트로 — avatars/intro_meeting.mp4 가 실제로 재생되고(재생 시간 증가), 고른 안건 이름이 뜬다.
   · 건너뛰기 → 곧바로 그 안건의 6분할 회의실(화상 보기) · 타일 6장
   · 영상이 끝나면(3.9초) 자동으로 회의실 진입 · 로비는 닫힌다
   · 이미 보던 안건으로 다시 입장하면 인트로를 다시 틀지 않고 이어서 본다
④ 회의 중 📁 서류 — 로비로 나가면 잠시 멈추고, 다시 입장하면 이어서 진행된다
⑤ 데스크톱 1440x900 — 로비 가로 넘침 0 · 인트로 영상이 화면 안 · 6분할 타일 6장
"""
import sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'

MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },380); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;

  /* 복사 확인용 — 클립보드에 실제로 들어간 문자열을 잡아 둔다 */
  window.__copied = [];
  try{ Object.defineProperty(window,'isSecureContext',{value:true, configurable:true}); }catch(e){}
  try{
    Object.defineProperty(navigator,'clipboard',{configurable:true, value:{
      writeText(t){ window.__copied.push(t); return Promise.resolve(); }
    }});
  }catch(e){}
  const ex = document.execCommand;
  document.execCommand = function(cmd){ if(cmd === 'copy'){ const a=document.activeElement; if(a && a.value) window.__copied.push(a.value); return true; } return ex.apply(document, arguments); };
})();
"""


def main():
    fails = []
    errs = []

    def ok(msg):
        print('OK ' + msg)

    def bad(msg):
        fails.append(msg)
        print('FAIL ' + msg)

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])

        # ═════════════════ 모바일 390x844 ═════════════════
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        p = ctx.new_page(); p.add_init_script(MOCK)
        p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        p.goto(URL)
        p.evaluate("localStorage.clear()")
        p.reload(); p.wait_for_timeout(600)

        # ══════════ ① 로비 ══════════
        lobby = p.evaluate("()=>window.__mr4.lobby()")
        if not lobby['open']:
            bad('첫 화면이 로비가 아님')
        else:
            ok('첫 화면 = 회의 서류철 로비')
        if not p.is_visible('#lobbyDoc'):
            bad('서류 카드가 안 보임')
        ags = lobby['agendas']
        if len(ags) < 2:
            bad('준비된 안건이 2건 미만: %s' % ags)
        if sum(1 for a in ags if a['checked']) != 1 or sum(1 for a in ags if a['sel']) != 1:
            bad('기본 선택이 1건이 아님: %s' % ags)
        else:
            ok('준비된 안건 %d건 · 기본 선택 1건 (%s)' % (len(ags), lobby['sel']))
        title0 = p.inner_text('#lobbyPickTitle')
        row0 = p.inner_text('#lobbyAgList .agdoc-item.sel')
        if not title0 or title0 not in row0:
            bad('하단 "선택한 안건"이 목록 선택과 다름: %r / %r' % (title0, row0))
        else:
            ok('선택한 안건 표시 일치 — %s' % title0)
        if not p.is_visible('#enterBtn'):
            bad('🚪 회의실 입장 버튼이 안 보임')

        # 입장 버튼을 토스트가 가리지 않는지(첫 화면)
        hit = p.evaluate("""()=>{
            const b=document.getElementById('enterBtn'); const r=b.getBoundingClientRect();
            const el=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
            const t=document.getElementById('toast');
            return {ok: !!(el && b.contains(el)), hit: el ? (el.id||el.className||el.tagName) : null,
                    toast: t ? t.classList.contains('show') : false, toastText: t?t.textContent:''};
        }""")
        if not hit['ok'] or hit['toast']:
            bad('입장 버튼이 가려짐/토스트 겹침: %s' % hit)
        else:
            ok('입장 버튼 클릭 가능 · 첫 화면 토스트 없음')

        # 두 번째 안건으로 바꾸기
        other = [a for a in ags if a['id'] != lobby['sel']][0]['id']
        p.click('#lobbyAgList .agdoc-item[data-id="%s"]' % other)
        p.wait_for_timeout(250)
        l2 = p.evaluate("()=>window.__mr4.lobby()")
        saved = p.evaluate("()=>localStorage.getItem('darkjin_mr46_sel')")
        if l2['sel'] != other or saved != other:
            bad('안건 선택이 바뀌지 않음: sel=%s saved=%s' % (l2['sel'], saved))
        else:
            ok('안건 선택 변경 → localStorage 저장 (%s)' % other)
        if p.inner_text('#lobbyPickTitle') != p.inner_text('#lobbyAgList .agdoc-item.sel .ai-title'):
            bad('선택 변경 후 "선택한 안건" 이름 불일치')
        else:
            ok('선택 변경 후 하단 표시도 같은 안건')

        # ══════════ ② 다음 회의 안건 메모 ══════════
        memo_txt = '릴스 3편 업로드 순서 정하기 — 어떤 순서로 올리면 조회수가 붙을지'
        p.fill('#memoInput', memo_txt)
        p.click('#memoSave'); p.wait_for_timeout(300)
        memos = p.evaluate("()=>window.__mr4.lobby().memos")
        if len(memos) != 1 or memos[0]['text'] != memo_txt:
            bad('메모 저장 실패: %s' % memos)
        else:
            ok('다음 안건 메모 저장 — 1건 · %s' % p.inner_text('#lobbyMemoN'))
        p.fill('#memoInput', '두 번째 메모')
        p.click('#memoSave'); p.wait_for_timeout(250)
        if len(p.evaluate("()=>window.__mr4.lobby().memos")) != 2:
            bad('메모가 누적되지 않음')
        else:
            ok('메모 누적 — 2건 (목록·카운터 %s)' % p.inner_text('#lobbyMemoN'))

        # 복사 → 피클에게 보내는 요청문
        p.evaluate("()=>{ window.__copied.length = 0; }")
        # 목록은 최신이 위 — 첫 줄이 방금 저장한 '두 번째 메모'
        assert '두 번째 메모' in p.inner_text('#memoList .memo:first-child'), '메모 목록 순서 이상'
        p.click('#memoList .memo:first-child .memo-b[data-act="copy"]')
        p.wait_for_timeout(350)
        copied = p.evaluate("()=>window.__copied")
        req = copied[-1] if copied else ''
        if '[회의 안건 예약]' not in req or '두 번째 메모' not in req or '피클' not in req:
            bad('복사문이 요청문이 아님: %r' % req[:120])
        else:
            ok('메모 복사 — 피클 요청문 %d자' % len(req))

        # 삭제
        p.click('#memoList .memo:first-child .memo-b[data-act="del"]')
        p.wait_for_timeout(250)
        if len(p.evaluate("()=>window.__mr4.lobby().memos")) != 1:
            bad('메모 삭제 실패')
        else:
            ok('메모 삭제 — 1건 남음')

        # 새로고침 후 유지
        p.reload(); p.wait_for_timeout(600)
        l3 = p.evaluate("()=>window.__mr4.lobby()")
        if len(l3['memos']) != 1 or l3['memos'][0]['text'] != memo_txt:
            bad('새로고침 후 메모 사라짐: %s' % l3['memos'])
        else:
            ok('새로고침 후에도 메모·선택 유지 (%s / %s)' % (l3['sel'], l3['memos'][0]['text'][:16] + '…'))
        if l3['sel'] != other:
            bad('새로고침 후 안건 선택이 되돌아감: %s' % l3['sel'])

        # ══════════ ③ 입장 인트로 ══════════
        p.click('#enterBtn'); p.wait_for_timeout(700)
        li = p.evaluate("()=>window.__mr4.lobby()")
        if not li['introShown']:
            bad('입장을 눌렀는데 인트로가 안 뜸')
        else:
            ok('입장 → 인트로 표시 (intro-on)')
        if not p.is_visible('#introVid'):
            bad('인트로 영상 요소가 안 보임')
        vsrc = p.get_attribute('#introVid', 'src') or ''
        if 'intro_meeting.mp4' not in vsrc:
            bad('인트로 영상 주소 이상: %r' % vsrc[:80])
        else:
            ok('인트로 영상 = %s' % vsrc)
        t1 = p.evaluate("()=>document.getElementById('introVid').currentTime")
        p.wait_for_timeout(700)
        t2 = p.evaluate("()=>document.getElementById('introVid').currentTime")
        paused = p.evaluate("()=>document.getElementById('introVid').paused")
        if paused or t2 <= t1:
            bad('인트로 영상이 재생되지 않음 (%.2f → %.2f, paused=%s)' % (t1, t2, paused))
        else:
            ok('인트로 영상 실제 재생 — %.2f초 → %.2f초' % (t1, t2))
        ipick = p.inner_text('#introPickTitle')
        if p.inner_text('#lobbyAgList .agdoc-item.sel .ai-title') not in ipick:
            bad('인트로에 고른 안건 이름이 없음: %r' % ipick)
        else:
            ok('인트로에 고른 안건 표시 — %s' % ipick)
        if not p.is_visible('#introSkip'):
            bad('건너뛰기 버튼 없음')
        else:
            ok('건너뛰기 버튼 있음')

        # 건너뛰기 → 회의실
        p.click('#introSkip')
        p.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=2500)
        p.wait_for_timeout(600)
        room = p.evaluate("""()=>({phase:window.__mr4.state.phase, view:window.__mr4.view(),
            agenda: window.__mr4.state.agenda ? window.__mr4.state.agenda.id : null,
            lobby: document.body.classList.contains('lobby-on'),
            tiles: document.querySelectorAll('.stage > .tile').length,
            vids: [...document.querySelectorAll('.stage video')].length})""")
        if room['lobby']:
            bad('건너뛰기 후에도 로비가 남음')
        if room['view'] != 'video' or room['tiles'] != 6:
            bad('건너뛰기 후 회의실 상태 이상: %s' % room)
        if room['agenda'] != other:
            bad('고른 안건이 아니라 다른 안건이 열림: %s' % room['agenda'])
        else:
            ok('건너뛰기 → 고른 안건의 6분할 화상 회의실 (%s · 타일 %d)' % (room['agenda'], room['tiles']))

        # ══════════ ④ 회의 중 📁 서류 → 다시 입장(이어서) ══════════
        p.click('#nextRoundBtn')
        p.wait_for_function("()=>window.__mr4.state.round >= 1 && window.__mr4.state.busy === false", timeout=30000)
        before = p.evaluate("()=>window.__mr4.state.round")
        p.click('#lobbyBackBtn'); p.wait_for_timeout(400)
        lb = p.evaluate("""()=>({lobby: document.body.classList.contains('lobby-on'),
            paused: window.__mr4.state.paused, sel: window.__mr4.lobby().sel})""")
        if not lb['lobby'] or not lb['paused']:
            bad('회의 중 서류를 눌렀는데 로비가 안 열리거나 멈추지 않음: %s' % lb)
        else:
            ok('회의 중 📁 서류 — 로비 열림 · 회의 잠시 정지 (round %s)' % before)
        p.click('#enterBtn'); p.wait_for_timeout(700)
        lr = p.evaluate("""()=>({intro: document.body.classList.contains('intro-on'),
            lobby: document.body.classList.contains('lobby-on'), paused: window.__mr4.state.paused,
            round: window.__mr4.state.round, agenda: window.__mr4.state.agenda ? window.__mr4.state.agenda.id : null})""")
        if lr['intro'] or lr['lobby']:
            bad('이어보기인데 인트로/로비가 남음: %s' % lr)
        elif lr['paused'] or lr['round'] != before or lr['agenda'] != other:
            bad('이어보기 상태 이상: %s' % lr)
        else:
            ok('같은 안건 재입장 — 인트로 다시 틀지 않고 %s라운드에서 이어서 (일시정지 해제)' % lr['round'])

        # ══════════ 자동 종료(영상 끝) ══════════
        p.evaluate("()=>window.__mr4.showLobby()")
        p.wait_for_timeout(200)
        p.click('#lobbyAgList .agdoc-item[data-id="%s"]' % lobby['sel'])
        p.wait_for_timeout(200)
        p.click('#enterBtn')
        p.wait_for_function("()=>document.body.classList.contains('intro-on')", timeout=2000)
        p.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=9000)
        p.wait_for_timeout(500)
        auto = p.evaluate("""()=>({lobby: document.body.classList.contains('lobby-on'),
            view: window.__mr4.view(), agenda: window.__mr4.state.agenda ? window.__mr4.state.agenda.id : null,
            tiles: document.querySelectorAll('.stage > .tile').length,
            vtime: Math.round(document.getElementById('introVid').currentTime*100)/100})""")
        if auto['lobby'] or auto['view'] != 'video' or auto['tiles'] != 6:
            bad('인트로 자동 종료 후 회의실 진입 실패: %s' % auto)
        elif auto['agenda'] != lobby['sel']:
            bad('자동 종료 후 안건이 다름: %s' % auto)
        else:
            ok('인트로 영상 끝 → 자동으로 6분할 회의실 (%s · 타일 %d · 영상 %.2f초)' % (auto['agenda'], auto['tiles'], auto['vtime']))

        # ══════════ ⑤ 데스크톱 ══════════
        dctx = b.new_context(viewport={'width': 1440, 'height': 900})
        dp = dctx.new_page(); dp.add_init_script(MOCK)
        dp.on('pageerror', lambda e: errs.append('desktop pageerror:' + str(e)))
        dp.goto(URL); dp.evaluate("localStorage.clear()")
        dp.reload(); dp.wait_for_timeout(600)
        d = dp.evaluate("""()=>{
            const doc=document.getElementById('lobbyDoc').getBoundingClientRect();
            const btn=document.getElementById('enterBtn').getBoundingClientRect();
            return {open: document.body.classList.contains('lobby-on'),
                    sw: document.documentElement.scrollWidth, iw: innerWidth,
                    docW: Math.round(doc.width), btnIn: btn.bottom <= innerHeight+1 && btn.top >= 0,
                    memoTa: !!document.getElementById('memoInput')};
        }""")
        if not d['open'] or d['sw'] > d['iw'] + 1 or not d['btnIn'] or not d['memoTa']:
            bad('데스크톱 로비 이상: %s' % d)
        else:
            ok('데스크톱 1440x900 로비 — 가로 넘침 0 · 서류 폭 %dpx · 입장 버튼·메모란 화면 안' % d['docW'])
        dp.click('#enterBtn'); dp.wait_for_timeout(700)
        dv = dp.evaluate("""()=>{ const v=document.getElementById('introVid'); const r=v.getBoundingClientRect();
            return {w: Math.round(r.width), h: Math.round(r.height), inView: r.top >= -1 && r.bottom <= innerHeight+1,
                    playing: !v.paused && v.currentTime > 0}; }""")
        if not dv['inView'] or not dv['playing']:
            bad('데스크톱 인트로 영상 이상: %s' % dv)
        else:
            ok('데스크톱 인트로 영상 %dx%d · 화면 안 · 재생 중' % (dv['w'], dv['h']))
        dp.click('#introSkip')
        dp.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=2500)
        dp.wait_for_timeout(600)
        dt = dp.evaluate("""()=>({view: window.__mr4.view(), tiles: document.querySelectorAll('.stage > .tile').length,
            heights: [...document.querySelectorAll('.stage > .tile')].map(t=>Math.round(t.getBoundingClientRect().height))})""")
        if dt['view'] != 'video' or dt['tiles'] != 6 or min(dt['heights']) < 40:
            bad('데스크톱 회의실 타일 이상: %s' % dt)
        else:
            ok('데스크톱 회의실 — 화상 6분할 타일 6장 (높이 %s)' % dt['heights'])

        b.close()

    real_errs = [e for e in errs if 'net::' not in e and 'Failed to load resource' not in e]
    if real_errs:
        bad('콘솔 오류: %s' % real_errs[:5])
    else:
        ok('콘솔 오류 0')

    print()
    if fails:
        print('FAILED %d:' % len(fails))
        for f in fails:
            print(' - ' + f)
        sys.exit(1)
    print('ALL PASS (v4.6)')


main()
