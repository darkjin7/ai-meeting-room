# 배포 메모 — 다크진 AI 비서실 · 6분할 회의실

## v4.6.3 (2026-11-27) — 폰 영상 꽉 채우기(풀블리드) · 조는 영상은 눈 감기면 정지
- 성진님 지시: ① "폰 때문에 옆이 공간이 생기네 꼭 폰 안보여도 되니 꽉차게 해주고." ② "조는 모습은 눈이 감기면 멈추고 있다가 자기 차례 되면 깨는 걸로 할 수 있나? 지금 것도 나쁘지는 않자만 보고 싶어"

### ① 영상 2편 다시 뽑음
| 상태 | 원본 | 쓴 구간 | 결과 |
|---|---|---|---|
| `sleepy` | `attachments/2026-11-27/470953036_…mp4` | **0.00~3.00초** (눈 뜬 정면 → 눈이 완전히 감기는 2.83초 → 고개가 더 내려가기 전 3.00초) | `avatars/pickle_sleepy.mp4` **183KB** · 3.00초 · 640×598 · 무음 · faststart · **루프 없음(크로스페이드 없음)** |
| `phone` | `attachments/2026-11-27/108998653_…mp4` | 1.90~4.10초 (힐끔 폰 보는 능글 → 눈 크게 뜸 → 입 벌린 '들킴') | `avatars/pickle_phone.mp4` **199KB** · 2.21초 · 640×598 · 무음 · faststart · 0.167초 크로스페이드 루프 |
- **sleepy 끝 타임코드 근거**(24fps 프레임 확인): 2.20s 눈 반쯤 · 2.58s 눈꺼풀 닿음 · **2.83s 완전히 감김** · 2.95s 그대로 · 3.02s부터 고개가 더 떨궈져 다른 타일과 구도가 어긋남 → 3.00초에서 끊어 **마지막 프레임이 '눈을 꼭 감은 얼굴'**이 되게 했다. v4.6.2 의 0.5초 크로스페이드(슬쩍 뜨는 대목이 섞임)는 없앴다.
- **phone 크롭이 v4.6.2 와 다르다**: v4.6.2 는 눈과 손에 든 폰을 함께 담으려고 422×598 앞면 + 좌우 흐린 배경이었다(좌우 여백). v4.6.3 은 **다른 타일과 똑같이 y=445 에서 720×673 → 640×598 풀블리드**로 자른다(흐린 배경·비네트 없음). 폰은 프레임 아래로 빠지지만 성진님이 "폰 안 보여도 된다"고 하셨고, 폰 불빛은 3.55~3.75초에 화면 맨 아래로 살짝 스친다.
- phone 크로스페이드를 0.375초 → **0.167초**로 줄였다: 얼굴 클로즈업이라 긴 크로스페이드는 끝에서 잔상(두 얼굴)이 보였다.

### ② 코드 (`v4/app.js` · `v4/head.html`)
- `VIDEO_ONCE = {sleepy:true}` — 한 번만 틀고 마지막 프레임에서 멈출 상태 영상 표. `motionVideo()` 가 이 상태만 `loop=false`(+ `loop` 속성 제거)로 만들고,
  - `ended`(와 마지막 0.04초 `timeupdate`)에서 `video.dataset.done="1"` 을 남긴다.
  - `syncAvatarMedia()` 는 `done==="1"` 인 겹을 **다시 재생하지 않는다**(paused 니까 play 하는 v4.6.2 규칙이 눈 뜨는 영상으로 되감던 문제).
  - `setTileMood(id,'sleepy')` 로 **새로 들어올 때만** `done` 을 지우고 `currentTime=0` 부터 다시 튼다(같은 상태 재설정·보기 전환·창 크기 변화로는 되감지 않는다).
- 발언 차례: `setTileState(...,'speaking')` → `setTileMood(id,'')` → 즉시 speaking 겹으로 바뀌며 눈을 뜨고 말한다(v4.6.2 그대로).
- **CSS**: v4.6.2 의 `body.view-video .tile.phone .vov{top:0;…}` 예외(폰 타일만 이름·상태를 위로) 삭제 — 6개 타일 모두 **하단 통일**. 폰이 프레임 밖으로 나갔으니 아래를 가릴 것도 없다.
- 표기: `<title>`·서류철 문서번호·`docNo` → v4.6.3.

### ③ 빌드
- `bash build_v4.sh` → `downloads/darkjin_meeting_room_v4.html` **2734KB** (webp 12장 + 영상 6개). 가드 3000KB 그대로.

### ④ 검증 (2026-11-27, 로컬 390×844)
- `test_v462.py` (v4.6.3 으로 갱신) **ALL PASS**
  - 파일 실측: sleepy 3.00초·640×598·183KB, phone 2.21초·640×598·199KB
  - **sleepy 첫 프레임 눈 뜸(눈동자 파란 픽셀 2749) → 마지막 프레임 눈 감음(0)** · phone 0.50초 프레임이 원본 720×673(y=445) 크롭과 **평균차 2.2**(좌우 여백·블러 없음)
  - sleepy 재생 중 `loop===false` → 3.00초에서 `paused`·`ended`·`done=1`, **1.2초 뒤에도 3.00초 그대로**(되감김 0) · 같은 상태 재설정에도 그대로 · **재진입하면 0초부터 다시 재생**
  - phone `loop===true` · sleepy 겹 정지 · **이름·상태 하단 통일**(pickle `.vov` 위에서 112px = gemini 112px · 같은 그라데이션)
  - 상태 전환 2회에도 DOM·src 불변 · 발언 차례 즉시 깨어남(발언 9샘플 모두 「발언 중」·조는/딴짓 0) · 자동 전환 1라운드 만에 발동(72샘플 겹침 0) · 글로 보기 배지만 · 단일 파일 인라인 2편 재생 · 콘솔 오류 0
- 기존 5종 **ALL PASS**: `test_v4.py` · `test_v44.py` · `test_v451.py` · `test_v46.py` · `test_v461.py`
- 스크린샷(눈검수, 390×844): `downloads/meeting_v463_pickle_sleepy.png`(눈 꼭 감은 채 멈춘 얼굴·보라 테두리·「😴 살짝 조는 중」) · `downloads/meeting_v463_pickle_phone.png`(눈 크게 뜨고 입 벌린 '들킴'·주황 테두리·이름·상태 하단)

## v4.6.2 (2026-11-27) — 피클의 '듣는 중' 상태 영상: 😴 조는 중 · 📱 딴짓(폰)
- 성진님 지시: ① 피클이 눈 감고 조는 720×1280 영상 → `sleepy` ② 회의 중 몰래 폰 보다 들켜 깜짝 놀라는 영상 → `phone`
  "듣는 중일 때 간헐적으로 sleepy·phone 중 하나가 랜덤으로, 발언 차례가 오면 즉시 깨서 speaking 으로"

### ① 영상 2편 (`make_pickle_sleepy.py` · `make_pickle_phone.py`)
| 상태 | 원본 | 쓴 구간 | 결과 |
|---|---|---|---|
| `sleepy` | `attachments/2026-11-27/470953036_…mp4` (8.04초 · 720×1280) | 1.95~5.45초 (눈꺼풀이 내려와 감기는 대목) | `avatars/pickle_sleepy.mp4` **252KB** · 3.50초 · 640×598 · 무음 · faststart · crf 24 |
| `phone` | `attachments/2026-11-27/108998653_…mp4` (8.04초 · 720×1280) | 2.0~4.2초 (폰 보며 능글 → 고개 들어 멈칫 → 들킨 얼굴) | `avatars/pickle_phone.mp4` **282KB** · 2.21초 · 640×598 · 무음 · faststart · crf 23 |
- 공통: 24fps · H.264 High · `-an` · `-movflags +faststart` · 끝과 시작을 0.375~0.5초 크로스페이드로 이어 붙인 루프.
- **sleepy 크롭**: v4.5 `pickle.mp4` 와 같은 기준(y=445 · 720×673 → 640×598). 원본 첫 프레임(눈 뜬 대목)이 기존 pickle.mp4 첫 프레임과 같은 얼굴 위치로 겹치는 것을 확인하고 그대로 썼다. 앞뒤의 '눈 뜬' 구간은 잘라 조는 대목만 남겼다(8초를 그대로 틀면 절반이 또렷한 눈이라 '조는 중'으로 안 읽힌다).
- **phone 은 크롭 기준이 다르다**: 폰을 허리 높이에 들고 있어 눈(원본 y≈600)과 폰(y≈1100~1270)을 673 높이 안에 함께 담으면 이마·머리가 잘린다. 그래서 이 영상만 세로로 길게 담고(원본 y=250~1270 → 422×598) 좌우를 같은 프레임을 크게 흐린 배경(30px blur · 밝기 72% · 채도 65%)으로 채워 640×598 로 만들었다. **얼굴과 손에 든 폰이 둘 다 프레임 안**에 있고, 위쪽 머리 끝만 살짝 덜어 낸다(타일에서 얼굴·폰이 커 보이게).
- 인코딩 후 프레임 눈검수: `sleepy` 0.15/1.05초 · `phone` 0.15/1.05초 → 눈 감김·폰 화면이 프레임 안에 있음(아래 스크린샷과 함께 확인).

### ② 코드 (`v4/app.js` · `v4/head.html`) — 상태마다 <video> 한 겹, src 교체 없음
- `PEOPLE` 피클: `video:'./avatars/pickle.mp4'(=speaking)` + `videos:{sleepy:'./avatars/pickle_sleepy.mp4', phone:'./avatars/pickle_phone.mp4'}`
- `motionVideo(p, state)` — 상태마다 `<video class="face vid">`(speaking) / `<video class="face vlay" data-state="sleepy|phone">` 를 **한 겹씩** 만들어 겹쳐 둔다. `src` 는 붙인 뒤 절대 바꾸지 않고(armAvatarVideos), 보임/숨김은 CSS opacity, 재생/정지는 `play()/pause()` 만.
  - 기존 검증(`video.vid` 1개)이 보는 요소는 speaking 그대로 두고, 새 상태는 `vlay` 로 분리했다 — 상태가 늘어도 기존 경로가 흔들리지 않는다.
- `setTileMood(id, mood)` — `sleepy`/`phone` 이면 타일에 그 클래스만 켜고 `.vstate` 를 **「😴 살짝 조는 중」/「📱 딴짓하다 걸림」** 으로, 글로 보기 카드 배지는 「😴 조는 중」/「📱 딴짓」으로 바꾼다. `syncAvatarMedia()` 가 그 겹만 재생.
- `avatarMood(r)` 한 곳에서 규칙을 정한다: **quiet → 없음 / speaking → speaking / mood → 그 상태**. 말하는 중에는 `setTileState(...,'speaking')` 이 `setTileMood(id,'')` 로 즉시 깨운다.
- `playRound` — 피클 차례 없이 다른 AI 가 2명 넘게 말하면(`rest>=2`) 피클이 `sleepy`/`phone` 중 하나를 랜덤으로 켠다(한 번 켜면 다음 에피소드까지 유지, 피클 차례·라운드 시작에 해제).
- CSS: `.tile.sleepy`(보라 테두리·문구) / `.tile.phone`(주황 테두리·문구). **phone 타일은 이름·상태를 위로 올린다** — 폰을 든 손이 프레임 아래쪽이라 하단 그라데이션이 그대로 덮으면 폰이 가려진다.
- 검증용 훅: `__mr4.setTileMood('pickle','sleepy'|'phone'|'')`, `__mr4.moods()`, `__mr4.media()` 에 sleepy/phone 겹 정보.

### ③ 빌드 (`build_v4.sh`)
- `pickle_sleepy.mp4` · `pickle_phone.mp4` 도 `inline_once` 로 인라인(주소는 코드에 1번만). 남은 `./avatars/*.{webp,css,png,mp4}` 가 있으면 빌드 실패 — mp4 까지 검사하도록 넓혔다.
- 가드: 2.5MB → **2.93MB(3000KB)**. 결과 `downloads/darkjin_meeting_room_v4.html` **2935KB** (webp 12장 + 영상 6개: 피클 3 + 인트로 3).

### ④ 검증 (2026-11-27, 로컬 390×844)
- `test_v462.py` (신규) **ALL PASS** — 두 영상 실측(3.50/2.21초·640×598·무음·faststart·252/282KB) · phone 1.05초 프레임에 폰 화면 밝은 픽셀 2457개(얼굴+폰 함께) · 3겹 구조 · sleepy 재생·루프 · phone 재생·sleepy 겹 정지 · **상태 전환 2회에도 DOM 노드·src 불변** · 발언 차례에 즉시 깨어남(발언 9샘플 모두 「발언 중」·조는/딴짓 0) · 자동 전환(1라운드 만에 발동, 72샘플 겹침 0) · 글로 보기는 배지만 · 단일 파일 인라인 2편 실제 재생 · 콘솔 오류 0
- 기존 5종도 **ALL PASS**: `test_v4.py` · `test_v44.py` · `test_v451.py` · `test_v46.py` · `test_v461.py`
  - 바뀐 단언은 버전 사실에 맞춘 3곳뿐: ① 피클 타일 영상 개수 1 → **3겹(vid 1 + vlay 2)** ② 화상 상태 문구 허용 목록에 두 상태 추가 ③ 단일 파일 인라인 영상 4 → **6개**·상한 2.93MB.
  - `test_v451.py` 에는 앞 라운드가 끝난 뒤 4라운드를 시작하도록 `busy===true` 대기 한 줄을 넣었다(영상 3겹으로 로딩이 느려져 생긴 경합 — 기능 문제 아님).
- 스크린샷(눈검수): `downloads/meeting_v462_pickle_sleepy.png`(눈 감고 조는 중·보라 테두리·「😴 살짝 조는 중」) · `downloads/meeting_v462_pickle_phone.png`(폰 든 손까지 보이고 이름·상태는 위로·「📱 딴짓하다 걸림」) — 390×844

### ⑤ 배포
- 커밋 `af85cd2` (2026-11-27 14:4x KST) → `env -u GH_TOKEN git push origin main` (이 환경 GH_TOKEN 은 만료 — 403 이면 이 방식)
- GitHub Pages: **built** (af85cd2, 2026-11-27T05:40:30Z) · https://darkjin7.github.io/ai-meeting-room/ HTTP 200 · `<title>` v4.6.2 · `avatars/pickle_sleepy.mp4`(257,806B)·`pickle_phone.mp4`(288,671B)·`pickle.mp4` 모두 200
- 라이브 실측(모바일 390×844): 입장 → 화상 6분할 → `setTileMood` 로 sleepy(readyState 4 · t 0.22s · 「😴 살짝 조는 중」) · phone(readyState 4 · 「📱 딴짓하다 걸림」) 모두 상대경로 영상이 실제 재생 · pageerror 0 (`downloads/meeting_v462_live_phone.png`)

## v4.6.1 (2026-11-27) — 입장 인트로 영상 3종 랜덤
- 성진님 지시: "회의실 로딩 장면 3가지 랜덤으로 바꿔줘. 다음에 다른거 만들면 또 넣게"

### ① 클립 3종 (`avatars/intro_1~3.mp4` + `intro_1~3_poster.webp`)
| # | 원본 | 장면 | 파일 | 포스터 |
|---|---|---|---|---|
| 1 | `downloads/group_assets/vid_1_255875777.mp4` (1.1초부터 3.85초) | 9인 전원 셀카(카메라 플래시) | 270KB · 3.88초 · 854×480 · 무음 | 29KB |
| 2 | `downloads/group_assets/vid_2_877722805.mp4` (2.0초부터) | 9인 일렬 정면 | 271KB · 3.88초 · 854×480 · 무음 | 26KB |
| 3 | `downloads/group_assets/vid_3_994233736.mp4` (1.0초부터) | 8인 회의 테이블(기존 `intro_meeting.mp4` 자리) | 270KB · 3.88초 · 854×480 · 무음 | 27KB |
- 인코딩: `ffmpeg -ss … -t 3.85 -vf scale=854:480:flags=lanczos,fps=24 -c:v libx264 -preset slow -profile:v high -b:v 560k -maxrate 840k -bufsize 1600k -pass 1/2 -an -movflags +faststart` (2패스, 소리 없음). 포스터는 512×288 webp q62.
- 기존 `avatars/intro_meeting.mp4`(473KB 960×540) · `intro_poster.webp`(79KB)는 **삭제**(3번 클립이 같은 장면을 더 작게 대신한다).

### ② 코드 (`v4/app.js` · `v4/head.html`)
- `INTRO_CLIPS = [{src, poster, label}, …]` 배열 하나로 관리. **새 영상을 넣을 때는 ① avatars/ 에 `intro_4.mp4`·`intro_4_poster.webp` 를 올리고 ② 배열 맨 끝에 항목 한 줄만 추가**하면 된다(빌드·코드 수정 불필요 — 주석으로 배열 위에 안내).
- `pickIntroIdx()` — `lastIntroIdx`(직전에 튼 클립)는 빼고 나머지에서 균등 랜덤. 클립이 1개면 그것, 처음이면 전체에서. 입장할 때마다 같은 영상이 연달아 나오지 않는다.
- `playIntro()` — 고른 클립의 `src`·`poster` 를 `<video>` 에, 같은 포스터를 `.intro-bg`(블러 배경)에 넣는다. `src` 가 바뀔 때만 `load()`. 리스너 정리·4초 상한(`INTRO_MAX`)·건너뛰기·error 대체는 v4.6 그대로.
- `<video id="introVid">` 에서 `src`/`poster` 속성을 뺐다(주소는 배열에만 한 번 적는다 — 빌드가 중복 인라인을 막는다). `.intro-bg` 의 CSS `url()` 도 제거(배경은 재생할 때 JS 가 넣는다).

### ③ 빌드 (`build_v4.sh`)
- 앱 코드의 `INTRO_CLIPS` 에 적힌 `"./avatars/intro_N.mp4"` 를 정규식으로 찾아 **전부** 인라인한다 → 클립을 늘려도 스크립트를 고칠 필요가 없다. webp 정규식에 숫자를 포함(`[a-z0-9_]+`)해 `intro_1_poster.webp` 도 인라인.
- 가드: 인트로 3종(약 1.15MB 인라인)을 담느라 단일 파일 상한을 2MB → **2.5MB(2560KB)** 로 올림. 중복 주소·파일 누락·인라인 안 된 자산이 남으면 빌드 실패.
- 결과: `downloads/darkjin_meeting_room_v4.html` **2216KB** (2.17MB) (webp 12장 + pickle.mp4 + 인트로 3종 = 영상 4개 인라인).

### ④ 검증 (2026-11-27, 로컬 390×844)
- `test_v461.py` (신규) **ALL PASS** — 클립 3종 실측(3.88초·854×480·무음·270~271KB) · 90회 뽑기에서 3종 모두(34/32/24)·연속 중복 0 · 안건을 번갈아 3번 입장해 3종이 모두 실제 재생(readyState 4, paused false, 시간 증가) · 포스터·배경이 클립과 일치 · 모바일 인트로 화면 안·가로 넘침 0 · 단일 파일 2216KB·영상 4개 인라인·인라인 영상 실제 재생 · 콘솔 오류 0
- `test_v46.py`(인트로 주소를 `intro_1~3.mp4` 중 하나로 확인하도록만 수정) · `test_v4.py` · `test_v44.py` · `test_v451.py` 모두 **ALL PASS**
- 스크린샷(눈검수): `downloads/meeting_v461_intro1.png`(전원 셀카) · `downloads/meeting_v461_intro2.png`(일렬 정면) — 390×844

### ⑤ 배포
- 커밋 `107cfb5`(본체) · `9756c3a`(화면 표기를 v4.6.1 로) · `fd52781`(클립 인코딩 560kbps·포스터 512×288 → 단일 파일 2216KB) → `git push origin main`
- GitHub Pages: **built** (fd52781) · https://darkjin7.github.io/ai-meeting-room/ HTTP 200 · `<title>` v4.6.1 · `avatars/intro_1~3.mp4`(270/271/270KB)·`intro_1~3_poster.webp` 200 · `avatars/intro_meeting.mp4` 404(의도된 삭제 — index.html 이 더는 그 주소를 안 부름)
- 라이브 실측(모바일 390×844, 3번 입장): 회의 테이블(intro_3) → 전원 셀카(intro_1) → 일렬 정면(intro_2) · 모두 readyState 4 · paused false · 854×480 · 콘솔 오류 0 (`work/meeting-room/live_v461_intro.png`)
- ⚠ 푸시 메모: 이 환경의 `GH_TOKEN` 은 만료(gh api 는 저장 자격증명으로 동작). `git push` 가 403 이면 **`env -u GH_TOKEN git push origin main`** 로 올린다.

## v4.6 (2026-11-27) — 회의 서류철 로비 · 다음 안건 메모 · 입장 인트로 영상
- 성진님 지시: "들어가면 준비된 회의 안건 고르는 거랑 다음에 회의를 할 안건을 적고 입장.. 영상이 있으면 다들 의자에 앉거나 화상회의 준비하는 그런 영상 나오고 우리가 만든 페이지 로딩 되면 좋겠어"
- 흐름: **회의 브리핑 서류(로비) → 🚪 회의실 입장 → 착석 인트로(3.9초) → 고른 안건의 6분할 화상 회의실**

### ① 로비 (`#lobby`, `v4/head.html` + `v4/app.js`)
- 종이 서류 한 장(`.doc`, 폭 880px) — 표제부(결재 대기 · 주전 6인+참관 2인 · 6분할 회의실), 01 준비된 회의 안건, 02 다음 회의 안건 메모, 오너 결재란.
- 01: `readyAgendas()`(자료 6/6·`ready:true`)만 라디오 목록. 항목을 누르면 파란 테두리 + `준비 완료` 도장, 하단 고정 바의 `선택한 안건`과 동기화. 선택은 `localStorage.darkjin_mr46_sel` 에 남아 다음 방문에도 유지.
- 02: 메모를 적고 `📌 다음 안건 저장`(Ctrl/⌘+Enter 도 가능) → 최신이 위로 누적(`localStorage.darkjin_mr46_next`, 최대 40건). `복사`는 피클에게 보내는 요청문(`[회의 안건 예약] … 6분할 회의실 v4.1 사전 자료를 준비해 주세요 …`)을 그대로 클립보드로, `삭제`는 그 줄만 지운다.
- 하단 고정 바: `선택한 안건`(모바일은 말줄임) + `🚪 회의실 입장`.
- 안건이 하나도 없으면 "아직 결재할 안건이 없습니다…" 안내(가짜 회의 금지 규칙 유지).

### ② 입장 인트로 (`#intro`, `avatars/intro_meeting.mp4` 473KB · 3.9초 · H.264 · poster `intro_poster.webp` 79KB)
- 입장 → 로비가 닫히고 `muted playsinline` 영상이 재생(사운드 없음). 위에 `DARKJIN AI DESK / 6분할 회의실 입장 준비`, 아래에 고른 안건 이름·진행 막대·"잠시 후 자동으로 입장합니다 · 건너뛰기".
- 끝나면(`ended`) 자동으로 그 안건의 6분할 화상 화면. `건너뛰기`(우상단)는 즉시. 영상이 못 열리는 기기는 `error` → 0.9초 뒤 진입, 자동재생이 막혀도 4초 상한(`INTRO_MAX`)으로 멈추지 않는다.
- 이미 보던 그 안건으로 다시 입장하면 **인트로를 다시 틀지 않고** 그 라운드에서 이어 본다. 회의 중 `📁 서류` 로 돌아가면 회의는 일시정지되고, 다시 입장하면 이어서 진행.

### ③ 이번에 고친 것 (그냥 두면 실제로 틀렸던 것)
| 문제 | 원인 | 수정 |
|---|---|---|
| 건너뛴 뒤 다음 인트로가 끝나면 **예전 안건**이 열림 | 건너뛴 인트로의 `ended` 리스너가 `<video>` 에 남아(once 미발화) 다음 종료 때 같이 호출 | 인트로를 열 때마다 리스너를 떼고(`clearIntroHandlers`) `finishIntro(introA)` 로 지금 인트로만 닫게 |
| 회의 중 `📁 서류` 를 눌러도 **입장 버튼이 눌리지 않음** | `.lobby` 와 `.ownerbar`(오너 코멘트 바)가 둘 다 z-index 70, DOM 상 뒤인 오너 바가 위 | 로비 76 · 인트로 82 (모달 90 · 토스트 120 아래) |
| 첫 화면에서 `🔔 새 회의 자료가 준비되었습니다` 토스트가 **입장 버튼을 가림** | `checkNewReady()` 가 `showLobby()` 앞에서 돌아 로비 위에 토스트가 뜸 | 로비를 먼저 열고 알림 검사. 로비·인트로가 열려 있으면 토스트 생략(01번 칸에 이미 보임) |
| 인트로에서 안건 토스트가 영상 위에 겹침 | `openRoom()` → `openAgenda()` 끝의 토스트 | 인트로로 들어올 때는 `openAgenda(id,{quiet:true})` |
| `test_v44.py` 가 가끔 실패(피클 발언 표본 0) | 2라운드가 도는 중에 다시 `playRound(2)` 를 던져 그대로 반환, 피클이 먼저 말한 판에서 표본이 빔 | 2라운드를 끝까지 기다린 뒤 3라운드를 80ms 간격으로 표본(연속 2회 통과 확인) |

### ④ 검증 (2026-11-27, 로컬 390×844 · 1440×900)
- `test_v46.py` (신규) **ALL PASS** — 로비 첫 화면·기본 선택 1건·선택 변경/저장·메모 저장·누적·피클 요청문 복사·삭제·새로고침 유지 · 인트로 재생(0.74→1.44초)·안건 표시·건너뛰기→6분할 진입 · 영상 끝 자동 진입 · 회의 중 서류→같은 안건 이어보기 · 데스크톱 로비 가로 넘침 0·영상 화면 안·6타일 · 콘솔 오류 0.
- `test_v4.py` **ALL PASS** — 4라운드·기록 24건·게스트 조언·역할 분담·자막 바 68px·글로 보기 중앙 오차 0px·화상 스크롤 0 (v4.5.1 규칙 유지)
- `test_v44.py` **ALL PASS** — 피클 640×598 7.92초, 발언 중에만 재생(샘플 82개 중 11개), 듣는 중 pause+opacity 0, src 불변, 글로 보기 정지, 데스크톱 동일
- `test_v451.py` **ALL PASS** — 글로 보기 1~4라운드 무대 노드 추가/삭제 0 · 화상 왕복 5회+3라운드 6타일 항상 화면 안·가려짐 0
- 기존 세 테스트는 첫 화면이 로비가 되었으므로 `__mr4.dismissLobby()` 한 줄로 로비만 닫고 원래 검증을 그대로 한다(검증 항목은 손대지 않음).
- 스크린샷(눈검수): `downloads/meeting_v46_mobile_lobby.png` · `downloads/meeting_v46_mobile_intro.png` · `downloads/meeting_v46_mobile_room.png` (390×844)
- 단일 파일 `downloads/darkjin_meeting_room_v4.html` 1872KB — webp 11장 + pickle.mp4 + intro_meeting.mp4 인라인(빌드가 중복 인라인·2MB 초과를 막음)

### ⑤ 배포
- 커밋 `315c9a6` (2026-11-27 13:01 KST) → `git push origin main`
- GitHub Pages: `built` (commit 315c9a6, 2026-11-27T04:02:28Z) · https://darkjin7.github.io/ai-meeting-room/ HTTP 200 · `<title>` v4.6 · `avatars/intro_meeting.mp4`·`intro_poster.webp`·`pickle.mp4` 모두 200
- 라이브 실측(모바일 390×844): 로비 2건 → 입장 → 인트로 재생(t 0.94, paused false) → 건너뛰기 → 6타일(높이 174) 화상 회의실 · 페이지 오류 0

---


## v4.5.1 (2026-11-27) — 글로 보기 깜박임 · 6분할 타일 소실 수정 · 피클은 발언 중에만 영상
- 성진님 실기기(iOS Safari) 피드백: "글로 보는 페이지 아직 깜박거림이 나오고 있고 6분할 페이지에서 참여한 ai화면이 없어지는 버그가 있음. 피클은 계속 얼굴영상 움직이는데 영상이 하나라서 그런가? 지금 영상은 발언 할 때 영상인데"

### ① 글로 보기 깜박임 — 원인은 "무대를 다시 그리는 일"이었다
| 원인 | 수정 |
|---|---|
| `buildTiles()` 가 매번 `stage.innerHTML=""` 로 6타일을 파괴·재생성 (안건 열기·새 회의·안건 교체마다) → `<img>`/`<video>` 가 DOM 에서 떨어졌다 붙으며 디코딩·합성 레이어가 초기화 | 타일 DOM 을 **사람마다 최초 1회만 생성(`tilePool`)**. 이후 `buildTiles()` 는 있는 타일을 옮기기(appendChild)만 하고, 잠깐 필요 없는 타일은 stage 에서 내려 두되 **파괴하지 않는다** |
| `renderBubble()` 이 발언이 바뀔 때마다 `bubble.innerHTML=""` → tag/role/text 노드를 새로 만듦(한 프레임 빈 본문) | 본문은 `mtag`·`mrole`·`msum` **3개 노드를 처음에 만들고 `textContent` 만 갱신** |
| `.tile.speaking .wave{display:flex}` → 웨이브가 나타날 때마다 `자료 펼치기` 버튼·마이크가 좌우로 튐 | 웨이브는 **자리를 늘 차지**(display:flex 고정) + `.tile.speaking` 에서 `opacity` 만 1 |
| `.wave i{animation:wv .9s infinite}` — 발언 중 내내 **height 를 애니메이션**(60fps 리플로우) | 애니메이션 삭제 → **정적 막대 높이**(화상 모드 `.vw` 와 같은 규칙) |
| `.talk-item{animation:rise .25s}` — 기록이 하나 추가될 때마다 페이드 인(리페인트) | 애니메이션 삭제 |
| `body` 배경이 큰 `radial-gradient` 2장 → 스크롤(자동 중앙 정렬) 때마다 루트 배경을 다시 칠함 | **body 는 단색**, 장식은 `.wrap::before{position:fixed}` 고정 레이어로 이동(스크롤해도 다시 안 칠함) |
| 글로 보기 카드 아래에 화상용 `발언 중` 배지(`.vbadge`)가 늘 보이던 것 | `.tile .vbadge{display:none}` — 화상 모드 전용으로 |

### ② 6분할에서 AI 화면이 없어지는 버그
- **타일을 다시 만들지 않는 것**(①의 tilePool)이 근본 수정이다. 안건을 바꾸거나 새 회의를 열어도 `<img>`/`<video>` 노드가 그대로 살아 있고, 디코딩도 유지된다.
- 추가 방어:
  - `.tile{isolation:isolate}` — 영상 합성 레이어가 이웃 타일 위로 새지 않게 스태킹 컨텍스트 고정.
  - 화상 모드 높이를 `100dvh` → **`100svh`**(도구모음이 보이는 가장 작은 화면). iOS 에서 주소창이 접히며 `dvh` 값이 바뀌어 마지막 줄 타일이 밀리거나 잘리는 문제를 없앤다.
  - **미디어 자동 복구(`assertTileMedia`/`watchdogMedia`)**: `pageshow`·`visibilitychange`·`resize`·`orientationchange`·화상 진입 시 한 번씩 검사해, 실패한 이미지(`complete && naturalWidth===0`, 타일당 3회 제한)만 다시 요청하고 발언 중 영상은 다시 재생.
  - 영상이 실제로 열리지 않는 기기(예: `data:` 영상)는 재생을 시도한 뒤 1.5초 동안 `readyState 0` 이면 `.off` 로 숨겨 **정지 이미지가 그대로 남는다**(검은 타일 방지).

### ③ 피클은 '발언 중'일 때만 영상, '듣는 중'은 정지 이미지
- 타일 구조: `.vbob` 안에 **아래층 `img.vposter`(pickle_poster.webp = 영상 첫 프레임) + 위층 `video.vid`**.
- `body.view-video .vbob video.face{opacity:0}` / `.tile.speaking .vbob video.face{opacity:1}` — **opacity 만** 바꾼다(transition 없음).
- `syncAvatarMedia()` 가 단일 판단자: `.tile.speaking`(그리고 `quiet` 아님) + 화상 모드일 때만 `play()`, 아니면 `pause()`. `setTileState`·`setView`·`quietAll`·`resumeAll`·`buildTiles` 에서 호출.
- **`src` 는 화상 화면에 처음 들어갈 때 한 번만 붙이고 뗴지 않는다**(`armAvatarVideos`, `preload="metadata"`). `autoplay` 속성은 제거 — 재생 시점은 코드가 정한다.
- 포스터는 화상 진입 전에 미리 받아 둔다(18KB) → 듣는 중·전환 순간에도 얼굴이 비지 않는다.
- 확장을 위해 데이터 구조를 열어 둠: `PEOPLE[].video`, `PEOPLE[].poster` (앞으로 `idle`·`react` 영상도 같은 자리에 추가하면 된다).

### 검증
- `test_v451.py` (신규) ALL PASS — 글로 보기 1~4라운드 동안 `.stage` 안 **요소 노드 추가/삭제 0**(클래스·글자만 변경) · 타일 6장 크기 고정(370×354 → 370×333, 배지 제거 후) · 화상 왕복 5회+3라운드 111샘플 동안 6타일 항상 화면 안·가려짐 0·이미지 로드 유지 · 피클 영상은 발언 중에만 재생(68샘플) · 조용/계속 · 안건 교체 시 노드 재생성 0.
- `test_v44.py` ALL PASS — 피클 영상 640×598 재생 → 발언이 끝나면 정지(opacity 0), 듣는 중엔 항상 pause+opacity 0, src 불변, 글로 보기 정지, 데스크톱 동일.
- `test_v4.py` ALL PASS — 기존 기능 전부 유지(4라운드·기록 24건·게스트 조언·역할 분담·자막 바 68px·글로 보기 중앙 오차 0px·화상 스크롤 0).
- 스크린샷(눈검수): `downloads/meeting_v451_mobile_video_idle.png`(듣는 중 정지 이미지) · `meeting_v451_mobile_video_pickle_speaking.png`(발언 중 영상) · `meeting_v451_mobile_text.png` · `meeting_v451_desktop_video6.png`. 데스크톱 비율·모바일 2×3 배치 그대로.
- 단일 파일(`downloads/darkjin_meeting_room_v4.html`, 1019KB)도 확인 — 9장 webp + mp4 인라인, 포스터·영상 모두 로드.

### 배포
- 커밋 `da05024` (2026-11-27 11:30 KST) → `git push origin main`
- GitHub Pages: https://darkjin7.github.io/ai-meeting-room/ — HTTP 200 · `<title>` v4.5.1 확인 · `./avatars/*.webp`·`pickle.mp4` 모두 200
- 라이브 URL 실측(모바일 390×844): 6타일 · 이미지 5장 로드 · 포스터 360 · 영상 `paused`(듣는 중) → 발언 중 `play`(t 0.31, opacity 1) · 페이지 오류 0

---

## v4.5 (2026-11-27) — 화상 6분할 타일 풀블리드(꽉 채우기)
- 성진님 피드백: "회의실 사진을 꽉 채워줘 동그렇게 깔끔하긴 한데 작고 움직임도 잘 안보이고"

### ① 타일 레이아웃 — 작은 원형(.vbob) → 타일 전체 채우기
- `body.view-video .tile .vstage{position:absolute;inset:0}`, `.vbob{position:absolute;inset:0;width/height:100%;border-radius:0}`. 미디어는 `position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 45%`(세로 크롭 시 턱이 하단 그라데이션에 묻히지 않는 위치).
- 이름·상태는 타일 하단 `.vov`(신규)에 `background:linear-gradient(transparent,rgba(0,0,0,.78))` 위로. 12px 굵은 흰 글씨 + text-shadow, 상태는 `듣는 중 / 발언 중`.
- 발언 중: **테두리를 항상 2px로 고정**하고 색만 초록으로 바꾼다(두께 변화 = 레이아웃 변화 금지). 여기에 정적 box-shadow 발광 + 좌상단 `● 발언 중` 배지(`.vbadge`, 신규). 리액션 이모지는 우상단 그대로라 배지와 겹치지 않는다.
- 화면 떨림 방지: 높이·그리드·자막 바 68px·`.tile{transition:none}` 규칙 전부 그대로. 화상 모드 발언 전환 스크롤 0 유지.
- **넓은 화면은 6분할 판을 가운데로** — `max-width:min(1040px, calc((100dvh - 352px)*1.875 + 34px))`(700~1024px는 600px). 전체 폭을 쓰면 타일이 1.7 비율까지 길어져 턱이 잘린다 → 어떤 창 크기에서도 타일 비율 0.9~1.25 유지(1280×800·1366×768 포함 실측).

### ② 아바타 이미지 재생성 (`make_avatars_v45.py`)
- 256×256 정사각 → **512×478(타일 1.07 비율)** WebP. 콘택트 시트 `attachments/2026-11-27/ai_family_8_avatars.jpg`의 칸(440×442)에서 400×374를 잘라 확대(머리 위 5% 여백, 턱 76%). 장당 19~29KB(합 196KB).
- 작은 썸네일(카드 헤더 30px·게스트·역할 카드)은 `img.face{aspect-ratio:1/1;object-fit:cover}`라 그대로 잘려 쓰인다.

### ③ 피클 영상 재생성 (`make_pickle_video.py`)
- v4.4의 원형용 1:1 + 흐린 비네트 여백을 버리고, 원본 720×1280에서 **타일 비율 그대로 720×673(y=445)을 잘라** 640×598로 인코딩(비네트·여백 없음). 이마·눈·턱·넥타이까지 들어오는 화상통화 클로즈업.
- 오디오 제거 · H.264 High yuv420p(tv) · CRF 29 · `+faststart` · 마지막 10프레임 ↔ 첫 10프레임 크로스페이드 루프 · **392KB**(원본 2.9MB). poster `pickle_poster.webp` 360×336 18KB.
- `<video muted loop playsinline autoplay preload="none" poster>` · 화상 진입 시 `data-src`→`src` · 글로 보기에서 `pause()` 로직은 v4.4 그대로.

### 검증 (2026-11-27)
- `test_v4.py` ALL PASS — 아바타 512×478 8장 로드 · 화상 타일 6개 전부 풀블리드(미디어 = 프레임 182×170 = 타일 186×174 − 테두리, `object-fit:cover`·`border-radius:0`·`50% 45%`) · 자막 바 68px · 글로 보기 중앙 정렬 0px · 스크롤 0.
- `test_v44.py` ALL PASS — 영상 392KB 640×598 7.92초 오디오 0 faststart, 모바일 타일 182×170 풀블리드 재생(t 0.87→2.07), 데스크톱 331×270, 글로 보기 정지 → 화상 복귀 재생, 화상 모드 스크롤 0.
- 스크린샷: `downloads/meeting_v45_mobile_video6.png`(390×844), `downloads/meeting_v45_desktop_video6.png`(1440×900)

---

## v4.4 (2026-11-27) — 글로 보기 발언 카드 '세로 중앙' 정렬 · 피클 움직이는 영상 아바타
- 성진님 피드백 2건: ① "발언 할 때 글로보는 페이지에서 화면 중앙으로 이동이 잘 안됨 ㅠㅠ" ② 피클 움직이는 영상 테스트 적용.

### ① 글로 보기 중앙 정렬 (`focusTile` 재작성)
- **원인**: v4.2.1 은 `scrollIntoView({block:'nearest'})` 라, 카드가 화면에 **걸치기만 하면 스크롤을 하지 않았다**. 그래서 아래·위 가장자리에 반쯤 걸친 카드가 그대로 발언하고 넘어가 "중앙으로 안 온다"고 느껴졌다. (`block:'nearest'` + "이미 보이면 return" 두 조건이 겹침)
- **수정**: 카드의 세로 중심을 **실제로 보이는 영역의 중앙**에 맞춘다.
  - 보이는 영역 = 위 스티키 `.topbar` 아래 ~ 아래 고정 오너 콘솔(`#ownerBar`, 챗 칩까지 포함) 위. 그 중앙을 목표로 잡는다(모바일 390×844 기준 y 94~756, 중심 425).
  - 자체 rAF 이징(ease-out, 260~520ms)으로 이동. `requestAnimationFrame` 두 번 뒤 좌표를 재고, `prefers-reduced-motion`이면 즉시. 중복 호출은 이전 이동을 취소하고 새 위치로 이어 간다(6인이 연달아 말해도 끊기지 않음).
  - **손 스크롤 우선**: `touchstart`·`wheel`·`mousedown`·`keydown` 이 들어오면 자동 이동을 즉시 멈춘다. 사용자가 보려고 잡고 있는 화면을 빼앗지 않는다.
  - **안착 후 1회 보정**: 이동이 끝난 뒤 한 번 더 재서 18px 넘게 벌어졌으면(늦게 온 이미지·iOS 주소창·툴바 접힘) 애니메이션 없이 조용히 다시 맞춘다.
  - 맨 끝 카드도 중앙까지 올라올 수 있게, 문서 끝 여백(`#scrollPad`)을 **필요한 만큼만** 늘린다(줄이지는 않아 흔들리지 않는다). 화상 모드에서는 `display:none`.
  - `body{overflow-anchor:none}` — 브라우저의 스크롤 앵커링이 중앙 정렬을 밀지 않게.
- **화상 6분할은 그대로**: `state.view !== 'text'` 또는 `body.view-video` 면 즉시 return. 스크롤 0(검증: 발언 전환 24샘플 모두 scrollY 0).

### ② 피클 움직이는 영상 (`avatars/pickle.mp4`)
- 원본 `attachments/2026-11-27/14721333_1795705520204730-…mp4` (피클 · 7.93초 · 720×1280 · H.264+AAC 2.9MB) → `make_pickle_video.py`
  - **오디오 제거**(`-an`), 1:1 480×480 재구성. 세로 영상을 그대로 원에 넣으면 얼굴이 잘려서, 머리~어깨는 선명한 전경(324×576)으로 가운데 두고 좌우는 같은 화면을 흐리게 깐 뒤 비네트로 어둡게 눌렀다(이음매 없음).
  - 8초 루프가 끊기지 않게 마지막 10프레임을 첫 10프레임과 크로스페이드. H.264 High · yuv420p(tv) · CRF 28 · `+faststart` · **282KB**(원본 2.9MB → 1/10).
  - poster `avatars/pickle_poster.webp`(360×360, 16KB) — 첫 프레임과 같은 그림이라 재생 시작 때 튀지 않는다.
- **적용 위치**: 🎥 화상 6분할 피클 타일의 원형 얼굴(`.vbob`). `<video muted loop playsinline autoplay preload=none poster>` + `play().catch(()=>{})`, 컨트롤·PiP 끔, `pointer-events:none`.
- **내려받기 절약**: `src` 는 화상 화면에 들어갈 때 `data-src` → `src` 로 붙인다. 📝 글로 보기에서는 내려받지도 재생하지도 않고 poster 만 쓰며, 화면을 벗어나면 `pause()`.
- **실패 대비**: 영상이 안 열리면(코덱·정책) 정지 이미지 `pickle.webp` → 그것도 실패하면 이모지. 원형 프레임 크기는 CSS 고정이라 레이아웃 불변.
- **단일 파일 배포**: `build_v4.sh` 가 `downloads/darkjin_meeting_room_v4.html` 에 webp 9장 + mp4 를 base64 로 인라인(약 719KB). 저장소의 `index.html` 은 상대경로 그대로.

### 검증 (2026-11-27)
- `test_v44.py` ALL PASS — 모바일 390×844에서 라운드 중 **매 프레임** 발언 카드 중앙 오차를 재서 6명 모두 **0px**(±12px 허용, 문서 끝 예외는 카드 전체 노출), `focusTile` 6장 전부 0px. 화상 모드 발언 전환 24샘플 스크롤 0.
- 영상: 282KB · H.264 480×480 7.92초 · 오디오 트랙 0 · faststart(moov 앞) · 재생 중(currentTime 0.88→2.08) · 원형 프레임 84×84(모바일)/142×142(데스크톱) 꽉 채움 · 글로 보기에서 정지 → 화상 복귀 시 재생.
- `test_v4.py` ALL PASS — 기존 v4.1~v4.3 기능 전부 유지(라운드·기록·게스트·자막 바 68px·카드 높이 불변·화상 모드 스크롤 0).
- 스크린샷: `downloads/meeting_v44_mobile_text_center.png`, `downloads/meeting_v44_mobile_video6.png`, `downloads/meeting_v44_desktop_video6.png`

---

## v4.3 (2026-11-26 밤) — 비서실 8인 SD 비서 캐릭터 아바타 적용
- 성진님 승인 그림체(`downloads/char_01_pickle_green.png`, SD 대두 · 3D 애니메이션 일러스트)로 **8인 전원** 아바타를 만들고, 6분할 회의실의 이모지 자리를 전부 실제 캐릭터 사진으로 바꿨다.

### 바뀐 것
1. **8인 캐릭터 세트** — `downloads/char_01_pickle_green.png`(피클) 외 7장을 같은 기준 이미지에서 `images --edit`로 생성(헤어·의상·배지만 변경, 얼굴 비율·배경·구도 유지). 7장 모두 눈으로 검수(오이/기형/글자 없음).
   - 콘택트 시트: `downloads/ai_family_8_avatars.jpg` (4×2, 칸 아래 이름·역할 라벨) — `make_contact_sheet.py`
   - 구글 드라이브: `다크진 AI 비서실/이미지/AI생성/2026-11-26/` (ID `1mup5p-i5E0xf3zXVF-ZvMTgrwsv5kquJ`) 에 `캐릭_01_피클_그린.png` ~ `캐릭_08_Keyring.png` 업로드.
2. **웹용 아바타**: `avatars/{pickle,gemini,cue,hark,chatgpt,claude,meta_muse,keyring}.webp` — 256×256, WebP 품질 86, **장당 9~13KB**(합 112KB). 저장소에 함께 커밋되고 Pages에서 `./avatars/*.webp` 상대경로로 바로 로드된다.
3. **적용 위치(이모지 → 캐릭터 썸네일)**
   - 🎥 화상 6분할: 타일 중앙 `.vbob` 원형 프레임을 캐릭터 사진이 꽉 채운다(`object-fit:cover`, `border-radius:50%`).
   - 📝 글로 보기: 카드 헤더 `.avatar` 30px 둥근 사각 썸네일.
   - 👀 참관 게스트 바 `.gie`(18px) · 🌟 참관 게스트 최종 조언 `.gce`(26px).
   - 🧩 역할 분담 카드 `.em`(22px).
4. **떨림 방지 규칙 유지** — `.vbob` 크기는 `clamp(56px,16vh,150px)`로 CSS가 정하고 `img`에 `width/height` 속성 + `aspect-ratio:1/1` + `object-fit:cover`를 명시해 **이미지가 늦게 와도 카드 높이가 변하지 않는다**. 자막 바 68px, 화상 모드 스크롤 0, 글로 보기 자동 스크롤 모두 그대로.
5. **실패 대비** — 이미지가 없거나 로드 실패하면 `.face-fallback`으로 조용히 이모지가 들어간다(레이아웃은 고정 크기라 불변).
6. **단일 파일 배포** — `build_v4.sh`가 `downloads/darkjin_meeting_room_v4.html`을 만들 때 8장을 base64 data URI로 인라인한다(약 312KB, 파일 하나로 열려도 아바타가 나온다). 저장소의 `index.html`은 상대경로 그대로라 112KB만 받는다.

### 검증 (`test_v4.py` → ALL PASS, 2026-11-26)
- 8인 아바타 `naturalWidth/Height == 256` 전부 로드 · src 8종 모두 `./avatars/*.webp` · 타일 6 + 게스트 2
- 화상 6분할: 타일 얼굴 6개가 50px 이상 정사각(±1px)으로 원형 프레임을 채움 · `object-fit:cover` · 390×844 한 화면 2×3 · 스크롤 0 · 자막 바 68px 유지
- 글로 보기: 카드 썸네일 6개 · 참관 게스트 최종 조언 썸네일 2개 · 역할 분담 카드 썸네일 6개 모두 256px 로드
- 발언 전환 카드 높이 불변, 글로 보기 자동 스크롤 smooth 유지(연속 발언으로 스크롤이 끊기면 `focusTile` 결정적 확인으로 대체)
- 스크린샷: `downloads/meeting_v43_mobile_video6.png`, `downloads/meeting_v43_mobile_text.png`

---

## v4.2.1 (2026-11-26 밤) — 화상 자막 높이 고정 · 글로 보기 자동 스크롤 복원
- 성진님 실기기 테스트 피드백 2건 반영.

### 바뀐 것
1. **🎥 화상 6분할 떨림 완전 제거**
   - 자막 바(`#vsub`) 높이를 **68px로 못 박음** (`height/min-height/max-height:68px` + `overflow:hidden`, `box-sizing:border-box`). 안쪽 `.vs-top` 15px · `.vs-tx` 40px(모바일 38px)도 고정 — 자막이 1줄↔2줄↔3줄로 바뀌어도 위 6분할 grid가 1px도 밀리지 않는다.
   - 화상 모드(`body.view-video`)에서 캐릭터 바운스 `transform` 애니메이션(`@keyframes vbob`) 삭제 — `animation:none;transform:none;will-change:auto;transition:none`. 발언 표시는 테두리·배경색만.
   - 점 웨이브(`.vw i`) 애니메이션 삭제 → 정적 막대 높이만 다르게(6/10/7/10/5px). 옆 캐릭터 리액션 배지도 transform 없이 opacity만.
2. **📝 글로 보기 자동 스크롤 복원 (화상 모드에서는 금지)**
   - `focusTile()`을 되살려 `state.view === 'text'`일 때만 `scrollIntoView({behavior:'smooth', block:'nearest'})`. 화상 모드에서는 즉시 return(스크롤 0). 이미 화면 안에 있는 카드는 스크롤하지 않는다(불필요한 흔들림 방지). `prefers-reduced-motion`이면 `auto`.
   - `speakLine()`에서 발언자 카드로 `focusTile(id)` 호출 — 자료 낭독·라운드 발언·오너 코멘트 모두 적용.

### 검증 (`test_v4.py` → ALL PASS, 2026-11-26)
- 화상 모드 자막 바: 재생 중 샘플 · 자막 1줄/2줄/3줄/아주 긴 글 4종 모두 **68px**, `.vs-tx` 38px, grid top/자막 바 top/컨트롤 바 top 불변
- 화상 모드 모션: `.vbob` animationName `none` · transform `none` · will-change `auto` · 웨이브 점 animation `none`
- 화상 모드 스크롤: 재생 중 `scrollIntoView(smooth)` 0회 · `scrollY` 항상 0 · `focusTile()` 직접 호출도 스크롤 0
- 글로 보기: 발언자 카드로 smooth 자동 스크롤 발생 + 발언 카드가 뷰포트 안에 들어옴(카드 높이는 여전히 불변)
- 스크린샷: `downloads/meeting_v42_mobile_video6.png`, `downloads/meeting_v421_desk_video_caption.png`

---
## v4.2 (2026-11-26) — 화상 6분할 ↔ 글로 보기 · 랜덤 치고 들어오기 · iOS 떨림 제거
- 성진님 피드백: "제미나이 cue 뮤즈 발언 때 화면 떨림이 있음. 하나씩 보여서 가독성은 좋아. 하지만 우리가 생각했던 회의 느낌은 아니야. 순서대로 발표 보다는 램덤으로 치고 들어오는 느낌이 좋겠어. 가독성이 좋아 글로 보는 회의 이게 좋겠구 6분할 화면 꽉 채운 화면에 캐락만 보이는 화면을 왔다갔다 보고 싶운대로 보게 해줘"

### 바뀐 것
1. **발언 떨림 제거 (iOS Safari)**
   - `focusTile()`의 `scrollIntoView({behavior:'smooth'})` 삭제 — 자동 스크롤을 아예 쓰지 않는다(보고 싶은 카드는 직접 스크롤). `openConfirm`·`backToTalk`·`newMeeting`의 smooth 스크롤도 제거.
   - `.tile.speaking`은 **border-color + 미세 배경색만** 바꾸고 `transition:none`, box-shadow 없음. border 두께·여백·높이 변화 없음.
   - 본문 `.bubble` 높이 고정(모바일 230px / 데스크톱 150px) — 라운드가 바뀌어 글자 길이가 달라져도 카드 높이가 변하지 않는다.
   - 캐릭터 애니메이션은 `transform`만(바운스), 카드 레이아웃은 그대로.
2. **🎥 화상 6분할 ↔ 📝 글로 보기 토글** (상단 헤더 2번째 줄, 회의 중 언제든 원터치 · 키보드 `v`)
   - 화상 모드: `100dvh`에서 헤더·자막·조작·오너 콘솔을 뺀 영역을 **6타일이 스크롤 없이 꽉 채운다**(모바일 2열×3행, 데스크톱 3열×2행). 타일에는 큰 캐릭터(원형 아바타) + 이름 + `듣는 중/발언 중` + 웨이브만, 긴 본문은 숨김.
   - 지금 말하는 AI의 한 줄 자막은 하단 **전용 자막 바 1곳**에만(2줄 클램프).
   - 발언 캐릭터는 가볍게 바운스, 옆 캐릭터에는 😄 👍 😲 👏 🔥 🤔 리액션 배지가 잠깐 뜬다(absolute — 레이아웃 영향 없음).
   - 결론 확정·역할 분담 화면은 문서라서 `📝 글로 보기`로 자동 전환된다.
   - 보기 선택은 localStorage(`darkjin_mr42_view`)에 남고, 안건을 열 때 복원된다.
3. **고정 1~6번 순서 제거 → 라운드마다 랜덤 셔플**
   - `playRound()`가 6인을 Fisher–Yates로 섞어 재생(고정 순서가 나오면 다시 섞음). 같은 라운드를 다시 틀어도 순서가 매번 달라진다.
   - `state.orderLog`에 재생별 순서 기록, `window.__mr4.lastOrder()`로 확인.
   - 6인+게스트 조언·결론 확정·역할 분담 구조는 그대로.

### 검증 (`test_v4.py` → ALL PASS)
- 🎥↔📝 전환, 모바일 390×844 화상 모드에서 6타일 모두 뷰포트 안 + 세로 스크롤 0 (`scrollHeight == innerHeight`)
- 발언 전환 중 카드 높이 변화 0, `scrollIntoView(smooth)` 0회, 페이지 자동 스크롤 없음
- 재생 5회에서 순서가 5가지로 달라짐(고정 `[pickle,gemini,cue,hark,chatgpt,claude]` 아님)
- 스크린샷: `downloads/meeting_v42_mobile_video6.png`, `downloads/meeting_v42_mobile_text.png` (`shot_v42.py`)

---

## v4.1 (2026-11-26) — 안건 목록 중심 · 4라운드 심화 토론 · 8인 체제(주전 6+게스트 2) · 모바일 1열
- 성진님 피드백: "주제는 내가 미리 정하는 것 목록에서 고르는 걸로 하자. 내가 내일 이 주제로 회의 예정이라고 하면 다들 준비하고 대기. 반박이 한 번 뿐이네. 의견 2번만 얘기하고 결론 선택으로 가는데 더 의견을 볼 수 없으려나?"
- 추가 확정 스펙: ① 주전 6인(기여도순) + 참관 게스트 2인, 결론 단계에서 '🌟 참관 게스트 최종 조언' ② 모바일은 2열이 아니라 **1열 큰 카드**(본문 15~16px · 줄간격 1.55+) + 말하는 AI 확대.

### 바뀐 것
1. **안건 목록 중심**: 옛 '주제 입력 + 요청문 복사 + 큐' 박스를 없애고, 준비실을 `✅ 준비 완료` / `⏳ 준비 중(대기)` 목록으로 재구성. `＋ 안건 예약`(모달: 주제·예정일·말로 입력)으로 "내일 이 주제로 회의" 슬롯을 만들면 localStorage에 남고, 카드의 `📋 피클에게 자료 요청문 복사`로 6인 자료 요청을 넘긴다. ⏳ 카드는 열리지 않는다(가짜 답변 금지).
2. **4라운드 토론**: `agendas.js`의 각 안건에 `rounds:[{n:2 정면 반박},{n:3 대안·절충},{n:4 최종 정리}]`(6인 발언) 추가. UI는 `1 자료 발표 → 2 정면 반박 → 3 대안·절충 → 4 최종 정리` 칩 + `▶️ 다음 라운드` 버튼. 앞 라운드 전에는 잠기고, 끝난 라운드는 다시 보기 가능. 결론은 언제든 가능(`✅ 논의 마치고 결론 고르기`).
3. **8인 체제**: 안건마다 `participants`(주전 6) + `guests`(참관 2, `advice:{option,why,missed}`).
   - `yt-growth`: 피클·Gemini·Cue·Hark·ChatGPT·Claude + 게스트 Meta Muse·Keyring
   - `ldp-workflow`: Meta Muse가 주전 합류, ChatGPT·Keyring이 게스트 (영상/편집 비중 반영)
   - 게스트는 타일 없이 `👀 참관 게스트 2인` 바로 표시만 하고, 결론 패널에서 `🌟 참관 게스트 최종 조언`(추천 결론·이유·놓친 포인트)을 낸다. 복사용 회의록에도 포함.
4. **모바일 개편**: `@media (max-width:768px)`에서 `.stage` 1열, 본문 15.5px/1.6, 카드 헤더 14px, 말하는 카드는 초록 테두리·배경·좌측 액센트 + `scrollIntoView`로 화면 중앙에. 데스크톱(≥769px)은 3×2 유지. 토스트가 오너 콘솔을 가리지 않게 위치 조정.
5. 자료 상세 모달에 `라운드별 발언`(누적) 추가 — 한 AI의 2~4라운드 발언을 한 화면에서 본다.

### 소스 구조 (v4.1)
```
v4/head.html    ← <head>·CSS·본문 마크업 (모바일 1열 블록 포함)
v4/agendas.js   ← 안건·6인 자료·rounds·participants/guests·결론 후보·후보별 역할·PLANNED(⏳)
v4/app.js       ← 안건 목록·예약·라운드 엔진·게스트 조언·결론/역할·음성·효과음·복사
```
빌드: `./build_v4.sh` (→ `index.html`, `index.v4.html`, `/workspace/downloads/darkjin_meeting_room_v4.html`)
검증: `LD_LIBRARY_PATH=/workspace/work/chrome/libs/usr/lib/x86_64-linux-gnu FONTCONFIG_PATH=/workspace/work/chrome python3 test_v4.py`

### 안건 추가 방법 (피클이 자료를 모은 뒤)
1. `AGENDAS`에 객체 추가 — `participants`(6), `guests`(2, advice 포함), `panels`(6인), `rounds`(2~4라운드), `options`, `roles`(후보 id별 6인), `ownerReplies`, `ownerChips`, `closing`.
2. `ready:true`면 ✅ 목록에 뜨고 준비 완료 알림이 간다. 앞으로 할 안건은 `PLANNED`에 넣으면 ⏳로 보인다.
3. **`agendas.js`에는 비밀키·개인정보를 넣지 않는다.**

---

## v4 (2026-11-26) — 사전 자료 · 선 논의 구조
- 성진님 요구: "주제를 먼저 논의하는 걸 보고 싶다" · "자료를 각자 준비해 준비 완료를 알려 주고, 내가 볼 때 의논" · "결론이 나오면 그때 분담".
- **가짜 동일 대본 제거.** 회의 발언은 `v4/agendas.js`에 적힌 **사전 준비 자료**에서만 나온다. 자료가 없는 주제는 지어내지 않고 '자료 준비 중'으로 남는다.
- 2단계 흐름: ① 준비 자료 열람·논의(자료 펼치기 / 낭독 / 반박 라운드 / 오너 코멘트) → ② 결론 후보 선택(+오너 추가 지시) → 확정 시에만 역할 분담표 생성.
- 6분할 = AI 6인(피클·Gemini·Cue·Hark·ChatGPT·Claude). 오너는 타일 대신 하단 콘솔·코멘트로 참여. Meta Muse·Keyring은 자료가 없어 참고 문구로만 표시.
- 노션 연동·Gemini API 호출은 넣지 않았다(성진님이 "완성되고 마음에 들면 그때 연결"이라고 함).

### 소스 구조 (v4)
```
v4/head.html    ← <head>·CSS·본문 마크업 (v3 iOS 깜빡임 규칙 유지: backdrop-filter 없음, 조용은 오버레이 opacity만)
v4/agendas.js   ← 안건·6인 준비 자료·결론 후보·후보별 역할 분담 (유일한 자료 원본)
v4/app.js       ← 준비실·자료 열람·논의·결론 확정·역할 분담·음성·효과음·복사·큐
```
빌드: `./build_v4.sh` (→ `index.html`, `index.v4.html`, `/workspace/downloads/darkjin_meeting_room_v4.html`)
검증: `LD_LIBRARY_PATH=/workspace/work/chrome/libs/usr/lib/x86_64-linux-gnu FONTCONFIG_PATH=/workspace/work/chrome python3 test_v4.py`

### 안건 추가 방법 (피클이 자료를 모은 뒤)
1. `v4/agendas.js`의 `AGENDAS` 배열에 객체 추가 — `panels`(6인: summary·points·concern·proposal·rebuttal·source), `options`(결론 후보 2~3), `roles`(후보 id별 6인 역할), `ownerReplies`, `ownerChips`, `closing`.
2. `ready:true`로 두면 웹 '준비 완료된 안건'에 뜨고, 그 브라우저에 준비 완료 알림이 간다.
3. 빌드 후 커밋. **`agendas.js`는 SEO/보안상 문제 없고, 비밀키·개인정보를 넣지 않는다.**

### 배포 상태
- **v4는 로컬 빌드까지만 했다.** `GH_TOKEN` 만료(401)로 `git push`를 시도하지 않았다. 원격 `darkjin7/ai-meeting-room`의 Pages는 아직 v3(`682bc9b`).
- 푸시할 때: `git add index.html v4/ build_v4.sh test_v4.py && git commit -m "v4 사전 자료·선 논의 구조" && git push origin main`

---

## 현재 상태 (2026-11-25 20:10 KST) — v3
- 저장소: `darkjin7/ai-meeting-room` (public), 기본 브랜치 `main`
- 최신 커밋: `682bc9b` — **v3** (`index.html`, 2라운드 티키타카 · 오너 끼어들기 · 조용 깜빡임 제거 · Web Audio 효과음)
- GitHub Pages: `built` · https://darkjin7.github.io/ai-meeting-room/ (HTTP 200)
- 이전 커밋: `82b18bf`(v2 iOS 스크롤 플리커 수정), `e43915e`(v2)

## 소스 구조 (v3부터)
```
v3/head.html   ← <head>·CSS·본문 마크업
v3/app1.js     ← 상태·효과음·음성·정지/재개·타일·회의록
v3/app2.js     ← 내장 회의 엔진(R1/R2/R3)·Gemini·진행 흐름·이벤트
```
빌드(=index.html 만들기):
```bash
cd /workspace/work/meeting-room
cat v3/head.html > index.html
printf '<script>\n' >> index.html
cat v3/app1.js v3/app2.js >> index.html
printf '</script>\n</body>\n</html>\n' >> index.html
cp index.html /workspace/downloads/darkjin_meeting_room_v3.html
```
`index.v3.html`은 같은 내용의 빌드 산출물(테스트가 이 파일을 연다).

## 테스트
```bash
cd /workspace/work/meeting-room
LD_LIBRARY_PATH=/workspace/work/chrome/libs/usr/lib/x86_64-linux-gnu \
FONTCONFIG_PATH=/workspace/work/chrome python3 test_v3.py      # 전 구간 (약 3분)
python3 test_buckets.py                                         # 일반·로또·업무자동화 안건
```
- `test_v3.py`: R1 → R2(이름 부르는 반박) → 🔄 R3 → ✅ 확정 → 재소집 / 회의 중 끼어들기 / 중간 정리에서 칩 개입 / 🤫 조용(카드 높이·버튼 위치 0px) / ▶️ 계속 / "다들 조용" 음성 감지 / 모바일 390px
- 헤드리스에는 가짜 `speechSynthesis`·`SpeechRecognition`을 주입한다. 테스트용 훅: `window.__spoken`, `window.__sfxCalls`, `window.__sfxLog`.

## 파일을 고칠 때
```bash
cd /workspace/work/meeting-room
# v3/*.js 또는 v3/head.html 수정 → 위 빌드 명령 → 테스트 → 커밋
git add index.html && git commit -m "..." && git push origin main
# Pages는 main push만으로 자동 재배포됨 (약 30~40초)
gh api repos/darkjin7/ai-meeting-room/pages/builds/latest --jq '{status,commit,updated_at}'
```

## 참고
- Pickle의 GitHub 앱에는 Pages/Workflows 권한이 없다. Pages 스위치는 성진님이 한 번 켰고(2026-11-25 19:02) 지금은 main push로 자동 배포된다.
- HTML에 비밀키·개인정보 없음. Gemini 키는 설정 화면에서 입력할 때만 브라우저 localStorage에 저장된다.
- v3에서 조용 전환 시 레이아웃을 바꾸지 않는 것이 핵심 규칙이다(카드 문구·높이·배경 변경 금지, 오버레이 opacity만). 이 규칙을 깨면 iOS Safari에서 다시 깜빡인다.
