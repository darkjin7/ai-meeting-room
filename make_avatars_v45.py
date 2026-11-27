"""v4.5 — 6분할 화상 타일을 꽉 채우는(full-bleed) 캐릭터 아바타 만들기.

원본: attachments/2026-11-27/ai_family_8_avatars.jpg (1870x1176 · 4x2 콘택트 시트)
      칸 이미지 영역: x 28/486/944/1402 ~ +440, y 102(1행)·634(2행) ~ +442

v4.4 까지는 타일 안의 작은 원(.vbob 84px)에 넣는 256x256 정사각 썸네일이었다.
v4.5 부터는 타일 전체(약 186x174 모바일 · 1.07 비율)를 채우므로
  - 타일 비율(1.07)에 맞춘 400x374 크롭을 잘라
  - 512x478 webp 로 저장한다 (모바일 2x 화면 372px 보다 커서 선명)
  - 크롭 위치: 머리카락 위 5% 여백 · 턱 76% — 영상(pickle.mp4)과 같은 구도
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/ai_family_8_avatars.jpg")
OUT = os.path.join(ROOT, "avatars")

IDS = ["pickle", "gemini", "cue", "hark", "chatgpt", "claude", "meta_muse", "keyring"]
COLS = [28, 486, 944, 1402]        # 칸 이미지 왼쪽
ROWS = [102, 634]                  # 칸 이미지 위
CW, CH = 440, 442                  # 칸 이미지 크기

CROP_W, CROP_H = 400, 374          # 타일 비율 1.07
OUT_W, OUT_H = 512, 478


def main():
    sheet = Image.open(SRC).convert("RGB")
    for i, pid in enumerate(IDS):
        x0 = COLS[i % 4] + (CW - CROP_W) // 2      # 가로 가운데
        y0 = ROWS[i // 4] + 11                     # 머리카락 위 5% 여백
        im = sheet.crop((x0, y0, x0 + CROP_W, y0 + CROP_H)).resize((OUT_W, OUT_H), Image.LANCZOS)
        p = os.path.join(OUT, pid + ".webp")
        im.save(p, "WEBP", quality=82, method=6)
        print("%-9s %s  %.0f KB" % (pid, im.size, os.path.getsize(p) / 1024))


main()
