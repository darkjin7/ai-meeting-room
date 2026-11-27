
(function(){
  "use strict";

  /* ═══════════════════ 기본 정의 ═══════════════════ */
  const LIB = window.AGENDA_LIB || {agendas:[], byId:{}};
  const AIS = ["pickle","gemini","cue","hark","chatgpt","claude"];
  const GUEST_POOL = ["meta_muse","keyring"];
  /* v4.3 — 비서실 8인 SD 캐릭터 아바타. img 는 512x478 webp(저장소 `avatars/`), 실패하면 emoji 로 대체된다.
     v4.5.1 — 영상은 "상태별로 한 겹씩" 쌓는 구조다.
       · poster = 정지 이미지(영상 첫 프레임) — 항상 아래층
       · video  = 발언 중(speaking) 영상 — 발언 중일 때만 opacity 1 + play()
     다른 AI나 다른 상태(idle·react) 영상을 추가할 때는 **src 를 갈아 끼우지 말고**
     `videos:{idle:'...', react:'...'}` 처럼 상태별 주소를 적은 뒤, motionVideo() 를 상태마다 하나씩
     만들어 겹쳐 두고 타일 클래스(`.tile.speaking` / `.tile.sleepy`)로 opacity 만 바꾼다.
     (iOS Safari 에서 src 교체·DOM 제거는 깜박임과 빈 타일의 원인이다)
     v4.6.2 — 피클에게 첫 상태 영상 `sleepy`(눈 감고 조는 영상)와 `phone`(몰래 폰 보다 들킴 2.2초 루프)가 붙었다.
       · speaking 영상은 지금처럼 class `vid` — 기존 검증(video.vid 1개)이 보는 그 요소
       · 나머지 상태 영상은 class `vlay` + data-state — 겹으로만 쌓이고 opacity 로만 켜진다
     v4.6.3 — `sleepy` 는 **한 번만 재생하고 마지막 프레임(눈을 꼭 감은 얼굴)에서 멈춘다**(VIDEO_ONCE).
       성진님: "조는 모습은 눈이 감기면 멈추고 있다가 자기 차례 되면 깨는 걸로" — 영상이 끝나면 loop 없이
       마지막 프레임에 그대로 머물고, setTileMood 로 조는 상태에 **다시 들어올 때만** currentTime=0 부터 재생한다.
     v4.7 — `listening`(Hark 가 만든 8초 루프)이 **듣는 중의 기본 겹**이 되면서 피클 타일 영상은 4겹이다:
       speaking(pickle.mp4) + listening(pickle_listening.mp4) + sleepy + phone. 여전히 src 교체 없이
       opacity + play()/pause() 만 쓴다. 졸기·딴짓은 '어쩌다 한 번'만 켜진다(maybeMoodEvent).
     v4.7.1 — `phone` 도 **한 번만 재생**한다(VIDEO_ONCE). 성진님: "딴짓이 계속 반복됨. 한 번만 하고 경청을 해야지".
       sleepy 처럼 마지막 프레임에 머물지 않고, 영상이 끝나는 순간(ended / 마지막 0.04초) 곧바로 mood 를 비워
       기본 `listening`(경청) 자세로 돌아온다 — 딱 한 번 폰 보다 들키고 민망해서 다시 듣는 연출. */
  const PEOPLE = [
    /* v4.4 — 피클만 움직이는 영상 아바타. 정지 이미지는 영상 poster/실패 시 대체용으로 그대로 둔다.
       v4.6.2 — 듣는 중에 조는 모습(sleepy)·몰래 폰 보는 모습(phone). 발언 차례가 오면 setTileMood 가 즉시 깨운다. */
    {id:"pickle",  name:"피클(다크)", emoji:"⚡", role:"총괄 · 자료 취합·진행",   color:"#8b7cf6", img:"./avatars/pickle.webp",
      video:"./avatars/pickle.mp4", poster:"./avatars/pickle_poster.webp",
      /* v4.7 — `listening`(듣는 중)이 **기본 영상**이다. 말하지 않을 때 이 겹이 계속 돌고(loop),
         sleepy·phone 은 '어쩌다 한 번' 얹히는 특별 이벤트 겹이다(playRound 의 maybeMoodEvent). */
      videos:{listening:"./avatars/pickle_listening.mp4",
              sleepy:"./avatars/pickle_sleepy.mp4", phone:"./avatars/pickle_phone.mp4"}},
    {id:"gemini",  name:"Gemini",    emoji:"🌀", role:"대본·카피·구조 분석",     color:"#4285f4", img:"./avatars/gemini.webp"},
    {id:"cue",     name:"Cue",       emoji:"🔍", role:"트렌드·수치 리서치",      color:"#38bdf8", img:"./avatars/cue.webp"},
    {id:"hark",    name:"Hark",      emoji:"🧐", role:"검증·리스크·조건 확인",   color:"#f0a23c", img:"./avatars/hark.webp"},
    {id:"chatgpt", name:"ChatGPT",   emoji:"🛠️", role:"구조 설계·DB·자동화",     color:"#10a37f", img:"./avatars/chatgpt.webp"},
    {id:"claude",  name:"Claude",    emoji:"✍️", role:"글쓰기·기획 검토",        color:"#d97757", img:"./avatars/claude.webp"},
    {id:"meta_muse",name:"Meta Muse",emoji:"🎨", role:"B롤 영상·이미지",        color:"#e879f9", img:"./avatars/meta_muse.webp"},
    {id:"keyring", name:"Keyring",   emoji:"🔑", role:"신규 합류 · 참관",        color:"#a3e635", img:"./avatars/keyring.webp"}
  ];
  const byId = id => PEOPLE.find(p => p.id === id) || (id === "owner" ? {id:"owner", name:"오너", emoji:"👑", color:"#f5c04a"} : null);
  /* 상태별 영상 표 — speaking 외 상태(sleepy …)는 PEOPLE 에 videos 로 적으면 여기서 speaking 과 합쳐진다.
     (주소 문자열을 PEOPLE 안에 중복해 적지 않는 이유: 단일 파일 빌드가 mp4 를 두 번 인라인해 파일이 두 배가 된다) */
  PEOPLE.forEach(p=>{ if(p.video) p.videos = Object.assign({speaking:p.video}, p.videos || {}); });
  /* v4.6.3 — 한 번만 재생하고 마지막 프레임에서 멈출 상태 영상.
     `sleepy` 는 눈이 감기는 순간까지의 클립이라 루프로 돌리면 눈을 다시 뜨는 대목이 섞인다(3.5초 루프였던 v4.6.2).
     여기 적힌 상태는 <video loop=false> 로 만들고, 끝나면 그 프레임에 멈춘다.
     v4.7.1 — `phone`(몰래 폰 보다 들킴 2.2초)도 한 번만 튼다. 단 끝나면 마지막 프레임에 남지 않고
       곧바로 기본 `listening`(경청)으로 돌아온다(backToListening — 아래 motionVideo 의 ended/timeupdate). */
  const VIDEO_ONCE = {sleepy:true, phone:true};
  /* v4.7.1 — 한 번 재생을 마친 상태 영상의 뒷정리. 지금은 `phone` 만 해당한다.
     영상이 끝나면(ended 또는 마지막 0.04초) mood 를 비워 기본 경청으로 되돌린다.
     이미 발언 차례가 와서 speaking 으로 바뀌었거나 다른 상태(sleepy)면 손대지 않는다 — 깨어 있는 쪽이 이긴다. */
  function backToListening(id){
    const r = id && tileRefs[id];
    if(!r || r.mood !== "phone") return false;
    return setTileMood(id, "");
  }

  /* ── v4.3 캐릭터 썸네일 ──
     모든 자리에서 크기는 CSS 로 고정하고 img 에 width/height/object-fit 을 명시한다.
     이미지가 늦게 와도(또는 실패해도) 카드 높이가 1px도 변하지 않는다. */
  function faceImg(p, cls){
    const img = document.createElement("img");
    img.className = "face" + (cls ? " " + cls : "");
    img.alt = (p && p.name) || "";
    img.width = 256; img.height = 256;
    img.loading = "eager"; img.decoding = "async"; img.draggable = false;
    if(p && p.img) img.src = p.img;
    return img;
  }
  /* holder 안을 캐릭터 썸네일로 채운다. 로드 실패 시 이모지로 조용히 대체.
     opts.video 가 true 이고 그 인물에 영상이 있으면 정지 이미지 위에 움직이는 영상을 겹쳐 둔다.
     (지금은 화상 6분할의 큰 얼굴 자리에서만 쓴다 — 작은 목록 썸네일까지 영상을 돌리면 무겁다)
     v4.5.1 — 영상 타일은 "정지 이미지(포스터) 아래 + 영상 위" 2겹으로 만들고,
              발언 중일 때만 영상을 opacity 1 로 켜 재생한다(듣는 중에는 정지 이미지). */
  function faceInto(holder, p, opts){
    holder.textContent = "";
    const wantVideo = !!(opts && opts.video && p && p.video);
    if(!p || (!p.img && !wantVideo)){ holder.textContent = (p && p.emoji) || "•"; return {}; }
    if(wantVideo){
      /* 아래층: 영상 첫 프레임과 같은 그림(pickle_poster.webp) — 듣는 중·전환 순간에 보인다 */
      const poster = document.createElement("img");
      poster.className = "vposter";
      poster.alt = "";
      poster.width = 360; poster.height = 336;
      poster.decoding = "async"; poster.draggable = false;
      poster.dataset.src = p.poster || p.img || "";
      poster.src = poster.dataset.src;   /* 정지는 정지 이미지가 바로 보여야 한다(18KB) — 영상만 화상 진입 시 내려받는다 */
      poster.addEventListener("error", function(){ poster.style.display = "none"; });
      /* 위층: 상태 영상 — speaking·sleepy … 를 상태마다 한 겹씩 쌓는다(주소는 손대지 않고 opacity 만) */
      const states = Object.keys(p.videos || {});
      const vids = {}, layers = [];
      (states.length ? states : ["speaking"]).forEach(st=>{
        const v = motionVideo(p, st);
        v.addEventListener("error", function(){ stillFallback(holder, p, v); });
        vids[st] = v;
        layers.push(v);
      });
      holder.append.apply(holder, [poster].concat(layers));
      return {video:vids.speaking || layers[0], vids:vids, poster:poster};
    }
    const img = faceImg(p);
    img.addEventListener("error", function(){ stillFallback(holder, p); });
    holder.appendChild(img);
    return {img:img};
  }
  /* 영상이 안 열리는 브라우저(=H.264 미지원 등)는 정지 이미지 → 그것도 실패하면 이모지.
     v4.5.1 — 영상 요소는 지우지 않고 숨기기만 한다(다시 살릴 수 있게). */
  function stillFallback(holder, p, culprit){
    const v = culprit || holder.querySelector("video.face");
    if(v){ v.classList.add("off"); try{ v.pause(); }catch(e){} }
    /* 영상 타일: 아래깔린 정지 이미지(포스터)를 살리면 그만 — 이모지로 갈 필요 없다 */
    const poster = holder.querySelector("img.vposter");
    if(poster){
      poster.style.display = "";
      if(!poster.getAttribute("src") && poster.dataset.src) poster.src = poster.dataset.src;
      return;
    }
    if(holder.querySelector("img.face")) return;
    holder.classList.remove("face-fallback");
    if(p && p.img){
      const img = faceImg(p);
      img.addEventListener("error", function(){
        holder.classList.add("face-fallback");
        holder.textContent = (p && p.emoji) || "•";
      });
      holder.appendChild(img);
      return;
    }
    holder.classList.add("face-fallback");
    holder.textContent = (p && p.emoji) || "•";
  }
  /* v4.4 — iOS Safari 자동재생 규칙을 그대로 지킨다:
     muted + playsinline + autoplay + loop, 그리고 play() 실패(.catch)는 조용히 무시.
     src 는 화상 화면에 처음 들어갈 때 한 번만 붙인다(armAvatarVideos) —
     v4.5.1 부터는 src 를 빼지도, 갈아 끼우지도 않고 play()/pause() + opacity 만 쓴다. */
  function motionVideo(p, state){
    state = state || "speaking";
    const src = (p && p.videos && p.videos[state]) || (p && p.video) || "";
    const once = !!VIDEO_ONCE[state];   // v4.6.3 — sleepy 처럼 한 번만 틀고 마지막 프레임에서 멈추는 상태
    const v = document.createElement("video");
    /* v4.6.2 — speaking 은 class `vid`(기존 검증·재생 경로), 그 밖의 상태는 `vlay` + data-state */
    v.className = "face " + (state === "speaking" ? "vid" : "vlay");
    v.dataset.state = state;
    v.muted = true; v.defaultMuted = true;
    v.loop = !once; v.autoplay = false; v.playsInline = true;
    v.preload = "none";
    v.width = 640; v.height = 598;   // v4.5 — 타일 비율(1.07)에 맞춘 풀블리드 영상
    v.setAttribute("muted", "");
    if(once) v.removeAttribute("loop"); else v.setAttribute("loop", "");
    v.setAttribute("playsinline", "");
    v.setAttribute("webkit-playsinline", "");
    v.setAttribute("disablepictureinpicture", "");
    v.setAttribute("disableremoteplayback", "");
    v.setAttribute("aria-label", ((p && p.name) || "") + " 움직이는 아바타");
    if(p && p.poster) v.poster = p.poster;
    v.dataset.src = src;
    v.dataset.who = p.id;
    /* v4.6.3 — once 상태 영상이 끝나면 그 자리(마지막 프레임)에 남긴다. done 표시가 없으면
       syncAvatarMedia 가 'paused 니까 다시 재생' 하며 처음으로 되감아 버린다(눈을 다시 뜨는 것처럼 보임). */
    if(once){
      /* v4.7.1 — 한 번 트는 영상의 끝 처리 한 곳.
         · done 표시는 syncAvatarMedia 가 'paused 니까 다시 재생' 하며 되감는 것을 막는다.
         · `phone` 은 끝나는 순간 곧바로 listening 으로 복귀(backToListening) — 마지막 프레임에 머물지 않는다. */
      const finish = function(){
        if(v.dataset.done === "1") return;
        v.dataset.done = "1";
        if(state === "phone") backToListening(p && p.id);
      };
      v.addEventListener("ended", finish);
      v.addEventListener("timeupdate", function(){
        if(!v.duration || !isFinite(v.duration)) return;
        if(v.currentTime >= v.duration - 0.04) finish();
      });
    }
    return v;
  }
  /* 화상 화면에 처음 들어갈 때 딱 한 번: 영상 src·포스터 src 를 붙인다(이후에는 건드리지 않는다).
     preload=metadata 로 바꾸고 붙인다 — 발언이 시작될 때 바로 재생되도록 치수·첫 프레임만 미리 받는다. */
  function armAvatarVideos(){
    document.querySelectorAll("video.face[data-src]").forEach(v=>{
      if(!v.getAttribute("src")){ v.preload = "metadata"; v.src = v.dataset.src; }
    });
    document.querySelectorAll("img.vposter[data-src]").forEach(im=>{
      if(!im.getAttribute("src")) im.src = im.dataset.src;
    });
  }
  /* 상태 영상 재생 규칙 (v4.6.2 확장)
     - 켜는 겹은 avatarMood() 한 곳에서 정한다: 발언 중 → speaking · 조는 중 → sleepy
     - src 는 그대로 둔다(떼었다 붙이면 iOS 에서 깜빡이거나 화면이 사라진다)
     - 보임/숨김은 CSS 가 타일 클래스로 정하고, 여기서는 play()/pause() 만 한다
     - 영상이 없거나 화상 모드가 아니면 아무것도 하지 않는다 */
  /* 어느 영상 겹을 켜야 하는가 — 발언 중(speaking) > 조는 중/딴짓(sleepy·phone) > 듣는 중(listening).
     조용(quiet) 이면 전부 끈다. 두 상태가 겹치지 않게 한 곳에서만 정한다.
     v4.7 — 특별 이벤트가 없을 때의 **기본값이 '듣는 중' 영상**이다(정지 사진이 아니라 살아 있는 얼굴).
       재생은 syncAvatarMedia 가 화상 모드(view-video)일 때만 하므로, 첫 입장 전·글로 보기에서는
       예전처럼 영상을 받지도 틀지도 않고 정지 이미지만 보인다(리소스 절약 원칙 그대로). */
  function avatarMood(r){
    if(!r) return "";
    if(r.tile.classList.contains("quiet")) return "";
    if(r.tile.classList.contains("speaking")) return "speaking";
    if(r.mood && r.vids && r.vids[r.mood]) return r.mood;
    if(r.vids && r.vids.listening) return "listening";
    return "";
  }
  function syncAvatarMedia(){
    const inVideo = document.body.classList.contains("view-video");
    Object.keys(tileRefs).forEach(id=>{
      const r = tileRefs[id];
      if(!r || !r.vids) return;
      const want = inVideo ? avatarMood(r) : "";
      Object.keys(r.vids).forEach(st=>{
        const v = r.vids[st];
        if(!v) return;
        if(v.classList.contains("off")) return;        // 코덱·정책으로 실패 → 정지 이미지 유지
        if(!v.getAttribute("src")) return;              // 아직 무장 전
        if(st === want){
          /* v4.6.3 — 한 번만 트는 영상(sleepy)이 끝나 마지막 프레임에 머무는 중이면 다시 재생하지 않는다 */
          if(v.dataset.done === "1"){ if(!v.paused) { try{ v.pause(); }catch(e){} } }
          else if(v.paused){
            try{ const pr = v.play(); if(pr && pr.catch) pr.catch(()=>{}); }catch(e){}
            /* 재생을 시작했는데 1.5초가 지나도록 아무것도 못 받았다면(readyState 0) 이 기기·이 방식으로는
               영상이 안 열린다(data: 영상 등) → 그 겹만 숨기고 정지 이미지를 그대로 보여 준다. */
            if(parseInt(v.dataset.watch, 10) !== 1){
              v.dataset.watch = "1";
              setTimeout(()=>{
                v.dataset.watch = "0";
                if(v.readyState === 0) v.classList.add("off");
                else if(v.readyState >= 2) v.classList.remove("off");
              }, 1500);
            }
          }
        } else if(!v.paused){
          try{ v.pause(); }catch(e){}
        }
      });
    });
  }
  function startMotionVideos(){
    armAvatarVideos();
    syncAvatarMedia();
    watchdogMedia(90);
  }
  function stopMotionVideos(){
    document.querySelectorAll("video.face").forEach(v=>{ try{ v.pause(); }catch(e){} });
  }
  /* v4.5.1 — 타일 미디어 자동 복구.
     iOS Safari 는 앱이 백그라운드로 갔다 오거나 메모리가 빠듯할 때 이미지·영상 디코딩을 버려
     "그 AI 화면만 빈다"는 일이 생긴다. 화상 화면으로 돌아오거나 창 크기가 바뀌면 한 번씩 확인해서,
     실패한(complete && naturalWidth==0) 이미지만 다시 요청하고, 발언 중인 영상은 다시 재생한다.
     시도 횟수는 타일당 3회로 제한한다(무한 재시도 금지). */
  let mediaWatchT = null;
  function watchdogMedia(delay){
    clearTimeout(mediaWatchT);
    mediaWatchT = setTimeout(assertTileMedia, delay || 120);
  }
  function assertTileMedia(){
    Object.keys(tileRefs).forEach(id=>{
      const r = tileRefs[id];
      const imgs = r.tile.querySelectorAll("img");
      [].forEach.call(imgs, im=>{
        if(!im.getAttribute("src")) return;
        if(!(im.complete && im.naturalWidth === 0)) return;   // 실패한 것만
        const n = (parseInt(im.dataset.retry, 10) || 0);
        if(n >= 3) return;
        im.dataset.retry = String(n + 1);
        const src = im.getAttribute("src");
        setTimeout(()=>{ im.src = src; }, 40 * (n + 1));
      });
    });
    syncAvatarMedia();
  }
  ["pageshow", "resize", "orientationchange"].forEach(ev=> window.addEventListener(ev, ()=> watchdogMedia(120), {passive:true}));
  document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState === "visible") watchdogMedia(120); });
  function faceBox(p, tag, cls){
    const h = document.createElement(tag || "div");
    h.className = cls || "facebox";
    faceInto(h, p);
    return h;
  }
  /* 게스트는 agendas.js 안에 {id,name,emoji,role,advice} 로 적혀 있다 — PEOPLE 의 사진을 붙인다 */
  function guestPerson(g){
    if(!g) return {};
    const p = g.id ? byId(g.id) : null;
    return p ? Object.assign({}, p, {name: g.name || p.name, role: g.role || p.role, emoji: g.emoji || p.emoji}) : g;
  }

  /* 주전 6인은 안건마다 바뀔 수 있다 (참관 게스트 2인은 타일 없이 조언만) */
  function partList(){
    const a = state.agenda;
    if(a && a.participants && a.participants.length) return a.participants.filter(id=> byId(id));
    return AIS.slice();
  }
  function guestList(){
    const a = state.agenda;
    if(!a || !a.guests) return [];
    return a.guests.filter(g=> g && g.name);
  }
  function panelCount(a){
    const target = a || state.agenda;
    if(!target || !target.panels) return 0;
    return partList().filter(id=> target.panels[id]).length;
  }

  const K_SPEED = "darkjin_mr4_speed";
  const K_VOICE = "darkjin_mr4_voice";
  const K_SFX   = "darkjin_mr4_sfx";
  const K_REQ   = "darkjin_mr4_requests";
  const K_SEEN  = "darkjin_mr4_seen_ready";
  const K_NOTIFY= "darkjin_mr4_notify";
  const K_PLAN  = "darkjin_mr4_plans";
  const K_VIEW  = "darkjin_mr42_view";
  const REACTIONS = ["😄","👍","😲","👏","🔥","🤔"];

  const LS = {
    get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } },
    set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} },
    del(k){ try{ localStorage.removeItem(k); }catch(e){} }
  };

  const state = {
    phase:"idle",        // idle | materials | discussion | confirm | roles
    agenda:null,         // 선택된 안건 객체
    option:null,         // 확정한 결론 후보 id
    ownerDir:"",         // 결론 확정 시 오너 추가 지시
    notes:[],            // 오너 코멘트 전체
    round:0,             // 지금까지 본 라운드 (0=아직 없음, 1~4)
    roundSet:{},         // 라운드별 완료 여부
    talked:{},           // 라운드:AI 중복 기록 방지
    busy:false,
    runToken:0,
    speed:Number(LS.get(K_SPEED) || 1),
    voiceOn:(LS.get(K_VOICE) || "1") !== "0",
    sfxOn:(LS.get(K_SFX) || "1") !== "0",
    paused:false,
    pausedAt:0,
    pausedMs:0,
    voiceWarned:false,
    startedAt:0,
    timerId:null,
    activeCut:null,
    activeSpeaker:null,
    matId:null,
    view:"text",        // text(글로 보기) | video(화상 6분할)
    lastLine:null,       // 화상 모드 자막에 남길 마지막 대사 {id, tag, text}
    lastOrder:[],        // 방금 재생한 라운드의 랜덤 발언 순서
    orders:{},           // 라운드별 마지막 발언 순서
    orderLog:[],         // 재생 때마다 쌓이는 순서 기록 (검증·복기용)
    /* v4.7 — 졸기/딴짓 발동 기록(세션 단위). openAgenda·newMeeting 에서 리셋된다. */
    moodEvents:0,
    moodRound:0,
    moodLog:[]
  };

  const $ = s => document.querySelector(s);
  const el = (tag, cls, txt) => { const n=document.createElement(tag); if(cls) n.className=cls; if(txt!==undefined) n.textContent=txt; return n; };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const pad = n => String(n).padStart(2,"0");
  const nowHM = () => { const d=new Date(); return pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds()); };
  const nowStamp = () => { const d=new Date(); return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes()); };
  const norm = s => String(s||"").replace(/\s+/g,"").replace(/[.,?!"'·:;()\[\]—–]/g,"").toLowerCase();

  /* ═══════════════════ 효과음 (Web Audio · 외부 파일 0) ═══════════════════ */
  const SFX = (function(){
    let ctx = null;
    const log = [], calls = [];
    window.__sfxLog = log; window.__sfxCalls = calls;
    function ac(){
      if(!state.sfxOn || !state.voiceOn) return null;
      try{
        if(!ctx){ const C = window.AudioContext || window.webkitAudioContext; if(!C) return null; ctx = new C(); }
        if(ctx.state === "suspended" && ctx.resume) ctx.resume();
        return ctx;
      }catch(e){ return null; }
    }
    function note(c,o){
      const t0=o.at, dur=o.dur||.12, f=o.freq, to=o.to||f;
      const osc=c.createOscillator(), g=c.createGain();
      osc.type=o.type||"sine";
      osc.frequency.setValueAtTime(f,t0);
      if(to!==f) osc.frequency.exponentialRampToValueAtTime(Math.max(30,to),t0+dur);
      const peak=o.gain==null?.16:o.gain;
      g.gain.setValueAtTime(.0001,t0);
      g.gain.exponentialRampToValueAtTime(peak,t0+Math.min(.02,dur/3));
      g.gain.exponentialRampToValueAtTime(.0001,t0+dur);
      osc.connect(g); g.connect(c.destination); osc.start(t0); osc.stop(t0+dur+.02);
    }
    function noise(c,o){
      const dur=o.dur||.18, len=Math.max(1,Math.floor(c.sampleRate*dur));
      const buf=c.createBuffer(1,len,c.sampleRate), d=buf.getChannelData(0);
      for(let i=0;i<len;i++){ const k=1-i/len; d[i]=(Math.random()*2-1)*k*k; }
      const src=c.createBufferSource(); src.buffer=buf;
      const bp=c.createBiquadFilter(); bp.type="bandpass"; bp.Q.value=o.q||1.1;
      bp.frequency.setValueAtTime(o.from||2400,o.at);
      bp.frequency.exponentialRampToValueAtTime(Math.max(120,o.to||700),o.at+dur);
      const g=c.createGain(); g.gain.setValueAtTime(o.gain==null?.13:o.gain,o.at);
      g.gain.exponentialRampToValueAtTime(.0001,o.at+dur);
      src.connect(bp); bp.connect(g); g.connect(c.destination); src.start(o.at);
    }
    function play(name,fn){
      calls.push(name); if(calls.length>120) calls.shift();
      const c=ac(); if(!c) return;
      try{ fn(c,c.currentTime+.01); log.push({name:name,t:Date.now()}); if(log.length>120) log.shift(); }catch(e){}
    }
    return {
      unlock(){ const c=ac(); if(c&&c.state==="suspended"&&c.resume) c.resume(); },
      shush(){ play("shush",(c,t)=>{
        note(c,{at:t,freq:900,to:560,dur:.10,type:"sine",gain:.13});
        note(c,{at:t+.085,freq:640,to:430,dur:.13,type:"sine",gain:.12});
        note(c,{at:t,freq:190,to:70,dur:.18,type:"sine",gain:.10});
        noise(c,{at:t+.02,dur:.22,from:2800,to:620,q:1.0,gain:.14});
      }); },
      ding(){ play("ding",(c,t)=>{
        note(c,{at:t,freq:660,dur:.26,type:"triangle",gain:.13});
        note(c,{at:t+.16,freq:880,dur:.34,type:"triangle",gain:.12});
        note(c,{at:t+.16,freq:1320,dur:.30,type:"sine",gain:.05});
      }); },
      confirm(){ play("confirm",(c,t)=>{
        [523.25,659.25,783.99,1046.5].forEach((f,i)=>note(c,{at:t+i*.075,freq:f,dur:.42,type:"triangle",gain:i===3?.10:.11}));
        note(c,{at:t,freq:130.81,dur:.5,type:"sine",gain:.07});
      }); },
      pop(){ play("pop",(c,t)=>{
        note(c,{at:t,freq:420,to:760,dur:.085,type:"sine",gain:.15});
        note(c,{at:t+.04,freq:1180,dur:.05,type:"sine",gain:.05});
      }); }
    };
  })();

  /* ═══════════════════ 음성 엔진 (Web Speech) ═══════════════════ */
  const VOICE_CFG = {
    pickle:  {pitch:0.90, rate:1.02, tone:"진행 · 낮고 또렷"},
    gemini:  {pitch:1.06, rate:1.00, tone:"분석 · 또박"},
    cue:     {pitch:1.30, rate:1.12, tone:"리서치 · 빠름"},
    hark:    {pitch:0.78, rate:1.04, tone:"검증 · 낮고 무겁게"},
    chatgpt: {pitch:1.00, rate:0.96, tone:"구조 · 차분"},
    claude:  {pitch:1.14, rate:0.88, tone:"작가 · 느긋"},
    meta_muse:{pitch:1.20, rate:1.05, tone:"영상 · 밝고 경쾌"},
    keyring: {pitch:1.02, rate:1.00, tone:"신참 · 차분"}
  };
  const synthOK = (typeof window !== "undefined") && ("speechSynthesis" in window) && (typeof window.SpeechSynthesisUtterance === "function");
  let koVoices = [];

  function refreshVoices(){
    if(!synthOK) return;
    try{
      const all = window.speechSynthesis.getVoices() || [];
      koVoices = all.filter(v => /^ko/i.test(v.lang || "") || /korean|한국/i.test(v.name || ""));
    }catch(e){ koVoices = []; }
  }
  function pickVoice(id){
    if(!koVoices.length) refreshVoices();
    if(!koVoices.length) return null;
    const i = Math.max(0, AIS.indexOf(id));
    return koVoices[i % koVoices.length];
  }
  function splitChunks(text){
    const clean = String(text || "").replace(/\s+/g," ").trim();
    if(!clean) return [];
    const parts = clean.match(/[^.!?。？！\n]+[.!?。？！]?/g) || [clean];
    const out = []; let buf="";
    parts.forEach(p=>{
      const s = p.trim(); if(!s) return;
      if(buf && (buf+" "+s).length > 110){ out.push(buf); buf=s; }
      else buf = buf ? buf+" "+s : s;
    });
    if(buf) out.push(buf);
    return out;
  }
  function speakChunk(id, text, cfg){
    return new Promise(resolve=>{
      if(!synthOK || !state.voiceOn){ resolve("skip"); return; }
      const synth = window.speechSynthesis;
      const u = new window.SpeechSynthesisUtterance(text);
      u.lang = "ko-KR";
      const v = pickVoice(id);
      if(v){ u.voice = v; if(v.lang) u.lang = v.lang; }
      u.pitch = cfg.pitch; u.rate = cfg.rate; u.volume = 1;
      let done=false, started=false, silent=0;
      const began = Date.now();
      const finish = r => { if(done) return; done=true; clearInterval(watch); clearTimeout(hard); resolve((started||r==="canceled")?r:"empty"); };
      u.onstart = ()=>{ started = true; };
      u.onend = ()=> finish("ended");
      u.onerror = ev => { const code=(ev&&(ev.error||ev.name))||""; finish(/cancel|interrupt/i.test(code)?"canceled":"error"); };
      const watch = setInterval(()=>{
        if(done) return;
        if(synth.paused){ silent=0; return; }
        if(synth.speaking || synth.pending){ silent=0; started = started || synth.speaking; return; }
        silent++;
        if(Date.now()-began > 700 && silent >= 4) finish("ended");
      },120);
      const hard = setTimeout(()=>finish("ended"), 1500 + text.length*300);
      try{ synth.speak(u); if(synth.paused) synth.resume(); }catch(e){ finish("error"); }
    });
  }
  async function speakText(id, text, token, cutRec){
    if(!synthOK || !state.voiceOn) return;
    const cfg = VOICE_CFG[id] || {pitch:1, rate:1};
    const chunks = splitChunks(text);
    let i=0, emptyRuns=0, cancelRuns=0;
    while(i < chunks.length){
      if(token !== state.runToken || !state.voiceOn) return;
      if(cutRec && cutRec.fired) return;
      await waitIfPaused();
      if(token !== state.runToken || !state.voiceOn) return;
      if(cutRec && cutRec.fired) return;
      const res = await speakChunk(id, chunks[i], cfg);
      if(cutRec && cutRec.fired) return;
      if(res === "empty"){ emptyRuns++; if(emptyRuns>=3){ voiceUnavailable(); return; } i++; continue; }
      emptyRuns = 0;
      if(res === "canceled"){ cancelRuns++; if(cutRec && cutRec.fired) return; if(cancelRuns>4 && !state.paused) return; continue; }
      cancelRuns = 0; i++;
    }
  }
  function voiceUnavailable(){
    if(state.voiceWarned) return;
    state.voiceWarned = true;
    setVoice(false, true);
    toast("🔇 이 브라우저에서 목소리를 재생할 수 없습니다 · 글자로만 진행합니다");
  }
  function setVoice(on, quiet){
    state.voiceOn = !!on;
    LS.set(K_VOICE, state.voiceOn ? "1" : "0");
    const b = document.getElementById("voiceBtn");
    if(b){
      b.classList.toggle("on", state.voiceOn);
      b.innerHTML = state.voiceOn ? '🔊 <span class="lg">음성 </span>ON' : '🔇 <span class="lg">음성 </span>OFF';
    }
    if(!state.voiceOn && synthOK){ try{ window.speechSynthesis.cancel(); }catch(e){} }
    if(!quiet) toast(state.voiceOn ? "🔊 AI 목소리 ON" : "🔇 AI 목소리 OFF · 글자로만 진행");
  }
  function unlockVoice(){
    if(!synthOK || !state.voiceOn) return;
    try{
      const s = window.speechSynthesis;
      const u = new window.SpeechSynthesisUtterance(" ");
      u.lang="ko-KR"; u.volume=0; u.rate=2; s.speak(u);
      if(s.paused) s.resume();
    }catch(e){}
    SFX.unlock();
  }

  /* ── 정지 / 재개 ── */
  let pauseWaiters = [];
  function waitIfPaused(){ if(!state.paused) return Promise.resolve(); return new Promise(res=>pauseWaiters.push(res)); }
  function releasePause(){ const ws=pauseWaiters; pauseWaiters=[]; ws.forEach(fn=>{ try{ fn(); }catch(e){} }); }
  async function psleep(ms){ await waitIfPaused(); if(state.paused) return; await sleep(ms); }

  function quietAll(){
    stopInterjectMic(true);
    const first = !state.paused;
    if(first){ state.paused = true; state.pausedAt = Date.now(); }
    Object.keys(tileRefs).forEach(id=>{
      const r = tileRefs[id]; if(!r) return;
      r.tile.classList.add("quiet");
      r.tile.classList.remove("speaking");
      r.state.classList.remove("s-speaking","s-ready","s-done");
      r.state.classList.add("s-quiet");
      r.state.textContent = "조용";
      if(r.vstate) r.vstate.textContent = "조용";
    });
    document.body.classList.add("is-quiet");
    syncAvatarMedia();   // 모두 조용 → 피클 영상도 멈춘다
    if(synthOK){ try{ window.speechSynthesis.cancel(); }catch(e){} }
    if(first) SFX.shush();
    setLive("조용히", "quiet");
    if(first){ addSystem("🤫 다들 조용! — 전원 음소거 · 진행 정지"); toast("🤫 다들 조용! · 모두 멈췄습니다"); }
  }
  function restoreTileState(id){
    const r = tileRefs[id]; if(!r) return;
    r.tile.classList.remove("quiet");
    r.state.classList.remove("s-quiet");
    if(state.phase === "roles") setTileState(id,"assigned","배정");
    else if(state.agenda) setTileState(id,"ready","자료 준비");
    else setTileState(id,"","대기");
  }
  function resumeAll(){
    if(!state.paused){ toast("지금은 멈춰 있지 않습니다"); return; }
    state.paused = false;
    document.body.classList.remove("is-quiet");
    Object.keys(tileRefs).forEach(restoreTileState);
    if(state.activeSpeaker && tileRefs[state.activeSpeaker]) setTileState(state.activeSpeaker,"speaking","발언 중");
    syncAvatarMedia();
    if(state.pausedAt){ state.pausedMs += Date.now()-state.pausedAt; state.pausedAt = 0; }
    if(state.agenda) startClock(state.pausedMs);
    setLive(state.phase==="roles" ? "역할 분담" : "회의 중", "");
    addSystem("▶️ 다시 계속 — 이어갑니다");
    SFX.ding();
    if(synthOK && state.voiceOn){ try{ window.speechSynthesis.resume(); }catch(e){} }
    releasePause();
    toast("▶️ 다시 계속");
  }

  /* ═══════════════════ 음성 인식 (오너 코멘트) ═══════════════════ */
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const STOP_WORDS = ["다들 조용","조용히 해","조용","그만","멈춰","멈춰요","스톱","중지"];
  let recog=null, listening=false, micWant=false, micBase="", micFinal="";
  let iRecog=null, iListening=false, iWant=false, iBase="", iFinal="";

  function isStopPhrase(t){
    const s = String(t||"").replace(/\s+/g," ").trim();
    if(!s) return false;
    return STOP_WORDS.some(w=>s.indexOf(w)>=0);
  }
  function setMicUI(on){
    const b=document.getElementById("planMic"); const f=document.getElementById("planTopic");
    if(b){ b.classList.toggle("on",on); b.textContent = on?"■":"🎤"; }
    if(f) f.classList.toggle("listening",on);
  }
  function setIMicUI(on){
    const b=document.getElementById("interjectMic");
    if(b){ b.classList.toggle("on",on); b.title = on?"듣는 중 · 누르면 멈춤":"말로 코멘트"; }
  }
  function beginRecognition(){
    if(!SR || !micWant || listening) return;
    try{
      recog = new SR();
      recog.lang="ko-KR"; recog.continuous=true; recog.interimResults=true; recog.maxAlternatives=1;
      recog.onstart = ()=>{ listening=true; setMicUI(true); };
      recog.onresult = ev=>{
        let fin="", interim="";
        for(let i=ev.resultIndex;i<ev.results.length;i++){
          const r=ev.results[i];
          if(r.isFinal) fin += (r[0]&&r[0].transcript)||"";
          else interim += (r[0]&&r[0].transcript)||"";
        }
        const heard=(fin||interim).trim();
        if(heard && isStopPhrase(heard)){ stopListening(true); quietAll(); toast('🤫 "'+heard+'" 감지 — 전체 정지'); return; }
        if(fin) micFinal=(micFinal+" "+fin).replace(/\s+/g," ").trim();
        const shown=(micFinal+(interim?" "+interim:"")).trim();
        const input=document.getElementById("planTopic");
        if(input && shown) input.value = micBase ? micBase+" "+shown : shown;
      };
      recog.onerror = ev=>{
        const e=ev&&ev.error;
        if(e==="not-allowed"||e==="service-not-allowed") toast("🎤 마이크 권한이 필요합니다");
        else if(e==="no-speech") toast("🎤 소리가 들리지 않았습니다");
        else if(e!=="aborted") toast("🎤 음성 인식 오류: "+e);
      };
      recog.onend = ()=>{ listening=false; setMicUI(false); recog=null; if(micWant) setTimeout(beginRecognition,260); };
      recog.start();
    }catch(err){ listening=false; setMicUI(false); toast("🎤 음성 입력을 시작하지 못했습니다"); }
  }
  function startListening(){
    if(!SR){ toast("이 브라우저는 음성 인식을 지원하지 않습니다"); return; }
    if(micWant){ toast("🎤 이미 듣고 있습니다"); return; }
    micWant=true; micBase=($("#planTopic").value||"").trim(); micFinal="";
    toast("🎤 듣는 중 … 회의 주제를 말해 주세요");
    beginRecognition();
  }
  function stopListening(silent){
    micWant=false;
    if(recog){ try{ recog.onend=null; recog.abort(); }catch(e){ try{ recog.stop(); }catch(e2){} } recog=null; }
    listening=false; setMicUI(false);
    if(!silent) toast("🎤 음성 입력을 멈췄습니다");
  }
  function beginInterjectMic(){
    if(!SR){ toast("이 브라우저는 음성 인식을 지원하지 않습니다 · 직접 입력해 주세요"); return; }
    if(iWant){ stopInterjectMic(); return; }
    stopListening(true);
    iWant=true; iListening=false;
    iBase=(document.getElementById("interjectInput").value||"").trim(); iFinal="";
    try{ if(synthOK && window.speechSynthesis.speaking && !window.speechSynthesis.paused) window.speechSynthesis.pause(); }catch(e){}
    (function start(){
      if(!iWant) return;
      try{
        iRecog = new SR();
        iRecog.lang="ko-KR"; iRecog.continuous=true; iRecog.interimResults=true; iRecog.maxAlternatives=1;
        iRecog.onstart = ()=>{ iListening=true; setIMicUI(true); };
        iRecog.onresult = ev=>{
          let fin="", interim="";
          for(let i=ev.resultIndex;i<ev.results.length;i++){
            const r=ev.results[i];
            if(r.isFinal) fin += (r[0]&&r[0].transcript)||"";
            else interim += (r[0]&&r[0].transcript)||"";
          }
          if(fin) iFinal=(iFinal+" "+fin).replace(/\s+/g," ").trim();
          const shown=(iFinal+(interim?" "+interim:"")).trim();
          const input=document.getElementById("interjectInput");
          if(input && shown) input.value = iBase ? iBase+" "+shown : shown;
        };
        iRecog.onerror = ev=>{
          const e=ev&&ev.error;
          if(e==="not-allowed"||e==="service-not-allowed") toast("🎤 마이크 권한이 필요합니다");
          else if(e!=="aborted"&&e!=="no-speech") toast("🎤 음성 인식 오류: "+e);
        };
        iRecog.onend = ()=>{ iListening=false; setIMicUI(false); iRecog=null; if(iWant) setTimeout(start,260); };
        iRecog.start();
        toast("🎤 듣는 중 … 말한 뒤 💬 코멘트를 누르세요");
      }catch(err){ iWant=false; iListening=false; setIMicUI(false); toast("🎤 음성 입력을 시작하지 못했습니다"); }
    })();
  }
  function stopInterjectMic(silent){
    iWant=false;
    if(iRecog){ try{ iRecog.onend=null; iRecog.abort(); }catch(e){ try{ iRecog.stop(); }catch(e2){} } iRecog=null; }
    iListening=false; setIMicUI(false);
    try{ if(synthOK && state.voiceOn && window.speechSynthesis.paused) window.speechSynthesis.resume(); }catch(e){}
    if(!silent) toast("🎤 코멘트 입력을 멈췄습니다");
  }

  /* ═══════════════════ 타일 ═══════════════════
     v4.5.1 — iOS Safari 깜빡임·타일 소실의 근본 원인은 "무대를 통째로 다시 그리는 것"이었다.
     · buildTiles 마다 stage.innerHTML = "" → <img>/<video> 가 DOM 에서 떨어졌다 붙고,
       아이폰은 그 순간 디코딩을 버려 빈 타일(검은 화면)로 남는 일이 있었다.
     · 발언이 바뀔 때마다 본문(.bubble)을 innerHTML 로 갈아 끼워 글자·배경이 한 프레임 비었다.
     그래서 v4.5.1 은 **타일 DOM 은 사람마다 최초 1회만 만들고(pool), 이후에는 절대 지우지 않는다.**
     발언 전환은 클래스 토글 + 텍스트 노드 갱신만 한다. */
  const stage = $("#stage");
  const tileRefs = {};      // 지금 회의에 올라와 있는 타일
  const tilePool = {};      // 만들어진 모든 타일(회의가 바뀌어도 파괴하지 않는다)

  function makeTile(p){
    const t = el("div","tile");
    t.dataset.id = p.id;

    const head = el("div","thead");
    const av = el("div","avatar");
    faceInto(av, p);
    av.style.borderColor = p.color + "55";
    const who = el("div","who");
    who.append(el("div","nm", p.name), el("div","rl", p.role));
    const st = el("div","state","대기");
    head.append(av, who, st);

    /* 본문: 태그·역할·요약 세 노드를 처음에 만들고, 이후에는 textContent 만 바꾼다 */
    const wrap = el("div","stagewrap");
    const bubble = el("div","bubble empty");
    const mtag = el("span","mtag"); mtag.style.display = "none";
    const mrole = el("span","mrole"); mrole.style.display = "none";
    const msum = el("span","msum","안건을 고르면 준비해 온 자료가 여기에 열립니다.");
    bubble.append(mtag, mrole, msum);
    wrap.append(bubble);

    const foot = el("div","tfoot");
    /* 웨이브: 발언 중이 아니어도 자리를 지킨다(display 를 켜고 끄면 옆 버튼이 튄다).
       opacity 만 바꾸고 막대는 정적 높이다 — 계속 도는 크기 애니메이션은 iOS 리페인트 원인. */
    const wave = el("div","wave");
    for(let i=0;i<7;i++) wave.append(el("i"));
    const roleTag = el("div","who-role");
    const mic = el("span","mic","🔇");
    roleTag.append(mic);
    const matbtn = el("button","matbtn ghost","자료 펼치기");
    matbtn.addEventListener("click", ()=> openMat(p.id));
    foot.append(wave, roleTag, matbtn);

    const qv = el("div","qveil");

    /* v4.2 화상 6분할용 얼굴 — v4.5 부터는 타일 전체를 미디어가 꽉 채우는 풀블리드 */
    const vs = el("div","vstage");
    const vbob = el("div","vbob");
    const media = faceInto(vbob, p, {video:true});   // 화상 6분할 타일 전체를 채우는 얼굴 — 피클만 움직인다
    const vov = el("div","vov");       // 하단 그라데이션 + 이름/상태
    const vnm = el("div","vnm", p.name);
    const vmeta = el("div","vmeta");
    const vst = el("span","vstate","대기");
    const vw = el("div","vw");
    for(let i=0;i<5;i++) vw.append(el("i"));
    vmeta.append(vst, vw);
    vov.append(vnm, vmeta);
    vs.append(vbob, vov);
    const vbadge = el("div","vbadge","발언 중");
    const react = el("div","react");

    t.append(head, wrap, foot, vs, vbadge, react, qv);
    const refs = {id:p.id, tile:t, state:st, bubble, mtag, mrole, msum, matbtn, wave, mic,
                  vstate:vst, vbob, vid:media && media.video, vids:(media && media.vids) || {},
                  poster:media && media.poster, mood:"", moodTimer:null, stateLbl:"대기",
                  react, reactT:null};
    return refs;
  }

  /* 무대에 올릴 타일을 맞춘다 — 새로 만들지 않고, 있는 타일을 옮기기만 한다 */
  function buildTiles(ids){
    const list = (ids && ids.length ? ids : AIS).map(id=> byId(id)).filter(Boolean);
    const want = list.map(p=> p.id);
    Object.keys(tileRefs).forEach(id=>{
      if(want.indexOf(id) >= 0) return;
      const t = tileRefs[id].tile;
      if(t.parentNode === stage) stage.removeChild(t);   // 잠시 내려 둠(파괴 아님)
      delete tileRefs[id];
    });
    want.forEach(id=>{
      if(!tilePool[id]) tilePool[id] = makeTile(byId(id));
      tileRefs[id] = tilePool[id];
    });
    const cur = [].map.call(stage.children, n=> n.dataset.id);
    if(cur.join("|") !== want.join("|")){
      want.forEach(id=> stage.appendChild(tileRefs[id].tile));   // 순서만 다시 맞춘다(이동)
    }
    Object.keys(tileRefs).forEach(id=>{
      const r = tileRefs[id];
      if(r.tile.parentNode !== stage) stage.appendChild(r.tile);
    });
    syncAvatarMedia();
    watchdogMedia(150);
  }

  function setTileState(id, kind, label){
    const r = tileRefs[id]; if(!r) return;
    if(kind === "speaking") setTileMood(id, "");   // v4.6.2 — 발언 차례가 오면 즉시 잠에서 깬다
    r.tile.classList.remove("speaking","assigned");
    r.state.classList.remove("s-speaking","s-ready","s-done","s-quiet");
    if(kind==="speaking"){ r.tile.classList.add("speaking"); r.state.classList.add("s-speaking"); }
    if(kind==="ready"){ r.tile.classList.add("matready"); r.state.classList.add("s-ready"); }
    if(kind==="assigned"){ r.tile.classList.add("assigned"); r.state.classList.add("s-done"); }
    if(kind==="quiet"){ r.state.classList.add("s-quiet"); }
    r.stateLbl = label || (kind==="speaking"?"발언 중":kind==="ready"?"자료 준비":kind==="assigned"?"배정":kind==="quiet"?"조용":"대기");
    r.state.textContent = (r.mood && kind !== "speaking") ? MOOD_TEXT[r.mood] : r.stateLbl;
    if(r.vstate) r.vstate.textContent = videoLabel(r);
    syncAvatarMedia();   // 지금 켜야 하는 겹(speaking / sleepy)만 재생하고 나머지는 멈춘다
  }
  /* ═════ v4.6.2 — '듣는 중의 피클' 상태 영상 (sleepy / phone) ═════
     피클이 듣기만 하는 동안(다른 AI 가 2명 넘게 연달아 말할 때) 눈을 감고 조는 모습(sleepy)과
     회의 중 몰래 폰을 보다 들키는 모습(phone) 중 하나가 랜덤으로 켜지고,
     자기 발언 차례가 오면 setTileState(speaking) 가 즉시 깨운다.
     영상은 상태마다 따로 쌓여 있으므로 여기서는 클래스 한 개와 문구만 바꾼다 — src 교체 없음. */
  const MOODS = ["sleepy", "phone"];
  const MOOD_TEXT  = {sleepy:"😴 조는 중",   phone:"📱 딴짓"};          // 글로 보기 카드 헤더 배지
  const MOOD_LABEL = {sleepy:"😴 살짝 조는 중", phone:"📱 딴짓하다 걸림"};   // 화상 타일 하단 상태
  /* ═════ v4.7 — 졸기·딴짓은 '어쩌다 한 번'만 (성진님: "어쩌다 졸고 딴짓하는 거지 계속 반복하니까 별로네") ═════
     v4.6.2~4.6.3 은 피클 차례 없이 다른 AI 가 2명만 말하면 매 라운드 무조건 켰다 — 4라운드를 도는 동안
     계속 반복돼 '회의'보다 '딴짓하는 비서'가 눈에 걸렸다. 이제는 한 회의 세션(입장~종료, 안건을 새로 열 때 리셋)
     통틀어 **최대 2회**, 그것도 피클 차례 없이 **다른 AI 3명이 지나간 뒤**부터 22% 확률로만 켠다.
     한 번 켜면 그 라운드와 다음 라운드는 건너뛴다(쿨다운 1라운드).
     `__mr4.setTileMood('pickle','sleepy'|'phone'|'')` 는 그대로라 테스트·시연은 100% 재현된다. */
  const MOOD_EVENT = {
    maxPerSession: 2,      // 한 세션(입장~종료) 총 발동 상한
    minRest: 3,            // 피클 차례 없이 다른 AI 가 3명 넘게 말한 뒤에만 후보
    prob: 0.22,            // 후보가 될 때마다 22% — 대부분의 라운드는 그냥 지나간다
    cooldownRounds: 1,     // 발동한 라운드 +1 라운드는 쉰다(연달아 나오지 않게)
    debugProb: null        // 검증용: 숫자를 넣으면 그 확률로 고정(기본 null = prob)
  };
  function resetMoodSession(){
    state.moodEvents = 0;
    state.moodRound = 0;
    state.moodLog = [];
  }
  /* 라운드 중 다른 AI 가 말할 때마다 불린다. 조건을 모두 통과한 '가끔'에만 sleepy/phone 을 켠다 */
  function moodGatePass(roundNo, rest, rand){
    if(rest < MOOD_EVENT.minRest) return false;                                  // 다른 AI 3명이 지나간 뒤부터
    if(state.moodEvents >= MOOD_EVENT.maxPerSession) return false;              // 세션 상한(최대 2회)
    if(state.moodRound && roundNo - state.moodRound <= MOOD_EVENT.cooldownRounds) return false;   // 쿨다운
    const p = (MOOD_EVENT.debugProb == null) ? MOOD_EVENT.prob : MOOD_EVENT.debugProb;
    return rand < p;                                                            // 22% — 대부분은 그냥 지나간다
  }
  function maybeMoodEvent(roundNo, rest){
    const r = tileRefs.pickle;
    if(!r || !r.vids) return false;
    if(r.mood) return false;                                     // 이미 켜져 있으면 그대로 둔다
    if(!moodGatePass(roundNo, rest, Math.random())) return false;
    const m = MOODS[Math.floor(Math.random() * MOODS.length)];
    if(!setTileMood("pickle", m)) return false;
    state.moodEvents++;
    state.moodRound = roundNo;
    state.moodLog.push({round:roundNo, rest:rest, mood:m, at:Date.now()});
    if(state.moodLog.length > 40) state.moodLog.shift();
    return true;
  }
  function setTileMood(id, mood){
    const r = tileRefs[id]; if(!r) return false;
    mood = (MOODS.indexOf(mood) >= 0 && r.vids && r.vids[mood]) ? mood : "";
    /* 말하는 중에는 다른 상태를 켜지 않는다 — 깨어 있는 쪽이 이긴다 */
    if(mood && r.tile.classList.contains("speaking")) mood = "";
    const was = r.mood || "";
    /* v4.6.3 — 한 번만 트는 영상(sleepy·phone)은 이 상태에 **새로 들어올 때만** 처음부터 다시 튼다.
       끝까지 틀어 done 이 찍힌 영상이니, 재진입이 아니면 되감지 않는다(phone 은 끝나면 mood 가 비어 다시 들어올 때 새로 튼다). */
    if(mood && mood !== was && VIDEO_ONCE[mood] && r.vids[mood]){
      const v = r.vids[mood];
      delete v.dataset.done;
      try{ v.currentTime = 0; }catch(e){}
    }
    r.mood = mood;
    MOODS.forEach(m=> r.tile.classList.toggle(m, mood === m));
    if(r.state) r.state.textContent = mood ? MOOD_TEXT[mood] : r.stateLbl;
    if(r.vstate) r.vstate.textContent = videoLabel(r);
    /* v4.7.1 — 딴짓(phone)은 영상이 도는 경우엔 ended 가 먼저 되돌리지만, 글로 보기·영상 차단·버퍼링처럼
       clips 이 안 도는 경우에는 배지가 '📱 딴짓'으로 남는다. 클립(2.21초)보다 넉넉한 3.5초 뒤 한 번 더
       되돌려, 어느 화면에서든 "한 번만 하고 경청" 이 지켜지게 한다(이미 경청이면 아무 일도 없다). */
    if(r.moodTimer){ clearTimeout(r.moodTimer); r.moodTimer = null; }
    if(mood === "phone"){
      r.moodTimer = setTimeout(()=>{ r.moodTimer = null; backToListening(id); }, 3500);
    }
    syncAvatarMedia();
    return !!mood;
  }
  /* 화상 6분할 타일의 상태 문구 — 화상통화처럼 "듣는 중 / 발언 중 / 조는 중"으로 보여 준다 */
  function videoLabel(r){
    if(!r) return "대기";
    if(r.tile.classList.contains("quiet")) return "조용";
    if(r.tile.classList.contains("speaking")) return "발언 중";
    if(r.mood && MOOD_LABEL[r.mood]) return MOOD_LABEL[r.mood];
    if(state.phase === "roles") return "배정";
    if(!state.agenda) return "대기";
    return "듣는 중";
  }

  function renderBubble(id, tag, text, opts){
    const r = tileRefs[id]; if(!r) return;
    opts = opts || {};
    /* 노드를 새로 만들지 않는다 — 글자만 바꾼다(innerHTML 교체는 iOS 에서 한 프레임 비어 보인다) */
    r.bubble.classList.remove("empty");
    if(r.mtag){ r.mtag.textContent = tag || ""; r.mtag.style.display = tag ? "" : "none"; }
    if(r.mrole){ r.mrole.textContent = opts.role || ""; r.mrole.style.display = opts.role ? "" : "none"; }
    const next = text || "";
    if(r.msum.textContent !== next){ r.msum.textContent = next; r.bubble.scrollTop = 0; }
    if(opts.showBtn) r.matbtn.classList.remove("ghost");
  }
  /* 본문을 비운다(자료 없는 타일) — 노드는 그대로 두고 문구만 바꾼다 */
  function clearBubble(id, msg){
    const r = tileRefs[id]; if(!r) return;
    if(r.mtag){ r.mtag.textContent = ""; r.mtag.style.display = "none"; }
    if(r.mrole){ r.mrole.textContent = ""; r.mrole.style.display = "none"; }
    r.msum.textContent = msg || "";
    r.bubble.classList.add("empty");
    r.bubble.scrollTop = 0;
  }

  /* ═══════════════════ 화상 6분할 ↔ 글로 보기 (v4.2) ═══════════════════ */
  function setView(v, opts){
    opts = opts || {};
    v = (v === "video") ? "video" : "text";
    if(v === "video" && !state.agenda){
      if(!opts.silent) toast("안건을 먼저 골라 주세요 · 화상 화면은 회의 중에 열립니다");
      v = "text";
    }
    state.view = v;
    LS.set(K_VIEW, v);
    document.body.classList.toggle("view-video", v === "video");
    const vb = document.getElementById("viewVideoBtn");
    const tb = document.getElementById("viewTextBtn");
    if(vb) vb.classList.toggle("on", v === "video");
    if(tb) tb.classList.toggle("on", v === "text");
    if(v === "video"){
      if(state.lastLine) setSubtitle(state.lastLine.id, state.lastLine.tag, state.lastLine.text);
      else setSubtitle(null, "", "", true);
      window.scrollTo(0,0);
      startMotionVideos();          // v4.4 — 화상 화면에 들어올 때만 영상을 내려받아 재생
    } else {
      stopMotionVideos();           // 글로 보기·다른 화면에서는 영상을 멈춰 배터리·CPU를 아낀다
      if(state.activeSpeaker) setTimeout(()=> focusTile(state.activeSpeaker), 60);
    }
    if(!opts.silent) toast(v === "video" ? "🎥 화상 6분할 — 캐릭터 화면으로 봅니다" : "📝 글로 보기 — 1열 큰 글씨로 봅니다");
    return v;
  }
  function setSubtitle(id, tag, text, empty){
    const who = document.getElementById("vsWho");
    const tg = document.getElementById("vsTag");
    const tx = document.getElementById("vsTx");
    const box = document.getElementById("vsub");
    if(!who || !tx) return;
    const p = id ? byId(id) : null;
    who.textContent = p ? (p.emoji ? p.emoji + " " : "") + p.name : "🎙 회의실";
    who.style.color = p && p.color ? p.color : "";
    if(tg){ tg.textContent = tag || ""; tg.style.display = tag ? "" : "none"; }
    tx.textContent = text || (empty ? "발언이 시작되면 여기에 한 줄로 나옵니다." : "");
    if(box) box.classList.toggle("empty", !text);
  }
  /* 발언자가 말할 때 옆 캐릭터에 리액션 배지를 띄운다 (레이아웃 영향 없음 — absolute) */
  function flashReactions(speakerId){
    const others = partList().filter(id=> id !== speakerId && tileRefs[id]);
    if(!others.length) return;
    shuffleOrder(others);
    const picks = others.slice(0, 1 + Math.floor(Math.random() * 2));
    picks.forEach(id=>{
      const r = tileRefs[id]; if(!r || !r.react) return;
      const emoji = REACTIONS[Math.floor(Math.random() * REACTIONS.length)];
      r.react.textContent = emoji;
      r.react.classList.add("on");
      clearTimeout(r.reactT);
      r.reactT = setTimeout(()=> r.react.classList.remove("on"), 1500 + Math.random() * 1100);
    });
  }
  /* 발언 순서 섞기 — 고정 1~6번 순서를 쓰지 않는다 (같은 라운드를 다시 틀어도 매번 달라진다) */
  function shuffleOrder(src){
    const a = src.slice();
    if(a.length < 2) return a;
    for(let tries=0; tries<4; tries++){
      for(let i=a.length-1; i>0; i--){
        const j = Math.floor(Math.random() * (i + 1));
        const t = a[i]; a[i] = a[j]; a[j] = t;
      }
      let same = true;
      for(let i=0;i<a.length;i++){ if(a[i] !== src[i]){ same = false; break; } }
      if(!same) return a;
    }
    return a;
  }

  /* ═══════════════════ 기록 (논의 / 회의록) ═══════════════════ */
  const talkList = $("#talkList"), talkCountEl = $("#talkCount");
  const minList = $("#minList"), minCountEl = $("#minCount");
  let talkN = 0, minN = 0;

  function clearTalkEmpty(){ const e=document.getElementById("talkEmpty"); if(e) e.remove(); }
  function clearMinEmpty(){ const e=document.getElementById("minEmpty"); if(e) e.remove(); }

  function addTalk(id, kind, text, opts){
    opts = opts || {};
    clearTalkEmpty();
    const li = el("li","talk-item" + (kind==="sys"?" sys":"") + (kind==="owner"?" owner":""));
    const tm = el("div","tt2", nowHM());
    const bd = el("div","bd");
    const who = el("div","tw");
    const p = byId(id) || {name:"시스템", emoji:"•"};
    const nm = el("span","", (p.emoji?p.emoji+" ":"") + p.name);
    if(p.color) nm.style.color = p.color;
    who.append(nm);
    if(kind==="read") who.append(el("span","pill","준비 자료"));
    if(kind==="round") who.append(el("span","pill", (opts.round ? opts.round + "R · " : "") + (opts.tag || "발언")));
    if(kind==="react") who.append(el("span","pill","코멘트 반영"));
    if(kind==="owner") who.append(el("span","pill","오너"));
    if(opts.to){
      const t = byId(opts.to);
      who.append(el("span","to","→ " + (t?t.name:opts.to)));
    }
    const tx = el("div","tx", text);
    bd.append(who, tx);
    li.append(tm, bd);
    talkList.append(li);
    talkN++; talkCountEl.textContent = talkN + "건";
    talkList.scrollTop = talkList.scrollHeight;
  }

  function addSystem(text){
    clearMinEmpty();
    const li = el("li","min-item sys");
    const tm = el("div","tm", nowHM());
    const bd = el("div","body");
    bd.append(el("div","tx", text));
    li.append(tm, bd);
    minList.append(li);
    minN++; minCountEl.textContent = minN + "건";
    minList.scrollTop = minList.scrollHeight;
  }

  /* ═══════════════════ 단계·상태 표시 ═══════════════════ */
  function setStep(idx){
    document.querySelectorAll(".step").forEach(s=>{
      const n = Number(s.dataset.step);
      s.classList.toggle("on", n === idx);
      s.classList.toggle("done", n < idx);
    });
  }
  function setStageHead(tag, descr, right, alt){
    const t = document.getElementById("roundTag");
    const d = document.getElementById("roundDescr");
    const k = document.getElementById("talkers");
    if(t){ t.textContent = tag; t.classList.toggle("r2", !!alt); }
    if(d) d.textContent = descr;
    if(k) k.textContent = right;
  }
  function setLive(text, kind){
    const lt = document.getElementById("liveTxt");
    if(lt) lt.textContent = text;
    const b = document.getElementById("liveBadge");
    if(b){
      b.style.borderColor = kind==="done" ? "rgba(46,224,106,.4)" : kind==="quiet" ? "rgba(242,84,91,.55)" : kind==="owner" ? "rgba(245,192,74,.55)" : "";
      b.style.background = kind==="quiet" ? "rgba(242,84,91,.10)" : kind==="owner" ? "rgba(245,192,74,.10)" : "";
    }
    if(lt) lt.style.color = kind==="quiet" ? "#ffb3b7" : kind==="owner" ? "#ffe0a2" : "";
  }
  function startClock(offsetMs){
    state.startedAt = Date.now() - (offsetMs||0);
    clearInterval(state.timerId);
    state.timerId = setInterval(()=>{
      if(state.paused) return;
      const s = Math.floor((Date.now()-state.startedAt)/1000);
      const c = document.getElementById("clock");
      if(c) c.textContent = pad(Math.floor(s/60))+":"+pad(s%60);
    },1000);
    const s0 = Math.floor((offsetMs||0)/1000);
    const c = document.getElementById("clock");
    if(c) c.textContent = pad(Math.floor(s0/60))+":"+pad(s0%60);
  }
  function toast(msg){
    const t = document.getElementById("toast");
    if(!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(()=> t.classList.remove("show"), 2800);
  }
  let toastTimer = null;

  /* ═══════════════════ 발언(낭독) ═══════════════════ */
  async function speakLine(id, text, opts){
    opts = opts || {};
    const token = state.runToken;
    await waitIfPaused();
    if(token !== state.runToken) return;
    const cutRec = {fired:false, fire:null};
    state.activeCut = cutRec;
    const cutP = new Promise(res=>{ cutRec.fire = ()=>{ if(!cutRec.fired){ cutRec.fired = true; res(); } }; });
    state.activeSpeaker = id;
    setTileState(id, "speaking", opts.label || "낭독 중");
    state.lastLine = {id:id, tag:opts.sub || "", text:text || ""};
    setSubtitle(id, opts.sub || "", text || "");
    focusTile(id);   // 📝 글로 보기에서만 발언 카드로 부드럽게 이동 (화상 모드는 scroll 0)
    flashReactions(id);
    const talking = (state.voiceOn && text) ? speakText(id, text, token, cutRec) : Promise.resolve();
    await Promise.race([talking, cutP]);
    state.activeCut = null;
    if(cutRec.fired){
      state.activeSpeaker = null;
      if(synthOK){ try{ window.speechSynthesis.cancel(); }catch(e){} }
      return;
    }
    state.activeSpeaker = null;
    if(token === state.runToken) await psleep(180/state.speed);
  }

  /* ═══════════════════ 준비실 ═══════════════════ */
  function readyAgendas(){ return (LIB.agendas||[]).filter(a=>a.ready && a.panels); }
  function localPlans(){
    try{ return JSON.parse(LS.get(K_PLAN)||"[]") || []; }catch(e){ return []; }
  }
  function saveLocalPlans(list){ LS.set(K_PLAN, JSON.stringify(list.slice(-30))); }
  function dstr(d){ return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate()); }
  function dayOffset(n){ const d=new Date(); d.setDate(d.getDate()+n); return dstr(d); }
  function prettyDate(iso){
    if(!iso) return "날짜 미정";
    const s = String(iso).slice(0,10);
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if(!m) return String(iso);
    const label = s === dayOffset(0) ? "오늘" : s === dayOffset(1) ? "내일" : s === dayOffset(2) ? "모레" : "";
    return (+m[2]) + "/" + (+m[3]) + (label ? " (" + label + ")" : "");
  }
  function plannedAgendas(){
    const out = [];
    (LIB.planned||[]).forEach(p=> out.push({topic:p.topic, date:p.date, by:p.by||"", note:p.note||"", sample:true}));
    localPlans().forEach(p=>{
      if(out.some(o=>norm(o.topic) === norm(p.topic))) return;
      out.push({topic:p.topic, date:p.date, by:p.by||"오너 예약", note:p.note||"", local:true});
    });
    out.sort((a,b)=> String(a.date||"").localeCompare(String(b.date||"")));
    return out;
  }
  function roundTotal(a){
    if(!a) return 1;
    if(a.rounds && a.rounds.length) return 1 + a.rounds.length;
    const hasReb = Object.keys(a.panels||{}).some(k=> a.panels[k] && a.panels[k].rebuttal && a.panels[k].rebuttal.text);
    return hasReb ? 2 : 1;
  }
  function findReadyByTopic(topic){
    const n = norm(topic);
    if(!n) return null;
    return readyAgendas().find(a => norm(a.title) === n || norm(a.title).indexOf(n) >= 0 || n.indexOf(norm(a.title)) >= 0) || null;
  }

  function renderPrep(){
    const list = document.getElementById("agList");
    const ready = readyAgendas();
    list.innerHTML = "";
    if(!ready.length){
      list.append(el("div","qempty","아직 ✅ 준비 완료 안건이 없습니다. ＋ 안건 예약으로 다음 회의 주제를 정해 두세요."));
    }
    ready.forEach(a=>{
      const b = el("button","agcard" + (state.agenda && state.agenda.id === a.id ? " active" : ""));
      b.dataset.id = a.id;
      const cnt = a.panels ? Object.keys(a.panels).filter(k=>a.panels[k]).length : 0;
      const top = el("div","agtop");
      top.append(el("span","tg", a.tag || "안건"));
      top.append(el("span","agst","✅ 준비 완료"));
      b.append(top);
      b.append(el("div","tt", a.title));
      b.append(el("div","bf", a.brief || ""));
      const mt = el("div","mt");
      const m1 = el("span"); m1.innerHTML = "자료 <b>"+cnt+"/6</b>";
      mt.append(m1);
      mt.append(el("span","rd", "· 🎙 " + roundTotal(a) + "라운드"));
      if(a.preparedAt) mt.append(el("span","", "· " + a.preparedAt));
      b.append(mt);
      b.addEventListener("click", ()=> openAgenda(a.id));
      list.append(b);
    });
    renderPlanList();
    const cntEl = document.getElementById("readyCnt");
    if(cntEl) cntEl.textContent = "✅ " + ready.length;
    const wEl = document.getElementById("waitCnt");
    if(wEl) wEl.textContent = "⏳ " + plannedAgendas().length;
  }

  function renderPlanList(){
    const box = document.getElementById("planList");
    if(!box) return;
    const plan = plannedAgendas();
    box.innerHTML = "";
    box.append(el("div","wt","⏳ 준비 중 (대기) — 자료가 모이면 ✅로 바뀝니다"));
    if(!plan.length){
      box.append(el("div","qempty","예약된 안건이 없습니다 — ＋ 안건 예약으로 '내일 이 주제로 회의'를 정해 두세요."));
      return;
    }
    plan.forEach(p=>{
      const card = el("div","agcard wcard");
      const top = el("div","agtop");
      top.append(el("span","tg","⏳ 준비 중"));
      if(p.sample) top.append(el("span","agst smp","예시"));
      card.append(top);
      card.append(el("div","tt", p.topic));
      card.append(el("div","bf", "예정 " + prettyDate(p.date) + (p.by ? " · " + p.by : "")));
      if(p.note) card.append(el("div","note2", p.note));
      const row = el("div","wrow");
      const cp = el("button","qb","📋 피클에게 자료 요청문 복사");
      cp.addEventListener("click", e=>{ e.stopPropagation(); copyText(requestText(p.topic, p.date)); });
      row.append(cp);
      if(p.local){
        const x = el("button","qx","✕");
        x.title = "예약 취소";
        x.addEventListener("click", e=>{
          e.stopPropagation();
          saveLocalPlans(localPlans().filter(v=>norm(v.topic) !== norm(p.topic)));
          renderPrep(); toast("예약을 취소했습니다");
        });
        row.append(x);
      }
      card.append(row);
      card.addEventListener("click", ()=>{
        toast("⏳ 아직 자료가 준비되지 않았습니다 · 피클이 6인 자료를 모으면 ✅로 바뀝니다");
      });
      box.append(card);
    });
  }

  function requestText(topic, date){
    return [
      "[회의 안건 예약] 다크진 AI 비서실 · 6분할 회의실",
      "",
      "예정일: " + (date || "미정") + (date ? " (" + prettyDate(date) + ")" : ""),
      "주제: " + topic,
      "요청: 오너 darkjin / " + nowStamp(),
      "",
      "피클, 이 주제로 6분할 회의실 v4.1 사전 자료를 준비해 주세요.",
      "- 6인(피클·Gemini·Cue·Hark·ChatGPT·Claude)이 서로 겹치지 않는 사전 조사 자료를 각각 만들 것",
      "- 각 AI 자료: 핵심 요약 1~2문장 / 근거·데이터 2~3개 / 우려·반박 1개 / 제안 1개 / 자료 출처 한 줄",
      "- 확인 가능한 근거와 추정을 구분해서 적을 것",
      "- 2라운드 정면 반박 · 3라운드 대안·절충 · 4라운드 최종 정리까지 서로 물고 물리는 발언을 rounds 에 적을 것",
      "- 결론 후보 2~3개와 후보별 6인 역할 분담을 함께 만들 것",
      "- 다 모이면 work/meeting-room/v4/agendas.js 에 안건을 추가하고 ready:true 로 표시",
      "",
      "자료가 모두 준비되면 '회의 준비 완료'로 알려 주세요. 그때까지 웹에는 '⏳ 준비 중'으로 남습니다."
    ].join("\n");
  }

  function addPlanned(topic, date){
    const t = String(topic||"").replace(/\s+/g," ").trim();
    if(!t){ toast("주제를 적어 주세요"); return null; }
    const hit = findReadyByTopic(t);
    if(hit){ toast("이미 ✅ 준비 완료된 안건입니다 · 목록에서 열어 주세요"); openAgenda(hit.id); return hit; }
    if(plannedAgendas().some(p=>norm(p.topic) === norm(t))){ toast("이미 예약된 안건입니다"); return null; }
    const list = localPlans();
    list.push({topic:t, date: date || dayOffset(1), at:Date.now()});
    saveLocalPlans(list);
    renderPrep();
    toast("⏳ 안건 예약 — 피클이 자료를 모으면 ✅로 바뀝니다");
    return null;
  }

  /* ═══════════════════ v4.6 — 회의 서류철 로비 · 입장 인트로 ═══════════════════
     성진님 지시: "들어가면 준비된 회의 안건 고르는 거랑 다음에 회의를 할 안건을 적고 입장..
     영상이 있으면 다들 의자에 앉거나 화상회의 준비하는 그런 영상 나오고 우리가 만든 페이지 로딩 되면 좋겠어"
     → 첫 화면은 종이 서류(로비). 입장을 누르면 착석 영상(인트로) → 6분할 회의실 본방.
     · 로비는 fixed 레이어다. 뒤의 회의실 DOM 은 하나도 지우지 않는다(v4.5.1 깜박임 방지 구조 유지).
     · 다음 안건 메모는 localStorage 에 누적되고, '복사'는 피클에게 보내는 자료 요청문을 그대로 담는다. */
  const K_NEXT = "darkjin_mr46_next";    // 다음 회의 안건 메모 (누적 목록)
  const K_SEL  = "darkjin_mr46_sel";     // 마지막으로 고른 안건
  const INTRO_MAX = 4000;                // 인트로 최대 4초 (영상이 더 길거나 자동재생이 막혀도 멈추지 않게)
  let lobbySel = null;
  let lobbyPaused = false;               // 로비로 나가면서 잠시 멈춘 상태인지
  let introDone = true;
  let introA = null;                     // 지금 재생 중인 인트로의 안건
  let introTimers = [];
  let introHandlers = null;              // 영상 ended/error 리스너 — 새 인트로를 틀 때 반드시 뗀다

  /* ── v4.6.1 — 입장 인트로 영상 3종 랜덤 ──
     성진님 지시: "회의실 로딩 장면 3가지 랜덤으로 바꿔줘. 다음에 다른거 만들면 또 넣게"
     ▶ 새 인트로 영상을 추가하는 방법 (딱 두 단계)
       ① avatars/ 폴더에 무음·3.8~3.9초·854x480 H.264 MP4 를 intro_4.mp4 로 넣고,
          같은 장면의 포스터 이미지를 intro_4_poster.webp(640x360 안팎) 로 넣는다.
       ② 아래 INTRO_CLIPS 배열 맨 끝에 intro_4.mp4 · intro_4_poster.webp 를 가리키는 항목 한 줄만 추가한다
          (예: src·poster·label 세 값을 적은 객체 하나 — 빌드가 이 배열을 그대로 읽는다).
     → 입장할 때마다 배열에서 직전에 튼 것만 피해서 랜덤으로 골라 튼다. 코드는 더 고칠 게 없다.
     → build_v4.sh 가 ./avatars/intro_N.mp4 와 ./avatars/intro_N_poster.webp 를 단일 파일에 인라인한다
        (주소는 배열에서 한 번씩만 적어야 한다 — 두 번 적으면 빌드가 멈춘다). */
  const INTRO_CLIPS = [
    { src:"./avatars/intro_1.mp4", poster:"./avatars/intro_1_poster.webp", label:"전원 셀카" },
    { src:"./avatars/intro_2.mp4", poster:"./avatars/intro_2_poster.webp", label:"일렬 정면" },
    { src:"./avatars/intro_3.mp4", poster:"./avatars/intro_3_poster.webp", label:"회의 테이블" }
  ];
  let lastIntroIdx = -1;                 // 직전에 튼 클립 번호 (같은 영상이 연달아 나오지 않게)

  function nextMemos(){
    try{
      const v = JSON.parse(LS.get(K_NEXT) || "[]");
      return Array.isArray(v) ? v.filter(m=> m && m.text) : [];
    }catch(e){ return []; }
  }
  function saveNextMemos(list){ LS.set(K_NEXT, JSON.stringify(list.slice(-40))); }
  function memoStamp(at){
    const d = new Date(at || Date.now());
    return (d.getMonth()+1) + "/" + d.getDate() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function lobbySelected(){
    const list = readyAgendas();
    if(!list.length) return null;
    let cur = lobbySel ? list.find(a=>a.id === lobbySel) : null;
    if(!cur && state.agenda) cur = list.find(a=>a.id === state.agenda.id) || null;
    if(!cur){ const saved = LS.get(K_SEL); cur = list.find(a=>a.id === saved) || null; }
    if(!cur) cur = list[0];
    lobbySel = cur.id;
    return cur;
  }

  function pickAgenda(id){
    const a = readyAgendas().find(x=>x.id === id);
    if(!a) return null;
    lobbySel = id; LS.set(K_SEL, id);
    const box = document.getElementById("lobbyAgList");
    if(box) [].forEach.call(box.children, n=>{
      if(!n.dataset || !n.dataset.id) return;
      const on = n.dataset.id === id;
      n.classList.toggle("sel", on);
      const r = n.querySelector("input"); if(r) r.checked = on;
    });
    const pt = document.getElementById("lobbyPickTitle");
    if(pt) pt.textContent = a.title;
    SFX.tap && SFX.tap();
    return a;
  }

  function renderLobby(){
    const box = document.getElementById("lobbyAgList");
    if(!box) return;
    const list = readyAgendas();
    const cur = lobbySelected();
    box.innerHTML = "";
    if(!list.length){
      box.append(el("div","lobby-empty","아직 결재할 안건이 없습니다. 피클이 6인 자료를 모아 ✅ 준비 완료로 바꾸면 이 서류에 올라옵니다."));
    }
    list.forEach((a, i)=>{
      const on = !!(cur && cur.id === a.id);
      const row = el("label","agdoc-item" + (on ? " sel" : ""));
      row.dataset.id = a.id;
      const radio = document.createElement("input");
      radio.type = "radio"; radio.name = "lobbyAgenda"; radio.value = a.id;
      radio.checked = on;
      radio.setAttribute("aria-label", a.title);
      radio.addEventListener("change", ()=> pickAgenda(a.id));
      row.append(radio);
      row.append(el("span","radio"));
      const body = el("span","abody");
      body.append(el("span","ai-tag", a.tag || ("안건 " + (i+1))));
      body.append(el("span","ai-title", a.title));
      if(a.brief) body.append(el("span","ai-brief", a.brief));
      const pc = panelCount(a);
      body.append(el("span","ai-meta", "자료 " + pc + "/6 · 🎙 " + roundTotal(a) + "라운드" + (a.preparedAt ? " · " + a.preparedAt : "")));
      row.append(body);
      row.append(el("span","okstamp", "준비 완료"));
      box.append(row);
    });
    const rn = document.getElementById("lobbyReadyN");
    if(rn) rn.textContent = list.length + "건";
    renderMemos();
    const pt = document.getElementById("lobbyPickTitle");
    if(pt) pt.textContent = cur ? cur.title : "—";
    const dn = document.getElementById("docNo");
    if(dn){ const d = new Date(); dn.textContent = "v4.7.1 · DOC " + d.getFullYear() + "-" + pad(d.getMonth()+1) + pad(d.getDate()); }
  }

  function renderMemos(){
    const box = document.getElementById("memoList");
    if(!box) return;
    const list = nextMemos();
    box.innerHTML = "";
    if(!list.length){
      box.append(el("div","memo-empty","아직 적어 둔 다음 안건이 없습니다."));
    }
    list.slice().reverse().forEach(m=>{
      const row = el("div","memo");
      row.dataset.mid = m.id;
      row.append(el("span","memo-tx", m.text));
      row.append(el("span","memo-when", memoStamp(m.at)));
      const cp = el("button","memo-b", "복사");
      cp.type = "button"; cp.dataset.act = "copy"; cp.dataset.mid = m.id;
      cp.title = "피클에게 보낼 자료 요청문으로 복사";
      const del = el("button","memo-b del", "삭제");
      del.type = "button"; del.dataset.act = "del"; del.dataset.mid = m.id;
      del.title = "이 메모 삭제";
      row.append(cp); row.append(del);
      box.append(row);
    });
    const n = document.getElementById("lobbyMemoN");
    if(n) n.textContent = list.length + "건";
  }

  function addMemo(){
    const ta = document.getElementById("memoInput");
    if(!ta) return null;
    const t = String(ta.value || "").replace(/\s+/g, " ").trim();
    if(!t){ toast("다음 회의에 다룰 안건을 먼저 적어 주세요"); ta.focus(); return null; }
    const list = nextMemos();
    const item = {id:"m" + Date.now(), text:t, at:Date.now()};
    list.push(item); saveNextMemos(list);
    ta.value = "";
    renderMemos();
    SFX.ding();
    toast("📌 다음 회의 안건으로 저장했습니다");
    return item;
  }
  function copyMemo(mid){
    const m = nextMemos().find(x=> x.id === mid);
    if(!m) return;
    copyText(requestText(m.text, ""));
  }
  function delMemo(mid){
    const list = nextMemos().filter(x=> x.id !== mid);
    saveNextMemos(list);
    renderMemos();
    toast("메모를 지웠습니다");
  }

  /* ── 로비 열기 / 닫기 ── */
  function showLobby(){
    if(!document.getElementById("lobby")) return;
    renderLobby();
    const sc = document.getElementById("lobbyScroll");
    if(sc) sc.scrollTop = 0;
    document.body.classList.add("lobby-on");
    if(state.agenda && !state.paused){
      state.paused = true; state.pausedAt = Date.now(); lobbyPaused = true;
      if(synthOK){ try{ window.speechSynthesis.cancel(); }catch(e){} }
      syncAvatarMedia();
    }
    setLive(state.agenda ? "서류함" : "준비실", "");
  }
  function hideLobby(){ document.body.classList.remove("lobby-on"); }
  function resumeFromLobby(){
    if(!lobbyPaused) return;
    lobbyPaused = false;
    state.paused = false;
    if(state.pausedAt){ state.pausedMs += Date.now() - state.pausedAt; state.pausedAt = 0; }
    if(state.agenda) startClock(state.pausedMs);
    setLive(state.phase === "roles" ? "역할 분담" : "회의 중", "");
    releasePause();
  }

  /* ── 입장: 인트로 → 6분할 회의실 본방 ── */
  function clearIntroTimers(){ introTimers.forEach(t=> clearTimeout(t)); introTimers = []; }
  /* 건너뛰기·자동 종료로 인트로를 닫았는데도 예전 영상의 ended 리스너가 남아 있으면,
     다음 인트로가 끝나는 순간 ‘예전 안건’으로 회의실을 열어 버린다(실제로 그랬다).
     리스너는 매번 떼고 새로 붙인다. */
  function clearIntroHandlers(){
    if(!introHandlers) return;
    const h = introHandlers; introHandlers = null;
    try{ h.vid.removeEventListener("ended", h.onEnd); h.vid.removeEventListener("error", h.onErr); }catch(e){}
  }

  function openRoom(a){
    lobbyPaused = false;
    // 인트로가 이미 "착석·자료 불러오는 중"을 알렸으므로 안건 토스트는 겹쳐 띄우지 않는다
    openAgenda(a.id, {quiet:true});
    setView("video", {silent:true});   // 서류 → 착석 영상 → 6분할 화상 화면으로 이어진다
  }

  function finishIntro(a){
    if(introDone) return;
    introDone = true;
    clearIntroTimers();
    clearIntroHandlers();
    const box = document.getElementById("intro");
    const vid = document.getElementById("introVid");
    if(vid){ try{ vid.pause(); }catch(e){} }
    if(box){ box.classList.remove("show"); box.setAttribute("aria-hidden", "true"); }
    document.body.classList.remove("intro-on");
    hideLobby();
    openRoom(a);
    introTimers.push(setTimeout(()=>{ if(vid){ try{ vid.currentTime = 0; }catch(e){} } }, 420));
  }

  /* 직전 클립(lastIntroIdx)은 빼고 나머지에서 균등하게 뽑는다.
     클립이 1개뿐이면 그걸 그대로, 처음(=-1)이면 전체에서 뽑는다. */
  function pickIntroIdx(){
    const n = INTRO_CLIPS.length;
    if(n === 0) return -1;
    if(n === 1) return 0;
    if(lastIntroIdx < 0) return Math.floor(Math.random() * n);
    const r = Math.floor(Math.random() * (n - 1));       // 0 .. n-2
    return r >= lastIntroIdx ? r + 1 : r;                // 자기 자신을 건너뛴 자리
  }

  function playIntro(a){
    const box = document.getElementById("intro");
    const vid = document.getElementById("introVid");
    hideLobby();
    const ip = document.getElementById("introPickTitle");
    if(ip) ip.textContent = "「" + a.title + "」";
    if(!box || !vid){ openRoom(a); return; }
    clearIntroTimers();
    clearIntroHandlers();
    introDone = false;
    introA = a;
    const ci = pickIntroIdx();
    const clip = ci >= 0 ? INTRO_CLIPS[ci] : null;
    if(clip){
      lastIntroIdx = ci;                                 // 이번 클립을 '직전' 으로 기억
      box.setAttribute("data-intro", String(ci + 1));
      vid.setAttribute("data-clip", clip.label || ("intro_" + (ci + 1)));
      vid.setAttribute("poster", clip.poster);
      if(vid.getAttribute("src") !== clip.src){
        vid.setAttribute("src", clip.src);
        try{ vid.load(); }catch(e){}
      }
      const bg = box.querySelector(".intro-bg");
      if(bg) bg.style.backgroundImage = 'url("' + clip.poster + '")';
    }
    setLive("착석 중", "");
    box.classList.add("show");
    box.setAttribute("aria-hidden", "false");
    document.body.classList.add("intro-on");
    const bar = box.querySelector(".it-bar i");
    if(bar){ bar.style.animation = "none"; void bar.offsetWidth; bar.style.animation = ""; }
    const finish = ()=> finishIntro(introA);   // 예전 리스너가 남아 있어도 지금 인트로를 닫는다
    const onEnd = finish;
    const onErr = ()=>{ if(introDone) return; clearIntroTimers(); introTimers.push(setTimeout(finish, 900)); };
    introHandlers = {vid:vid, onEnd:onEnd, onErr:onErr};
    vid.addEventListener("ended", onEnd, {once:true});
    vid.addEventListener("error", onErr, {once:true});
    try{ vid.currentTime = 0; }catch(e){}
    try{ const p = vid.play(); if(p && p.catch) p.catch(()=>{}); }catch(e){}
    introTimers.push(setTimeout(finish, INTRO_MAX));
  }

  function enterMeeting(){
    const a = lobbySelected();
    if(!a){ toast("아직 결재할 안건이 없습니다 · 피클이 자료를 모으면 올라옵니다"); return; }
    unlockVoice();
    LS.set(K_SEL, a.id);
    // 이미 그 안건으로 회의 중이었다면 처음부터 다시 틀지 않고 이어서 본다
    if(state.agenda && state.agenda.id === a.id && state.phase !== "idle"){
      hideLobby();
      resumeFromLobby();
      setView(state.view === "video" ? "video" : "text", {silent:true});
      toast("회의를 이어서 봅니다");
      return;
    }
    playIntro(a);
  }

  /* ═══════════════════ 안건 열기 ═══════════════════ */
  function openAgenda(id, opts){
    const a = (LIB.byId && LIB.byId[id]) || (LIB.agendas||[]).find(x=>x.id === id);
    if(!a){ toast("안건을 찾지 못했습니다"); return; }
    if(!a.panels || !Object.keys(a.panels).length){
      toast("이 안건은 아직 자료가 준비되지 않았습니다");
      return;
    }
    state.runToken++;
    state.agenda = a;
    state.option = null;
    state.ownerDir = "";
    state.notes = [];
    state.round = 0; state.roundSet = {}; state.talked = {};
    resetMoodSession();          // v4.7 — 새 세션(입장)이면 졸기/딴짓 발동 횟수도 0 부터
    state.paused = false; state.pausedAt = 0; state.pausedMs = 0;
    document.body.classList.remove("is-quiet");
    releasePause();
    state.phase = "materials";

    document.body.classList.add("meeting-on");
    document.getElementById("stage1Bar").style.display = "";
    document.getElementById("confirmPanel").classList.remove("show");
    document.getElementById("rolePanel").classList.remove("show");
    document.getElementById("finalBlock").classList.remove("show");
    document.getElementById("ownerDirection").value = "";

    buildTiles(partList());
    resetScrollPad();
    renderPrep();
    renderMaterials();
    renderOwnerChips();
    renderRoundBar();
    renderGuestBar();
    document.getElementById("prepCard").classList.add("has-agenda");
    document.getElementById("prepCard").classList.add("collapsed");
    document.getElementById("curAgendaTitle").textContent = a.title;
    document.getElementById("prepToggle").textContent = "다른 안건 ▾";

    setStep(1);
    const goal = roundTotal(a);
    const pc = panelCount(a);
    setStageHead("1라운드", "📖 자료 발표 — 각자 준비해 온 근거부터", "자료 " + pc + " / " + pc, false);
    setLive("자료 열람", "");
    startClock(0);
    SFX.ding();

    showReadyBanner(true);
    document.getElementById("refNote").innerHTML =
      "자료 출처는 각 패널의 <b>자료 펼치기</b>에서 확인할 수 있습니다. " +
      "이 안건은 <b>1라운드 자료 발표 → 2 정면 반박 → 3 대안·절충 → 4 최종 정리</b>까지 " + goal + "라운드로 이어집니다. " +
      (guestList().length
        ? "👀 <b>참관 게스트 " + guestList().length + "인</b>(" + guestList().map(g=>g.name).join(" · ") + ")은 토론 중에는 말하지 않고, 결론을 고를 때 최종 조언만 냅니다."
        : "");

    clearMinEmpty();
    minList.innerHTML = ""; minN = 0; minCountEl.textContent = "0건";
    talkList.innerHTML = ""; talkN = 0; talkCountEl.textContent = "0건";
    const te = el("li","talk-empty", "자료 " + pc + "/" + pc + " 도착 — 카드를 펼쳐 읽고, 아래 ▶️ 라운드를 이어서 누르면 1라운드 발표부터 2 정면 반박 · 3 대안·절충 · 4 최종 정리까지 " + pc + "인의 티키타카가 이어집니다. 💬 오너 코멘트를 넣으면 그 라운드 흐름에서 바로 반응합니다.");
    te.id = "talkEmpty"; talkList.append(te);

    addSystem('안건 열람 — "' + a.title + '" (자료 ' + pc + '/' + pc + ' · ' + (a.preparedAt||"") + ")");
    addSystem("라운드 " + goal + "개 준비됨 · 1라운드 자료 발표부터 차례로 진행하세요 (결론은 언제든 고를 수 있습니다)");

    state.lastLine = null; state.lastOrder = []; state.orders = {};
    setSubtitle(null, "", "", true);
    setView(LS.get(K_VIEW) === "video" ? "video" : "text", {silent:true});

    if(!(opts && opts.quiet)) toast("🗂️ 안건 열었습니다 · 주전 " + pc + "인 자료와 " + goal + "라운드 토론이 준비되어 있습니다");
    if(state.view !== "video"){
      const sh = document.getElementById("stageHd");
      if(sh) sh.scrollIntoView({block:"start"});
    }
  }

  function renderMaterials(){
    const a = state.agenda;
    partList().forEach(id=>{
      const p = a.panels[id];
      const r = tileRefs[id];
      if(!p){
        clearBubble(id, "이번 안건 자료 없음");
        r.matbtn.classList.add("ghost");
        setTileState(id,"","자료 없음");
        return;
      }
      renderBubble(id, "준비 자료", p.summary, {showBtn:true});
      setTileState(id,"ready","자료 준비");
    });
  }

  function openMat(id){
    const a = state.agenda;
    if(!a || !a.panels[id]) return;
    const p = a.panels[id];
    const who = byId(id);
    state.matId = id;
    document.getElementById("matTitle").textContent = who.name + " 준비 자료";
    document.getElementById("matWho").textContent = who.role + " · 준비 " + (a.preparedAt||"") + (a.preparedBy ? " · " + a.preparedBy : "");
    document.getElementById("matSum").textContent = p.summary || "";
    const ul = document.getElementById("matPoints");
    ul.innerHTML = "";
    (p.points||[]).forEach(t=> ul.append(el("li","", t)));
    document.getElementById("matConcern").textContent = p.concern || "—";
    document.getElementById("matProposal").textContent = p.proposal || "—";
    const mr = document.getElementById("matRounds");
    if(mr){
      mr.innerHTML = "";
      let any = 0;
      roundPlan().forEach(rd=>{
        if(rd.n === 1) return;
        if(!state.roundSet[rd.n]) return;
        const l = lineFor(id, rd);
        if(!l) return;
        any++;
        const row = el("div","rline");
        row.append(el("span","who3", rd.n + "R " + (rd.emoji||"") + " " + rd.tag));
        if(l.to){ const t2 = byId(l.to); row.append(el("span","to3", " → " + (t2 ? t2.name : l.to))); }
        row.append(document.createTextNode(" — " + l.text));
        mr.append(row);
      });
      if(!any) mr.append(el("div","dnone","아직 2라운드 이후가 진행되지 않았습니다. 아래 라운드를 눌러 이어서 들을 수 있습니다."));
    }
    const rb = document.getElementById("matRebuttal");
    if(p.rebuttal && p.rebuttal.text){
      const to = byId(p.rebuttal.to);
      rb.textContent = "→ " + (to?to.name:p.rebuttal.to) + " : " + p.rebuttal.text;
    } else rb.textContent = "—";
    document.getElementById("matSource").textContent = p.source || "";
    document.getElementById("matModal").classList.add("show");
  }

  /* ═══════════════════ 라운드 엔진 (1 자료발표 → 2 반박 → 3 절충 → 4 정리) ═══════════════════ */
  function setBarBusy(v){
    state.busy = !!v;
    ["nextRoundBtn","toConfirmBtn","confirmRoleBtn","backToTalkBtn"].forEach(i=>{
      const b = document.getElementById(i);
      if(b) b.disabled = state.busy;
    });
    if(!state.busy) renderRoundBar();
  }

  function roundPlan(){
    const a = state.agenda;
    if(!a) return [];
    const out = [{n:1, emoji:"📖", tag:"자료 발표", desc:"각자 준비해 온 근거와 관점을 차례로 발표합니다", lines:null, order:null}];
    const rs = (a.rounds||[]).slice();
    if(rs.length){
      rs.forEach((r,i)=>{
        const n = r.n || (i+2);
        out.push({n:n, emoji:r.emoji||"🔁", tag:r.tag||(n+"라운드"), desc:r.desc||"", order:r.order||null, lines:r.lines||null});
      });
    } else {
      const lines = {}; let has = false;
      partList().forEach(x=>{
        const p = a.panels[x];
        if(p && p.rebuttal && p.rebuttal.text){ lines[x] = {to:p.rebuttal.to, text:p.rebuttal.text}; has = true; }
      });
      if(has) out.push({n:2, emoji:"🔁", tag:"정면 반박", desc:"각자 다른 AI의 자료를 짚고 반박합니다", lines:lines, order:null});
    }
    return out;
  }

  function lineFor(id, rd){
    if(!rd || !state.agenda) return null;
    if(rd.n === 1){ const p = state.agenda.panels[id]; return p ? {text:p.summary} : null; }
    const l = rd.lines && rd.lines[id];
    if(!l) return null;
    return (typeof l === "string") ? {text:l} : l;
  }

  function renderNextLabel(){
    const b = document.getElementById("nextRoundBtn");
    if(!b) return;
    const nx = roundPlan()[state.round];
    if(!state.agenda){ b.textContent = "📖 1라운드: 자료 발표 시작"; return; }
    if(nx) b.textContent = (nx.emoji||"▶️") + " " + nx.n + "라운드: " + nx.tag + " 시작";
    else b.textContent = "📖 1라운드부터 다시 보기";
  }

  function renderRoundBar(){
    const bar = document.getElementById("roundBar");
    if(!bar) return;
    bar.innerHTML = "";
    renderNextLabel();
    if(!state.agenda) return;
    roundPlan().forEach(rd=>{
      const done = !!state.roundSet[rd.n];
      const isNext = !done && rd.n === state.round + 1;
      const open = done || rd.n <= state.round + 1;
      const b = el("button","rchip" + (done ? " done" : "") + (isNext ? " next" : ""), (done ? "✓ " : "") + rd.n + " " + rd.tag);
      b.dataset.round = rd.n;
      b.disabled = !open;
      b.title = done ? (rd.n + "라운드 다시 보기") : isNext ? "이어서 재생" : "앞 라운드부터 차례로";
      b.addEventListener("click", ()=>{ unlockVoice(); playRound(rd.n); });
      bar.append(b);
    });
  }

  /* ═══════════════════ 참관 게스트 (2인) ═══════════════════ */
  function renderGuestBar(){
    const bar = document.getElementById("guestBar");
    if(!bar) return;
    const gs = guestList();
    bar.innerHTML = "";
    if(!gs.length){ bar.classList.remove("on"); return; }
    bar.classList.add("on");
    bar.append(el("div","gt", "👀 참관 게스트 " + gs.length + "인 — 토론 중에는 말하지 않고 지켜봅니다"));
    const w = el("div","gw");
    gs.forEach(g=>{
      const i = el("div","gi");
      i.append(faceBox(guestPerson(g), "span", "gie"));
      i.append(el("span","gin", g.name));
      if(g.role) i.append(el("span","gir", g.role));
      w.append(i);
    });
    bar.append(w);
    bar.append(el("div","gh", "결론을 고를 때 🌟 최종 조언으로 두 사람의 추천과 놓친 포인트가 나옵니다"));
  }

  function renderGuestAdvice(){
    const box = document.getElementById("guestAdviceBox");
    const list = document.getElementById("guestAdvice");
    if(!box || !list) return;
    const gs = guestList();
    list.innerHTML = "";
    if(!gs.length){ box.style.display = "none"; return; }
    box.style.display = "";
    const opts = (state.agenda && state.agenda.options) || [];
    gs.forEach(g=>{
      const ad = g.advice || {};
      const card = el("div","gcard");
      const head = el("div","gch");
      head.append(faceBox(guestPerson(g), "span", "gce"));
      const nm = el("div","gcn");
      nm.append(el("div","gcnm", g.name));
      if(g.role) nm.append(el("div","gcr", g.role));
      head.append(nm);
      if(ad.option){
        const o = opts.find(x=>x.id === ad.option);
        head.append(el("span","gco", "추천 " + ad.option + (o ? " · " + o.title : "")));
      }
      card.append(head);
      if(g.reason) card.append(el("div","gcrs", "참관 이유 — " + g.reason));
      if(ad.why) card.append(el("div","gcw", ad.why));
      if(ad.missed){
        const m = el("div","gcm");
        m.append(el("b","", "놓친 포인트 "));
        m.append(document.createTextNode(ad.missed));
        card.append(m);
      }
      list.append(card);
    });
  }

  /* ═══════════════ 발언 카드 세로 중앙 정렬 (v4.4) ═══════════════
     v4.2.1 은 scrollIntoView({block:"nearest"}) 로 "화면에 걸치기만 하면 안 움직임" 이었다.
     그래서 카드가 화면 아래·위 가장자리에 걸친 채로 발언이 넘어가 "중앙으로 안 온다"고 느껴진다.
     → 카드의 세로 중심을 "실제로 보이는 영역"의 중앙에 맞춘다.
       (위 스티키 헤더와 아래 고정 오너 콘솔을 뺀 구간의 중앙)
     🎥 화상 6분할 모드에서는 절대 스크롤하지 않는다(화면 떨림 방지). */
  const scroller = {raf:0, to:null};

  function cancelScrollTween(){
    if(scroller.raf){ cancelAnimationFrame(scroller.raf); scroller.raf = 0; }
    scroller.to = null;
  }
  /* 위 고정 바·아래 고정 콘솔을 제외한 보이는 영역의 중앙 Y (뷰포트 기준) */
  function visibleCenter(){
    const vh = window.innerHeight || document.documentElement.clientHeight;
    let top = 0, bottom = vh;
    const tb = document.querySelector(".topbar");
    if(tb){
      const r = tb.getBoundingClientRect();
      if(r.height > 0 && r.bottom > 0) top = Math.min(vh * 0.45, Math.max(0, r.bottom));
    }
    const ob = document.getElementById("ownerBar");
    if(ob && ob.offsetHeight > 0){
      let st = null;
      try{ st = getComputedStyle(ob); }catch(e){}
      if(st && st.display !== "none" && st.position === "fixed"){
        const r = ob.getBoundingClientRect();
        if(r.height > 0 && r.top < vh) bottom = Math.min(bottom, r.top);
      }
    }
    if(bottom - top < 160){ top = 0; bottom = vh; }   // 창이 아주 낮을 때는 전체 화면 기준
    return {top:top, bottom:bottom, center: top + (bottom - top) / 2, vh:vh};
  }
  /* 마지막 카드도 중앙까지 올라올 수 있게 문서 끝 여백을 필요한 만큼만 늘린다(줄이지는 않는다) */
  function growScrollPad(extra){
    const pad = document.getElementById("scrollPad");
    if(!pad || !(extra > 0)) return false;
    const cur = parseFloat(pad.style.height) || 0;
    pad.style.height = Math.round(cur + extra) + "px";
    return true;
  }
  function resetScrollPad(){
    const pad = document.getElementById("scrollPad");
    if(pad) pad.style.height = "";
  }

  function scrollToY(y, smooth, done){
    const cur = window.pageYOffset || document.documentElement.scrollTop || 0;
    const target = Math.max(0, Math.round(y));
    cancelScrollTween();
    if(!smooth || Math.abs(target - cur) < 2){
      window.scrollTo(0, target);
      scroller.to = target;
      if(done) setTimeout(done, 0);
      return;
    }
    const start = cur, dist = target - cur, t0 = performance.now();
    const dur = Math.min(520, Math.max(260, Math.abs(dist) * 0.45));
    scroller.to = target;
    const step = function(now){
      const k = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - k, 3);   // ease-out
      window.scrollTo(0, Math.round(start + dist * e));
      if(k < 1){ scroller.raf = requestAnimationFrame(step); }
      else { scroller.raf = 0; window.scrollTo(0, target); if(done) done(); }
    };
    scroller.raf = requestAnimationFrame(step);
  }
  /* 사용자가 직접 스크롤하면 자동 이동은 바로 손을 뗀다(발언 이동과 손 스크롤이 싸우지 않게) */
  ["touchstart", "wheel", "mousedown", "keydown"].forEach(function(ev){
    window.addEventListener(ev, cancelScrollTween, {passive:true});
  });

  function focusTile(id){
    if(state.view !== "text"){ cancelScrollTween(); return false; }
    if(document.body.classList.contains("view-video")) return false;
    const r = tileRefs[id];
    if(!r || !r.tile || !r.tile.isConnected) return false;
    const t = r.tile;
    if(!t.offsetHeight) return false;                       // 숨은 카드는 건드리지 않는다
    const band = visibleCenter();
    const cur = window.pageYOffset || document.documentElement.scrollTop || 0;
    const rect = t.getBoundingClientRect();
    const want = cur + (rect.top + rect.height / 2) - band.center;
    let maxY = Math.max(0, (document.documentElement.scrollHeight || 0) - band.vh);
    if(want > maxY + 4){
      // 문서 끝 여백을 늘려 끝쪽 카드도 중앙에 올 수 있게 한다
      if(growScrollPad(want - maxY + 8)) maxY = Math.max(0, (document.documentElement.scrollHeight || 0) - band.vh);
    }
    const target = Math.min(maxY, Math.max(0, want));
    const ref = scroller.raf ? scroller.to : cur;
    if(ref != null && Math.abs(target - ref) < 8) return false;   // 이미 그 자리(또는 그 자리로 가는 중)
    let smooth = true;
    try{ smooth = !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }catch(e){}
    /* 안착 후 한 번만 다시 맞춘다 — iOS 주소창·툴바가 접히며 보이는 높이가 바뀌거나
       늦게 온 이미지/글자로 카드가 몇 px 밀렸을 때, 애니메이션 없이 조용히 제자리로. */
    const settle = function(){
      if(state.view !== "text" || document.body.classList.contains("view-video")) return;
      const r2 = tileRefs[id];
      if(!r2 || !r2.tile) return;
      const b2 = visibleCenter();
      const rect2 = r2.tile.getBoundingClientRect();
      const err = (rect2.top + rect2.height / 2) - b2.center;
      if(Math.abs(err) <= 18) return;
      const max2 = Math.max(0, (document.documentElement.scrollHeight || 0) - b2.vh);
      const y2 = (window.pageYOffset || 0) + err;
      window.scrollTo(0, Math.min(max2, Math.max(0, Math.round(y2))));
    };
    scrollToY(target, smooth, settle);
    return true;
  }

  async function playRound(n){
    if(!state.agenda || state.busy) return;
    const plan = roundPlan();
    const rd = plan.find(r=> r.n === n);
    if(!rd){ toast("이 안건에는 그 라운드가 없습니다"); return; }
    if(n > state.round + 1){ toast((state.round + 1) + "라운드부터 차례로 넘어가 주세요"); return; }
    setBarBusy(true);
    const token = ++state.runToken;
    state.phase = n === 1 ? "materials" : "discussion";
    setStep(n === 1 ? 1 : 2);
    const plist = partList();
    /* v4.2 — 고정 1~6번 순서를 버리고 매번 랜덤으로 섞는다.
       "순서대로 발표"가 아니라 "랜덤으로 치고 들어오는" 회의 느낌. 같은 라운드를 다시 들어도 순서가 달라진다. */
    const baseOrder = ((rd.order && rd.order.length) ? rd.order : plist).filter(id=> plist.indexOf(id) >= 0);
    const order = shuffleOrder(baseOrder);
    state.lastOrder = order.slice();
    state.orders[rd.n] = order.slice();
    state.orderLog.push({round:rd.n, at:Date.now(), order:order.slice()});
    if(state.orderLog.length > 40) state.orderLog.shift();
    const headLbl = (rd.emoji||"") + " " + rd.n + "라운드 · " + rd.tag;
    setStageHead(rd.n + "라운드", (rd.desc || rd.tag), headLbl + " 0 / " + order.length, n > 1);
    addSystem((rd.emoji||"") + " " + rd.n + "라운드 " + rd.tag + " — " + (rd.desc || ""));
    setLive(n === 1 ? "자료 발표" : rd.tag, "");
    let k = 0;
    let rest = 0;   // v4.6.2 — 피클 차례 없이 다른 AI 가 말한 횟수(2번째부터 피클은 조기 시작)
    setTileMood("pickle", "");   // 라운드 시작 — 일단 또릇하게
    for(const id of order){
      if(token !== state.runToken) break;
      await waitIfPaused();
      if(token !== state.runToken) break;
      if(id === "pickle"){
        setTileMood("pickle", "");      // 내 차례 — 즉시 깨서 영상도 speaking 으로 바뀜
        rest = 0;
      } else {
        rest++;
        /* v4.7 — 예전엔 여기서 rest>=2 면 무조건 켰다. 이제는 maybeMoodEvent 가 상한·확률·쿨다운을 본다. */
        maybeMoodEvent(rd.n, rest);
      }
      const line = lineFor(id, rd);
      if(!line) continue;
      const who = line.to ? byId(line.to) : null;
      const tag = rd.n + "라운드 · " + (who ? "→ " + who.name + "에게" : rd.tag);
      const sub = who ? "🔥 " + rd.n + "라운드 · " + who.name + "에게 치고 들어오기" : (rd.n + "라운드 · " + rd.tag);
      renderBubble(id, tag, line.text, {showBtn:true});
      await speakLine(id, line.text, {label: rd.tag + " 중", sub: sub});
      if(token !== state.runToken) break;
      const key = rd.n + ":" + id;
      if(!state.talked[key]){
        addTalk(id, n === 1 ? "read" : "round", line.text, {to:line.to, round:rd.n, tag:rd.tag});
        state.talked[key] = true;
      }
      setTileState(id, "ready", n === 1 ? "발표 완료" : rd.n + "라운드 완료");
      k++;
      setStageHead(rd.n + "라운드", (rd.desc || rd.tag), headLbl + " " + k + " / " + order.length, n > 1);
      await psleep(150/state.speed);
    }
    if(token === state.runToken){
      state.round = Math.max(state.round, rd.n);
      state.roundSet[rd.n] = true;
      if(state.round >= 1) setStep(2);
      renderRoundBar();
      const nx = plan[state.round];
      if(nx){
        setLive("논의 중", "");
        addSystem(rd.n + "라운드 완료 — 다음은 " + nx.n + "라운드 " + nx.tag + "입니다");
        toast("✅ " + rd.n + "라운드 끝 · ▶️ " + nx.n + "라운드 " + nx.tag + "로 이어서 보세요");
      } else {
        setLive("오너 결정 대기", "owner");
        addSystem("모든 라운드 완료 — ✅ 논의 마치고 결론을 고르세요");
        toast("🏁 " + plan.length + "라운드 끝 · ✅ 결론을 고르세요");
      }
      SFX.ding();
    }
    setBarBusy(false);
  }

  /* ═══════════════════ 오너 코멘트 ═══════════════════ */
  function renderOwnerChips(){
    const box = document.getElementById("interjectChips");
    box.innerHTML = "";
    const a = state.agenda;
    const chips = (a && a.ownerChips) ? a.ownerChips : [];
    chips.forEach(c=>{
      const b = el("button","chip2", c);
      b.addEventListener("click", ()=>{ unlockVoice(); submitComment(c); });
      box.append(b);
    });
  }

  function submitComment(text){
    const note = String(text||"").replace(/\s+/g," ").trim();
    if(!note){ toast("코멘트를 적어 주세요"); return false; }
    if(!state.agenda){ toast("먼저 준비실에서 안건을 골라 주세요"); return false; }
    state.notes.push(note);
    addTalk("owner","owner", note);
    addSystem('💬 오너 코멘트 — "' + note + '"');
    document.getElementById("interjectInput").value = "";
    stopInterjectMic(true);
    if(state.activeCut && state.activeCut.fire) state.activeCut.fire();
    if(synthOK){ try{ window.speechSynthesis.cancel(); }catch(e){} }
    SFX.pop();
    setLive("오너 코멘트", "owner");

    if(state.phase === "roles"){
      const c = document.getElementById("conclText");
      c.textContent = (c.textContent||"") + "\n[오너 코멘트] " + note;
      state.ownerDir = (state.ownerDir ? state.ownerDir + " / " : "") + note;
      toast("💬 코멘트를 결론에 덧붙였습니다");
      return true;
    }

    // 진행 중인 낭독/반박 스크립트를 여기서 끊는다 (코멘트 반영이 덮이지 않도록)
    state.runToken++;

    const a = state.agenda;
    let picked = null;
    partList().forEach(id=>{
      const p = a.panels[id];
      if(!p) return;
      const rep = (a.ownerReplies && a.ownerReplies[id]) || "";
      if(!rep) return;
      renderBubble(id, "코멘트 반영", rep, {showBtn:true});
      addTalk(id, "react", rep);
      setTileState(id,"ready","반영 완료");
      if(id === "pickle") picked = rep;
    });
    if(picked){
      const token = state.runToken;
      speakLine("pickle", picked, {label:"오너 지시 반영"});
    }
    toast("💬 코멘트 접수 — 6인이 각자 반응을 남겼습니다");
    return true;
  }

  /* ═══════════════════ 결론 확정 ═══════════════════ */
  function openConfirm(){
    if(!state.agenda) return;
    setView("text", {silent:true});   // 결론·역할은 문서 화면이라 글로 보기로 전환한다
    state.phase = "confirm";
    setStep(3);
    setLive("결론 확정 대기", "owner");
    document.getElementById("stage1Bar").style.display = "none";
    const opts = state.agenda.options || [];
    const list = document.getElementById("optList");
    list.innerHTML = "";
    opts.forEach(o=>{
      const b = el("button","opt" + (state.option === o.id ? " sel" : ""));
      b.dataset.id = o.id;
      const ot = el("div","ot");
      ot.append(el("span","ck2","✓"), el("span","", o.title));
      const od = el("div","od", o.detail || "");
      const om = el("div","om");
      const sup = (o.support||[]).map(x=>byId(x)?byId(x).name:x).join(" · ");
      if(sup) om.append(el("span","sup","지지 " + sup));
      if(o.risk) om.append(el("span","rk","위험 " + o.risk));
      b.append(ot, od, om);
      b.addEventListener("click", ()=>{
        state.option = o.id;
        document.querySelectorAll("#optList .opt").forEach(x=>x.classList.toggle("sel", x.dataset.id === o.id));
        document.getElementById("cfMeta").textContent = "선택: " + o.id + " · 논의 " + state.round + "/" + roundPlan().length + "라운드";
      });
      list.append(b);
    });
    const total = roundPlan().length;
    document.getElementById("cfMeta").textContent = "결론 후보 " + opts.length + " · 논의 " + state.round + "/" + total + "라운드 · 발언 " + talkN + "건";
    renderGuestAdvice();
    const hint = document.getElementById("cfHint");
    if(hint){
      hint.innerHTML = state.round >= total
        ? "🏁 " + total + "라운드까지 다 보셨습니다. 후보를 고르면 그 결론에 맞춘 역할 분담표가 나옵니다."
        : "지금 " + state.round + "라운드까지 보셨습니다. 더 들어 보려면 아래 <b>↩️ 논의로 돌아가기</b>로 나가 ▶️ 다음 라운드를 이어가면 됩니다. 결론은 언제든 골라도 됩니다.";
    }
    document.getElementById("confirmPanel").classList.add("show");
    addSystem("결론 확정 단계 — 오너가 후보를 고르고 역할 분담이 생성됩니다");
    document.getElementById("confirmPanel").scrollIntoView({block:"center"});
  }

  function backToTalk(){
    state.phase = "discussion";
    setStep(2);
    document.getElementById("confirmPanel").classList.remove("show");
    document.getElementById("stage1Bar").style.display = "";
    setLive("논의 중", "");
    toast("↩️ 논의로 돌아왔습니다");
    window.scrollTo(0,0);
  }

  function confirmRoles(){
    if(!state.agenda) return;
    setView("text", {silent:true});   // 역할 분담표도 문서 화면이다
    if(!state.option){
      toast("결론 후보를 하나 골라 주세요");
      document.querySelectorAll("#optList .opt").forEach(x=>{
        if(!x.dataset.done){ x.style.borderColor = "rgba(242,84,91,.6)"; setTimeout(()=>{ x.style.borderColor = ""; }, 900); }
      });
      return;
    }
    const a = state.agenda;
    const opt = (a.options||[]).find(o=>o.id === state.option);
    if(!opt){ toast("결론을 찾지 못했습니다"); return; }
    state.ownerDir = (document.getElementById("ownerDirection").value || "").replace(/\s+\n/g,"\n").trim();
    const roles = (a.roles && a.roles[state.option]) || {};

    state.phase = "roles";
    state.runToken++;
    setStep(4);
    document.getElementById("confirmPanel").classList.remove("show");
    document.getElementById("stage1Bar").style.display = "none";
    document.getElementById("rolePanel").classList.add("show");
    SFX.confirm();

    const concl = opt.title + "\n" + (opt.detail||"") + (state.ownerDir ? "\n[오너 추가 지시] " + state.ownerDir : "") + (state.notes.length ? "\n[오너 코멘트] " + state.notes.join(" / ") : "");
    document.getElementById("conclText").textContent = concl;
    document.getElementById("ccMeta").textContent = "결론 " + opt.id + " · " + (a.tag||"");
    document.getElementById("roleTitle").textContent = "결론과 역할 분담";

    const list = document.getElementById("actionList");
    list.innerHTML = "";
    const plist = partList();
    plist.forEach(id=>{
      const p = byId(id);
      const card = el("div","ac"); card.dataset.id = id;
      const body = el("div");
      body.append(el("div","nm", p.name), el("div","tx", roles[id] || "역할 미정"));
      card.append(faceBox(p, "div", "em"), body);
      list.append(card);
      renderBubble(id, "맡은 일", roles[id] || "역할 미정", {role:"2단계 · 역할 분담", showBtn:false});
      setTileState(id,"assigned","배정");
      tileRefs[id].matbtn.classList.add("ghost");
    });

    const fin = document.getElementById("finalText");
    fin.textContent = a.closing || "역할 분담대로 진행하고, 결과는 다음 회의에서 복기합니다.";
    document.getElementById("finalBlock").classList.add("show");

    setStageHead("2단계","결론 확정 → 역할 분담", "배정 " + plist.length + " / " + plist.length, true);
    setLive("역할 분담 완료", "done");
    addSystem("✅ 결론 확정 — 후보 " + opt.id + " · 역할 " + plist.length + "건 배정");
    plist.forEach(id=>{
      if(roles[id]) addTalk(id,"sys", "배정 — " + roles[id]);
    });
    toast("🧩 역할 분담 완료 · 복사해서 피클에게 넘기세요");
    const sh2 = document.getElementById("stageHd");
    if(sh2) sh2.scrollIntoView({block:"start"});

    const token = state.runToken;
    speakLine("pickle", "결론 확정했습니다. " + opt.title + ". 역할 여섯 개를 나눴습니다.", {label:"결론 확정"})
      .then(()=>{ if(token === state.runToken){ partList().forEach(id=>{ if(state.phase==="roles") setTileState(id,"assigned","배정"); }); } });
  }

  function newMeeting(){
    state.runToken++;
    state.phase = "idle";
    setView("text", {silent:true});
    state.lastLine = null;
    state.lastOrder = [];
    setSubtitle(null, "", "", true);
    state.agenda = null; state.option = null; state.ownerDir = "";
    state.notes = []; state.round = 0; state.roundSet = {}; state.talked = {};
    resetMoodSession();          // v4.7 — 회의를 끝내면 다음 세션은 다시 0 부터
    document.body.classList.remove("meeting-on");
    document.getElementById("prepCard").classList.remove("collapsed");
    document.getElementById("prepCard").classList.remove("has-agenda");
    document.getElementById("curAgendaTitle").textContent = "";
    document.getElementById("prepToggle").textContent = "다른 안건 ▾";
    document.getElementById("stage1Bar").style.display = "none";
    document.getElementById("confirmPanel").classList.remove("show");
    document.getElementById("rolePanel").classList.remove("show");
    document.getElementById("readyBanner").classList.remove("show");
    document.getElementById("refNote").textContent = "";
    clearInterval(state.timerId);
    document.getElementById("clock").textContent = "00:00";
    buildTiles(AIS);
    renderGuestBar();
    setStep(0);
    setStageHead("준비","안건 목록에서 고르면 6인 자료와 4라운드 토론이 열립니다","자료 0 / 6",false);
    setLive("준비실", "");
    renderPrep();
    renderRoundBar();
    window.scrollTo(0,0);
    toast("준비실로 돌아왔습니다");
  }

  /* ═══════════════════ 복사 ═══════════════════ */
  function copyText(text){
    const done = ()=> toast("📋 복사되었습니다 · 붙여넣기 하세요");
    if(navigator.clipboard && window.isSecureContext){
      navigator.clipboard.writeText(text).then(done).catch(()=>{ if(fallbackCopy(text)) done(); else manualCopy(text); });
    } else if(fallbackCopy(text)){ done(); }
    else { manualCopy(text); }
  }
  function fallbackCopy(text){
    try{
      const ta=document.createElement("textarea");
      ta.value=text; ta.setAttribute("readonly",""); ta.style.position="fixed"; ta.style.opacity="0"; ta.style.top="0";
      document.body.append(ta); ta.select();
      const ok=document.execCommand("copy"); ta.remove(); return ok;
    }catch(e){ return false; }
  }
  function manualCopy(text){
    const modal=el("div","modal show"); const veil=el("div","veil"); const sheet=el("div","sheet");
    sheet.append(el("h3","","복사"));
    sheet.append(el("p","note","이 브라우저는 자동 복사가 막혀 있습니다. 아래 내용을 길게 눌러 전체 선택한 뒤 복사해 주세요."));
    const ta=document.createElement("textarea");
    ta.value=text; ta.readOnly=true;
    ta.style.cssText="width:100%;height:42vh;background:#0a0d14;border:1px solid #242a3a;color:#c9cfe0;border-radius:10px;padding:9px;font-size:11px;line-height:1.5;font-family:inherit;resize:vertical";
    sheet.append(ta);
    const foot=el("div","foot"); const close=el("button","btn2 green","닫기");
    foot.append(close); sheet.append(foot); modal.append(veil,sheet);
    const shut=()=>modal.remove();
    veil.addEventListener("click",shut); close.addEventListener("click",shut);
    document.body.append(modal);
    setTimeout(()=>{ ta.focus(); ta.select(); },60);
  }

  function rolesText(){
    const a = state.agenda; if(!a) return "";
    const opt = (a.options||[]).find(o=>o.id === state.option);
    const roles = (a.roles && a.roles[state.option]) || {};
    const L = [];
    L.push("## " + a.title);
    L.push("");
    L.push("- 안건 ID: " + a.id);
    L.push("- 자료 준비: " + (a.preparedAt||"") + " · " + (a.preparedBy||""));
    L.push("- 회의 일시: " + nowStamp());
    L.push("- 확정 결론: " + state.option + (opt ? " · " + opt.title : ""));
    L.push("");
    L.push("### 결론");
    L.push(opt ? opt.detail : "");
    if(state.ownerDir){ L.push(""); L.push("### 오너 추가 지시"); L.push(state.ownerDir); }
    if(state.notes.length){ L.push(""); L.push("### 오너 코멘트"); state.notes.forEach(n=>L.push("- " + n)); }
    L.push("");
    L.push("### 역할 분담");
    partList().forEach(id=>{
      const p = byId(id);
      L.push("- " + p.name + " (" + p.role + ") — " + (roles[id] || "미정"));
    });
    L.push("");
    L.push("### 다음 단계");
    L.push(a.closing || "");
    const roundsPlayed = roundPlan().filter(r=> r.n >= 2 && state.roundSet[r.n]);
    if(roundsPlayed.length){
      L.push("");
      L.push("### 논의 라운드");
      roundsPlayed.forEach(rd=>{
        L.push("");
        L.push("#### " + rd.n + "라운드 · " + rd.tag);
        partList().forEach(id=>{
          const l = lineFor(id, rd); if(!l) return;
          const to = l.to ? (byId(l.to) ? byId(l.to).name : l.to) : "";
          L.push("- " + byId(id).name + (to ? " → " + to : "") + ": " + l.text);
        });
      });
    }
    L.push("");
    L.push("### 준비 자료 요약");
    partList().forEach(id=>{
      const p = a.panels[id]; if(!p) return;
      L.push("- " + byId(id).name + ": " + p.summary);
    });
    const gs = guestList();
    if(gs.length){
      L.push("");
      L.push("### 🌟 참관 게스트 최종 조언");
      gs.forEach(g=>{
        const ad = g.advice || {};
        L.push("- " + g.name + " (" + (g.role||"참관") + ") → 추천 " + (ad.option||"—") + ": " + (ad.why||""));
        if(ad.missed) L.push("  · 놓친 포인트: " + ad.missed);
      });
    }
    return L.join("\n");
  }

  function talkText(){
    return Array.from(talkList.querySelectorAll(".talk-item")).map(li=>{
      const tm = li.querySelector(".tt2") ? li.querySelector(".tt2").textContent : "";
      const who = li.querySelector(".tw") ? li.querySelector(".tw").innerText.replace(/\n/g," ") : "";
      const tx = li.querySelector(".tx") ? li.querySelector(".tx").textContent : "";
      return "- " + tm + " " + (who ? who + ": " : "") + tx;
    }).join("\n");
  }
  function minutesText(){
    return Array.from(minList.querySelectorAll(".min-item")).map(li=>{
      const tm = li.querySelector(".tm") ? li.querySelector(".tm").textContent : "";
      const tx = li.querySelector(".tx") ? li.querySelector(".tx").textContent : "";
      return "- " + tm + " " + tx;
    }).join("\n");
  }

  /* ═══════════════════ 준비 완료 알림 ═══════════════════ */
  function showReadyBanner(force){
    const a = state.agenda;
    const b = document.getElementById("readyBanner");
    if(!a){ b.classList.remove("show"); return; }
    const cnt = panelCount(a);
    document.getElementById("readyTitle").textContent = "회의 준비 완료 — " + a.title;
    document.getElementById("readySub").textContent = "주전 " + cnt + "인 자료 " + cnt + "/" + cnt + " · 준비 " + (a.preparedAt||"") + " · " + (a.preparedBy||"") + (guestList().length ? " · 👀 게스트 " + guestList().length + "인" : "");
    b.classList.add("show");
    if(force) SFX.ding();
  }
  function checkNewReady(){
    const ready = readyAgendas();
    let seen = [];
    try{ seen = JSON.parse(LS.get(K_SEEN)||"[]") || []; }catch(e){ seen = []; }
    const fresh = ready.filter(a=>seen.indexOf(a.id) < 0);
    LS.set(K_SEEN, JSON.stringify(ready.map(a=>a.id)));
    if(!fresh.length) return;
    if(state.agenda) return;
    document.getElementById("readyTitle").textContent = "새 안건 " + fresh.length + "건 준비 완료";
    document.getElementById("readySub").textContent = fresh.map(a=>a.title).join(" · ");
    document.getElementById("readyBanner").classList.add("show");
    // v4.6 — 첫 화면(서류 로비)·입장 인트로에서는 토스트가 입장 버튼·영상 위를 가리므로 띄우지 않는다.
    //         로비 01번 칸에 이미 "준비된 회의 안건 N건"으로 보인다.
    const covered = document.body.classList.contains("lobby-on") || document.body.classList.contains("intro-on");
    if(!covered) toast("🔔 새 회의 자료가 준비되었습니다 · " + fresh.length + "건");
    if(LS.get(K_NOTIFY) === "1"){
      try{
        if(window.Notification && Notification.permission === "granted"){
          new Notification("다크진 AI 비서실 · 회의 준비 완료", {body: fresh.map(a=>a.title).join("\n")});
        }
      }catch(e){}
    }
  }

  /* ═══════════════════ 설정 ═══════════════════ */
  function openSettings(){
    document.getElementById("settingsModal").classList.add("show");
    document.querySelectorAll("#speedRow .chip").forEach(c=>c.classList.toggle("on", Number(c.dataset.speed) === state.speed));
    const sfx = document.getElementById("sfxToggle");
    sfx.classList.toggle("on", state.sfxOn);
    sfx.textContent = state.sfxOn ? "🔔 효과음 ON" : "🔕 효과음 OFF";
    const nb = document.getElementById("notifyToggle");
    nb.classList.toggle("on", LS.get(K_NOTIFY) === "1");
    nb.textContent = LS.get(K_NOTIFY) === "1" ? "🔔 알림 켜짐" : "🔕 알림 꺼짐";
  }
  function closeSettings(){ document.getElementById("settingsModal").classList.remove("show"); }
  function openPlan(){
    const t = document.getElementById("planTopic");
    const d = document.getElementById("planDate");
    if(t) t.value = "";
    if(d) d.value = dayOffset(1);
    document.querySelectorAll("#planDateRow .chip").forEach(c=>c.classList.toggle("on", c.dataset.day === "tomorrow"));
    document.getElementById("planModal").classList.add("show");
    setTimeout(()=>{ if(t) t.focus(); }, 80);
  }
  function closePlan(){
    stopListening(true);
    document.getElementById("planModal").classList.remove("show");
  }

  /* ═══════════════════ 이벤트 ═══════════════════ */
  document.getElementById("nextRoundBtn").addEventListener("click", ()=>{
    unlockVoice();
    if(!state.agenda){ toast("먼저 안건 목록에서 안건을 골라 주세요"); return; }
    const nx = roundPlan()[state.round];
    playRound(nx ? nx.n : 1);
  });
  document.getElementById("toConfirmBtn").addEventListener("click", ()=>{ unlockVoice(); openConfirm(); });
  document.getElementById("backToTalkBtn").addEventListener("click", backToTalk);
  document.getElementById("confirmRoleBtn").addEventListener("click", confirmRoles);
  document.getElementById("newMeeting").addEventListener("click", newMeeting);
  document.getElementById("changeOption").addEventListener("click", ()=>{
    if(!state.agenda) return;
    document.getElementById("rolePanel").classList.remove("show");
    document.getElementById("finalBlock").classList.remove("show");
    document.getElementById("stage1Bar").style.display = "";
    state.phase = "materials";
    renderMaterials();
    partList().forEach(id=>{ const r=tileRefs[id]; if(r) r.matbtn.classList.remove("ghost"); });
    openConfirm();
    toast("↩️ 결론을 다시 고를 수 있습니다 · 자료도 그대로 남아 있습니다");
  });
  document.getElementById("copyRoles").addEventListener("click", ()=> copyText(rolesText()));
  document.getElementById("copyTalk").addEventListener("click", ()=> copyText("[" + (state.agenda?state.agenda.title:"회의") + "]\n" + talkText()));
  document.getElementById("copyMinutes").addEventListener("click", ()=> copyText("[" + (state.agenda?state.agenda.title:"회의") + "]\n" + minutesText()));
  document.getElementById("copyAll").addEventListener("click", ()=>{
    copyText("[" + (state.agenda?state.agenda.title:"회의") + "]\n\n" +
      "== 역할 분담 ==\n" + rolesText() + "\n\n== 논의 기록 ==\n" + talkText());
  });
  document.getElementById("readyClose").addEventListener("click", ()=> document.getElementById("readyBanner").classList.remove("show"));
  document.getElementById("prepToggle").addEventListener("click", ()=>{
    const c = document.getElementById("prepCard");
    const open = c.classList.toggle("collapsed");
    document.getElementById("prepToggle").textContent = open ? "다른 안건 ▾" : "접기 ▴";
    if(!open) document.getElementById("agList").scrollIntoView({block:"nearest"});
  });
  document.getElementById("settingsBtn").addEventListener("click", openSettings);
  /* v4.2 보기 전환 — 회의 중 언제든 원터치로 왔다 갔다 */
  document.getElementById("viewVideoBtn").addEventListener("click", ()=>{ unlockVoice(); setView("video"); });
  document.getElementById("viewTextBtn").addEventListener("click", ()=>{ unlockVoice(); setView("text"); });
  document.querySelectorAll("[data-close]").forEach(n=> n.addEventListener("click", ()=>{
    if(n.closest("#matModal")) document.getElementById("matModal").classList.remove("show");
    else if(n.closest("#planModal")) closePlan();
    else closeSettings();
  }));
  document.getElementById("matSpeak").addEventListener("click", ()=>{
    if(!state.matId || !state.agenda) return;
    const p = state.agenda.panels[state.matId];
    if(!p) return;
    unlockVoice();
    state.runToken++;
    speakLine(state.matId, p.summary, {label:"자료 낭독"}).then(()=>{ if(state.phase!=="roles" && state.agenda) setTileState(state.matId,"ready","자료 준비"); });
  });

  /* v4.6 — 서류철 로비 · 입장 인트로 · 다음 안건 메모 */
  document.getElementById("enterBtn").addEventListener("click", ()=>{ unlockVoice(); enterMeeting(); });
  document.getElementById("introSkip").addEventListener("click", ()=>{ if(!introDone && introA) finishIntro(introA); });
  document.getElementById("memoSave").addEventListener("click", ()=>{ unlockVoice(); addMemo(); });
  document.getElementById("memoList").addEventListener("click", (e)=>{
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if(!b) return;
    if(b.dataset.act === "copy") copyMemo(b.dataset.mid);
    else if(b.dataset.act === "del") delMemo(b.dataset.mid);
  });
  document.getElementById("memoInput").addEventListener("keydown", e=>{
    if((e.metaKey || e.ctrlKey) && e.key === "Enter"){ e.preventDefault(); addMemo(); }
  });
  document.getElementById("lobbyBackBtn").addEventListener("click", ()=>{ unlockVoice(); showLobby(); });

  document.getElementById("planAddBtn").addEventListener("click", ()=>{ unlockVoice(); openPlan(); });
  document.getElementById("planSave").addEventListener("click", ()=>{
    const t = ($("#planTopic").value||"").trim();
    if(!t){ toast("주제를 먼저 적어 주세요"); return; }
    const d = ($("#planDate").value||"").trim() || dayOffset(1);
    stopListening(true);
    addPlanned(t, d);
    $("#planTopic").value = "";
    closePlan();
  });
  $("#planTopic").addEventListener("keydown", e=>{ if(e.key === "Enter"){ e.preventDefault(); document.getElementById("planSave").click(); } });
  document.getElementById("planMic").addEventListener("click", ()=>{ unlockVoice(); startListening(); });
  document.querySelectorAll("#planDateRow .chip").forEach(c=>{
    c.addEventListener("click", ()=>{
      document.querySelectorAll("#planDateRow .chip").forEach(x=>x.classList.toggle("on", x === c));
      const off = c.dataset.day === "today" ? 0 : c.dataset.day === "after" ? 2 : 1;
      document.getElementById("planDate").value = dayOffset(off);
    });
  });

  document.getElementById("voiceBtn").addEventListener("click", ()=>{
    setVoice(!state.voiceOn);
    if(state.voiceOn){ unlockVoice(); SFX.ding(); }
  });
  document.getElementById("quietBtn").addEventListener("click", ()=>{
    unlockVoice();
    if(state.paused) resumeAll(); else quietAll();
  });
  document.getElementById("interjectMic").addEventListener("click", ()=>{ unlockVoice(); beginInterjectMic(); });
  document.getElementById("interjectSend").addEventListener("click", ()=>{
    const v = (document.getElementById("interjectInput").value||"").trim();
    if(!v){ toast("코멘트를 적거나 🎤로 말해 주세요"); return; }
    submitComment(v);
  });
  document.getElementById("interjectInput").addEventListener("keydown", e=>{
    if(e.key === "Enter"){ e.preventDefault(); const v=(document.getElementById("interjectInput").value||"").trim(); if(v) submitComment(v); }
  });

  document.querySelectorAll("#speedRow .chip").forEach(c=>{
    c.addEventListener("click", ()=>{
      state.speed = Number(c.dataset.speed);
      LS.set(K_SPEED, String(state.speed));
      document.querySelectorAll("#speedRow .chip").forEach(x=>x.classList.toggle("on", x === c));
      toast("낭독 속도: " + c.textContent);
    });
  });
  const sfxBtn = document.getElementById("sfxToggle");
  sfxBtn.addEventListener("click", ()=>{
    state.sfxOn = !state.sfxOn;
    LS.set(K_SFX, state.sfxOn ? "1" : "0");
    sfxBtn.classList.toggle("on", state.sfxOn);
    sfxBtn.textContent = state.sfxOn ? "🔔 효과음 ON" : "🔕 효과음 OFF";
    if(state.sfxOn){ SFX.unlock(); SFX.pop(); }
  });
  document.getElementById("notifyToggle").addEventListener("click", ()=>{
    const on = LS.get(K_NOTIFY) === "1";
    const b = document.getElementById("notifyToggle");
    if(on){
      LS.del(K_NOTIFY); b.classList.remove("on"); b.textContent = "🔕 알림 꺼짐";
      toast("준비 완료 알림을 껐습니다");
      return;
    }
    LS.set(K_NOTIFY, "1"); b.classList.add("on"); b.textContent = "🔔 알림 켜짐";
    try{
      if(window.Notification && Notification.permission === "default") Notification.requestPermission();
    }catch(e){}
    toast("🔔 새 안건이 준비되면 이 브라우저에 알립니다");
  });

  document.getElementById("voiceTest").addEventListener("click", ()=>{
    if(!synthOK){ toast("이 브라우저는 음성 합성을 지원하지 않습니다"); return; }
    if(!state.voiceOn) setVoice(true, true);
    unlockVoice();
    speakChunk("pickle","안건 자료 확인했습니다. 제가 회의를 진행하겠습니다.", VOICE_CFG.pickle);
    toast("🔊 피클 목소리 테스트");
  });
  document.getElementById("voiceTestAll").addEventListener("click", async ()=>{
    if(!synthOK){ toast("이 브라우저는 음성 합성을 지원하지 않습니다"); return; }
    if(!state.voiceOn) setVoice(true, true);
    unlockVoice();
    toast("🎚️ 여섯 목소리를 차례로 들려드립니다");
    for(const id of AIS){
      const p = byId(id);
      await speakChunk(id, p.name + "입니다. " + (VOICE_CFG[id]?VOICE_CFG[id].tone:""), VOICE_CFG[id]||{pitch:1,rate:1});
      await sleep(140);
    }
  });
  document.addEventListener("keydown", e=>{
    if(e.key === "Escape"){ closeSettings(); closePlan(); document.getElementById("matModal").classList.remove("show"); }
    const tag = (e.target && e.target.tagName) || "";
    if((e.key === "q" || e.key === "Q") && !/input|textarea/i.test(tag)){ if(state.paused) resumeAll(); else quietAll(); }
    if((e.key === "v" || e.key === "V") && !/input|textarea/i.test(tag)){ setView(state.view === "video" ? "text" : "video"); }
  });

  /* ═══════════════════ 시작 ═══════════════════ */
  buildTiles();
  setStep(0);
  setStageHead("준비","안건 목록에서 고르면 6인 자료와 4라운드 토론이 시작됩니다","자료 0 / 6",false);
  setVoice(state.voiceOn, true);
  setView(LS.get(K_VIEW) === "video" ? "video" : "text", {silent:true});
  refreshVoices();
  if(synthOK){ try{ window.speechSynthesis.onvoiceschanged = refreshVoices; }catch(e){} }
  setIMicUI(false);
  if(!SR){
    const ib = document.getElementById("interjectMic");
    if(ib){ ib.style.opacity = ".55"; ib.title = "이 브라우저는 음성 인식 미지원"; }
  }
  renderPrep();
  renderLobby();

  // URL 파라미터: ?agenda=yt-growth / ?topic=새 주제
  let deepLinked = false;
  try{
    const q = new URLSearchParams(location.search);
    const ag = q.get("agenda");
    const tp = q.get("topic");
    if(ag && LIB.byId && LIB.byId[ag]){ deepLinked = true; openAgenda(ag); }
    else if(tp){ openPlan(); document.getElementById("planTopic").value = tp; }
  }catch(e){}

  // v4.6 — 첫 화면은 회의실이 아니라 '회의 서류철' 로비다 (?agenda= 딥링크일 때만 바로 회의실)
  if(!deepLinked) showLobby();
  // 새 자료 알림은 로비가 열린 뒤에 본다 — 로비 위에 토스트가 입장 버튼을 가리지 않게.
  checkNewReady();

  const unlockOnce = ()=>{ unlockVoice(); document.removeEventListener("pointerdown", unlockOnce); document.removeEventListener("touchstart", unlockOnce); };
  document.addEventListener("pointerdown", unlockOnce, {passive:true});
  document.addEventListener("touchstart", unlockOnce, {passive:true});

  /* 테스트용: DOM 노드마다 고유 번호(같은 노드인지 비교) */
  const nodeKeyMap = new WeakMap();
  let nodeKeySeq = 0;
  function nodeKey(n){ if(!n) return 0; if(!nodeKeyMap.has(n)) nodeKeyMap.set(n, ++nodeKeySeq); return nodeKeyMap.get(n); }

  // 테스트용 훅
  window.__mr4 = {
    state: state,
    setView: setView,
    focusTile: focusTile,
    visibleCenter: visibleCenter,
    centerOf: (id)=>{
      const r = tileRefs[id];
      if(!r || !r.tile) return null;
      const b = visibleCenter();
      const rect = r.tile.getBoundingClientRect();
      const y = window.pageYOffset || document.documentElement.scrollTop || 0;
      return {id:id, top:Math.round(rect.top), bottom:Math.round(rect.bottom), center:Math.round(rect.top + rect.height/2),
              bandTop:Math.round(b.top), bandBottom:Math.round(b.bottom), bandCenter:Math.round(b.center),
              err:Math.round(rect.top + rect.height/2 - b.center), scrollY:Math.round(y),
              maxScroll:Math.round(Math.max(0, (document.documentElement.scrollHeight||0) - b.vh)), vh:Math.round(b.vh)};
    },
    videos: ()=> [].map.call(document.querySelectorAll("video.vid"), v=>({
      who:v.dataset.who, src:v.getAttribute("src"), poster:v.getAttribute("poster"),
      paused:v.paused, t:Math.round(v.currentTime*100)/100, rs:v.readyState,
      w:v.videoWidth, h:v.videoHeight, muted:v.muted, loop:v.loop,
      plays:v.playsInline, autoplay:v.autoplay, controls:v.controls,
      op:getComputedStyle(v).opacity, off:v.classList.contains("off")
    })),
    /* v4.5.1 — 타일별 미디어 상태(타일 소실·영상 재생 조건 감시)
       v4.6.2 — mood(조는 중)·sleepy 겹 정보 추가 */
    media: ()=> Object.keys(tileRefs).map(id=>{
      const r = tileRefs[id];
      const rect = r.tile.getBoundingClientRect();
      const img = r.tile.querySelector(".vbob img.face");
      const pos = r.poster;
      const v = r.vid;
      const sl = r.vids && r.vids.sleepy;
      const ph = r.vids && r.vids.phone;
      const ls = r.vids && r.vids.listening;
      const cast = (x)=> x ? {nw:x.naturalWidth, c:x.complete, src:x.getAttribute("src"),
                              op:getComputedStyle(x).opacity, disp:getComputedStyle(x).display} : null;
      const vcast = (x)=> x ? {src:x.getAttribute("src"), paused:x.paused, rs:x.readyState,
                               t:Math.round(x.currentTime*100)/100, op:getComputedStyle(x).opacity,
                               off:x.classList.contains("off"), w:x.videoWidth, h:x.videoHeight} : null;
      return {id:id, speaking:r.tile.classList.contains("speaking"),
              sleepy:r.tile.classList.contains("sleepy"), phone:r.tile.classList.contains("phone"),
              mood:r.mood || "",
              vstate:(r.vstate && r.vstate.textContent) || "",
              rect:{w:Math.round(rect.width), h:Math.round(rect.height), t:Math.round(rect.top), l:Math.round(rect.left)},
              img:cast(img), poster:cast(pos),
              video: vcast(v), sleep: vcast(sl), phon: vcast(ph), listen: vcast(ls)};
    }),
    tileIds: ()=> [].map.call(stage.children, n=> n.dataset.id),
    nodeIds: ()=> Object.keys(tileRefs).map(id=>{
      const r = tileRefs[id];
      return {id:id, tile:nodeKey(r.tile), img:nodeKey(r.tile.querySelector(".vbob img.face") || r.tile.querySelector(".thead img.face")),
              poster:nodeKey(r.poster), video:nodeKey(r.vid), bubble:nodeKey(r.msum), state:nodeKey(r.state)};
    }),
    scrollPad: ()=> { const p=document.getElementById("scrollPad"); return p ? Math.round(p.getBoundingClientRect().height) : -1; },
    view: () => state.view,
    subtitle: () => { const t=document.getElementById("vsTx"), b=document.getElementById("vsub"); return {text:(t&&t.textContent)||"", h: b? Math.round(b.getBoundingClientRect().height):0}; },
    sub: setSubtitle,   // 검증용: 자막을 직접 갈아 끼워 높이 고정 확인
    shuffleOrder: shuffleOrder,
    orderLog: () => state.orderLog,
    lastOrder: () => state.lastOrder.slice(),
    agendaIds: () => (LIB.agendas||[]).map(a=>a.id),
    openAgenda: openAgenda,
    playRound: playRound,
    roundPlan: roundPlan,
    roundTotal: roundTotal,
    participants: partList,
    guests: guestList,
    submitComment: submitComment,
    openConfirm: openConfirm,
    confirmRoles: confirmRoles,
    addPlanned: addPlanned,
    plannedAgendas: plannedAgendas,
    rolesText: rolesText,
    /* v4.6 — 로비·인트로 검증용 훅 */
    showLobby: showLobby,
    dismissLobby: hideLobby,     // 테스트용: 로비만 닫고 배경 회의실 UI 를 그대로 쓴다
    enterMeeting: enterMeeting,
    enterRoom: (id)=>{           // 테스트·딥링크용: 로비와 인트로를 건너뛰고 바로 회의실
      const a = id ? readyAgendas().find(x=>x.id === id) : lobbySelected();
      if(!a) return null;
      lobbySel = a.id; LS.set(K_SEL, a.id);
      introDone = true; clearIntroTimers();
      document.body.classList.remove("intro-on");
      const box = document.getElementById("intro"); if(box){ box.classList.remove("show"); box.setAttribute("aria-hidden","true"); }
      lobbyPaused = false;
      hideLobby(); openAgenda(a.id);
      return a.id;
    },
    lobby: ()=>({
      open: document.body.classList.contains("lobby-on"),
      sel: lobbySel,
      picked: (()=>{ const el2 = document.getElementById("lobbyPickTitle"); return el2 ? el2.textContent : ""; })(),
      agendas: [].map.call(document.querySelectorAll("#lobbyAgList .agdoc-item"), n=>({
        id:n.dataset.id, sel:n.classList.contains("sel"),
        checked: !!(n.querySelector("input") && n.querySelector("input").checked)
      })),
      memos: nextMemos(),
      introShown: document.body.classList.contains("intro-on"),
      introTime: (()=>{ const v=document.getElementById("introVid"); return v ? Math.round(v.currentTime*100)/100 : -1; })()
    }),
    addMemo: addMemo,
    delMemo: delMemo,
    /* v4.6.1 — 인트로 3종 랜덤 검증용 훅 */
    introClips: () => INTRO_CLIPS.map((c,i)=>({ idx:i, src:c.src, poster:c.poster, label:c.label })),
    introState: () => ({
      lastIdx: lastIntroIdx,
      count: INTRO_CLIPS.length,
      clip: (()=>{ const v=document.getElementById("introVid"); return v ? (v.getAttribute("data-clip")||"") : ""; })(),
      src: (()=>{ const v=document.getElementById("introVid"); return v ? (v.getAttribute("src")||"") : ""; })(),
      poster: (()=>{ const v=document.getElementById("introVid"); return v ? (v.getAttribute("poster")||"") : ""; })(),
      bg: (()=>{ const b=document.querySelector("#intro .intro-bg"); return b ? (b.style.backgroundImage||"") : ""; })(),
      readyState: (()=>{ const v=document.getElementById("introVid"); return v ? v.readyState : -1; })(),
      paused: (()=>{ const v=document.getElementById("introVid"); return v ? v.paused : true; })(),
      time: (()=>{ const v=document.getElementById("introVid"); return v ? Math.round(v.currentTime*100)/100 : -1; })()
    }),
    /* v4.6.2 — 조는 중(sleepy) 검증용 훅 */
    setTileMood: (id, mood)=> setTileMood(id, mood),
    setTileState: (id, kind, label)=> setTileState(id, kind, label),   // v4.7.1 — 발언 차례에 잠이 깨는지 검증용
    moods: ()=> Object.keys(tileRefs).map(id=>{
      const r = tileRefs[id];
      const one = (x)=> x ? {src:x.getAttribute("src"), paused:x.paused,
                             t:Math.round(x.currentTime*100)/100, rs:x.readyState,
                             op:getComputedStyle(x).opacity, off:x.classList.contains("off"),
                             w:x.videoWidth, h:x.videoHeight,
                             loop:x.loop, ended:x.ended, dur:Math.round((x.duration||0)*100)/100,
                             done:x.dataset.done || ""} : null;
      return {id:id, mood:r.mood || "",
              sleepy:r.tile.classList.contains("sleepy"), phone:r.tile.classList.contains("phone"),
              speaking:r.tile.classList.contains("speaking"),
              moodNow:avatarMood(r),      // v4.7 — 지금 켜야 하는 겹(speaking/listening/sleepy/phone/"")
              vstate:(r.vstate && r.vstate.textContent) || "",
              state:(r.state && r.state.textContent) || "",
              layers:Object.keys(r.vids || {}),
              sleep: one(r.vids && r.vids.sleepy), phon: one(r.vids && r.vids.phone),
              listen: one(r.vids && r.vids.listening),
              speak: one(r.vid)};
    }),
    /* v4.7 — '어쩌다 한 번' 정책 검증용 훅 */
    moodPolicy: () => ({maxPerSession:MOOD_EVENT.maxPerSession, minRest:MOOD_EVENT.minRest,
                        prob:MOOD_EVENT.prob, cooldownRounds:MOOD_EVENT.cooldownRounds,
                        debugProb:MOOD_EVENT.debugProb, events:state.moodEvents,
                        lastRound:state.moodRound, log:state.moodLog.slice()}),
    setMoodPolicy: (o)=>{ o = o || {};
      if("maxPerSession" in o) MOOD_EVENT.maxPerSession = o.maxPerSession;
      if("minRest" in o) MOOD_EVENT.minRest = o.minRest;
      if("prob" in o) MOOD_EVENT.prob = o.prob;
      if("cooldownRounds" in o) MOOD_EVENT.cooldownRounds = o.cooldownRounds;
      "debugProb" in o ? (MOOD_EVENT.debugProb = o.debugProb) : (MOOD_EVENT.debugProb = null);
      return {maxPerSession:MOOD_EVENT.maxPerSession, minRest:MOOD_EVENT.minRest,
              prob:MOOD_EVENT.prob, cooldownRounds:MOOD_EVENT.cooldownRounds,
              debugProb:MOOD_EVENT.debugProb};
    },
    resetMoodSession: ()=> resetMoodSession(),
    moodGate: (roundNo, rest, rand)=> moodGatePass(roundNo, rest, rand),   // 확률·상한·쿨다운 경계 검증용
    pickIntroIdx: () => { const i = pickIntroIdx(); lastIntroIdx = i; return i; }   // 분포만 볼 때(영상 재생 없이)
  };
})();
