# 배포 메모 — 다크진 AI 비서실 · 6분할 회의실

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
