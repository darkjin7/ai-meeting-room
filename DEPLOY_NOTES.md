# 배포 메모 — 다크진 AI 비서실 · 6분할 회의실

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
