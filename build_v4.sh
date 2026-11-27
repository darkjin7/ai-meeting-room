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
python3 - <<'PY'
import base64, pathlib, re
html = pathlib.Path("index.html").read_text(encoding="utf-8")
def sub(m):
    rel = m.group(0)
    p = pathlib.Path(rel)
    if not p.exists():
        return rel
    return "data:image/webp;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
out = re.sub(r"\./avatars/[a-z_]+\.webp", sub, html)
mp4 = pathlib.Path("avatars/pickle.mp4")
vid_inlined = 0
if mp4.exists():
    vid_src = '"./avatars/pickle.mp4"'
    dup = out.count(vid_src)
    if dup > 1:   # v4.5.1 — 주소를 여러 번 적으면 mp4 가 그만큼 인라인되어 파일이 배로 커진다
        raise SystemExit("pickle.mp4 주소가 %d번 나온다 — PEOPLE/app.js 의 중복 문자열을 지워 주세요" % dup)
    out = out.replace(vid_src, '"data:video/mp4;base64,' + base64.b64encode(mp4.read_bytes()).decode("ascii") + '"')
    vid_inlined = out.count("data:video/mp4;base64,")
    if vid_inlined != 1:
        raise SystemExit("mp4 인라인 %d개 — 1개여야 합니다" % vid_inlined)
dest = pathlib.Path("/workspace/downloads/darkjin_meeting_room_v4.html")
dest.write_text(out, encoding="utf-8")
print("download build: %s (%.0f KB, avatars inlined: %d, video inlined: %d)" % (dest, dest.stat().st_size/1024, out.count("data:image/webp;base64,"), vid_inlined))
PY
echo "built: work/meeting-room/index.html ($(wc -l < index.html) lines)"
