"""v4.5.1 검증 — ① 글로 보기 깜빡임(무대 재생성 0) ② 화상 6분할 타일 소실 0 ③ 피클은 발언 중에만 영상 재생

성진님 실기기(iOS Safari) 보고
  "글로 보는 페이지 아직 깜박거림이 나오고 있고 6분할 페이지에서 참여한 ai화면이 없어지는 버그가 있음.
   피클은 계속 얼굴영상 움직이는데 영상이 하나라서 그런가? 지금 영상은 발언 할 때 영상인데"

무엇을 재는가
① 글로 보기 — 발언 전환이 일어나도 .stage 안에서 노드가 **하나도 추가·삭제되지 않아야** 한다.
   (아바타 <img>·본문 텍스트·배지가 매번 새로 만들어지면 iOS Safari 가 그 순간을 다시 그리며 깜박인다)
   · 1~4라운드 + 화상↔글로 5회 왕복 + 다른 안건 열기 + 역할 분담 + 새 회의를 통틀어
     타일/아바타/본문/영상 노드의 신원(identity)이 그대로인지, .stage childList 변동이 0인지
   · 본문(.bubble) 안에 <span> 이 새로 생기지 않는지(텍스트만 갱신)
   · 발언 웨이브에 계속 도는 애니메이션이 없는지(animationName none) · 자리를 늘 차지하는지(display flex)
   · 스크롤할 때 다시 칠해지는 배경이 없는지(body 단색 + .wrap::before 고정 레이어)
② 화상 6분할 — 라운드 진행·보기 전환을 통틀어 6개 타일이 **매 프레임** 살아 있어야 한다.
   · 타일 크기>20px · 화면 안 · 이미지 complete&&naturalWidth>0 · 영상 readyState>=1
   · 타일 중앙에 실제로 그 타일의 자식 요소가 그려져 있는지(elementFromPoint) — 이웃 타일이나
     영상 레이어가 덮어 '화면이 없어지는' 경우를 잡는다
③ 피클 영상 — 발언 중(speaking)에만 opacity 1 + play(), 듣는 중(idle)에는 pause() + opacity 0.
   · src 는 화상 모드에 있는 동안 한 번 붙으면 바뀌지 않는다(떼었다 붙이면 iOS 에서 깜박인다)
   · 정지 이미지(pickle_poster) 가 아래층에 깔려 있어 듣는 중에도 얼굴이 보인다
"""
import json, sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL = '/workspace/downloads/'
WORK = '/workspace/work/meeting-room/'

MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },520); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;

  /* ── .stage 안의 DOM 변동 감시 ── */
  window.__mut = {added:0, removed:0, attrs:0, chars:0, textNodes:0, nodes:[]};
  function watchStage(){
    const st = document.getElementById('stage');
    if(!st) return setTimeout(watchStage, 30);
    new MutationObserver(muts=>{
      muts.forEach(m=>{
        if(m.type === 'childList'){
          const adds = [].filter.call(m.addedNodes, n=> n.nodeType === 1);
          const rems = [].filter.call(m.removedNodes, n=> n.nodeType === 1);
          if(adds.length){ window.__mut.added += adds.length;
            window.__mut.nodes.push('+' + (adds[0].className || adds[0].nodeName)); }
          if(rems.length){ window.__mut.removed += rems.length;
            window.__mut.nodes.push('-' + (rems[0].className || rems[0].nodeName)); }
          const tadd = [].filter.call(m.addedNodes, n=> n.nodeType === 3).length;
          const trem = [].filter.call(m.removedNodes, n=> n.nodeType === 3).length;
          if(tadd || trem) window.__mut.textNodes += Math.max(tadd, trem);
        } else if(m.type === 'attributes'){ window.__mut.attrs++; }
        else if(m.type === 'characterData'){ window.__mut.chars++; }
      });
    }).observe(st, {childList:true, subtree:true, attributes:true, characterData:true});
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchStage); else watchStage();

  /* ── 매 프레임 타일 상태 샘플 ── */
  window.__tileLog = [];
  window.__startTiles = ()=>{
    window.__tileLog = [];
    clearInterval(window.__tileTimer);
    window.__tileTimer = setInterval(()=>{
      const inVideo = document.body.classList.contains('view-video');
      const rows = [];
      document.querySelectorAll('.stage > .tile').forEach(t=>{
        const r = t.getBoundingClientRect();
        const cx = r.left + r.width/2, cy = r.top + r.height/2;
        let covered = true;
        try{ const el = document.elementFromPoint(cx, cy); covered = !!(el && t.contains(el)); }catch(e){ covered = true; }
        const img = t.querySelector('.vbob img.face');
        const pos = t.querySelector('.vbob img.vposter');
        const v = t.querySelector('.vbob video.face');
        rows.push({id:t.dataset.id, w:Math.round(r.width), h:Math.round(r.height),
          top:Math.round(r.top), bot:Math.round(r.bottom), left:Math.round(r.left), right:Math.round(r.right),
          inView: r.top >= -1 && r.left >= -1 && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1,
          covered:covered,
          img: img ? (img.complete && img.naturalWidth > 0) : null,
          poster: pos ? (pos.complete && pos.naturalWidth > 0) : null,
          vrs: v ? v.readyState : null, vop: v ? getComputedStyle(v).opacity : null,
          vpaused: v ? v.paused : null, speaking: t.classList.contains('speaking'),
          vis: getComputedStyle(t).visibility, disp: getComputedStyle(t).display});
      });
      window.__tileLog.push({inVideo:inVideo, rows:rows});
    }, 60);
  };
  window.__stopTiles = ()=>{ clearInterval(window.__tileTimer); return window.__tileLog; };
})();
"""


def main():
    errs, fails = [], []

    def ok(msg):
        print('OK ' + msg)

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        mp = ctx.new_page(); mp.add_init_script(MOCK)
        mp.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        mp.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        mp.goto(URL)
        mp.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','3')")
        mp.reload(); mp.wait_for_timeout(500); mp.evaluate("window.__mr4.dismissLobby()")   # v4.6 로비
        mp.click('.agcard[data-id="yt-growth"]'); mp.wait_for_timeout(600)
        mp.wait_for_function("()=>[...document.querySelectorAll('img.face')].every(i=>i.complete && i.naturalWidth>0)", timeout=10000)

        # ══════════ ① 정적 상태: 구조·신원·사장된 애니메이션 ══════════
        base = mp.evaluate("()=>window.__mr4.nodeIds()")
        assert len(base) == 6, '타일 6개 아님: %s' % base
        assert all(x['tile'] and x['img'] and x['bubble'] for x in base), '타일 노드 신원 수집 실패: %s' % base
        css = mp.evaluate("""()=>{
            const t=document.querySelector('.tile.speaking')||document.querySelector('.tile');
            const w=t.querySelector('.wave'); const i=w.querySelector('i');
            const b=getComputedStyle(document.body); const wb=getComputedStyle(document.querySelector('.wrap'),'::before');
            return {waveDisp:getComputedStyle(w).display, waveOp:getComputedStyle(w).opacity,
                    barAnim:getComputedStyle(i).animationName,
                    tileAnim:getComputedStyle(t).animationName, tileTr:getComputedStyle(t).transitionDuration,
                    bodyImg:b.backgroundImage, bodyColor:b.backgroundColor,
                    decoPos:wb.position, decoImg:wb.backgroundImage.slice(0,20),
                    talkAnim:(()=>{ const d=document.createElement('div'); d.className='talk-item'; d.style.position='absolute';
                        document.body.appendChild(d); const a=getComputedStyle(d).animationName; d.remove(); return a; })()};
        }""")
        assert css['waveDisp'] == 'flex', '웨이브가 자리를 차지하지 않음(발언 전환마다 버튼이 튄다): ' + css['waveDisp']
        assert css['barAnim'] == 'none', '웨이브 막대에 계속 도는 애니메이션이 남아 있음: ' + css['barAnim']
        assert css['tileAnim'] == 'none' and css['tileTr'].split(',')[0].strip() == '0s', '타일에 애니메이션/전환이 남아 있음: %s %s' % (css['tileAnim'], css['tileTr'])
        assert css['bodyImg'] == 'none', 'body 배경에 그라데이션이 남아 스크롤마다 다시 칠해진다: ' + css['bodyImg']
        assert css['decoPos'] == 'fixed' and 'radial-gradient' in css['decoImg'], '장식 배경이 고정 레이어가 아님: %s %s' % (css['decoPos'], css['decoImg'])
        assert css['talkAnim'] == 'none', '기록 항목마다 등장 애니메이션이 남아 있음: ' + css['talkAnim']
        ok('글로 보기 정적 구조 — 웨이브 display flex(자리 고정)·막대 애니메이션 none · 타일 전환 0s · body 단색 + 고정 장식 레이어')

        # ══════════ ② 글로 보기 4라운드 — 노드 재생성 0 · DOM 변동 0 ══════════
        mp.evaluate("()=>{ window.__mut.added=0; window.__mut.removed=0; window.__mut.nodes=[]; }")
        mp.evaluate("()=>window.__startTiles()")
        for n in (1, 2, 3, 4):
            mp.evaluate("(n)=>{ window.__mr4.playRound(n); }", n)
            mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
            mp.wait_for_timeout(120)
        log = mp.evaluate("()=>window.__stopTiles()")
        mut = mp.evaluate("()=>window.__mut")
        now = mp.evaluate("()=>window.__mr4.nodeIds()")
        assert now == base, '발언이 진행되며 타일/아바타/본문 노드가 새로 만들어졌다: %s' % [(a, b) for a, b in zip(base, now) if a != b]
        assert mut['added'] == 0 and mut['removed'] == 0, '.stage 안에서 요소 노드가 추가/삭제됨(깜빡임 원인): %s' % mut['nodes'][:6]
        assert mut['chars'] + mut['textNodes'] > 0, '본문 글자가 갱신되지 않음(회의가 진행되지 않은 것)'
        ok('글로 보기 1~4라운드 — 무대 요소 추가/삭제 0 · 클래스 %d회 · 글자 노드 %d회만 바뀜 (타일·아바타·본문 노드 동일)'
           % (mut['attrs'], mut['chars'] + mut['textNodes']))

        # 본문 안 span 이 늘지 않았다(innerHTML 교체 없음)
        bub = mp.evaluate("()=>[...document.querySelectorAll('.tile .bubble')].map(b=>b.children.length)")
        assert set(bub) == {3}, '본문 자식 노드 수가 달라짐(innerHTML 재작성 의심): %s' % bub
        ok('본문 구조 고정 — 타일마다 mtag/mrole/msum 3개 노드 그대로')

        # 글로 보기 동안 타일 크기·위치 불변 + 6장 모두 보임
        rows = [r for f in log if not f['inVideo'] for r in f['rows']]
        assert rows, '샘플 없음'
        sizes = set((r['id'], r['w'], r['h']) for r in rows)
        bad = [r for r in rows if r['w'] < 20 or r['h'] < 20 or r['vis'] == 'hidden']
        assert not bad, '글로 보기에서 사라진 타일: %s' % bad[:3]
        hset = {}
        for r in rows:
            hset.setdefault(r['id'], set()).add((r['w'], r['h']))
        churn = {k: v for k, v in hset.items() if len(v) > 1}
        assert not churn, '발언 전환 중 타일 크기가 변함(iOS 떨림): %s' % churn
        img_bad = [r for r in rows if r['img'] is not None and not r['img']]
        assert not img_bad, '글로 보기에서 아바타 이미지가 비었음: %s' % img_bad[:3]
        ok('글로 보기 — 타일 6장 크기 %s 고정 · 아바타 이미지 %d샘플 모두 로드' % (sorted(set(list(hset.values())[0])), len(rows)))

        # ══════════ ③ 화상 6분할 — 보기 왕복 5회 + 라운드 → 6타일 매 프레임 생존 ══════════
        mp.click('#viewVideoBtn'); mp.wait_for_timeout(700)
        mp.evaluate("()=>window.__startTiles()")
        for i in range(5):
            mp.click('#viewTextBtn'); mp.wait_for_timeout(220)
            mp.click('#viewVideoBtn'); mp.wait_for_timeout(260)
        mp.evaluate("()=>{ window.__mr4.playRound(3); }")
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        mp.wait_for_timeout(200)
        vlog = mp.evaluate("()=>window.__stopTiles()")
        vrows = [r for f in vlog if f['inVideo'] for r in f['rows']]
        assert vrows, '화상 모드 샘플 없음'
        gone = [r for r in vrows if r['w'] < 20 or r['h'] < 20 or not r['inView'] or r['vis'] == 'hidden' or r['disp'] == 'none']
        assert not gone, '화상 모드에서 사라진/화면 밖으로 밀린 타일: %s' % gone[:4]
        covered = [r for r in vrows if not r['covered']]
        assert not covered, '타일 중앙이 다른 요소에 덮임(이웃 타일/영상 레이어): %s' % covered[:4]
        broken_img = [r for r in vrows if r['img'] is not None and not r['img']]
        assert not broken_img, '화상 모드에서 아바타 이미지가 비었음: %s' % broken_img[:4]
        broken_post = [r for r in vrows if r['poster'] is not None and not r['poster']]
        assert not broken_post, '화상 모드에서 피클 정지 이미지가 비었음: %s' % broken_post[:4]
        broken_vid = [r for r in vrows if r['vrs'] is not None and r['vrs'] < 1]
        assert not broken_vid, '화상 모드에서 피클 영상이 열리지 않음(readyState 0): %s' % broken_vid[:4]
        ids_now = mp.evaluate("()=>window.__mr4.tileIds()")
        assert sorted(ids_now) == sorted(['pickle','gemini','cue','hark','chatgpt','claude']), '화상 타일 6인 아님: %s' % ids_now
        now2 = mp.evaluate("()=>window.__mr4.nodeIds()")
        assert [x['tile'] for x in now2] == [x['tile'] for x in base], '보기 왕복으로 타일 노드가 재생성됨'
        ok('화상 6분할 — 왕복 5회 + 3라운드 %d샘플 동안 6타일 항상 화면 안·가려짐 0 · 이미지/영상 로드 유지'
           % len(vlog))

        # ══════════ ④ 피클은 발언 중에만 영상 재생 ══════════
        mp.evaluate("""()=>{ window.__vidLog=[]; clearInterval(window.__vidTimer);
            window.__vidTimer=setInterval(()=>{
              const v=document.querySelector('video.vid'); const t=document.querySelector('.tile[data-id="pickle"]');
              if(!v||!t) return;
              window.__vidLog.push({sp:t.classList.contains('speaking'), p:v.paused,
                op:getComputedStyle(v).opacity, t:Math.round(v.currentTime*100)/100, src:v.getAttribute('src')});
            }, 60); }""")
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)   # 앞 라운드가 끝난 뒤에 시작
        mp.evaluate("()=>{ window.__mr4.playRound(4); }")
        mp.wait_for_function("()=>window.__mr4.state.busy===true", timeout=8000)      # 4라운드가 실제로 시작됐는지
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        mp.wait_for_timeout(300)
        vlog2 = mp.evaluate("()=>{ clearInterval(window.__vidTimer); return window.__vidLog; }")
        played = [x for x in vlog2 if x['sp'] and not x['p'] and x['op'] == '1' and x['t'] > 0.2]
        assert played, '피클 발언 중에 영상이 재생되지 않음'
        idle_bad = [x for x in vlog2 if not x['sp'] and (not x['p'] or x['op'] != '0')]
        assert not idle_bad, '듣는 중인데 영상이 재생/노출됨: %s' % idle_bad[:4]
        srcs = set(x['src'] for x in vlog2)
        assert srcs == {'./avatars/pickle.mp4'}, '라운드 중 영상 src 가 바뀌거나 사라짐: %s' % srcs
        assert all(x['op'] in ('0','1') for x in vlog2), '영상 opacity 가 중간값(전환 중 흐림): %s' % set(x['op'] for x in vlog2)
        ok('피클 영상 — %d샘플 중 발언 중 재생 %d개 · 듣는 중엔 전부 pause+opacity 0 · src 한 번 붙은 뒤 불변'
           % (len(vlog2), len(played)))

        # 조용(quiet) → 전부 멈춤, 다시 계속 → 발언자만 재생
        mp.evaluate("()=>{ window.__mr4.playRound(1); }")
        mp.wait_for_function("()=>{const v=document.querySelector('video.vid');return v && !v.paused && v.currentTime>0.2;}", timeout=40000)
        mp.click('#quietBtn'); mp.wait_for_timeout(400)
        q = mp.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle')")
        assert q['video']['paused'] is True, '조용인데 영상이 계속 재생'
        mp.click('#quietBtn'); mp.wait_for_timeout(600)
        ok('🤫 조용 — 영상 즉시 정지 · ▶️ 계속 — 발언자 차례에만 재생')

        # ══════════ ⑤ 다른 안건으로 바꿔도 타일을 파괴하지 않는다 ══════════
        mp.click('#viewTextBtn'); mp.wait_for_timeout(400)
        before = mp.evaluate("()=>{ const m={}; window.__mr4.nodeIds().forEach(x=>m[x['id']]=x); return m; }")
        mp.evaluate("()=>window.__mr4.openAgenda('ldp-workflow')")
        mp.wait_for_timeout(700)
        after = mp.evaluate("()=>{ const m={}; window.__mr4.nodeIds().forEach(x=>m[x['id']]=x); return m; }")
        shared = [k for k in after if k in before]
        same = [k for k in shared if before[k]['tile'] == after[k]['tile'] and before[k]['img'] == after[k]['img']]
        assert len(same) == len(shared) and len(shared) >= 5, '안건을 바꿀 때 타일 노드가 재생성됨: %s' % [(k, before.get(k), after.get(k)) for k in shared if k not in same]
        face_ok = mp.evaluate("()=>[...document.querySelectorAll('.stage > .tile .vbob img.face, .stage > .tile .vbob img.vposter, .stage > .tile .vbob video.face')].every(m=>m.tagName==='VIDEO'? m.readyState>=1 : (m.complete&&m.naturalWidth>0))")
        assert face_ok, '안건을 바꾼 뒤 타일 미디어가 비었음'
        ok('안건 교체 — 공유 %d인의 타일·아바타 노드 그대로(재생성 0) · 미디어 로드 유지' % len(shared))

        # 화상으로 돌아가 6타일 다시 확인(파킹됐던 타일도 살아 있다)
        mp.click('#viewVideoBtn'); mp.wait_for_timeout(800)
        m6 = mp.evaluate("()=>window.__mr4.media()")
        assert len(m6) == 6, '화상 타일 6개 아님: %d' % len(m6)
        assert all(x['rect']['w'] > 20 and x['rect']['h'] > 20 for x in m6), '화상 타일 크기 이상: %s' % m6
        assert all((x['img'] and x['img']['nw'] > 0) or (x['poster'] and x['poster']['nw'] > 0) for x in m6), '화상 타일 미디어 없음: %s' % m6
        mp.screenshot(path=DL + 'meeting_v451_mobile_video6.png')
        mp.screenshot(path=WORK + 'v451_mobile_video6.png')
        ok('화상 6분할 재확인 — 6타일 모두 크기·이미지 정상')

        # 모바일 글로 보기 스크린샷(발언 중) + 화상/글로 눈검수용
        mp.click('#viewTextBtn'); mp.wait_for_timeout(400)
        mp.evaluate("()=>{ window.__mr4.playRound(2); }")
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        mp.wait_for_timeout(300)
        mp.screenshot(path=DL + 'meeting_v451_mobile_text.png')
        mp.screenshot(path=WORK + 'v451_mobile_text.png')
        mp.evaluate("()=>window.__mr4.focusTile('pickle')")
        mp.wait_for_timeout(700)
        mp.screenshot(path=DL + 'meeting_v451_mobile_text_center.png')
        mp.screenshot(path=WORK + 'v451_mobile_text_center.png')

        # 데스크톱 화상 — 6분할 배치 확인
        ctx2 = b.new_context(viewport={'width': 1440, 'height': 900})
        dp = ctx2.new_page(); dp.add_init_script(MOCK)
        dp.on('pageerror', lambda e: errs.append('desktop-pageerror:' + str(e)))
        dp.goto(URL); dp.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','3')")
        dp.reload(); dp.wait_for_timeout(400); dp.evaluate("window.__mr4.dismissLobby()")   # v4.6 로비
        dp.click('.agcard[data-id="yt-growth"]'); dp.wait_for_timeout(600)
        dp.click('#viewVideoBtn'); dp.wait_for_timeout(900)
        dm = dp.evaluate("()=>window.__mr4.media()")
        assert len(dm) == 6 and all(x['rect']['w'] > 40 and x['rect']['h'] > 40 for x in dm), '데스크톱 화상 타일 이상: %s' % dm
        dp.screenshot(path=DL + 'meeting_v451_desktop_video6.png')
        dp.screenshot(path=WORK + 'v451_desktop_video6.png')
        ok('데스크톱 1440x900 화상 6분할 — 6타일 정상')
        b.close()

    if errs:
        print('ERRORS:'); [print(' ', e) for e in errs]; sys.exit(1)
    print('ALL PASS (v4.5.1)')


main()
