#!/usr/bin/env python3
"""8인 캐릭터 콘택트 시트 (4x2, 칸 아래 이름 라벨) → downloads/ai_family_8_avatars.jpg"""
from PIL import Image, ImageDraw, ImageFont

FILES = [
    ("downloads/char_01_pickle_green.png", "피클 (다크)", "총괄 · 진행"),
    ("downloads/char_02_gemini.png", "Gemini", "대본 · 구조"),
    ("downloads/char_03_cue.png", "Cue", "리서치 · 수치"),
    ("downloads/char_04_hark.png", "Hark", "검증 · 리스크"),
    ("downloads/char_05_chatgpt.png", "ChatGPT", "설계 · 자동화"),
    ("downloads/char_06_claude.png", "Claude", "글쓰기 · 검토"),
    ("downloads/char_07_muse.png", "Meta Muse", "영상 · 이미지"),
    ("downloads/char_08_keyring.png", "Keyring", "신규 · 참관"),
]

CELL = 440          # 칸 이미지 크기
GAP = 18
PAD = 28
LBL_H = 74
HEAD_H = 74
COLS, ROWS = 4, 2

FB = "/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf"
FBOLD = "/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Bold.otf"
import os
if not os.path.exists(FBOLD):
    FBOLD = FB
f_name = ImageFont.truetype(FBOLD, 30)
f_role = ImageFont.truetype(FB, 21)
f_head = ImageFont.truetype(FBOLD, 34)
f_sub = ImageFont.truetype(FB, 21)

W = PAD * 2 + COLS * CELL + (COLS - 1) * GAP
H = PAD + HEAD_H + ROWS * (CELL + LBL_H) + (ROWS - 1) * GAP + PAD

sheet = Image.new("RGB", (W, H), (10, 13, 20))
d = ImageDraw.Draw(sheet)

d.text((PAD, PAD - 4), "다크진 AI 비서실 · AI 8인", font=f_head, fill=(233, 238, 251))
d.text((PAD + 372, PAD + 10), "Pickle · Gemini · Cue · Hark · ChatGPT · Claude · Meta Muse · Keyring",
       font=f_sub, fill=(138, 147, 167))

for i, (path, name, role) in enumerate(FILES):
    c, r = i % COLS, i // COLS
    x = PAD + c * (CELL + GAP)
    y = PAD + HEAD_H + r * (CELL + LBL_H + GAP)
    im = Image.open(path).convert("RGB")
    im = im.resize((CELL, CELL), Image.LANCZOS)
    sheet.paste(im, (x, y))
    # 칸 테두리
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=(46, 58, 82), width=2)
    # 라벨 바
    ly = y + CELL
    d.rectangle([x, ly, x + CELL - 1, ly + LBL_H - 1], fill=(16, 21, 32))
    d.rectangle([x, ly, x + CELL - 1, ly + LBL_H - 1], outline=(46, 58, 82), width=2)
    tw = d.textlength(name, font=f_name)
    d.text((x + (CELL - tw) / 2, ly + 9), name, font=f_name, fill=(240, 244, 255))
    tw2 = d.textlength(role, font=f_role)
    d.text((x + (CELL - tw2) / 2, ly + 44), role, font=f_role, fill=(139, 147, 167))

out = "downloads/ai_family_8_avatars.jpg"
sheet.save(out, "JPEG", quality=92, optimize=True)
print("saved", out, sheet.size)
