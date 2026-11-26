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
# 저장소에 올라가는 index.html 은 ./avatars/*.webp 상대경로 그대로 (Pages 에서 캐시됨).
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
dest = pathlib.Path("/workspace/downloads/darkjin_meeting_room_v4.html")
dest.write_text(out, encoding="utf-8")
print("download build: %s (%.0f KB, avatars inlined: %d)" % (dest, dest.stat().st_size/1024, out.count("data:image/webp;base64,")))
PY
echo "built: work/meeting-room/index.html ($(wc -l < index.html) lines)"
