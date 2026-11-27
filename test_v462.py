"""v4.6.3 검증 — 피클의 상태 영상 `sleepy`(조는 중 · 눈 감기면 정지) · `phone`(딴짓 · 풀블리드)

성진님 지시
  "폰 때문에 옆이 공간이 생기네 꼭 폰 안보여도 되니 꽉차게 해주고." → v4.6.3 phone 풀블리드
  "조는 모습은 눈이 감기면 멈추고 있다가 자기 차례 되면 깨는 걸로 할 수 있나?" → v4.6.3 sleepy 정지

무엇을 재는가
① 파일 — avatars/pickle_sleepy.mp4 · pickle_phone.mp4 가 640x598 · 무음 H.264 · faststart
   (sleepy 3.0초 · phone 2.2초)
   · sleepy: **첫 프레임은 눈을 뜨고(눈동자 파란 픽셀 다수), 마지막 프레임은 눈을 감은 상태**(파란 픽셀 0)
   · phone : 첫 프레임이 원본 720x673(y=445) 크롭과 거의 같다 → 좌우 흐린 여백·비네트가 없다(풀블리드)
② 구조 — 피클 타일에 영상이 상태마다 한 겹씩(speaking=video.vid 1 + sleepy·phone=video.vlay 2).
   상태를 바꿔도 요소·src 가 그대로다(CSS 클래스·opacity 로만 전환)
③ sleepy — 재생 중 loop===false · 3초를 다 틀면 마지막 프레임(눈 감은 얼굴)에서 paused 로 멈춰 있고
   done 표시로 다시 되감기지 않는다(같은 상태를 다시 setTileMood 해도 재생 안 함).
   상태를 벗었다가 다시 들어올 때만 currentTime 0 에서 다시 재생된다.
④ phone — .tile.phone · '📱 딴짓하다 걸림' · 루프 재생 · sleepy 겹 정지.
   이름·상태(.vov)는 다른 타일과 같이 **하단**에 있다(v4.6.2 의 위로 올리기 예외 제거 확인)
⑤ 복귀 — 피클 발언 차례(playRound)가 오면 즉시 잠이 깨고 .sleepy/.phone 이 사라지며 speaking 영상이 재생
⑥ 자동 — 라운드에서 피클 차례 없이 다른 AI 가 2명 넘게 말하면 sleepy/phone 중 하나가 스스로 켜진다
⑦ 글로 보기 — 화상이 아닐 때는 상태 배지만 바뀌고 영상은 재생되지 않는다
⑧ 단일 파일(downloads/darkjin_meeting_room_v4.html) — sleepy·phone 이 인라인되어 실제로 재생된다
⑨ 모바일 390x844 스크린샷 — downloads/meeting_v463_pickle_sleepy.png · meeting_v463_pickle_phone.png
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

        # ══════════ ② 구조 — 상태마다 한 겹 ══════════
        p.click('#viewVideoBtn'); p.wait_for_timeout(900)
        layers = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if sorted(layers['layers']) != ['phone', 'sleepy', 'speaking']:
            bad('피클 영상 겹이 %s (speaking·sleepy·phone 3겹이어야 함)' % layers['layers'])
        else:
            ok('피클 타일 영상 3겹 — speaking(vid) + sleepy·phone(vlay) · src 교체 없이 겹으로만')
        dom0 = p.evaluate("()=>window.__mr4.nodeIds().find(n=>n.id==='pickle')")
        src0 = {k: (layers[k] or {}).get('src') for k in ('speak', 'sleep', 'phon')}
        if not (src0['speak'] and src0['sleep'] and src0['phon']):
            bad('영상 src 가 비었다: %s' % src0)
        elif not (src0['sleep'].endswith('pickle_sleepy.mp4') and src0['phon'].endswith('pickle_phone.mp4')):
            bad('겹 src 가 엉뚱함: %s' % src0)
        else:
            ok('세 겹 src — pickle.mp4 / pickle_sleepy.mp4 / pickle_phone.mp4')

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
        p.screenshot(path=DL + 'meeting_v463_pickle_sleepy.png')
        print('  shot', DL + 'meeting_v463_pickle_sleepy.png')

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
        if ph['phon']['loop'] is not True:
            bad('phone 영상 loop=%s (딴짓 영상은 계속 도는 루프여야 함)' % ph['phon']['loop'])
        ok('phone — .tile.phone · 「📱 딴짓하다 걸림」 · pickle_phone.mp4 재생 t=%.2fs op=1 · loop=true · sleepy 겹 정지'
           % ph['phon']['t'])
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
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.phon && m.phon.t >= 1.50 && m.phon.t <= 1.62;}""", timeout=6000)
        p.screenshot(path=DL + 'meeting_v463_pickle_phone.png')
        print('  shot', DL + 'meeting_v463_pickle_phone.png')

        # 구조 불변 — 상태를 두 번 바꿔도 DOM 노드·src 그대로
        dom1 = p.evaluate("()=>window.__mr4.nodeIds().find(n=>n.id==='pickle')")
        src1 = {k: (p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")[k] or {}).get('src')
                for k in ('speak', 'sleep', 'phon')}
        if dom0 != dom1:
            bad('상태 전환에서 타일 DOM 노드가 바뀜: %s → %s' % (dom0, dom1))
        elif src1 != src0:
            bad('상태 전환에서 영상 src 가 바뀜: %s → %s' % (src0, src1))
        else:
            ok('상태 전환 2회 — 타일·영상 노드와 src 그대로(클래스·opacity 만 변경)')

        # ══════════ ⑤ 복귀 — 발언 차례 ══════════
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
        after = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        if not after['speak']['paused'] or after['speak']['op'] != '0':
            bad('발언이 끝났는데 speaking 영상이 계속 재생/노출: %s' % after['speak'])
        else:
            ok('발언 종료 — speaking 영상 정지(op 0) · 상태 문구 %r' % after['vstate'])

        # ══════════ ⑥ 자동 — 다른 AI 둘이 지나가면 스스로 딴짓/조기 ══════════
        p.evaluate("""()=>{ window.__auto=[]; clearInterval(window.__a);
            window.__a=setInterval(()=>{ const m=window.__mr4.moods().find(x=>x.id==='pickle');
              if(!m) return;
              window.__auto.push({sp:m.speaking, mood:m.mood, vt:m.vstate,
                                  slp:m.sleep&&m.sleep.paused, ph_p:m.phon&&m.phon.paused,
                                  sl_op:m.sleep&&m.sleep.op, ph_op:m.phon&&m.phon.op,
                                  sl_done:m.sleep&&m.sleep.done, sl_t:m.sleep&&m.sleep.t}); }, 60); }""")
        seen = {}
        rounds = 0
        while rounds < 4 and not seen:
            rounds += 1
            p.evaluate("(n)=>{ window.__mr4.playRound(n); }", rounds)
            p.wait_for_function("()=>window.__mr4.state.busy===false && window.__mr4.state.round>=%d" % rounds, timeout=90000)
            p.wait_for_timeout(300)
            auto = p.evaluate("()=>window.__auto")
            for x in auto:
                if x['mood']:
                    seen[x['mood']] = x
            if seen:
                break
        p.evaluate("()=>clearInterval(window.__a)")
        auto = p.evaluate("()=>window.__auto")
        if not seen:
            bad('%d라운드 동안 피클이 스스로 조는/딴짓 상태로 바뀌지 않음' % rounds)
        else:
            k = list(seen)[0]
            x = seen[k]
            # sleepy 는 3초를 다 틀면 마지막 프레임에서 멈춘다 — '재생 중'과 '끝나서 멈춘 상태' 둘 다 정상
            if k == 'sleepy':
                playing = (x['slp'] is False and x['sl_op'] == '1') or x['sl_done'] == '1'
            else:
                playing = (x['ph_p'] is False and x['ph_op'] == '1')
            if not playing:
                bad('자동 %s 상태인데 영상이 재생되지 않음: %s' % (k, x))
            else:
                ok('자동 전환 — %d라운드 만에 피클이 「%s」 상태로 (영상 재생 · t=%s)' % (rounds, x['vt'], x['sl_t']))
        overlap = [x for x in auto if x['sp'] and x['mood']]
        if overlap:
            bad('발언 중에 자동 상태가 켜진 샘플 %d개' % len(overlap))
        else:
            ok('자동 전환 %d샘플 — 발언 중과 조는/딴짓 상태가 겹친 샘플 0' % len(auto))

        # ══════════ ⑦ 글로 보기 — 영상은 멈춘다 ══════════
        p.click('#viewTextBtn'); p.wait_for_timeout(500)
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_timeout(400)
        t2 = p.evaluate("()=>window.__mr4.moods().find(x=>x.id==='pickle')")
        vstage = p.evaluate("""()=>{const s=document.querySelector('.tile[data-id=\"pickle\"] .vstage');
            return s ? getComputedStyle(s).display : 'none';}""")
        # 글로 보기에서는 .vstage 가 숨겨지고, 영상은 전부 pause 상태여야 한다(opacity 는 화상 모드 CSS 전용이라 보지 않는다)
        if not t2['sleep']['paused'] or not t2['phon']['paused'] or not t2['speak']['paused']:
            bad('글로 보기인데 상태 영상이 재생됨: %s' % t2)
        elif t2['state'] != '😴 조는 중' or vstage != 'none':
            bad('글로 보기 카드 배지/화면 상태가 %r · vstage %s' % (t2['state'], vstage))
        else:
            ok('글로 보기 — 카드 배지 「😴 조는 중」만 바뀌고 영상은 정지(vstage none)')
        p.evaluate("()=>window.__mr4.setTileMood('pickle','')")

        # ══════════ ⑧ 단일 파일 ══════════
        single = Path('/workspace/downloads/darkjin_meeting_room_v4.html')
        kb = single.stat().st_size / 1024
        if kb > 3000:
            bad('단일 파일 %.0fKB — 2.93MB 를 넘음' % kb)
        sp = ctx.new_page(); sp.add_init_script(MOCK)
        sp.on('pageerror', lambda e: errs.append('single pageerror:' + str(e)))
        sp.goto('file://' + str(single)); sp.wait_for_timeout(800)
        sp.evaluate("()=>window.__mr4.enterRoom('yt-growth')"); sp.wait_for_timeout(500)
        sp.click('#viewVideoBtn'); sp.wait_for_timeout(900)
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
    print("ALL PASS (v4.6.3)")


main()
