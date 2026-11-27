"""v4.7 검증 — 피클 '듣는 중(listening)' 기본 영상 · 졸기/딴짓 희소화

성진님 지시
  Hark 가 만든 피클 경청 영상(8초 루프)을 기본으로 → 말하지 않을 때도 살아 있는 얼굴
  "어쩌다 졸고 딴짓하는 거지 계속 반복하니까 별로네" → sleepy/phone 은 '어쩌다 한 번'

무엇을 재는가
① 파일 — avatars/pickle_sleepy.mp4 · pickle_phone.mp4 가 640x598 · 무음 H.264 · faststart
   (sleepy 3.0초 · phone 2.2초)
   · sleepy: **첫 프레임은 눈을 뜨고(눈동자 파란 픽셀 다수), 마지막 프레임은 눈을 감은 상태**(파란 픽셀 0)
   · phone : 첫 프레임이 원본 720x673(y=445) 크롭과 거의 같다 → 좌우 흐린 여백·비네트가 없다(풀블리드)
② 구조 — 피클 타일에 영상이 상태마다 한 겹씩
   (speaking=video.vid 1 + listening·sleepy·phone=video.vlay 3 = 4겹). 상태를 바꿔도 요소·src 그대로
③ 기본 — 화상 6분할에 들어가면 피클은 **듣는 중(listening)** 영상이 loop=true 로 계속 돌고 있다
   (speaking 겹은 pause · opacity 0 · 상태 문구 「듣는 중」 · moodNow=listening)
④ sleepy — 재생 중 loop===false · 3초를 다 틀면 마지막 프레임(눈 감은 얼굴)에서 paused 로 멈춰 있고
   done 표시로 다시 되감기지 않는다(같은 상태를 다시 setTileMood 해도 재생 안 함).
   상태를 벗었다가 다시 들어올 때만 currentTime 0 에서 다시 재생된다.
⑤ phone — .tile.phone · '📱 딴짓하다 걸림' · **한 번만 재생(v4.7.1 loop=false)** 하고 끝나면 즉시 경청 복귀 · sleepy 겹 정지.
   이름·상태(.vov)는 다른 타일과 같이 **하단**에 있다(v4.6.2 의 위로 올리기 예외 제거 확인)
⑥ 복귀 — 발언 차례가 오면 즉시 깨고 speaking 이 재생, 발언이 끝나면 listening 으로 돌아온다
⑦ 희소화 — 정책값(상한 2 · rest>=3 · 22% · 쿨다운 1라운드)과 경계(moodGate),
   실제 4라운드에서 발동이 2회를 넘지 않고 모든 발동이 rest>=3 · 라운드 간격 >1 임을 확인
⑧ 글로 보기 — 화상이 아닐 때는 listening 영상도 정지한다
⑨ 단일 파일(downloads/darkjin_meeting_room_v4.html) — listening·sleepy·phone 이 인라인되어 실제 재생
⑩ 모바일 390x844 스크린샷 — downloads/meeting_v47_pickle_sleepy.png · meeting_v47_pickle_phone.png
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
    return sec, wh, 'Audio:' in out


def first_moov_before_mdat(path):
    d = Path(path).read_bytes()
    return 0 <= d.find(b'moov') < d.find(b'mdat')


def frame_brightness_bands(path, t, out_png):
    """프레임을 뽑아 아래쪽 밝은 픽셀 수를 센다(참고용 — v4.6.2 의 폰 화면 확인에 썼다)"""
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', str(path),
                    '-frames:v', '1', out_png], check=True)
    from PIL import Image
    im = Image.open(out_png).convert('L')
    w, h = im.size
    px = im.load()
    band = [(x, y) for y in range(int(h * 0.62), h) for x in range(int(w * 0.28), int(w * 0.72))]
    bright = sum(1 for (x, y) in band if px[x, y] > 205)
    return w, h, bright, len(band), out_png


def grab(path, t, out_png):
    """영상의 t초 프레임을 파일로"""
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', str(path),
                    '-frames:v', '1', '-update', '1', out_png], check=True)
    return out_png


def grab_last(path, out_png):
    """영상의 마지막 프레임을 파일로"""
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-sseof', '-0.10', '-i', str(path),
                    '-frames:v', '1', '-update', '1', out_png], check=True)
    return out_png


def iris_px(png):
    """눈 부근 띠(위 22~45%) 안의 '파란 눈동자' 픽셀 수 — 눈을 뜨면 많고, 감으면 0 에 가깝다"""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(png).convert('RGB')).astype(int)
    h, w, _ = im.shape
    band = im[int(h * 0.22):int(h * 0.45), int(w * 0.15):int(w * 0.85)]
    r, g, b = band[:, :, 0], band[:, :, 1], band[:, :, 2]
    return int(((b > 120) & (b - r > 45) & (r < 140)).sum())


def crop_match(video, t, src, src_t, out_png, src_png):
    """영상 t초 프레임이 원본의 720x673(y=445) 크롭과 얼마나 같은가(평균 절대차).
       작을수록 '좌우 흐린 배경 없이 그대로 잘라 채운' 풀블리드다.
       프레임 시작 오프셋(±1프레임) 때문에 생기는 오차는 가장 잘 맞는 값을 쓴다."""
    import numpy as np
    from PIL import Image
    grab(video, t, out_png)
    a = np.asarray(Image.open(out_png).convert('RGB')).astype(int)
    best = None
    for off in (0.0, -1 / 24.0, 1 / 24.0, -2 / 24.0, 2 / 24.0):
        grab(src, round(src_t + off, 3), src_png)
        s = Image.open(src_png).convert('RGB').crop((0, 445, 720, 1118)).resize((640, 598), Image.LANCZOS)
        d = float(np.abs(a - np.asarray(s).astype(int)).mean())
        best = d if best is None else min(best, d)
    return best


def main():
    fails, errs = [], []

    def ok(m):
        print('OK ' + m)

    def bad(m):
        fails.append(m)
        print('FAIL ' + m)

    # ══════════ ① 파일 ══════════
    specs = [('pickle_sleepy.mp4', 3.0, 3.0), ('pickle_phone.mp4', 2.2, 2.2)]
    for name, lo, hi in specs:
        f = ROOT / 'avatars' / name
        if not f.exists():
            bad('%s 가 없다' % name)
            continue
        sec, wh, audio = probe(f)
        kb = f.stat().st_size / 1024
        fs = first_moov_before_mdat(f)
        if not (lo - 0.1 <= sec <= hi + 0.1):
            bad('%s 길이 %.2fs (%.1f초 여야 함)' % (name, sec, lo))
        if wh != (640, 598):
            bad('%s 해상도 %s (640x598 이어야 함)' % (name, wh))
        if audio:
            bad('%s 에 소리가 들어 있음(무음이어야 함)' % name)
        if not fs:
            bad('%s 가 faststart 아님(moov 가 mdat 뒤)' % name)
        if not (120 <= kb <= 400):
            bad('%s %.0fKB — 120~400KB 밖' % (name, kb))
        else:
            ok('%s — %.2f초 · 640x598 · 무음 · faststart · %.0fKB' % (name, sec, kb))

    # sleepy — 첫 프레임은 눈을 뜨고, **마지막 프레임은 눈을 감은 얼굴**이어야 한다(그 프레임에서 멈춘다)
    slp = ROOT / 'avatars/pickle_sleepy.mp4'
    if slp.exists():
        i_first = iris_px(grab(slp, 0.02, str(ROOT / '.tmp_sl_first.png')))
        i_last = iris_px(grab_last(slp, str(ROOT / '.tmp_sl_last.png')))
        if i_first < 1200:
            bad('pickle_sleepy.mp4 첫 프레임에 눈동자가 안 보임(파란 픽셀 %d)' % i_first)
        elif i_last > 150:
            bad('pickle_sleepy.mp4 마지막 프레임이 눈을 뜬 상태(파란 픽셀 %d) — 감긴 프레임에서 끝나야 함' % i_last)
        else:
            ok('pickle_sleepy.mp4 — 첫 프레임 눈 뜸(눈동자 %d) → 마지막 프레임 눈 감음(눈동자 %d) '
               '· 그 프레임에서 정지' % (i_first, i_last))

    # phone — 좌우 흐린 여백 없이 다른 타일과 같은 크롭(y=445)으로 꽉 채워졌다
    phr = ROOT / 'avatars/pickle_phone.mp4'
    if phr.exists():
        SRC_PHONE = '/workspace/attachments/2026-11-27/108998653_1795756473323304-184d1227a43f4c64ba878ca9de4c1d89.mp4'
        diff = crop_match(phr, 0.50, SRC_PHONE, 2.40, str(ROOT / '.tmp_ph_out.png'), str(ROOT / '.tmp_ph_src.png'))
        if diff > 10:
            bad('pickle_phone.mp4 0.50s 프레임이 원본 크롭과 다름(평균차 %.1f) — 좌우 여백/블러가 남아 있을 수 있음' % diff)
        else:
            ok('pickle_phone.mp4 — 원본 720x673(y=445) 크롭과 평균차 %.1f (좌우 여백·블러 없이 풀블리드)' % diff)

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            is_mobile=True, has_touch=True)
        p = ctx.new_page(); p.add_init_script(MOCK)
        p.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        p.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        p.goto(URL)
        p.evaluate("()=>localStorage.clear()")
        p.reload(); p.wait_for_timeout(700)
        p.evaluate("()=>window.__mr4.enterRoom('yt-growth')")
        p.wait_for_timeout(600)

        # ══════════ ② 구조 — 상태마다 한 겹 (v4.7: 4겹) ══════════
        p.click('#viewVideoBtn'); p.wait_for_timeout(1400)
        layers = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if sorted(layers['layers']) != ['listening', 'phone', 'sleepy', 'speaking']:
            bad('피클 영상 겹이 %s (speaking·listening·sleepy·phone 4겹이어야 함)' % layers['layers'])
        else:
            ok('피클 타일 영상 4겹 — speaking(vid) + listening·sleepy·phone(vlay) · src 교체 없이 겹으로만')
        dom0 = p.evaluate("()=>window.__mr4.nodeIds().find(n=>n.id==='pickle')")
        src0 = {k: (layers[k] or {}).get('src') for k in ('speak', 'listen', 'sleep', 'phon')}
        if not (src0['speak'] and src0['listen'] and src0['sleep'] and src0['phon']):
            bad('영상 src 가 비었다: %s' % src0)
        elif not (src0['listen'].endswith('pickle_listening.mp4') and src0['sleep'].endswith('pickle_sleepy.mp4')
                  and src0['phon'].endswith('pickle_phone.mp4')):
            bad('겹 src 가 엉뚱함: %s' % src0)
        else:
            ok('네 겹 src — pickle.mp4 / pickle_listening.mp4 / pickle_sleepy.mp4 / pickle_phone.mp4')

        # ══════════ ③ 기본 — 듣는 중(listening) 영상이 계속 돌고 있다 ══════════
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.listen && !m.listen.paused && m.listen.t > 0.2 && m.listen.rs >= 2;}""", timeout=9000)
        ld = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if ld['moodNow'] != 'listening':
            bad('듣는 중 기본 겹이 %r (listening 이어야 함)' % ld['moodNow'])
        if ld['vstate'] != '듣는 중':
            bad('듣는 중 상태 문구가 %r' % ld['vstate'])
        if ld['listen']['op'] != '1':
            bad('listening 영상 opacity %s (1이어야 함)' % ld['listen']['op'])
        if ld['listen']['loop'] is not True:
            bad('listening 영상 loop=%s (8초 루프여야 함)' % ld['listen']['loop'])
        if not ld['speak']['paused'] or ld['speak']['op'] != '0':
            bad('듣는 중인데 speaking 영상이 %s' % ld['speak'])
        if ld['listen']['w'] != 640 or ld['listen']['h'] != 598:
            bad('listening 영상 치수 %sx%s' % (ld['listen']['w'], ld['listen']['h']))
        if ld['vstate'] == '듣는 중' and ld['listen']['op'] == '1' and ld['listen']['loop'] is True \
                and ld['speak']['paused'] and ld['speak']['op'] == '0':
            ok('듣는 중 기본 — pickle_listening.mp4 재생 t=%.2fs op=1 loop=true(%.2f초) · speaking pause/op 0 · 「듣는 중」'
               % (ld['listen']['t'], ld['listen']['dur']))
        t_a0 = ld['listen']['t']
        p.wait_for_timeout(700)
        ld2 = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if not ld2['listen']['t'] > t_a0:
            bad('listening 영상 재생 시간이 늘지 않음 %.2f → %.2f' % (t_a0, ld2['listen']['t']))
        else:
            ok('listening 재생 중 %.2fs → %.2fs (계속 도는 루프)' % (t_a0, ld2['listen']['t']))

        # ══════════ ③ sleepy — 3초를 틀고 눈 감은 마지막 프레임에서 멈춘다 ══════════
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.sleepy && m.sleep && !m.sleep.paused && m.sleep.t > 0.1;}""", timeout=8000)
        p.wait_for_timeout(400)
        s = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if s['vstate'] != '😴 살짝 조는 중':
            bad('sleepy 상태 문구가 %r' % s['vstate'])
        if s['sleep']['op'] != '1':
            bad('sleepy 영상 opacity %s (1이어야 함)' % s['sleep']['op'])
        if not (s['speak']['paused'] and s['speak']['op'] == '0'):
            bad('sleepy 인데 speaking 영상이 %s' % s['speak'])
        if not (s['listen']['paused'] and s['listen']['op'] == '0'):
            bad('sleepy 인데 listening 영상이 계속 %s' % s['listen'])
        if s['sleep']['w'] != 640 or s['sleep']['h'] != 598:
            bad('sleepy 영상 치수 %sx%s' % (s['sleep']['w'], s['sleep']['h']))
        if s['sleep']['loop'] is not False:
            bad('sleepy 영상 loop=%s (한 번만 틀고 멈추려면 false 여야 함)' % s['sleep']['loop'])
        if s['vstate'] == '😴 살짝 조는 중' and s['sleep']['op'] == '1' and s['speak']['paused'] and s['sleep']['loop'] is False:
            ok('sleepy — .tile.sleepy · 「😴 살짝 조는 중」 · pickle_sleepy.mp4 재생 t=%.2fs op=1 · loop=false · speaking 정지'
               % s['sleep']['t'])
        t_a = s['sleep']['t']
        p.wait_for_timeout(600)
        s2 = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if not (s2['sleep']['t'] > t_a):
            bad('sleepy 영상 재생 시간이 늘지 않음 %.2f → %.2f' % (t_a, s2['sleep']['t']))
        else:
            ok('sleepy 재생 중 %.2fs → %.2fs (3.00초 · readyState %d)' % (t_a, s2['sleep']['t'], s2['sleep']['rs']))

        # 끝까지 재생 → 마지막 프레임(눈 감은 얼굴)에서 멈춘다
        try:
            p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
                return m && m.sleep && m.sleep.paused && m.sleep.ended;}""", timeout=9000)
        except Exception:
            bad('sleepy 영상이 9초 안에 끝나지 않음(ended/paused 안 됨)')
        p.wait_for_timeout(1200)
        fz = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        fz_t = fz['sleep']['t']
        if not fz['sleep']['paused']:
            bad('sleepy 끝난 뒤에도 영상이 재생 중(되감겨 루프하는 것으로 보임)')
        elif fz['sleep']['t'] < fz['sleep']['dur'] - 0.12:
            bad('sleepy 끝난 뒤 위치가 %.2fs (마지막 %.2fs 여야 함) — 되감겼다' % (fz['sleep']['t'], fz['sleep']['dur']))
        elif fz['sleep']['done'] != '1':
            bad('sleepy 끝난 뒤 done 표시가 %r (1이어야 함)' % fz['sleep']['done'])
        else:
            ok('sleepy 끝 — 마지막 프레임에서 정지 t=%.2fs/%.2fs · paused · done=1 · 1.2초 지나도 그대로'
               % (fz['sleep']['t'], fz['sleep']['dur']))
        # 같은 상태를 다시 켜도 되감지 않는다(재진입이 아니면 다시 틀지 않음)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_timeout(700)
        again = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if not again['sleep']['paused'] or abs(again['sleep']['t'] - fz_t) > 0.15:
            bad('같은 sleepy 상태를 다시 켰더니 되감겼다: %s' % again['sleep'])
        else:
            ok('같은 상태 재설정에도 마지막 프레임 그대로(%.2fs) — 자동 재생 없음' % again['sleep']['t'])
        p.wait_for_function("""()=>{const t=document.getElementById('toast');
            return !t || !t.classList.contains('show');}""", timeout=6000)   # 화면 전환 토스트가 사라진 뒤 찍는다
        p.wait_for_timeout(500)
        p.screenshot(path=DL + 'meeting_v47_pickle_sleepy.png')
        print('  shot', DL + 'meeting_v47_pickle_sleepy.png')

        # 상태를 벗었다가 다시 들어오면 처음(눈 뜬 프레임)부터 다시 튼다
        p.evaluate("()=>window.__mr4.setTileMood('pickle','')")
        p.wait_for_timeout(200)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_timeout(600)
        re1 = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if re1['sleep']['done'] or re1['sleep']['paused'] or re1['sleep']['t'] > 1.2:
            bad('sleepy 재진입인데 처음부터 재생되지 않음: %s' % re1['sleep'])
        else:
            ok('sleepy 재진입 — currentTime 0 부터 다시 재생(t=%.2fs · done 없음)' % re1['sleep']['t'])

        # ══════════ ④ phone ══════════
        p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.phone && m.phon && !m.phon.paused && m.phon.t > 0.1;}""", timeout=8000)
        p.wait_for_timeout(400)
        ph = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if ph['vstate'] != '📱 딴짓하다 걸림':
            bad('phone 상태 문구가 %r' % ph['vstate'])
        if ph['phon']['op'] != '1' or not ph['phon']['paused'] is False:
            bad('phone 영상이 재생·노출되지 않음: %s' % ph['phon'])
        if not ph['sleep']['paused'] or ph['sleep']['op'] != '0':
            bad('phone 인데 sleepy 영상이 %s' % ph['sleep'])
        if ph['sleepy']:
            bad('phone 으로 바꿨는데 .tile.sleepy 가 남아 있음')
        if ph['phon']['loop'] is not False:
            bad('phone 영상 loop=%s — v4.7.1 부터는 한 번만 재생(loop=false)하고 경청으로 돌아와야 함' % ph['phon']['loop'])
        ok('phone — .tile.phone · 「📱 딴짓하다 걸림」 · pickle_phone.mp4 재생 t=%.2fs op=1 · loop=false(1회) · sleepy 겹 정지'
           % ph['phon']['t'])
        # v4.7.1 — 2.2초 클립이 끝나면 마지막 프레임에 머물지 않고 곧바로 경청(listening)으로 돌아온다
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.mood==='' && m.moodNow==='listening' && m.listen && !m.listen.paused;
            }""", timeout=8000)
        back = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if back['phon']['done'] != '1' or not back['phon']['paused']:
            bad('phone 이 1회 재생 후 멈추지 않음: %s' % back['phon'])
        else:
            ok('phone 1회 종료 — mood \'\' · listening 재생 t=%.2fs · phone 정지(done=1) · 문구 %r'
               % (back['listen']['t'], back['vstate']))
        # '들킨' 표정 프레임(~1.6초) 스크린샷용으로 한 번 더 켠다(1회 클립이라 그 순간을 다시 잡아야 한다)
        # v4.6.3 — 이름·상태(.vov)는 다른 타일과 같이 하단. v4.6.2 의 'phone 만 위로' 예외가 없어졌다
        vov = p.evaluate("""()=>{
            const pick=document.querySelector('.tile[data-id=\"pickle\"]'), gem=document.querySelector('.tile[data-id=\"gemini\"]');
            if(!pick || !gem) return null;
            const a=pick.querySelector('.vov'), bz=gem.querySelector('.vov');
            if(!a || !bz) return null;
            const ra=a.getBoundingClientRect(), rb=bz.getBoundingClientRect();
            const tp=pick.getBoundingClientRect(), tg=gem.getBoundingClientRect();
            const ca=getComputedStyle(a), cb=getComputedStyle(bz);
            return {pickBottom:Math.round(tp.bottom-ra.bottom), gemBottom:Math.round(tg.bottom-rb.bottom),
                    pickFromTop:Math.round(ra.top-tp.top), gemFromTop:Math.round(rb.top-tg.top),
                    cssTop:ca.top, cssBottom:ca.bottom, bg:ca.backgroundImage===cb.backgroundImage};
        }""")
        if not vov:
            bad('phone 타일·다른 타일의 .vov 를 찾지 못함')
        elif vov['cssBottom'] != '0px' or abs(vov['pickBottom'] - vov['gemBottom']) > 2 \
                or abs(vov['pickFromTop'] - vov['gemFromTop']) > 2 or not vov['bg']:
            bad('phone 타일 이름·상태가 다른 타일과 같은 하단이 아님: %s' % vov)
        else:
            ok('phone 타일 이름·상태도 하단 통일 — 위에서 %dpx(다른 타일 %dpx) · 아래 2px · 같은 그라데이션'
               % (vov['pickFromTop'], vov['gemFromTop']))
        # 스크린샷은 '들킨' 표정(클립 1.6~1.9초)에서 — 조는 얼굴과 헷갈리지 않게 눈 크게 뜬 프레임을 잡는다
        # (일부러 pause 시키면 다음 syncAvatarMedia 가 다시 틀어 버리므로, 재생 중에 그 순간을 기다려 찍는다)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.phon && m.phon.t >= 1.50 && m.phon.t <= 2.20;}""", timeout=6000)
        p.screenshot(path=DL + 'meeting_v47_pickle_phone.png')
        print('  shot', DL + 'meeting_v47_pickle_phone.png')

        # phone 을 벗으면 다시 듣는 중 영상으로 돌아온다
        p.evaluate("()=>window.__mr4.setTileMood('pickle','')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.listen && !m.listen.paused && m.listen.op === '1';}""", timeout=8000)
        ok('딴짓 벗음 — listening 영상이 다시 재생(op 1)')

        # 구조 불변 — 상태를 두 번 바꿔도 DOM 노드·src 그대로
        dom1 = p.evaluate("()=>window.__mr4.nodeIds().find(n=>n.id==='pickle')")
        src1 = {k: (p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")[k] or {}).get('src')
                for k in ('speak', 'listen', 'sleep', 'phon')}
        if dom0 != dom1:
            bad('상태 전환에서 타일 DOM 노드가 바뀜: %s → %s' % (dom0, dom1))
        elif src1 != src0:
            bad('상태 전환에서 영상 src 가 바뀜: %s → %s' % (src0, src1))
        else:
            ok('상태 전환 2회 — 타일·영상 노드와 src 그대로(클래스·opacity 만 변경)')

        # ══════════ ⑤ 복귀 — 발언 차례 ══════════
        # 이 라운드에서는 '어쩌다 한 번' 졸기/딴짓 이벤트를 끈다 — 여기서 보려는 것은 발언↔경청 전환뿐이고,
        # 이벤트가 우연히 끼면 발언이 끝난 직후 타일이 딴짓/졸기로 보여 전환 검사가 흔들린다.
        # 이벤트 자체는 ⑥~⑧ 에서 따로 검증한다(v4.7.1 — phone 은 2.2초 뒤 스스로 경청으로 돌아온다).
        p.evaluate("()=>window.__mr4.setMoodPolicy({maxPerSession:0})")
        p.evaluate("""()=>{ window.__log=[]; clearInterval(window.__t);
            window.__t=setInterval(()=>{ const m=window.__mr4.moods().find(x=>x.id==='pickle');
              if(!m) return;
              window.__log.push({sp:m.speaking, mood:m.mood, sl:m.sleepy, ph:m.phone,
                                 vt:m.vstate, slp:m.sleep&&m.sleep.paused, sp_p:m.speak&&m.speak.paused,
                                 sp_op:m.speak&&m.speak.op, ph_p:m.phon&&m.phon.paused}); }, 60); }""")
        # playRound 는 async 라 evaluate 가 끝까지 기다린다 → 블록으로 감싸 즉시 반환시킨다
        p.evaluate("()=>{ window.__mr4.playRound(1); }")
        p.wait_for_function("()=>window.__mr4.state.busy===false && window.__mr4.state.round>=1", timeout=90000)
        p.wait_for_timeout(300)
        awake = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        log = p.evaluate("()=>{ clearInterval(window.__t); return window.__log; }")
        sp = [x for x in log if x['sp']]
        first_sp = sp[0] if sp else None
        if not sp:
            bad('라운드 %d샘플 중 피클 발언(발언 중 상태)을 못 봄' % len(log))
        elif not any(x['sp_p'] is False and x['sp_op'] == '1' for x in sp):
            bad('발언 중인데 speaking 영상이 재생되지 않음: %s' % sp[:3])
        elif first_sp and (first_sp['mood'] or first_sp['sl'] or first_sp['ph']):
            bad('발언이 시작된 첫 샘플에 아직 조는/딴짓 상태: %s' % first_sp)
        elif not any(x['slp'] is not False for x in sp):
            bad('발언 중에 sleep/phone 겹이 멈춰 있지 않음: %s' % sp[:3])
        else:
            ok('발언 차례 → 즉시 깨어남 · 「발언 중」 · speaking 영상 재생(op 1) · sleepy/phone 정지 (발언 샘플 %d개)' % len(sp))
        bad_samples = [x for x in sp if x['mood'] or x['sl'] or x['ph'] or x['vt'] != '발언 중']
        if bad_samples:
            bad('발언 중에 조는/딴짓 상태가 켜진 샘플 %d개: %s' % (len(bad_samples), bad_samples[:3]))
        else:
            ok('발언 중 %d샘플 모두 상태 문구 「발언 중」 · 조는/딴짓 상태 0' % len(sp))
        p.wait_for_timeout(400)
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.moodNow==='listening' && m.listen.op==='1' && !m.listen.paused;}""", timeout=6000)
        after = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        p.evaluate("()=>window.__mr4.setMoodPolicy({maxPerSession:2})")   # ⑥ 정책 검사 전에 원래값으로
        if not after['speak']['paused'] or after['speak']['op'] != '0':
            bad('발언이 끝났는데 speaking 영상이 계속 재생/노출: %s' % after['speak'])
        elif after['moodNow'] != 'listening' or after['listen']['op'] != '1' or after['listen']['paused']:
            bad('발언이 끝났는데 듣는 중 영상으로 돌아오지 않음: %s / %s' % (after['moodNow'], after['listen']))
        else:
            ok('발언 종료 — speaking 정지(op 0) · listening 재생 복귀(op 1) · 상태 문구 %r' % after['vstate'])

        # ══════════ ⑥ 졸기/딴짓은 '어쩌다 한 번' — 상한 2회 · rest>=3 · 22% · 쿨다운 ══════════
        pol = p.evaluate("()=>window.__mr4.moodPolicy()")
        want = {'maxPerSession': 2, 'minRest': 3, 'prob': 0.22, 'cooldownRounds': 1}
        gap = {k: (pol[k], v) for k, v in want.items() if pol[k] != v}
        if gap:
            bad('희소화 정책값이 다름: %s' % gap)
        else:
            ok('희소화 정책 — 세션 최대 %d회 · rest>=%d · 확률 %.0f%% · 쿨다운 %d라운드'
               % (pol['maxPerSession'], pol['minRest'], pol['prob'] * 100, pol['cooldownRounds']))
        # 확률·조건 경계(moodGate) — 발동하지 않는 쪽이 기본값이다
        p.evaluate("()=>window.__mr4.resetMoodSession()")
        gate = p.evaluate("""()=>{ const g=(r,rest,x)=>window.__mr4.moodGate(r,rest,x);
            return {rest2:g(1,2,0.0), p21:g(1,3,0.21), p23:g(1,3,0.23), first:g(1,3,0.0)};}""")
        if gate['rest2'] or not gate['first']:
            bad('moodGate 조건 이상(rest<3 차단 / rest>=3 허용): %s' % gate)
        elif not gate['p21'] or gate['p23']:
            bad('moodGate 확률 문턱이 22%% 가 아님: %s' % gate)
        else:
            ok('moodGate — rest 2는 발동 안 함 · rand 0.21은 발동 · 0.23은 안 함 (22% 문턱)')
        # 상한 — 상한을 0으로 두면 어떤 조건에서도 발동하지 않는다
        p.evaluate("()=>window.__mr4.setMoodPolicy({maxPerSession:0})")
        cap0 = p.evaluate("()=>window.__mr4.moodGate(9,9,0.0)")
        p.evaluate("()=>window.__mr4.setMoodPolicy({maxPerSession:2})")
        if cap0:
            bad('상한이 0인데 moodGate 가 통과함')
        else:
            ok('상한 — maxPerSession 0 이면 통과 0(세션 상한이 실제로 막는다)')
        # 실제 라운드 4회 (확률 1로 강제) — 발동은 2회를 넘지 않고, 모두 rest>=3 · 라운드 간격>1
        p.evaluate("()=>{ window.__mr4.resetMoodSession(); window.__mr4.setMoodPolicy({debugProb:1}); }")
        seen_mood = []
        for n in (1, 2, 3, 4):
            p.evaluate("(n)=>{ window.__mr4.playRound(n); }", n)
            p.wait_for_function("()=>window.__mr4.state.busy===false && window.__mr4.state.round>=%d" % n, timeout=90000)
            p.wait_for_timeout(200)
            st = p.evaluate("()=>window.__mr4.moodPolicy()")
            if st['events'] > 2:
                bad('%d라운드에서 발동이 %d회 — 세션 상한 2회를 넘음' % (n, st['events']))
            mnow = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
            if mnow['mood']:
                seen_mood.append((n, mnow['mood'], mnow['vstate']))
        pol2 = p.evaluate("()=>window.__mr4.moodPolicy()")
        log = pol2['log']
        badrest = [x for x in log if x['rest'] < 3]
        badgap = [x for i, x in enumerate(log[1:], 1) if log[i]['round'] - log[i - 1]['round'] <= 1]
        if pol2['events'] > 2:
            bad('세션 발동 %d회 — 상한 2회 초과' % pol2['events'])
        elif badrest:
            bad('rest<3 인데 발동한 기록: %s' % badrest)
        elif badgap:
            bad('쿨다운 없이 연달아 발동: %s' % log)
        else:
            ok('4라운드(확률 1 강제) — 발동 %d회(상한 2 이내) · 모두 rest>=3 · 라운드 간격>1 · 기록 %s'
               % (pol2['events'], [(x['round'], x['rest'], x['mood']) for x in log]))
        # 발동한 뒤 쿨다운/상한이 게이트에서 실제로 막는지
        if log:
            last = log[-1]['round']
            cool = p.evaluate("()=>window.__mr4.moodPolicy()")
            g_next = p.evaluate("(r)=>window.__mr4.moodGate(r,9,0.0)", last + 1)
            if g_next:
                bad('발동한 라운드(%d) 바로 다음 라운드에 또 발동 가능(쿨다운 없음)' % last)
            else:
                ok('쿨다운 — 라운드 %d 발동 뒤 라운드 %d 는 게이트에서 막힘(발동 %d회/2)'
                   % (last, last + 1, cool['events']))
        # 확률 1을 풀고 기본(22%)으로 되돌린다 — 실제 회의에서는 대부분 그냥 지나간다
        p.evaluate("()=>window.__mr4.setMoodPolicy({debugProb:null})")
        pol3 = p.evaluate("()=>window.__mr4.moodPolicy()")
        if pol3['debugProb'] is not None:
            bad('확률 강제가 풀리지 않음: %s' % pol3['debugProb'])
        else:
            ok('확률 강제 해제 — 기본 22% 로 복귀')
        # 자동 발동이 '발언 중'과 겹치지 않는다(발동한 순간에도 speaking 이면 안 된다)
        overlap = [x for x in seen_mood if x[2] == '발언 중']
        if overlap:
            bad('자동 상태가 발언 중에 켜짐: %s' % overlap)
        else:
            ok('자동 상태는 발언 중이 아닐 때만 켜짐(관측 %d회)' % len(seen_mood))

        # ══════════ ⑦ 글로 보기 — 영상은 멈춘다 ══════════
        p.click('#viewTextBtn'); p.wait_for_timeout(500)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_timeout(400)
        t2 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        vstage = p.evaluate("""()=>{const s=document.querySelector('.tile[data-id=\"pickle\"] .vstage');
            return s ? getComputedStyle(s).display : 'none';}""")
        # 글로 보기에서는 .vstage 가 숨겨지고, 영상은 전부 pause 상태여야 한다(opacity 는 화상 모드 CSS 전용이라 보지 않는다)
        if not t2['sleep']['paused'] or not t2['phon']['paused'] or not t2['speak']['paused'] \
                or not t2['listen']['paused']:
            bad('글로 보기인데 상태 영상이 재생됨(듣는 중 영상 포함): %s' % t2)
        elif t2['state'] != '😴 조는 중' or vstage != 'none':
            bad('글로 보기 카드 배지/화면 상태가 %r · vstage %s' % (t2['state'], vstage))
        else:
            ok('글로 보기 — 카드 배지 「😴 조는 중」만 바뀌고 영상은 정지(vstage none · listening 포함 정지)')
        p.evaluate("()=>window.__mr4.setTileMood('pickle','')")

        # ══════════ ⑧ 단일 파일 ══════════
        single = Path('/workspace/downloads/darkjin_meeting_room_v4.html')
        kb = single.stat().st_size / 1024
        if kb > 3400:
            bad('단일 파일 %.0fKB — 3.32MB 를 넘음' % kb)
        sp = ctx.new_page(); sp.add_init_script(MOCK)
        sp.on('pageerror', lambda e: errs.append('single pageerror:' + str(e)))
        sp.goto('file://' + str(single)); sp.wait_for_timeout(800)
        sp.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); sp.wait_for_timeout(500)
        sp.click('#viewVideoBtn'); sp.wait_for_timeout(1400)
        # v4.7 — 기본 겹(listening)도 인라인되어 있어야 한다
        try:
            sp.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
                return m && m.listen && !m.listen.paused && m.listen.t>0.15 && m.listen.rs>=2;}""", timeout=9000)
            sl = sp.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
            if not (sl['listen']['src'] or '').startswith('data:video/mp4'):
                bad('단일 파일 listening 영상이 인라인되지 않음: %s' % (sl['listen']['src'] or '')[:40])
            else:
                ok('단일 파일 — 인라인 listening 영상이 기본으로 재생(readyState %d · t=%.2fs · loop=%s)'
                   % (sl['listen']['rs'], sl['listen']['t'], sl['listen']['loop']))
        except Exception:
            bad('단일 파일에서 listening 영상이 재생되지 않음')
        sp.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        try:
            sp.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
                return m && m.sleep && !m.sleep.paused && m.sleep.t>0.15 && m.sleep.rs>=2;}""", timeout=9000)
            sv = sp.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
            inline = (sv['sleep']['src'] or '').startswith('data:video/mp4')
            if not inline:
                bad('단일 파일 sleepy 영상이 인라인되지 않음: %s' % (sv['sleep']['src'] or '')[:40])
            else:
                ok('단일 파일 %.0fKB — 인라인 sleepy 영상 재생(readyState %d · t=%.2fs · %dx%d)'
                   % (kb, sv['sleep']['rs'], sv['sleep']['t'], sv['sleep']['w'], sv['sleep']['h']))
        except Exception:
            bad('단일 파일에서 sleepy 영상이 재생되지 않음')
        sp.evaluate("()=>window.__mr4.setTileMood('pickle','phone')")
        try:
            sp.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
                return m && m.phon && !m.phon.paused && m.phon.t>0.15 && m.phon.rs>=2;}""", timeout=9000)
            spv = sp.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
            if not (spv['phon']['src'] or '').startswith('data:video/mp4'):
                bad('단일 파일 phone 영상이 인라인되지 않음: %s' % (spv['phon']['src'] or '')[:40])
            else:
                ok('단일 파일 — 인라인 phone 영상 재생(readyState %d · t=%.2fs)' % (spv['phon']['rs'], spv['phon']['t']))
        except Exception:
            bad('단일 파일에서 phone 영상이 재생되지 않음')
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
    print("ALL PASS (v4.7)")


main()
