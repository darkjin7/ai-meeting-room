"""v4.5 — 피클 움직이는 아바타 영상 (v4.5 full-bleed 타일용 · 비네트 없이 원본 그대로).

원본: attachments/2026-11-27/14721333_1795705520204730-a76018e78928422ea8771a0b82cd4156.mp4
      (피클 · 7.93초 · 720x1280 · H.264 + AAC 3.0MB)

v4.4 는 타일 안의 원형 프레임(1:1)에 넣느라 좌우에 흐린 비네트 여백을 깔았다.
v4.5 는 타일 자체가 가로로 넓은 사각형(모바일 186x174 = 1.07)이므로
  - 원본에서 타일 비율(1.07) 그대로 720x673 을 잘라 쓴다 → 여백·비네트 없음
  - 크롭 위치 y=445: 이마·눈(44%)·턱(72%)·넥타이까지 — 아바타 정지 이미지와 같은 구도
  - 640x598 로 축소(모바일 2x 372px 보다 큼) · 오디오 제거 · faststart
  - 8초 루프 이음매는 마지막 10프레임 ↔ 첫 10프레임 크로스페이드로 지운다
결과: avatars/pickle.mp4 (poster: avatars/pickle_poster.webp)
"""
import os, shutil, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/14721333_1795705520204730-a76018e78928422ea8771a0b82cd4156.mp4")
TMP = os.path.join(ROOT, ".tmp_pickle")
OUT_MP4 = os.path.join(ROOT, "avatars/pickle.mp4")
OUT_POSTER = os.path.join(ROOT, "avatars/pickle_poster.webp")

CROP_Y = 445
CROP_H = 673                  # 720 / 1.07 ≒ 673 → 타일과 같은 비율
OUT_W, OUT_H = 640, 598
FPS = 24
XFADE = 10
CRF = 29


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("failed: %s" % " ".join(cmd))


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP + "/src", exist_ok=True)
    os.makedirs(TMP + "/out", exist_ok=True)

    sh([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", SRC,
        "-vf", "fps=%d" % FPS, "-q:v", "2", TMP + "/src/%04d.jpg"])
    src = sorted(os.listdir(TMP + "/src"))
    print("frames:", len(src))

    frames = []
    for name in src:
        im = Image.open(os.path.join(TMP + "/src", name)).convert("RGB")
        im = im.crop((0, CROP_Y, 720, CROP_Y + CROP_H)).resize((OUT_W, OUT_H), Image.LANCZOS)
        frames.append(im)

    n = len(frames)
    out = frames[:n - XFADE]
    for i in range(XFADE):
        a = (i + 1) / XFADE
        out.append(Image.blend(frames[n - XFADE + i], frames[i], a))

    for i, img in enumerate(out, 1):
        img.save(TMP + "/out/%04d.jpg" % i, quality=90)

    out[0].resize((360, 336), Image.LANCZOS).save(OUT_POSTER, "WEBP", quality=86, method=6)

    sh([FF, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(FPS), "-i", TMP + "/out/%04d.jpg",
        "-an", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
        "-crf", str(CRF), "-preset", "slow", "-g", "48",
        "-movflags", "+faststart", OUT_MP4])

    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0f KB" % (OUT_MP4, os.path.getsize(OUT_MP4) / 1024))
    print("poster: %s  %.0f KB" % (OUT_POSTER, os.path.getsize(OUT_POSTER) / 1024))


main()
