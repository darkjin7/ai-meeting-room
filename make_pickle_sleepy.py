"""v4.6.2 — 피클 '조는 중(sleepy)' 아바타 영상.

원본: attachments/2026-11-27/470953036_1795756046285661-721a46f539ad4606af64de05b86a6540.mp4
      (피클 · 8.04초 · 720x1280 · H.264 + AAC 3.2MB — 눈을 감고 조는 장면)

원본은 8초짜리 한 호흡이다.
  0.0~2.0s  눈 뜨고 정면
  2.2~5.4s  눈꺼풀이 내려오고 고개가 살짝 떨궈짐(완전히 감김)
  5.5~6.0s  눈을 살짝 떠서 슬쩍 봄
  6.0~8.0s  다시 눈 뜨고 정면
화상 타일에서 '듣는 중' 내내 틀 영상이므로 앞뒤의 또렷한 '눈 뜬' 구간은 잘라 내고,
조는 구간(1.95~5.95s)만 4초 루프로 쓴다. 끝(슬쩍 뜸)과 시작(눈꺼풀 내려옴)은
0.5초 크로스페이드로 이어 붙여 이음매가 보이지 않게 한다.

크롭·축소 기준은 v4.5 의 pickle.mp4(make_pickle_video.py)와 같다 —
  y=445 에서 720x673(타일 비율 1.07) → 640x598. 원본이 같은 구도로 만들어져
  첫 프레임(눈 뜬 장면)이 pickle.mp4 첫 프레임과 같은 얼굴 위치로 겹치는 것을 확인했다.
결과: avatars/pickle_sleepy.mp4 (무음 · H.264 · faststart · 250~380KB)
"""
import os, shutil, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/470953036_1795756046285661-721a46f539ad4606af64de05b86a6540.mp4")
TMP = os.path.join(ROOT, ".tmp_sleepy_build")
OUT_MP4 = os.path.join(ROOT, "avatars/pickle_sleepy.mp4")

CROP_Y = 445
CROP_H = 673
OUT_W, OUT_H = 640, 598
FPS = 24
SEG_START = "1.95"           # 조는 구간만
SEG_LEN = "3.50"          # 5.45s 에서 끊는다 — 그 뒤로는 눈이 완전히 떠서 '조는 중'이 깨진다
XFADE = 12                   # 0.5초 — 끝(슬쩍 뜸) ↔ 시작(눈꺼풀 내려옴)
CRF_TRY = [29, 28, 27, 26, 25, 24, 30]   # 250~380KB 에 드는 첫 CRF 를 쓴다
KB_MIN, KB_MAX = 250, 380


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("failed: %s" % " ".join(cmd))


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP + "/src", exist_ok=True)
    os.makedirs(TMP + "/out", exist_ok=True)

    sh([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", SEG_START, "-t", SEG_LEN, "-i", SRC,
        "-vf", "fps=%d" % FPS, "-q:v", "2", TMP + "/src/%04d.jpg"])
    src = sorted(os.listdir(TMP + "/src"))
    print("세그먼트 %ss + %ss → 프레임 %d장" % (SEG_START, SEG_LEN, len(src)))

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

    best = None
    for crf in CRF_TRY:
        sh([FF, "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(FPS), "-i", TMP + "/out/%04d.jpg",
            "-an", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-crf", str(crf), "-preset", "slow", "-g", "48",
            "-movflags", "+faststart", TMP + "/try.mp4"])
        kb = os.path.getsize(TMP + "/try.mp4") / 1024
        print("  crf %d → %.0fKB" % (crf, kb))
        if best is None or (KB_MIN <= kb <= KB_MAX and not (KB_MIN <= best[1] <= KB_MAX)):
            best = (crf, kb, TMP + "/try.mp4")
        if KB_MIN <= kb <= KB_MAX:
            best = (crf, kb, TMP + "/try.mp4")
            break

    crf, kb, path = best
    shutil.copyfile(path, OUT_MP4)
    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0fKB (crf %d · %d프레임 = %.2f초 루프)" % (OUT_MP4, kb, crf, len(out), len(out) / FPS))
    if not (200 <= kb <= 420):
        print("!! 용량이 목표(250~380KB) 밖 — 확인 필요")


main()
