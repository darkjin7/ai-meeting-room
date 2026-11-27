#!/usr/bin/env bash
# 다크진 AI 비서실 · 6분할 회의실 v4 빌드 (v4/* → 단일 index.html)
set -e
cd "$(dirname "$0")"
cat v4/head.html > index.html
printf '<script>\n' >> index.html
cat v4/agendas.js v4/app.js >> index.html
printf '</script>\n</body>\n</html>\n' >> index.html
cp index.html index.v4.html
# v4.3 — 성진님께 보내는 단일 파일(downloads/)은 아바타를 base64 로 품어 혼자서도 열린다.
# v4.4 — 피클 움직이는 영상도 이 파일에만 base64 로 함께 넣는다(약 +375KB).
#         저장소에 올라가는 index.html 은 ./avatars/*.webp · pickle.mp4 상대경로 그대로 (Pages 에서 캐시됨).
#         iOS Safari 가 data: 영상을 못 열면 코드가 poster/정지 이미지로 조용히 대체한다.
# v4.6.1 — 입장 인트로 영상 3종(intro_1~3.mp4 + 포스터)도 인라인한다. 앱 코드의 INTRO_CLIPS 배열에
#          적힌 주소를 그대로 훑으므로, 새 클립(intro_4 …)을 넣어도 이 스크립트는 고칠 필요가 없다.
# v4.6.2 — 피클 '조는 중'(sleepy) 영상도 인라인한다. 상태 영상은 상태마다 한 겹씩 늘어나므로
#          새 상태(sleepy …)를 넣을 때는 이 스크립트의 inline_once 목록에 주소를 하나 더 적는다.
# v4.7  — '듣는 중'(listening) 기본 영상도 인라인한다(4겹: speaking·listening·sleepy·phone).
python3 - <<'PY'
import base64, pathlib, re
html = pathlib.Path("index.html").read_text(encoding="utf-8")

# ── 1) 아바타 이미지(webp)는 전부 인라인 ──
def sub_webp(m):
    rel = m.group(0)
    p = pathlib.Path(rel)
    return "data:image/webp;base64," + base64.b64encode(p.read_bytes()).decode("ascii") if p.exists() else rel
html = re.sub(r"\./avatars/[a-z0-9_]+\.webp", sub_webp, html)

def inline_once(html, rel, mime, what):
    pat = '"%s"' % rel
    n = html.count(pat)
    if n > 1:
        raise SystemExit("%s 주소(%s)가 %d번 나온다 — 1번만 적어야 한다" % (what, rel, n))
    if n == 0:
        return html, 0
    p = pathlib.Path(rel)
    if not p.exists():
        raise SystemExit("%s 파일이 없다: %s" % (what, rel))
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return html.replace(pat, '"data:%s;base64,%s"' % (mime, b64)), 1

# ── 2) 피클 상태 영상 (v4.7 — speaking pickle.mp4 + listening pickle_listening.mp4 + sleepy + phone) ──
html, n_pickle = inline_once(html, "./avatars/pickle.mp4", "video/mp4", "pickle.mp4")
html, n_listen = inline_once(html, "./avatars/pickle_listening.mp4", "video/mp4", "pickle_listening.mp4")
html, n_sleepy = inline_once(html, "./avatars/pickle_sleepy.mp4", "video/mp4", "pickle_sleepy.mp4")
html, n_phone = inline_once(html, "./avatars/pickle_phone.mp4", "video/mp4", "pickle_phone.mp4")
if n_pickle != 1 or n_listen != 1:
    raise SystemExit("피클 speaking/listening 영상 주소가 PEOPLE 에 1번씩 있어야 한다 (%d/%d)" % (n_pickle, n_listen))

# ── 3) 입장 인트로 클립 — 코드(INTRO_CLIPS)에 적힌 순서대로 ──
intro_srcs = list(dict.fromkeys(re.findall(r'"(\./avatars/intro_[0-9]+\.mp4)"', html)))
if not intro_srcs:
    raise SystemExit("INTRO_CLIPS 에 인트로 영상이 하나도 없다")
n_intro = 0
for rel in intro_srcs:
    html, k = inline_once(html, rel, "video/mp4", "인트로")
    n_intro += k
missing = [r for r in intro_srcs if ('"%s"' % r) in html]   # 아직 주소로 남아 있으면 인라인 실패
if missing:
    raise SystemExit("인트로 영상이 인라인되지 않았다: %s" % ", ".join(missing))
left = re.findall(r'"\./avatars/[a-z0-9_]+\.(?:webp|css|png|mp4)"', html)
if left:
    raise SystemExit("인라인되지 않은 자산이 남았다: %s" % ", ".join(sorted(set(left))))

dest = pathlib.Path("/workspace/downloads/darkjin_meeting_room_v4.html")
dest.write_text(html, encoding="utf-8")
kb = dest.stat().st_size / 1024
print("download build: %s (%.0f KB, avatars inlined: %d, pickle videos: %d/%d/%d/%d (speaking/listening/sleepy/phone), intro clips: %s)"
      % (dest, kb, html.count("data:image/webp;base64,"), n_pickle, n_listen, n_sleepy, n_phone,
         ", ".join(p.name for p in map(pathlib.Path, intro_srcs))))
if kb > 3400:   # v4.7 — 듣는 중 기본 영상(309KB)까지 4겹이 되어 2.93MB → 3.32MB 로 올림
    raise SystemExit("단일 파일이 %.0f KB — 3.32MB 를 넘었습니다" % kb)
PY
echo "built: work/meeting-room/index.html ($(wc -l < index.html) lines)"
