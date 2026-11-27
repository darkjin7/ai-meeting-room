"""v4.6.3 — 피클 '딴짓(phone)' 아바타 영상 — 회의 중 몰래 폰 보다 들켜서 깜짝 놀라는 얼굴 클로즈업.

원본: attachments/2026-11-27/108998653_1795756473323304-184d1227a43f4c64ba878ca9de4c1d89.mp4
      (피클 · 8.04초 · 720x1280 · H.264 + AAC 4.2MB)

성진님 요청(v4.6.3)
  "폰 때문에 옆이 공간이 생기네 꼭 폰 안보여도 되니 꽉차게 해주고."
  → v4.6.2 는 눈과 손에 든 폰을 함께 담으려고 세로로 긴 422x598 앞면 + 좌우 흐린 배경이었다(좌우 여백).
    v4.6.3 은 그 여백을 없애고 **다른 타일과 같은 얼굴 크기·구도로 꽉 채운다**:
    y=445 에서 720x673(타일 비율 1.07) → 640x598 풀블리드, 흐린 배경·비네트 없음.
    성진님이 "폰 안 보여도 된다"고 하셨으므로 폰을 포기하고 얼굴 표정(몰래 봄 → 들킴)을 살린다.
    폰 불빛은 3.55~3.75초에 프레임 맨 아래에 살짝 스친다(그대로 둔다).

구간: 1.90~4.10초(2.20초) — 힐끔 폰 보는 능글 얼굴 → 눈 크게 뜸 → 입 벌린 '들킴' 얼굴
      끝(들킨 얼굴)과 시작(몰래 보는 얼굴)은 0.375초 크로스페이드로 이어 붙여 반복이 튀지 않게 한다.
      * 폰을 든 손이 화면 아래로 내려가 있는 2.0~3.0초가 가장 자연스럽다 — 그 구간을 앞부분에 둔다.
결과: avatars/pickle_phone.mp4 (무음 · H.264 · faststart · 약 160~300KB · 2.20초 루프)
"""
import os, shutil, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/108998653_1795756473323304-184d1227a43f4c64ba878ca9de4c1d89.mp4")
TMP = os.path.join(ROOT, ".tmp_phone_build")
OUT_MP4 = os.path.join(ROOT, "avatars/pickle_phone.mp4")

CROP_Y = 445                      # 다른 타일과 같은 크롭 기준(얼굴 크기·위치가 같아야 6분할이 한 화면처럼 보인다)
CROP_H = 673
OUT_W, OUT_H = 640, 598
FPS = 24
SEG_START = "1.90"
SEG_LEN = "2.20"
XFADE = 4                         # 0.167초 — 들킨 얼굴 ↔ 몰래 보는 얼굴(짧게: 얼굴 클로즈업이라 길면 잔상이 보인다)
CRF_TRY = [25, 24, 26, 23, 27, 22]
KB_MIN, KB_MAX = 160, 300


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
    names = sorted(os.listdir(TMP + "/src"))
    print("세그먼트 %ss + %ss → 프레임 %d장" % (SEG_START, SEG_LEN, len(names)))

    frames = []
    for n in names:
        im = Image.open(os.path.join(TMP + "/src", n)).convert("RGB")
        im = im.crop((0, CROP_Y, 720, CROP_Y + CROP_H)).resize((OUT_W, OUT_H), Image.LANCZOS)
        frames.append(im)

    n = len(frames)
    out = frames[:n - XFADE]
    for i in range(XFADE):
        a = (i + 1) / XFADE
        out.append(Image.blend(frames[n - XFADE + i], frames[i], a))
    for i, img in enumerate(out, 1):
        img.save(TMP + "/out/%04d.jpg" % i, quality=90)
    out[0].save(os.path.join(ROOT, "diag/phone_first_frame.png"))
    out[len(out) // 2].save(os.path.join(ROOT, "diag/phone_mid_frame.png"))

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
    print("mp4   : %s  %.0fKB (crf %d · %d프레임 = %.2f초 루프 · 640x598 풀블리드)"
          % (OUT_MP4, kb, crf, len(out), len(out) / FPS))
    if not (KB_MIN <= kb <= KB_MAX):
        print("!! 용량이 목표(160~300KB) 밖 — 확인 필요")


main()
