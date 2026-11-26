#!/usr/bin/env bash
# 다크진 AI 비서실 · 6분할 회의실 v4 빌드 (v4/* → 단일 index.html)
set -e
cd "$(dirname "$0")"
cat v4/head.html > index.html
printf '<script>\n' >> index.html
cat v4/agendas.js v4/app.js >> index.html
printf '</script>\n</body>\n</html>\n' >> index.html
cp index.html index.v4.html
cp index.html /workspace/downloads/darkjin_meeting_room_v4.html
echo "built: work/meeting-room/index.html ($(wc -l < index.html) lines)"
