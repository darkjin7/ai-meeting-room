"""v4.7 — 피클 '듣는 중(listening)' 기본 아바타 영상.

원본: attachments/2026-11-27/c8523dc2-081d-42eb-91fe-16c804f35d1b-listening_8s_loop-…mp4
      (Hark 가 만든 1080x1080 · 30fps · 8.00초 · 무음 · 이미 루프로 맞춰진 클립)

성진님 요청(v4.7)
  피클이 말하지 않을 때(듣는 중) 화면이 정지 이미지로 굳어 있지 않고, 살아 있는 얼굴로 계속 듣고 있게.
  → 이 클립을 `listening` 기본 영상으로 깔고, 졸기/딴짓은 '어쩌다 한 번'만 얹는다.

크롭 기준 — 대화면 얼굴 크기·위치를 speaking(pickle.mp4)·sleepy·phone 과 똑같이 맞춘다
  · 기준점은 **두 눈동자의 파란 픽셀 무게중심**
      speaking(pickle.mp4) 640x598 : 눈 중심 x 322.8 (0.5043W) · y 191.8 (0.3207H) · 눈 사이 236.9px
      sleepy                      : x 322.5 (0.5039W) · y 191.4 (0.3200H) · 눈 사이 238.1px
  · 원본 1080x1080 을 24fps 로 훑어 잰 값(47프레임 평균)
      눈 중심 (547, 559) · 눈 사이 231.0px (머리를 살짝 돌리는 동안 224~242px, 시작·끝 프레임은 224.6px 로 같다)
  · 눈 사이 231px → 236.9px 이 되도록 640/236.9*231 = 624px 폭을 잘라 640 으로 (배율 1.0256)
      crop w 624 · h 583 (타일 비율 1.0702) · x0 = 547 - 0.5043*624 = 232 · y0 = 559 - 0.3207*583 = 372
  → 출력에서 눈 중심 (323.0, 191.8) · 눈 사이 236.9px — speaking 과 같은 자리.

루프: 원본이 이미 8초 루프다. 첫 프레임과 마지막 프레임의 평균차 1.67(연속 프레임 평균 0.83, 최대 2.44)로
      이어 붙임이 자연스러워 **자르거나 크로스페이드하지 않고 그대로** 쓴다(HTML 에서 loop=true).

결과: avatars/pickle_listening.mp4 (640x598 · 무음 · H.264 High · faststart · 8.00초 · 220~350KB)
"""
import os, shutil, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = "/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
SRC = os.path.join(ROOT, "../../attachments/2026-11-27/c8523dc2-081d-42eb-91fe-16c804f35d1b-listening_8s_loop-f29a657556dc4c5cb875cb864d8cfcc7.mp4")
TMP = os.path.join(ROOT, ".tmp_listen_build")
OUT_MP4 = os.path.join(ROOT, "avatars/pickle_listening.mp4")

CROP_X, CROP_Y, CROP_W, CROP_H = 232, 372, 624, 583
OUT_W, OUT_H = 640, 598
FPS = 24
CRF_TRY = [26, 27, 25, 28, 29, 24, 30]
KB_MIN, KB_MAX = 220, 350
BITRATE_FALLBACK = ["330k", "300k", "270k"]


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("failed: %s" % " ".join(cmd))


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP + "/frames", exist_ok=True)
    if not os.path.exists(SRC):
        sys.exit("원본이 없다: %s" % SRC)

    # 1) 크롭 + 640x598 + 24fps 프레임으로 뽑는다(원본 30fps → 24fps, 길이는 8.00초 그대로)
    sh([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", SRC,
        "-vf", "fps=%d,crop=%d:%d:%d:%d,scale=%d:%d:flags=lanczos" % (FPS, CROP_W, CROP_H, CROP_X, CROP_Y, OUT_W, OUT_H),
        "-q:v", "2", TMP + "/frames/%04d.jpg"])
    frames = sorted(os.listdir(TMP + "/frames"))
    print("프레임 %d장 = %.2f초 (원본 8.00초 · 30→24fps)" % (len(frames), len(frames) / FPS))
    # 눈검수용: 첫/마지막 프레임
    Image.open(TMP + "/frames/" + frames[0]).save(os.path.join(ROOT, "diag/listening_first_frame.png"))
    Image.open(TMP + "/frames/" + frames[-1]).save(os.path.join(ROOT, "diag/listening_last_frame.png"))

    # 2) 목표 용량(220~350KB) 안에 드는 crf 를 먼저 찾는다
    best = None
    for crf in CRF_TRY:
        sh([FF, "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(FPS), "-i", TMP + "/frames/%04d.jpg",
            "-an", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-crf", str(crf), "-preset", "slow", "-g", "48",
            "-movflags", "+faststart", TMP + "/try.mp4"])
        kb = os.path.getsize(TMP + "/try.mp4") / 1024
        print("  crf %d → %.0fKB" % (crf, kb))
        if KB_MIN <= kb <= KB_MAX:
            best = (crf, kb, TMP + "/try.mp4")
            break
        if best is None or abs(kb - (KB_MIN + KB_MAX) / 2) < abs(best[1] - (KB_MIN + KB_MAX) / 2):
            best = (crf, kb, TMP + "/try.mp4")

    # 3) crf 로는 안 들어가면 2패스 비트레이트로 맞춘다(움직임이 많은 8초라 crf 편차가 크다)
    if not (KB_MIN <= best[1] <= KB_MAX):
        for br in BITRATE_FALLBACK:
            for pf in ("1", "2"):
                sh([FF, "-hide_banner", "-loglevel", "error", "-y",
                    "-framerate", str(FPS), "-i", TMP + "/frames/%04d.jpg",
                    "-an", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_range", "tv",
                    "-b:v", br, "-pass", pf, "-passlogfile", TMP + "/2p", "-preset", "slow", "-g", "48",
                    "-movflags", "+faststart", TMP + "/try2.mp4"])
            kb = os.path.getsize(TMP + "/try2.mp4") / 1024
            print("  2pass %s → %.0fKB" % (br, kb))
            if KB_MIN <= kb <= KB_MAX:
                best = ("2pass " + br, kb, TMP + "/try2.mp4")
                break
            best = ("2pass " + br, kb, TMP + "/try2.mp4")

    crf, kb, path = best
    shutil.copyfile(path, OUT_MP4)
    shutil.rmtree(TMP, ignore_errors=True)
    print("mp4   : %s  %.0fKB (%s · %d프레임 = %.2f초 · 루프)" % (OUT_MP4, kb, crf, len(frames), len(frames) / FPS))
    if not (KB_MIN <= kb <= KB_MAX):
        print("!! 용량이 목표(220~350KB) 밖 — 확인 필요")


main()
