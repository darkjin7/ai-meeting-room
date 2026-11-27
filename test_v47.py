"""v4.7 / v4.7.1 검증 — avatars/pickle_listening.mp4 (Hark 경청 영상 → 640x598 풀블리드 · 8초 루프)

성진님 지시
  "Hark 가 만든 피클 경청 영상(listening_8s_loop)을 기본으로 넣어라"
  (v4.7.1) "조는 건 못 봤는데 딴짓이 계속 반복됨. 한 번만 하고 경청을 해야지... 조는 것도 반복으로 되있나 확인해줘"

무엇을 재는가
① 파일 — 640x598 · 무음 H.264 · faststart · 8.00초 · 220~350KB · 24fps
② 얼굴 크기·위치 — speaking(pickle.mp4) 과 같은 자리인가
   두 눈동자(파란 픽셀) 무게중심으로 잰다: 눈 사이 간격 236.9px · 눈 중심 (0.5043W, 0.3207H) 와 비교
③ 루프 — 첫 프레임과 마지막 프레임의 평균차가 연속 프레임 수준(끊김 없이 이어진다)
④ 앱 — 모바일 390x844 화상 6분할에서 listening 이 기본 재생(loop · opacity 1) 이고
   발언 차례에는 멈추고 speaking 영상이 나온다. 스크린샷 downloads/meeting_v47_pickle_listening.png
⑤ v4.7.1 딴짓(phone) — loop=false(한 번만) · 끝나면 mood ''/listening 으로 자동 복귀 · 다시 반복하지 않음 ·
   다시 켜면 처음부터 한 번. sleepy 는 loop=false 로 마지막 프레임(눈 감은 얼굴)에 그대로 머문다.
"""
import re
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
ROOT = Path('/workspace/work/meeting-room')
DL = '/workspace/downloads/'
FF = '/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2'
LISTEN = ROOT / 'avatars/pickle_listening.mp4'
SPEAK = ROOT / 'avatars/pickle.mp4'

MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },340); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; } };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
})();
"""


def probe(path):
    out = subprocess.run([FF, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', out)
    sec = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else -1
    dim = re.search(r'Video: h264.*?, (\d+)x(\d+)', out)
    wh = (int(dim.group(1)), int(dim.group(2))) if dim else (0, 0)
    fps = re.search(r'(\d+(?:\.\d+)?) fps', out)
    return sec, wh, 'Audio:' in out, float(fps.group(1)) if fps else -1


def first_moov_before_mdat(path):
    d = Path(path).read_bytes()
    return 0 <= d.find(b'moov') < d.find(b'mdat')


def grab(path, t, out_png):
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', str(path),
                    '-frames:v', '1', '-update', '1', out_png], check=True)
    return out_png


def eyes(png):
    """두 눈동자(파란 픽셀) 무게중심 — 위쪽 띠만 본다(타이·배경 파란색 제외)"""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert('RGB')).astype(int)
    h, w, _ = a.shape
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = (b > 150) & (b - r > 70) & (b - g > 15) & (g > 70)
    band = np.zeros_like(m)
    band[int(h * 0.10):int(h * 0.55), :] = True
    m &= band
    cols = np.nonzero(m.any(axis=0))[0]
    runs, start, prev = [], cols[0], cols[0]
    for c in cols[1:]:
        if c - prev > 25:
            runs.append((start, prev)); start = c
        prev = c
    runs.append((start, prev))
    res = []
    for c0, c1 in runs:
        ys, xs = np.nonzero(m[:, c0:c1 + 1]); xs = xs + c0
        if len(xs) < 150:
            continue
        res.append((float(xs.mean()), float(ys.mean()), len(xs)))
    res = sorted(res, key=lambda x: x[1])[:2]
    res.sort()
    assert len(res) == 2, '눈동자 두 개를 못 찾음: %s' % res
    inter = res[1][0] - res[0][0]
    return inter, (res[0][0] + res[1][0]) / 2, (res[0][1] + res[1][1]) / 2, w, h


def mad(png_a, png_b):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png_a).convert('RGB')).astype(int)
    b = np.asarray(Image.open(png_b).convert('RGB')).astype(int)
    return float(np.abs(a - b).mean())


def main():
    fails, errs = [], []

    def ok(m):
        print('OK ' + m)

    def bad(m):
        fails.append(m)
        print('FAIL ' + m)

    # ══════════ ① 파일 ══════════
    if not LISTEN.exists():
        bad('avatars/pickle_listening.mp4 가 없다')
        sys.exit(1)
    sec, wh, audio, fps = probe(LISTEN)
    kb = LISTEN.stat().st_size / 1024
    if not (7.9 <= sec <= 8.1):
        bad('pickle_listening.mp4 길이 %.2fs (8.00초 여야 함)' % sec)
    if wh != (640, 598):
        bad('pickle_listening.mp4 해상도 %s (640x598 이어야 함)' % (wh,))
    if audio:
        bad('pickle_listening.mp4 에 소리가 들어 있음(무음이어야 함)')
    if not first_moov_before_mdat(LISTEN):
        bad('pickle_listening.mp4 가 faststart 아님(moov 가 mdat 뒤)')
    if not (220 <= kb <= 350):
        bad('pickle_listening.mp4 %.0fKB — 220~350KB 밖' % kb)
    if abs(fps - 24) > 0.1:
        bad('pickle_listening.mp4 fps %.2f (24 여야 함)' % fps)
    if not (7.9 <= sec <= 8.1 and wh == (640, 598) and not audio and first_moov_before_mdat(LISTEN)
            and 220 <= kb <= 350 and abs(fps - 24) <= 0.1):
        print('  (파일 항목 실패 — 아래 검사는 계속)')
    else:
        ok('pickle_listening.mp4 — %.2f초 · 640x598 · 무음 · H.264 · faststart · %.0fKB · 24fps' % (sec, kb))

    # ══════════ ② 얼굴 크기·위치 — speaking 과 같은 자리 ══════════
    li_i, li_x, li_y, W, H = eyes(grab(LISTEN, 0.05, str(ROOT / '.tmp_lst_first.png')))
    sp_i, sp_x, sp_y, W2, H2 = eyes(grab(SPEAK, 0.05, str(ROOT / '.tmp_spk_first.png')))
    d_i, d_x, d_y = li_i - sp_i, li_x - sp_x, li_y - sp_y
    if abs(d_i) > 8 or abs(d_x) > 8 or abs(d_y) > 8:
        bad('listening 얼굴이 speaking 과 다름 — 눈 사이 %+.1fpx · 중심 %+.1f,%+.1fpx (허용 ±8px)'
            % (d_i, d_x, d_y))
    else:
        ok('얼굴 크기·위치 — 눈 사이 %.1fpx(speaking %.1f) · 중심 (%.1f, %.1f)(speaking (%.1f, %.1f))'
           % (li_i, sp_i, li_x, li_y, sp_x, sp_y))

    # ══════════ ③ 루프 이음매 ══════════
    f_first = grab(LISTEN, 0.02, str(ROOT / '.tmp_lst_a.png'))
    f_last = grab(LISTEN, sec - 0.10, str(ROOT / '.tmp_lst_b.png'))
    f_mid = grab(LISTEN, sec / 2, str(ROOT / '.tmp_lst_c.png'))
    seam = mad(f_first, f_last)
    far = mad(f_first, f_mid)
    if seam > 4.0 or far < seam:
        bad('listening 루프 이음매가 끊김(첫↔끝 평균차 %.2f · 첫↔중간 %.2f)' % (seam, far))
    else:
        ok('루프 이음매 — 첫↔끝 평균차 %.2f (첫↔중간 %.2f 보다 작음 · 크로스페이드 없이 그대로 사용)' % (seam, far))

    # ══════════ ④ 앱 — 모바일 390x844 화상 6분할 ══════════
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        p = ctx.new_page(); p.add_init_script(MOCK)
        p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        p.goto(URL); p.evaluate("()=>localStorage.clear()"); p.reload(); p.wait_for_timeout(700)
        p.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); p.wait_for_timeout(600)
        p.click('#viewVideoBtn')
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.listen && !m.listen.paused && m.listen.t>0.3 && m.listen.rs>=2;}""", timeout=9000)
        m = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        if m['listen']['loop'] is not True or m['listen']['op'] != '1' or m['listen']['paused']:
            bad('listening 기본 재생 이상: %s' % m['listen'])
        elif m['speak']['paused'] is not True:
            bad('듣는 중인데 speaking 영상이 재생 중')
        else:
            ok('화상 6분할 기본 — listening 재생 t=%.2fs · loop=true · op=1 · speaking 정지' % m['listen']['t'])
        # 풀블리드 — 미디어가 타일 안쪽을 꽉 채운다
        bl = p.evaluate("""()=>{const t=document.querySelector('.tile[data-id="pickle"]');
            const b=t.querySelector('.vbob').getBoundingClientRect();
            const v=t.querySelector('.vbob video.vlay[data-state="listening"]'); const r=v.getBoundingClientRect();
            const s=getComputedStyle(v);
            return {frame:[Math.round(b.width),Math.round(b.height)], media:[Math.round(r.width),Math.round(r.height)],
                    fit:s.objectFit, rad:s.borderRadius, op:s.opacity};}""")
        if abs(bl['media'][0] - bl['frame'][0]) > 1 or abs(bl['media'][1] - bl['frame'][1]) > 1 \
                or bl['fit'] != 'cover' or bl['rad'] != '0px':
            bad('listening 영상이 타일을 꽉 채우지 않음: %s' % bl)
        else:
            ok('listening 풀블리드 — 영상 %dx%d = 프레임 %dx%d · object-fit cover' % (bl['media'][0], bl['media'][1], bl['frame'][0], bl['frame'][1]))
        # 토스트가 사라진 뒤 스크린샷 (듣는 중 장면)
        p.wait_for_function("""()=>{const t=document.getElementById('toast');
            return !t || !t.classList.contains('show');}""", timeout=6000)
        p.wait_for_timeout(700)
        p.screenshot(path=DL + 'meeting_v47_pickle_listening.png')
        print('  shot', DL + 'meeting_v47_pickle_listening.png')
        # 발언 중에는 listening 이 멈추고 speaking 이 나온다 → 끝나면 다시 listening
        p.evaluate("()=>{ window.__mr4.playRound(1); }")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.speaking && m.listen.paused && m.listen.op==='0';}""", timeout=60000)
        ok('발언 순간 — listening 정지(op 0) · speaking 재생')
        p.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && !m.speaking && m.listen && !m.listen.paused && m.listen.op==='1';}""", timeout=10000)
        ok('발언 종료 — listening 이 다시 재생(op 1)')
        b.close()

    # ══════════ ⑤ v4.7.1 — 딴짓(phone) 은 한 번만, 끝나면 경청 복귀 ══════════
    html = (ROOT / 'v4/app.js').read_text(encoding='utf-8')
    if 'const VIDEO_ONCE = {sleepy:true, phone:true}' not in html:
        bad("v4/app.js — VIDEO_ONCE 에 phone 이 없다(딴짓이 무한 반복됨)")
    else:
        ok('VIDEO_ONCE — sleepy·phone 둘 다 한 번 재생(loop=false)')
    title = re.search(r'<title>([^<]*)</title>', (ROOT / 'v4/head.html').read_text(encoding='utf-8')).group(1)
    if 'v4.7.1' not in title:
        bad('<title> 이 v4.7.1 이 아님: %s' % title)
    else:
        ok('<title> v4.7.1 — %s' % title)
    if 'v4.7.1 · DOC' not in (ROOT / 'index.v4.html').read_text(encoding='utf-8'):
        bad('서류철 문서번호가 v4.7.1 이 아님')
    else:
        ok('서류철 문서번호 — v4.7.1 · DOC')

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        p = ctx.new_page(); p.add_init_script(MOCK)
        p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        p.goto(URL); p.evaluate("()=>localStorage.clear()"); p.reload(); p.wait_for_timeout(700)
        p.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); p.wait_for_timeout(600)
        p.click('#viewVideoBtn')
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.listen && !m.listen.paused && m.listen.t>0.3;}""", timeout=9000)
        pick = "()=>window.__mr4.moods().find(x=>x.id==='pickle')"
        # 두 이벤트 영상(sleepy·phone)은 loop 속성 자체가 없다 = 한 번만 재생
        m = p.evaluate(pick)
        if m['phon']['loop'] is not False or m['sleep']['loop'] is not False:
            bad('딴짓/졸기 영상이 loop=true — %s / %s' % (m['phon']['loop'], m['sleep']['loop']))
        else:
            ok('phone · sleepy 영상 loop=false (한 번만 재생)')
        # 딴짓 켜기 — 폰 보는 영상이 실제로 돈다
        p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m.mood==='phone' && m.moodNow==='phone' && m.phon && !m.phon.paused && m.phon.t>0.3;}""", timeout=6000)
        m = p.evaluate(pick)
        ok('딴짓 켜짐 — mood=%s · phone 재생 t=%.2fs · listening 정지(op %s)'
           % (m['mood'], m['phon']['t'], m['listen']['op']))
        if m['listen']['op'] != '0' or not m['listen']['paused']:
            bad('딴짓 중인데 listening 이 아직 보임: %s' % m['listen'])
        # 2.21초 클립이 끝나면 곧바로 경청 복귀 (마지막 프레임에 머물지 않는다)
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m.mood==='' && m.moodNow==='listening' && m.listen && !m.listen.paused;}""", timeout=9000)
        p.wait_for_timeout(600)
        m = p.evaluate(pick)
        if m['phon']['done'] != '1' or not m['phon']['paused']:
            bad('phone 이 끝난 뒤에도 재생 중(done=%s paused=%s)' % (m['phon']['done'], m['phon']['paused']))
        elif m['listen']['op'] != '1' or m['listen']['paused']:
            bad('phone 종료 후 경청 복귀 실패: %s' % m['listen'])
        else:
            ok('딴짓 1회 종료 — mood \'\' 로 복귀 · listening 재생 t=%.2fs · phone 정지(done=1)'
               % m['listen']['t'])
        if m['vstate'] != '듣는 중':
            bad('딴짓이 끝났는데 화상 타일 문구가 \'%s\'' % m['vstate'])
        else:
            ok('화상 타일 문구 — 딴짓 종료 후 \'듣는 중\'')
        # 한 번 끝난 딴짓은 저절로 다시 켜지지 않는다(6초 지켜봐도 그대로 경청)
        t0 = p.evaluate(pick)['phon']['t']; lt0 = p.evaluate(pick)['listen']['t']
        p.wait_for_timeout(6000)
        m = p.evaluate(pick)
        if m['mood'] != '' or m['phone'] or m['moodNow'] != 'listening':
            bad('딴짓이 끝난 뒤 스스로 다시 켜졌다(mood=%s · tile.phone=%s)' % (m['mood'], m['phone']))
        elif abs(m['phon']['t'] - t0) > 0.05:
            bad('phone 영상이 계속 돌고 있다(t %.2f → %.2f)' % (t0, m['phon']['t']))
        elif m['listen']['t'] == lt0:
            bad('경청 영상이 멈춰 있다(t %.2f 그대로)' % m['listen']['t'])
        else:
            ok('6초 뒤에도 딴짓 재발 없음 — phone t=%.2fs 고정 · listening 계속 재생(t %.2f → %.2f)'
               % (m['phon']['t'], lt0, m['listen']['t']))
        # 다시 켜면 처음(0초)부터 한 번 더 — 재진입은 정상 동작
        p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m.mood==='phone' && m.phon && !m.phon.paused && m.phon.t>0.1 && m.phon.t<1.4;}""", timeout=6000)
        m = p.evaluate(pick)
        ok('다시 켜면 처음부터 — phone t=%.2fs (되감기 정상)' % m['phon']['t'])
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m.mood==='' && m.moodNow==='listening';}""", timeout=9000)
        ok('두 번째 딴짓도 1회로 끝나 경청 복귀')
        # 글로 보기에서는 영상이 안 돌아도 배지가 '딴짓'으로 남지 않는다(3.5초 안전 타이머)
        p.click('#viewTextBtn'); p.wait_for_timeout(400)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        p.wait_for_function("()=>window.__mr4.moods().find(x=>x.id==='pickle').state.indexOf('딴짓')>=0", timeout=4000)
        ok('글로 보기 — 카드 배지 「📱 딴짓」 표시')
        p.wait_for_function("()=>window.__mr4.moods().find(x=>x.id==='pickle').mood===''", timeout=7000)
        m = p.evaluate(pick)
        ok('글로 보기 — 3.5초 뒤 배지 자동 해제(%r) · mood \'\'' % m['state'])
        p.click('#viewVideoBtn'); p.wait_for_timeout(500)
        # 조는 영상은 반대로 마지막 프레임(눈 감은 얼굴)에 머문다 — 발언 차례에 깨어난다
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m.sleep && m.sleep.done==='1' && m.sleep.paused && m.mood==='sleepy';}""", timeout=12000)
        p.wait_for_timeout(1500)
        m = p.evaluate(pick)
        if m['mood'] != 'sleepy' or m['moodNow'] != 'sleepy' or m['sleep']['t'] < 2.9:
            bad('sleepy 가 마지막 프레임에 머물지 않는다: mood=%s t=%.2f' % (m['mood'], m['sleep']['t']))
        elif m['phon']['paused'] is not True:
            bad('자는 중인데 phone 이 재생 중')
        else:
            ok('졸기(sleepy) — loop 1회 후 마지막 프레임(t=%.2fs)에서 정지 · 반복 없음 · 발언 차례까지 유지'
               % m['sleep']['t'])
        p.evaluate("()=>window.__mr4.setTileState && window.__mr4.setTileState('pickle','speaking','발언 중')")
        p.wait_for_function("()=>window.__mr4.moods().find(x=>x.id==='pickle').mood===''" , timeout=5000)
        ok('발언 차례 — 조는 상태 해제(mood \'\')')
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
    print('ALL PASS (v4.7.1 · listening + 딴짓 1회)')


main()
