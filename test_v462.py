"""v4.6.2 검증 — 피클의 상태 영상 `sleepy`(조는 중) · `phone`(딴짓) 과 speaking 복귀

성진님 지시
  "피클이 눈 감고 조는 영상을 넣어 줘" → v4.6.2 sleepy
  "회의 중에 몰래 폰 보다 들킨 영상도 넣어 줘" → v4.6.2 phone

무엇을 재는가
① 파일 — avatars/pickle_sleepy.mp4 · pickle_phone.mp4 가 640x598 · 무음 H.264 · faststart · 250~380KB
   (phone 은 얼굴 아래 손에 든 폰이 프레임 안에 있는지도 프레임을 열어 확인)
② 구조 — 피클 타일에 영상이 상태마다 한 겹씩(speaking=video.vid 1 + sleepy·phone=video.vlay 2).
   상태를 바꿔도 요소·src 가 그대로다(CSS 클래스·opacity 로만 전환)
③ sleepy — setTileMood('pickle','sleepy') → .tile.sleepy · 하단 문구 '😴 살짝 조는 중' ·
   pickle_sleepy.mp4 재생(opacity 1, currentTime 증가) · speaking 영상은 pause + opacity 0
④ phone — setTileMood('pickle','phone') → .tile.phone · 문구 '📱 딴짓하다 걸림' · pickle_phone.mp4 재생 ·
   sleepy 겹은 정지
⑤ 복귀 — 피클 발언 차례(playRound)가 오면 즉시 잠이 깨고 .sleepy/.phone 이 사라지며 speaking 영상이 재생.
   듣는 중으로 돌아오면 다시 멈춘다
⑥ 자동 — 라운드에서 피클 차례 없이 다른 AI 가 2명 넘게 말하면 sleepy/phone 중 하나가 스스로 켜진다.
   발언 중에는 절대 조는/딴짓 상태가 켜지지 않는다
⑦ 글로 보기 — 화상이 아닐 때는 상태 배지만 바뀌고 영상은 재생되지 않는다
⑧ 단일 파일(downloads/darkjin_meeting_room_v4.html) — sleepy·phone 이 인라인되어 실제로 재생된다
⑨ 모바일 390x844 스크린샷 — downloads/meeting_v462_pickle_sleepy.png · meeting_v462_pickle_phone.png
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
    """프레임을 뽑아 아래쪽(폰이 드는 자리) 밝은 픽셀 수를 센다 — 폰 화면이 프레임 안에 있는지"""
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', str(path),
                    '-frames:v', '1', out_png], check=True)
    from PIL import Image
    im = Image.open(out_png).convert('L')
    w, h = im.size
    px = im.load()
    band = [(x, y) for y in range(int(h * 0.62), h) for x in range(int(w * 0.28), int(w * 0.72))]
    bright = sum(1 for (x, y) in band if px[x, y] > 205)
    return w, h, bright, len(band), out_png


def main():
    fails, errs = [], []

    def ok(m):
        print('OK ' + m)

    def bad(m):
        fails.append(m)
        print('FAIL ' + m)

    # ══════════ ① 파일 ══════════
    specs = [('pickle_sleepy.mp4', 3.5, 3.5), ('pickle_phone.mp4', 2.2, 2.2)]
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
        if not (250 <= kb <= 380):
            bad('%s %.0fKB — 250~380KB 밖' % (name, kb))
        else:
            ok('%s — %.2f초 · 640x598 · 무음 · faststart · %.0fKB' % (name, sec, kb))

    # phone 은 얼굴·폰이 같이 보여야 한다 — 폰이 들리는 장면(1.05s)의 아래·가운데 띠에 폰 화면 밝기가 있어야 한다
    if (ROOT / 'avatars/pickle_phone.mp4').exists():
        w, h, bright, total, png = frame_brightness_bands(ROOT / 'avatars/pickle_phone.mp4', 1.05,
                                                          str(ROOT / '.tmp_phone_check.png'))
        if bright < 200:
            bad('pickle_phone.mp4 1.05s 프레임에서 폰 화면이 보이지 않음(밝은 픽셀 %d/%d)' % (bright, total))
        else:
            ok('pickle_phone.mp4 1.05s — 아래·가운데 띠에 폰 화면 밝은 픽셀 %d개 (얼굴+폰 함께 프레임 안)' % bright)

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

        # ══════════ ③ sleepy ══════════
        p.evaluate("()=>window.__mr4.setTileMood('pickle','sleepy')")
        p.wait_for_function("""()=>{const m=window.__mr4.moods().find(x=>x.id==='pickle');
            return m && m.sleepy && m.sleep && !m.sleep.paused && m.sleep.t > 0.1;}""", timeout=8000)
        p.wait_for_timeout(500)
        s = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if s['vstate'] != '😴 살짝 조는 중':
            bad('sleepy 상태 문구가 %r' % s['vstate'])
        if s['sleep']['op'] != '1':
            bad('sleepy 영상 opacity %s (1이어야 함)' % s['sleep']['op'])
        if not (s['speak']['paused'] and s['speak']['op'] == '0'):
            bad('sleepy 인데 speaking 영상이 %s' % s['speak'])
        if s['sleep']['w'] != 640 or s['sleep']['h'] != 598:
            bad('sleepy 영상 치수 %sx%s' % (s['sleep']['w'], s['sleep']['h']))
        if s['vstate'] == '😴 살짝 조는 중' and s['sleep']['op'] == '1' and s['speak']['paused']:
            ok('sleepy — .tile.sleepy · 「😴 살짝 조는 중」 · pickle_sleepy.mp4 재생 t=%.2fs op=1 · speaking 영상 정지'
               % s['sleep']['t'])
        t_a = s['sleep']['t']
        p.wait_for_timeout(700)
        s2 = p.evaluate("()=>window.__mr4.moods().find(m=>m.id==='pickle')")
        if not (s2['sleep']['t'] > t_a):
            bad('sleepy 영상 재생 시간이 늘지 않음 %.2f → %.2f' % (t_a, s2['sleep']['t']))
        else:
            ok('sleepy 루프 재생 중 %.2fs → %.2fs (3.5초 루프 · readyState %d)' % (t_a, s2['sleep']['t'], s2['sleep']['rs']))
        p.wait_for_function("""()=>{const t=document.getElementById('toast');
            return !t || !t.classList.contains('show');}""", timeout=6000)   # 화면 전환 토스트가 사라진 뒤 찍는다
        p.wait_for_timeout(600)                                             # 토스트 페이드아웃까지 기다린다
        p.screenshot(path=DL + 'meeting_v462_pickle_sleepy.png')
        print('  shot', DL + 'meeting_v462_pickle_sleepy.png')

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
        ok('phone — .tile.phone · 「📱 딴짓하다 걸림」 · pickle_phone.mp4 재생 t=%.2fs op=1 · sleepy 겹 정지'
           % ph['phon']['t'])
        p.wait_for_timeout(300)
        p.screenshot(path=DL + 'meeting_v462_pickle_phone.png')
        print('  shot', DL + 'meeting_v462_pickle_phone.png')

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
                                  sl_op:m.sleep&&m.sleep.op, ph_op:m.phon&&m.phon.op}); }, 60); }""")
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
            playing = (x['slp'] is False and x['sl_op'] == '1') if k == 'sleepy' else (x['ph_p'] is False and x['ph_op'] == '1')
            if not playing:
                bad('자동 %s 상태인데 영상이 재생되지 않음: %s' % (k, x))
            else:
                ok('자동 전환 — %d라운드 만에 피클이 「%s」 상태로 (영상 재생 중)' % (rounds, x['vt']))
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
    print('ALL PASS (v4.6.2)')


main()
