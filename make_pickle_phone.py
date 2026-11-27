"""v4.6.2 — 피클 '딴짓(phone)' 아바타 영상 — 회의 중 몰래 폰 보다 들켜서 깜짝 놀라는 2.2초 루프.

원본: attachments/2026-11-27/108998653_1795756473323304-184d1227a43f4c64ba878ca9de4c1d89.mp4
      (피클 · 8.04초 · 720x1280 · H.264 + AAC 4.2MB)

왜 다른 영상과 크롭이 다른가
  speaking·sleepy 는 720x673 을 잘라 640x598 로 채운다(얼굴만 크게).
  그런데 이 영상은 폰을 **가슴 아래·허리 높이에 든 손**이 같이 나온다.
  눈(원본 y≈600)과 폰(원본 y≈1100~1270)을 673 높이 안에 함께 담으려면
  크롭을 아래로 내려야 하는데, 그러면 이마·머리 위가 잘리고 눈이 화면 맨 위에 붙는다.
  → 이 영상만 '세로로 길게 담고 좌우를 흐린 배경으로 채우는' 구도로 만든다.
    · 앞면: 원본 y=250~1270(1020)를 높이 598 로 축소 → 422x598 (머리 위 끝은 살짝 잘리고, 얼굴·폰이 크게 남는다)
    · 배경: 같은 프레임을 640x598 로 채워 크게 흐리게(30px)·어둡게(-28%) 깐다
    · 얼굴과 손에 든 폰이 둘 다 잘리지 않는다(원본이 자른 아래쪽 끝까지만).
  원본 스스로 2.0~2.8초에는 폰을 화면 아래로 내려 들고 있어 폰 윗면만 빛으로 보인다 —
  그 구간도 그대로 살린다(폰을 몰래 보다 들키는 흐름의 앞부분).

구간: 2.0~4.2초 (2.2초) — 폰 보며 능글 → 고개 들어 멈칫 → 들킨 얼굴
      끝과 시작은 0.375초 크로스페이드로 이어 붙인다.
결과: avatars/pickle_phone.mp4 (무음 · H.264 · faststart · 250~380KB)
"""
import os, shutil, subprocess, sys
from PIL import Image, ImageFilter, ImageEnhance

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/108998653_1795756473323304-184d1227a43f4c64ba878ca9de4c1d89.mp4")
TMP = os.path.join(ROOT, ".tmp_phone_build")
OUT_MP4 = os.path.join(ROOT, "avatars/pickle_phone.mp4")

OUT_W, OUT_H = 640, 598
FG_TOP, FG_BOTTOM = 250, 1270     # 얼굴(눈·턱) → 손에 든 폰 아래 (머리 위 끝은 살짝 덜어 낸다 — 폰을 더 크게)
FPS = 24
SEG_START = "2.00"
SEG_LEN = "2.20"
XFADE = 9                          # 0.375초
CRF_TRY = [27, 26, 28, 25, 24, 29, 23]
KB_MIN, KB_MAX = 250, 380


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("failed: %s" % " ".join(cmd))


def compose(src_im):
    src = src_im.convert("RGB")
    # 배경: 640x598 을 채우도록 확대 후 가운데를 잘라 크게 흐리게
    sw, sh_ = src.size
    cover = max(OUT_W / sw, OUT_H / sh_)
    bg = src.resize((int(sw * cover + 0.5), int(sh_ * cover + 0.5)), Image.LANCZOS)
    bx, by = bg.size
    left = (bx - OUT_W) // 2
    top = (by - OUT_H) // 2
    bg = bg.crop((left, top, left + OUT_W, top + OUT_H))
    bg = bg.filter(ImageFilter.GaussianBlur(30))
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    bg = ImageEnhance.Color(bg).enhance(0.65)
    # 앞면: 얼굴~폰 전체를 높이 598 로
    fg = src.crop((0, FG_TOP, sw, FG_BOTTOM))
    fw = int(fg.width * OUT_H / fg.height + 0.5)
    fg = fg.resize((fw, OUT_H), Image.LANCZOS)
    x = (OUT_W - fw) // 2
    bg.paste(fg, (x, 0))
    return bg


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP + "/src", exist_ok=True)
    os.makedirs(TMP + "/out", exist_ok=True)

    sh([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", SEG_START, "-t", SEG_LEN, "-i", SRC,
        "-vf", "fps=%d" % FPS, "-q:v", "2", TMP + "/src/%04d.jpg"])
    names = sorted(os.listdir(TMP + "/src"))
    print("세그먼트 %ss + %ss → 프레임 %d장" % (SEG_START, SEG_LEN, len(names)))

    frames = [compose(Image.open(os.path.join(TMP + "/src", n))) for n in names]
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
        best = (crf, kb, TMP + "/try.mp4")
        if KB_MIN <= kb <= KB_MAX:
            break

    crf, kb, path = best
    shutil.copyfile(path, OUT_MP4)
    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0fKB (crf %d · %d프레임 = %.2f초 루프)" % (OUT_MP4, kb, crf, len(out), len(out) / FPS))


main()
