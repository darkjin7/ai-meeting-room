"""v4.6.1 검증 — 입장 인트로 영상 3종 랜덤

성진님 지시
  "회의실 로딩 장면 3가지 랜덤으로 바꿔줘. 다음에 다른거 만들면 또 넣게"

무엇을 재는가
① 클립 3종이 준비돼 있다 — INTRO_CLIPS 3개 · 각 mp4 가 3.8~3.9초 무음 854x480 · 포스터 webp 존재
② 뽑기 규칙 — 90번 뽑으면 3가지가 모두 나오고, 직전에 나온 클립은 연달아 나오지 않는다,
   세 클립이 고르게 나온다(각 20% 이상)
③ 실제 입장 — 안건을 번갈아 골라 여러 번 입장하면 매번 인트로가 뜨고,
   고른 클립 영상이 readyState>=2 · paused=false 로 실제 재생되며(currentTime 증가),
   포스터·배경도 같은 클립 것으로 바뀐다. 세 클립이 한 번씩은 실제로 재생된다
④ 모바일 390x844 — 인트로 영상이 화면 안에 들어오고 가로 넘침이 없다
⑤ 성진님께 보내는 단일 파일(downloads/darkjin_meeting_room_v4.html) — 2.5MB 이하 · 3종이 모두 인라인 ·
   인라인된 영상이 실제로 재생된다(성진님 휴대폰에서 바로 열리는 파일)
"""
import re
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
ROOT = Path('/workspace/work/meeting-room')
FF = '/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2'

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
})();
"""


def probe(path):
    """mp4 길이·해상도·오디오 유무"""
    out = subprocess.run([FF, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', out)
    sec = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else -1
    dim = re.search(r'Video: h264.*?, (\d+)x(\d+)', out)
    wh = (int(dim.group(1)), int(dim.group(2))) if dim else (0, 0)
    has_audio = 'Audio:' in out
    return sec, wh, has_audio


def main():
    fails, errs = [], []

    def ok(m):
        print('OK ' + m)

    def bad(m):
        fails.append(m)
        print('FAIL ' + m)

    # ══════════ ① 클립 파일 ══════════
    clips = []
    for i in (1, 2, 3):
        mp4 = ROOT / 'avatars' / ('intro_%d.mp4' % i)
        pos = ROOT / 'avatars' / ('intro_%d_poster.webp' % i)
        if not mp4.exists() or not pos.exists():
            bad('intro_%d.mp4 / 포스터가 없음' % i)
            continue
        sec, wh, has_audio = probe(mp4)
        kb = mp4.stat().st_size / 1024
        clips.append({'i': i, 'sec': sec, 'wh': wh, 'kb': kb})
        if not (3.8 <= sec <= 3.95):
            bad('intro_%d 길이 %.2fs (3.8~3.9초 여야 함)' % (i, sec))
        if has_audio:
            bad('intro_%d 에 소리가 들어 있음(무음이어야 함)' % i)
        if wh != (854, 480):
            bad('intro_%d 해상도 %s (854x480 이어야 함)' % (i, wh))
        if kb > 300:
            bad('intro_%d %.0fKB — 300KB 를 넘음' % (i, kb))
        else:
            ok('intro_%d.mp4 %.2f초 · %dx%d · 무음 · %.0fKB · 포스터 %.0fKB'
               % (i, sec, wh[0], wh[1], kb, pos.stat().st_size / 1024))
    if len(clips) != 3:
        bad('클립 3종을 갖추지 못함')

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        p = ctx.new_page(); p.add_init_script(MOCK)
        p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        p.goto(URL)
        p.evaluate("()=>localStorage.clear()")
        p.reload(); p.wait_for_timeout(600)

        arr = p.evaluate("()=>window.__mr4.introClips()")
        if len(arr) != 3:
            bad('INTRO_CLIPS 가 %d개 (3개 여야 함): %s' % (len(arr), arr))
        else:
            ok('INTRO_CLIPS 3종 — ' + ' / '.join('%d.%s' % (c['idx'] + 1, c['label']) for c in arr))
        srcs = [c['src'] for c in arr]
        if len(set(srcs)) != 3:
            bad('클립 주소가 겹침: %s' % srcs)

        # ══════════ ② 뽑기 규칙 (90회) ══════════
        draws = p.evaluate("()=>{ const a=[]; for(let i=0;i<90;i++) a.push(window.__mr4.pickIntroIdx()); return a; }")
        cnt = {0: 0, 1: 0, 2: 0}
        for d in draws:
            cnt[d] = cnt.get(d, 0) + 1
        rep = sum(1 for a, c in zip(draws, draws[1:]) if a == c)
        if set(draws) != {0, 1, 2}:
            bad('90번 뽑았는데 3종이 다 안 나옴: %s' % cnt)
        elif rep:
            bad('직전 클립이 연달아 %d번 나옴' % rep)
        elif min(cnt.values()) < 90 * 0.20:
            bad('한쪽으로 쏠림: %s' % cnt)
        else:
            ok('랜덤 뽑기 90회 — 1번 %d · 2번 %d · 3번 %d (연속 중복 0)' % (cnt[0], cnt[1], cnt[2]))

        # ══════════ ③ 실제 입장 (안건 번갈아) ══════════
        lobby = p.evaluate("()=>window.__mr4.lobby()")
        ids = [a['id'] for a in lobby['agendas']]
        if len(ids) < 2:
            bad('준비된 안건이 2건 미만이라 인트로를 다시 틀 수 없음: %s' % ids)
        played = {}          # 클립 idx -> 재생 시간 기록
        prev_clip = None
        prev_ag = None
        entries = 0
        while len(played) < 3 and entries < 12 and len(ids) >= 2:
            target = [a for a in ids if a != prev_ag][0]
            entries += 1
            p.evaluate("()=>window.__mr4.showLobby()")
            p.wait_for_timeout(150)
            p.click('#lobbyAgList .agdoc-item[data-id="%s"]' % target)
            p.wait_for_timeout(150)
            p.click('#enterBtn')
            try:
                p.wait_for_function("()=>document.body.classList.contains('intro-on')", timeout=3000)
            except Exception:
                bad('%d번째 입장(%s)에서 인트로가 안 뜸' % (entries, target))
                break
            p.wait_for_timeout(500)
            st = p.evaluate("()=>window.__mr4.introState()")
            idx = int(p.get_attribute('#intro', 'data-intro') or '0') - 1
            if st['src'] not in srcs:
                bad('%d번째 입장 인트로 주소가 배열 밖: %r' % (entries, st['src'][:60]))
            if not (0 <= idx < 3):
                bad('%d번째 입장 data-intro 값 이상: %s' % (entries, idx))
            if idx == prev_clip:
                bad('%d번째 입장에서 직전과 같은 클립(%d번)이 다시 나옴' % (entries, idx + 1))
            want = arr[idx] if 0 <= idx < 3 else None
            if want:
                if want['src'] != st['src'] or want['poster'] != st['poster']:
                    bad('%d번째 입장 — 클립/포스터 짝이 안 맞음: %s vs %s' % (entries, st, want))
                if want['poster'].split('/')[-1] not in st['bg']:
                    bad('%d번째 입장 — 배경 이미지가 클립 포스터가 아님: %r' % (entries, st['bg'][:80]))
            t1 = p.evaluate("()=>document.getElementById('introVid').currentTime")
            p.wait_for_timeout(600)
            v = p.evaluate("""()=>{ const v=document.getElementById('introVid');
                return {rs: v.readyState, paused: v.paused, t: v.currentTime, w: v.videoWidth, h: v.videoHeight}; }""")
            if v['rs'] < 2:
                bad('%d번째 입장 — readyState %d (<2)' % (entries, v['rs']))
            elif v['paused']:
                bad('%d번째 입장 — 영상이 멈춰 있음' % entries)
            elif v['t'] <= t1:
                bad('%d번째 입장 — 재생 시간이 늘지 않음 %.2f → %.2f' % (entries, t1, v['t']))
            else:
                played[idx] = v['t']
                ok('%d번째 입장(%s) — %d번 클립 「%s」 재생 중 (%.2fs → %.2fs · readyState %d · %dx%d)'
                   % (entries, target, idx + 1, want['label'] if want else '?', t1, v['t'],
                      v['rs'], v['w'], v['h']))
            prev_clip, prev_ag = idx, target
            p.click('#introSkip')
            p.wait_for_function("()=>!document.body.classList.contains('intro-on')", timeout=3000)
            p.wait_for_timeout(300)
            if p.evaluate("()=>window.__mr4.state.agenda ? window.__mr4.state.agenda.id : null") != target:
                bad('%d번째 입장 — 건너뛰기 후 안건이 %s 가 아님' % (entries, target))
        if len(played) != 3:
            bad('실제로 재생된 클립이 %d종 (3종 여야 함): %s' % (len(played), sorted(played)))
        else:
            ok('입장 %d번 만에 3종 클립 모두 실제 재생 확인' % entries)

        # ══════════ ④ 모바일 화면 ══════════
        cur_ag = p.evaluate("()=>window.__mr4.state.agenda ? window.__mr4.state.agenda.id : null")
        p.evaluate("()=>window.__mr4.showLobby()")
        p.wait_for_timeout(150)
        p.click('#lobbyAgList .agdoc-item[data-id="%s"]' % [a for a in ids if a != cur_ag][0])
        p.wait_for_timeout(150)
        p.click('#enterBtn')
        p.wait_for_function("()=>document.body.classList.contains('intro-on')", timeout=3000)
        p.wait_for_timeout(700)
        box = p.evaluate("""()=>{ const v=document.getElementById('introVid'); const r=v.getBoundingClientRect();
            return {inView: r.top >= -1 && r.bottom <= innerHeight+1, w: Math.round(r.width), h: Math.round(r.height),
                    sw: document.documentElement.scrollWidth, iw: innerWidth,
                    skip: !!document.getElementById('introSkip')}; }""")
        if not box['inView'] or box['sw'] > box['iw'] + 1 or not box['skip']:
            bad('모바일 인트로 화면 이상: %s' % box)
        else:
            ok('모바일 390x844 — 인트로 영상 %dx%d 화면 안 · 가로 넘침 0' % (box['w'], box['h']))
        p.screenshot(path='/workspace/work/meeting-room/v461_test_final.png')

        # ══════════ ⑤ 단일 파일 ══════════
        single = Path('/workspace/downloads/darkjin_meeting_room_v4.html')
        kb = single.stat().st_size / 1024
        # v4.6.2 — 피클 상태 영상(speaking·sleepy·phone) 3편 + 인트로 3편, 가드 2.93MB
        if kb > 3000:
            bad('단일 파일 %.0fKB — 2.93MB 를 넘음' % kb)
        txt = single.read_text(encoding='utf-8')
        n_inline = txt.count('data:video/mp4;base64,')
        if n_inline != 6:
            bad('단일 파일에 인라인된 영상이 %d개 (피클 3 + 인트로 3 = 6개 여야 함)' % n_inline)
        else:
            ok('단일 파일 %.0fKB · 영상 6개 인라인(피클 3·인트로 3)' % kb)
        sp = ctx.new_page(); sp.add_init_script(MOCK)
        sp.on('pageerror', lambda e: errs.append('single pageerror:' + str(e)))
        sp.goto('file://' + str(single)); sp.wait_for_timeout(700)
        sp.click('#enterBtn')
        sp.wait_for_function("()=>document.body.classList.contains('intro-on')", timeout=4000)
        sp.wait_for_timeout(700)
        sv = sp.evaluate("""()=>{ const v=document.getElementById('introVid'); const s=v.getAttribute('src')||'\\u0000'; return {
            data: s.slice(0,18), poster: (v.getAttribute('poster')||'').slice(0,16),
            rs: v.readyState, paused: v.paused, t: v.currentTime}; }""")
        sp.wait_for_timeout(600)
        sv2 = sp.evaluate("()=>document.getElementById('introVid').currentTime")
        if not sv['data'].startswith('data:video/mp4') or not sv['poster'].startswith('data:image/webp'):
            bad('단일 파일 인트로가 인라인되지 않음: %s' % sv)
        elif sv['rs'] < 2 or sv['paused'] or sv2 <= sv['t']:
            bad('단일 파일 인트로 영상이 재생되지 않음: %s → %.2f' % (sv, sv2))
        else:
            ok('단일 파일 인트로 인라인 재생 — readyState %d · %.2fs → %.2fs' % (sv['rs'], sv['t'], sv2))
        sp.close()
        b.close()

    real = [e for e in errs if 'net::' not in e and 'Failed to load resource' not in e]
    if real:
        bad('콘솔 오류: %s' % real[:5])
    else:
        ok('콘솔 오류 0')

    print()
    if fails:
        print('FAILED %d:' % len(fails))
        for f in fails:
            print(' - ' + f)
        sys.exit(1)
    print('ALL PASS (v4.6.1)')


main()
