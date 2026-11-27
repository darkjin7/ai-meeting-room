"""v4.4 — 피클 움직이는 아바타 영상 만들기.

원본: attachments/2026-11-27/14721333_1795705520204730-a76018e78928422ea8771a0b82cd4156.mp4
      (1번 피클 · 7.93초 · 720x1280 · H.264 + AAC 3.0MB)

하는 일
  1) 오디오 트랙 제거(-an)
  2) 6분할 타일의 원형 얼굴 프레임에 맞는 1:1(480x480) 화면으로 다시 구성
     - 세로 영상(9:16)을 그대로 원에 넣으면 얼굴이 잘린다.
       → 얼굴(머리~어깨)은 선명한 전경으로 가운데에 두고, 좌우는 같은 화면을
         흐리게·어둡게 깔아 원 안에서 얼굴이 잘리지 않게 채운다.
     - 전경 324x576 을 (78,14) 에 얹는다 = 머리 위·턱·어깨까지 원 안에 들어옴.
     - 좌우는 흐린 화면을 비네트로 어둡게 깔아 이음매가 보이지 않게 한다.
  3) 8초 루프가 끊기지 않게 마지막 10프레임을 첫 10프레임과 크로스페이드
  4) H.264 baseline-friendly yuv420p + faststart + no audio, CRF 28

결과: work/meeting-room/avatars/pickle.mp4  (poster: avatars/pickle_poster.webp)
"""
import os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/14721333_1795705520204730-a76018e78928422ea8771a0b82cd4156.mp4")
TMP = os.path.join(ROOT, ".tmp_pickle")   # 워크스페이스 안(셸 호출마다 /tmp 가 비워진다)
OUT_MP4 = os.path.join(ROOT, "avatars/pickle.mp4")
OUT_POSTER = os.path.join(ROOT, "avatars/pickle_poster.webp")

S = 480          # 정사각 캔버스
FG_W, FG_H = 324, 576   # 전경 크기 (원본 720x1280 의 0.45배)
FG_X, FG_Y = 78, 14     # 전경 위치
FPS = 24
XFADE = 10       # 크로스페이드 프레임 수


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

    # 좌우 여백: 같은 화면을 흐리게 깐 뒤 바깥으로 갈수록 어둡게(비네트) —
    # 원형 프레임 안에서 얼굴만 밝게 남고 옆은 그림자처럼 사라진다.
    vig = Image.new("L", (S, S), 0)
    ImageDraw.Draw(vig).ellipse((-S * 0.10, -S * 0.10, S * 1.10, S * 1.10), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(60)).point(lambda v: int(255 - (255 - v) * 0.85))
    DARK = Image.new("RGB", (S, S), (9, 12, 20))

    composed = []
    for name in src:
        im = Image.open(os.path.join(TMP + "/src", name)).convert("RGB")   # 720x1280
        bg = im.crop((0, 280, 720, 1000)).resize((S, S), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(22))
        bg = ImageEnhance.Brightness(bg).enhance(0.55)
        bg = ImageEnhance.Color(bg).enhance(0.5)
        bg = Image.composite(bg, DARK, vig)
        fg = im.resize((FG_W, FG_H), Image.LANCZOS)
        bg.paste(fg, (FG_X, FG_Y))
        composed.append(bg)

    # 마지막 XFADE 프레임을 첫 XFADE 프레임과 겹쳐 8초 루프의 이음매를 지운다
    n = len(composed)
    out = composed[:n - XFADE]
    for i in range(XFADE):
        a = (i + 1) / XFADE
        out.append(Image.blend(composed[n - XFADE + i], composed[i], a))

    for i, img in enumerate(out, 1):
        img.save(TMP + "/out/%04d.jpg" % i, quality=93)

    out[0].resize((360, 360), Image.LANCZOS).save(OUT_POSTER, "WEBP", quality=86, method=6)

    sh([FF, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(FPS), "-i", TMP + "/out/%04d.jpg",
        "-an", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
        "-crf", "28", "-preset", "slow", "-g", "48",
        "-movflags", "+faststart", OUT_MP4])

    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0f KB" % (OUT_MP4, os.path.getsize(OUT_MP4) / 1024))
    print("poster: %s  %.0f KB" % (OUT_POSTER, os.path.getsize(OUT_POSTER) / 1024))


main()
