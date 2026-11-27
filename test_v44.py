"""v4.5 검증 — ① 글로 보기 발언 카드 '세로 중앙' 정렬 ② 피클 움직이는 영상(풀블리드 타일)

① 글로 보기 중앙 정렬
   - 모바일 390x844에서 라운드를 재생하는 동안 매 프레임 '지금 말하는 카드'의 중앙 오차
     (카드 중심 − 보이는 영역 중심, 위 스티키 헤더/아래 고정 오너 콘솔 제외)를 실측한다.
   - 발언이 바뀔 때마다 그 카드가 실제로 세로 중앙에 안착해야 한다(±12px).
   - 문서 끝/처음에 걸려 더 올릴 수 없는 경우는 카드 전체가 보이면 통과로 본다.
   - 🎥 화상 6분할 모드에서는 스크롤이 절대 일어나지 않아야 한다.
② 피클 영상
   - avatars/pickle.mp4: 오디오 트랙 없음 · H.264 · 640x598(타일 1.07 비율) · faststart · 300~600KB (ffmpeg 로 직접 확인)
   - 화상 6분할 피클 타일: <video muted loop playsinline autoplay poster> + play().catch,
     실제로 재생되고(currentTime 증가) 타일 전체를 꽉 채우며(v4.5 풀블리드 · 둥근 프레임 없음),
     글로 보기로 돌아가면 멈춘다.
"""
import json, os, re, subprocess, sys
from playwright.sync_api import sync_playwright

EXE = '/workspace/work/chrome/chrome-headless-shell-linux64/chrome-headless-shell'
FF  = '/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2'
URL = 'file:///workspace/work/meeting-room/index.v4.html'
DL  = '/workspace/downloads/'
WORK = '/workspace/work/meeting-room/'
MP4 = WORK + 'avatars/pickle.mp4'
POSTER = WORK + 'avatars/pickle_poster.webp'
SRC = '/workspace/attachments/2026-11-27/14721333_1795705520204730-a76018e78928422ea8771a0b82cd4156.mp4'

# 실제 음성 속도에 가까운 목업(발언당 0.7초) — 자동 스크롤이 안착하는지 볼 수 있게
MOCK = r"""
(() => {
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'},{name:'Test Korean C',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ this.speaking=true; setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },700); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; }
  };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
  window.__siv=[];
  const __siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(o){ window.__siv.push((o&&o.behavior)||"auto"); return __siv.apply(this, arguments); };
  // 매 프레임 '지금 말하는 카드'의 중앙 오차 기록
  window.__center=[];
  (function loop(){
    const t=document.querySelector('.tile.speaking');
    if(t && window.__mr4){
      const b=window.__mr4.visibleCenter();
      const r=t.getBoundingClientRect();
      window.__center.push({id:t.dataset.id, err:Math.round(r.top+r.height/2-b.center),
        top:Math.round(r.top), bottom:Math.round(r.bottom),
        bandTop:Math.round(b.top), bandBottom:Math.round(b.bottom), y:Math.round(window.pageYOffset)});
    }
    requestAnimationFrame(loop);
  })();
})();
"""

def probe(path):
    r = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True)
    return r.stdout + r.stderr

def main():
    errs = []
    # ── 0) 영상 파일 자체 검사 ────────────────────────────────
    assert os.path.exists(MP4), 'pickle.mp4 없음'
    assert os.path.exists(POSTER), 'pickle_poster.webp 없음'
    info = probe(MP4)
    size_kb = os.path.getsize(MP4) / 1024
    assert 300 <= size_kb <= 600, '영상 용량이 목표(300~600KB) 밖: %.0fKB' % size_kb
    assert 'Video: h264' in info, 'H.264 아님:\n' + info
    assert '640x598' in info, '640x598 아님'
    assert 'Audio:' not in info, '오디오 트랙이 남아 있음:\n' + info
    dur = float(re.search(r'Duration: 00:00:(\d+\.\d+)', info).group(1))
    assert 7.0 <= dur <= 9.0, '길이 이상: %s' % dur
    head = open(MP4, 'rb').read(4096)
    assert b'moov' in head, 'faststart 아님(moov 가 앞에 없음)'
    print('OK avatars/pickle.mp4 — %.0fKB · H.264 640x598(타일 1.07 비율) %.2f초 · 오디오 0 · faststart (원본 %.1fMB)'
          % (size_kb, dur, os.path.getsize(SRC) / 1048576))

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE, args=['--no-sandbox'])

        # ═════════ 모바일 390x844 ═════════
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = ctx.new_page(); mp.add_init_script(MOCK)
        mp.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        mp.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        mp.goto(URL); mp.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','1')")
        mp.reload(); mp.wait_for_timeout(500); mp.evaluate("window.__mr4.dismissLobby()")   # v4.6 로비
        mp.click('.agcard[data-id="yt-growth"]'); mp.wait_for_timeout(800)

        # 글로 보기에서는 영상을 내려받지 않는다(src 없음, 재생 안 함)
        v0 = mp.evaluate("()=>window.__mr4.videos()")
        assert len(v0) == 1, '피클 영상 요소가 없음: %s' % v0
        assert v0[0]['src'] in (None, ''), '글로 보기인데 영상 src 가 붙음: %s' % v0[0]
        assert v0[0]['paused'] is True, '글로 보기인데 영상이 재생 중: %s' % v0[0]
        assert v0[0]['poster'] and v0[0]['poster'].endswith('pickle_poster.webp'), 'poster 없음: %s' % v0[0]
        assert v0[0]['muted'] and v0[0]['loop'] and v0[0]['plays'] and not v0[0]['autoplay'], '영상 속성 이상: %s' % v0[0]
        assert v0[0]['controls'] is False, '영상에 컨트롤이 붙음'
        print('OK 글로 보기 — 영상은 src 없이 대기(poster·muted·loop·playsinline · v4.5.1 부터 autoplay 속성 없이 코드가 발언 중에만 재생)')

        # ── ① 글로 보기: 발언이 바뀔 때마다 카드가 세로 중앙으로 ──
        mp.wait_for_function("()=>!document.getElementById('toast').classList.contains('show')", timeout=6000)
        mp.evaluate("()=>{ window.__center = []; window.scrollTo(0, document.documentElement.scrollHeight); }")
        band = mp.evaluate("()=>window.__mr4.visibleCenter()")
        mp.wait_for_timeout(200)
        mp.click('#nextRoundBtn')
        # 발언 중 카드가 중앙에 안착한 순간을 잡아 화면을 남긴다(눈 검수용)
        shot = False
        try:
            mp.wait_for_function("""()=>{const t=document.querySelector('.tile.speaking'); if(!t) return false;
                const b=window.__mr4.visibleCenter(); const r=t.getBoundingClientRect();
                return Math.abs(r.top+r.height/2-b.center) <= 6 && r.top > b.top && r.bottom < b.bottom;}""", timeout=9000)
            mp.screenshot(path=DL + 'meeting_v44_mobile_text_center.png')
            mp.screenshot(path=WORK + 'v44_mobile_text_center.png')
            shot = True
        except Exception:
            pass
        mp.wait_for_function("()=>window.__mr4.state.round>=1 && window.__mr4.state.busy===false", timeout=40000)
        mp.wait_for_timeout(500)
        log = mp.evaluate("()=>window.__center")
        per = []
        for s in log:
            if not per or per[-1]['id'] != s['id']:
                per.append(dict(s))
            else:
                per[-1].update(s)          # 그 발언자의 마지막(안착한) 값
        assert len(per) >= 5, '발언자 순서 기록 부족: %s' % [x['id'] for x in per]
        maxy = mp.evaluate("()=>Math.round(document.documentElement.scrollHeight - innerHeight)")
        stuck = []
        for x in per:
            if abs(x['err']) <= 12: continue
            at_edge = x['y'] <= 2 or x['y'] >= maxy - 2
            if at_edge and x['top'] >= x['bandTop'] - 1 and x['bottom'] <= x['bandBottom'] + 1: continue
            stuck.append(x)
        assert not stuck, '발언 카드가 세로 중앙에 오지 않음: %s' % stuck
        # 화면 가장자리에 걸친 채 멈추지 않았는지: 카드가 '보이는 영역' 안에 있어야 한다
        off = [x for x in per if x['top'] < x['bandTop'] - 1 or x['bottom'] > x['bandBottom'] + 1]
        assert not off, '발언 카드가 보이는 영역을 벗어남: %s' % off
        print('OK 글로 보기 중앙 정렬 — 보이는 영역 %d~%d(중심 %d) · %d명 순서대로 중앙 오차(px) %s'
              % (band['top'], band['bottom'], band['center'], len(per), [(x['id'], x['err']) for x in per]))
        if not shot:
            mp.screenshot(path=DL + 'meeting_v44_mobile_text_center.png')
            mp.screenshot(path=WORK + 'v44_mobile_text_center.png')

        # 카드 하나씩 직접 지정해도 정확히 중앙에 온다(결정적 확인)
        per_tile = []
        for tid in ['pickle', 'gemini', 'cue', 'hark', 'chatgpt', 'claude']:
            mp.evaluate("(id)=>window.__mr4.focusTile(id)", tid)
            mp.wait_for_timeout(700)
            c = mp.evaluate("(id)=>window.__mr4.centerOf(id)", tid)
            per_tile.append((tid, c['err'], c['scrollY']))
        assert all(abs(e) <= 12 for _, e, _ in per_tile), 'focusTile 중앙 정렬 실패: %s' % per_tile
        print('OK focusTile 6장 전부 중앙 — 오차(px) %s' % per_tile)

        # ── ② 화상 6분할 피클 영상 (v4.5.1 — 발언 중에만 재생 · 듣는 중에는 정지 이미지) ──
        mp.evaluate("()=>{ window.__siv = []; }")
        mp.click('#viewVideoBtn'); mp.wait_for_timeout(900)
        vv = mp.evaluate("()=>window.__mr4.videos()")
        assert len(vv) == 1, '화상 모드 피클 영상 1개 아님: %s' % vv
        v = vv[0]
        assert v['src'] and v['src'].endswith('avatars/pickle.mp4'), '영상 src 이상: %s' % v
        assert v['rs'] >= 1 and v['w'] == 640 and v['h'] == 598, '영상이 실제로 열리지 않음(metadata): %s' % v
        # 듣는 중(idle) → 멈춰 있고 opacity 0, 아래깔린 정지 이미지는 보인다
        idle = mp.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle')")
        assert v['paused'] is True, '아무도 말하지 않는데 영상이 재생 중: %s' % v
        assert idle['video']['op'] == '0', '듣는 중인데 영상이 보임: %s' % idle['video']
        assert idle['poster'] and idle['poster']['nw'] == 360 and idle['poster']['c'], '정지 이미지 레이어가 없음: %s' % idle['poster']
        assert idle['poster']['op'] == '1' and idle['poster']['disp'] != 'none', '듣는 중 정지 이미지가 안 보임: %s' % idle['poster']
        print('OK 화상 모드 듣는 중 — 영상 pause + opacity 0 · 정지 이미지(pickle_poster 360x336) 표시 · src 유지')
        geo = mp.evaluate("""()=>{
            const t=document.querySelector('.tile[data-id="pickle"]');
            const b=t.querySelector('.vbob'); const v=b.querySelector('video.face');
            const rb=b.getBoundingClientRect(), rv=v.getBoundingClientRect(), s=getComputedStyle(v);
            const p=b.querySelector('img.vposter'); const rp=p.getBoundingClientRect(), ps=getComputedStyle(p);
            return {tile:{w:Math.round(t.getBoundingClientRect().width),h:Math.round(t.getBoundingClientRect().height)},
                    bob:{w:Math.round(rb.width),h:Math.round(rb.height)}, video:{w:Math.round(rv.width),h:Math.round(rv.height)},
                    poster:{w:Math.round(rp.width),h:Math.round(rp.height),fit:ps.objectFit,pos:ps.objectPosition,rad:ps.borderRadius},
                    fit:s.objectFit, pos:s.objectPosition, radius:s.borderRadius, nw:v.videoWidth, nh:v.videoHeight,
                    speaking:t.classList.contains('speaking')};
        }""")
        assert geo['fit'] == 'cover', 'object-fit 이 cover 아님: %s' % geo['fit']
        assert geo['radius'] == '0px', '풀블리드가 아님(둥근 프레임 잔존): %s' % geo['radius']
        assert abs(geo['video']['w'] - geo['bob']['w']) <= 2 and abs(geo['video']['h'] - geo['bob']['h']) <= 2, '영상이 프레임과 크기가 다름: %s' % geo
        assert geo['bob']['w'] >= geo['tile']['w'] - 6 and geo['bob']['h'] >= geo['tile']['h'] - 6, '영상이 타일을 꽉 채우지 않음: %s' % geo
        assert geo['nw'] == 640 and geo['nh'] == 598 and abs(geo['nw']/geo['nh'] - 1.07) < 0.01, '영상 소스 비율이 타일과 다름: %s' % geo
        assert abs(geo['poster']['w'] - geo['bob']['w']) <= 2 and abs(geo['poster']['h'] - geo['bob']['h']) <= 2, '정지 이미지가 프레임과 크기가 다름: %s' % geo
        assert geo['poster']['fit'] == 'cover' and geo['poster']['rad'] == '0px' and geo['poster']['pos'].endswith('45%'), '정지 이미지 풀블리드 속성 이상: %s' % geo['poster']
        assert geo['speaking'] is False, '듣는 중인데 발언 클래스가 붙음'
        # 화상 모드: 스크롤 없음 + 발언이 바뀌어도 스크롤 없음
        assert mp.evaluate("()=>Math.round(window.pageYOffset)") == 0, '화상 모드에서 페이지가 스크롤됨'
        mp.evaluate("()=>{ window.__siv = []; }")
        mp.evaluate("()=>{ window.__mr4.playRound(2); }")   # Promise 를 기다리지 않고 던지기만
        mp.wait_for_function("()=>!!document.querySelector('.tile.speaking')", timeout=12000)
        ys = []
        for _ in range(24):
            ys.append(mp.evaluate("()=>Math.round(window.pageYOffset)"))
            mp.wait_for_timeout(120)
        assert set(ys) == {0}, '화상 모드 발언 전환에서 스크롤 발생: %s' % sorted(set(ys))
        assert not [x for x in mp.evaluate("()=>window.__siv") if x == 'smooth'], '화상 모드에서 smooth 스크롤 호출'
        # 피클 차례가 오면 그때만 재생된다 — 라운드 전 구간을 80ms 마다 샘플링해 확인한다.
        # (2026-11-27) 2라운드가 아직 도는 중에 다시 playRound(2) 를 던지면 그대로 반환돼
        #              피클이 먼저 발언한 판에서는 표본이 비었다 — 라운드를 마저 끝내고 3라운드를 새로 잰다.
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        mp.wait_for_timeout(300)
        mp.evaluate("""()=>{ window.__vidLog = [];
            clearInterval(window.__vidTimer);
            window.__vidTimer = setInterval(()=>{
              const v=document.querySelector('video.vid'); const t=document.querySelector('.tile[data-id=\"pickle\"]');
              if(!v||!t) return;
              window.__vidLog.push({sp:t.classList.contains('speaking'), p:v.paused,
                op:getComputedStyle(v).opacity, t:Math.round(v.currentTime*100)/100, src:!!v.getAttribute('src')});
            }, 80); }""")
        mp.evaluate("()=>{ window.__mr4.playRound(3); }")
        mp.wait_for_function("()=>window.__mr4.state.busy===false", timeout=60000)
        mp.wait_for_timeout(400)
        log = mp.evaluate("()=>{ clearInterval(window.__vidTimer); return window.__vidLog; }")
        played = [x for x in log if x['sp'] and not x['p'] and x['op'] == '1' and x['t'] > 0.2]
        assert played, '피클 발언 중에 영상이 재생되지 않음: %s' % [x for x in log if x['sp']][:5]
        bad_idle = [x for x in log if not x['sp'] and (not x['p'] or x['op'] != '0')]
        assert not bad_idle, '듣는 중인데 영상이 재생/노출됨: %s' % bad_idle[:5]
        assert all(x['src'] for x in log), '라운드 중 영상 src 가 사라진 구간이 있음'
        t1 = played[0]['t']; t2 = played[-1]['t']
        print('OK 피클 발언 중에만 재생 — 샘플 %d개 중 발언 중 재생 %d개(t %.2f→%.2f, opacity 1) · 듣는 중엔 모두 pause+opacity 0 · src 유지'
              % (len(log), len(played), t1, t2))
        mp.screenshot(path=DL + 'meeting_v44_mobile_pickle_speaking.png')
        mp.screenshot(path=WORK + 'v44_mobile_pickle_speaking.png')
        mp.wait_for_timeout(400)
        mp.screenshot(path=DL + 'meeting_v44_mobile_video6.png')
        mp.screenshot(path=WORK + 'v44_mobile_video6.png')
        print('OK 화상 6분할 피클 영상 — %s · 640x598 · 타일 %dx%d 풀블리드 · 발언 전환 스크롤 0'
              % (v['src'], geo['video']['w'], geo['video']['h']))

        # 발언이 끝나면 다시 멈춘다
        vdone = mp.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle')")
        assert vdone['speaking'] is False and vdone['video']['paused'] is True, '발언이 끝났는데 영상이 계속 재생: %s' % vdone['video']
        assert vdone['video']['op'] == '0', '발언이 끝났는데 영상이 아직 보임: %s' % vdone['video']
        print('OK 발언 종료 — 영상 자동 정지(opacity 0) · 정지 이미지로 복귀')

        # 글로 보기로 돌아가면 영상은 멈춘다
        mp.click('#viewTextBtn'); mp.wait_for_timeout(500)
        v3 = mp.evaluate("()=>window.__mr4.videos()")[0]
        assert v3['paused'] is True, '글로 보기로 돌아왔는데 영상이 계속 재생: %s' % v3
        # 다시 화상으로 → 듣는 중이면 멈춘 채(정지 이미지), 발언 중이면 그때만 재생
        mp.click('#viewVideoBtn'); mp.wait_for_timeout(900)
        v4 = mp.evaluate("()=>window.__mr4.videos()")[0]
        assert v4['paused'] is True, '듣는 중인데 화상 복귀 시 영상이 재생됨: %s' % v4
        assert mp.evaluate("()=>window.__mr4.media().find(m=>m.id==='pickle').video.src").endswith('avatars/pickle.mp4'), '화상 복귀 후 영상 src 가 사라짐'
        print('OK 보기 전환 — 글로 보기에서 영상 정지 · 화상으로 돌아오면 듣는 중이면 정지(정지 이미지, src 유지)')

        # 데스크톱 1440x900 화상 모드 — 영상 크기/레이아웃(듣는 중이라도 치수는 metadata 로 확보)
        ctx2 = b.new_context(viewport={'width': 1440, 'height': 900})
        dp = ctx2.new_page(); dp.add_init_script(MOCK)
        dp.on('pageerror', lambda e: errs.append('desktop-pageerror:' + str(e)))
        dp.goto(URL); dp.evaluate("localStorage.clear(); localStorage.setItem('darkjin_mr4_speed','2')")
        dp.reload(); dp.wait_for_timeout(400); dp.evaluate("window.__mr4.dismissLobby()")   # v4.6 로비
        dp.click('.agcard[data-id="yt-growth"]'); dp.wait_for_timeout(600)
        dp.click('#viewVideoBtn'); dp.wait_for_timeout(1200)
        dv = dp.evaluate("()=>window.__mr4.videos()")[0]
        dg = dp.evaluate("""()=>{const b=document.querySelector('.tile[data-id="pickle"] .vbob');const v=b.querySelector('video.face');
            const rb=b.getBoundingClientRect(), rv=v.getBoundingClientRect();
            return {bob:[Math.round(rb.width),Math.round(rb.height)], video:[Math.round(rv.width),Math.round(rv.height)], nw:v.videoWidth};}""")
        assert dv['rs'] >= 1 and dv['w'] == 640, '데스크톱에서 영상 metadata 로드 실패: %s' % dv
        assert dv['paused'] is True and dv['op'] == '0', '든는 중인데 데스크톱에서 영상이 재생/노출: %s' % dv
        assert abs(dg['video'][0]-dg['bob'][0]) <= 2 and dg['video'][0] >= 100, '데스크톱 풀블리드 채움 실패: %s' % dg
        assert dp.evaluate("()=>Math.round(window.pageYOffset)") == 0
        # 발언 중에만 재생(데스크톱 확인)
        dp.evaluate("()=>{ window.__mr4.playRound(1); }")
        dp.wait_for_function("""()=>{const v=document.querySelector('video.vid');return v && !v.paused && v.currentTime>0.2;}""", timeout=30000)
        dp.screenshot(path=WORK + 'v44_desktop_video6.png')
        dp.screenshot(path=DL + 'meeting_v44_desktop_video6.png')
        print('OK 데스크톱 1440x900 — 피클 영상 %dx%d · 듣는 중 정지 → 발언 중 재생 · 스크롤 0' % (dg['video'][0], dg['video'][1]))
        b.close()

    if errs:
        print('ERRORS:'); [print(' ', e) for e in errs]; sys.exit(1)
    print('ALL PASS (v4.5.1)')

main()
