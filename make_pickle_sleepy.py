"""v4.6.3 — 피클 '조는 중(sleepy)' 아바타 영상 — 눈이 감기는 순간까지 재생하고 그 프레임에서 멈춘다.

원본: attachments/2026-11-27/470953036_1795756046285661-721a46f539ad4606af64de05b86a6540.mp4
      (피클 · 8.04초 · 720x1280 · H.264 + AAC 3.2MB — 눈을 감고 조는 장면)

성진님 요청(v4.6.3)
  "조는 모습은 눈이 감기면 멈추고 있다가 자기 차례 되면 깨는 걸로 할 수 있나?
   지금 것도 나쁘지는 않자만 보고 싶어"
  → v4.6.2 는 1.95~5.45초(눈 감김 → 슬쩍 뜸)를 0.5초 크로스페이드로 이어 붙여 4초 루프였다.
    눈을 살짝 뜨는 대목이 섞여 '조는 중'이 끊겼다.
  → v4.6.3 은 **눈을 뜨고 있다가 완전히 감기는 지점까지만**(0.00~3.00초) 잘라 쓴다.
    그 뒤로 영상은 끝나고(loop=false) 마지막 프레임(눈을 꼭 감은 얼굴)에서 그대로 멈춰 있는다.
    발언 차례가 오면 코드가 speaking 영상으로 바꾸며 눈을 뜬다. 크로스페이드 없음.

끝 타임코드(3.00초)를 고른 근거 — 24fps 프레임 확인
  2.20s 눈 반쯤 · 2.58s 눈꺼풀 닿음 · **2.83s 완전히 감김(속눈썹 선만)** · 2.95s 그대로 감김
  3.02s 부터는 고개가 더 떨궈지며 얼굴이 프레임 아래로 내려간다(= 다른 타일과 구도가 어긋나기 시작)
  → 눈이 완전히 감기고 고개 위치가 다른 타일(speaking·phone)과 같은 3.00초에서 끊는다.

크롭 기준은 v4.5 pickle.mp4 · v4.6.2 sleepy 와 같다 — y=445 에서 720x673(타일 비율 1.07) → 640x598 풀블리드.
결과: avatars/pickle_sleepy.mp4 (무음 · H.264 · faststart · 약 200~300KB · 3.00초)
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
SEG_START = "0.00"           # 눈 뜬 정면 — 조는 중으로 넘어가는 시작
SEG_LEN = "3.00"             # 3.00초 = 눈이 완전히 감긴 프레임(2.83s) 뒤 고개가 더 내려가기 전
XFADE = 0                    # 루프가 아니다 — 마지막 프레임에서 멈추므로 이어 붙이지 않는다
CRF_TRY = [26, 25, 27, 24, 28, 23, 29]
KB_MIN, KB_MAX = 170, 330


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

    out = []
    for name in src:
        im = Image.open(os.path.join(TMP + "/src", name)).convert("RGB")
        im = im.crop((0, CROP_Y, 720, CROP_Y + CROP_H)).resize((OUT_W, OUT_H), Image.LANCZOS)
        out.append(im)
    for i, img in enumerate(out, 1):
        img.save(TMP + "/out/%04d.jpg" % i, quality=90)
    out[-1].save(TMP + "/last_frame.png")     # 눈검수용 마지막 프레임

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
    shutil.copyfile(TMP + "/last_frame.png", os.path.join(ROOT, "diag/sleepy_last_frame.png"))
    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0fKB (crf %d · %d프레임 = %.2f초 · 마지막 프레임에서 정지)"
          % (OUT_MP4, kb, crf, len(out), len(out) / FPS))
    if not (KB_MIN <= kb <= KB_MAX):
        print("!! 용량이 목표(170~330KB) 밖 — 확인 필요")


main()
