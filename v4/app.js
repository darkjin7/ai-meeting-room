
(function(){
  "use strict";

  /* ═══════════════════ 기본 정의 ═══════════════════ */
  const LIB = window.AGENDA_LIB || {agendas:[], byId:{}};
  const AIS = ["pickle","gemini","cue","hark","chatgpt","claude"];
  const GUEST_POOL = ["meta_muse","keyring"];
  /* v4.3 — 비서실 8인 SD 캐릭터 아바타. img 는 256x256 webp(저장소 `avatars/`), 실패하면 emoji 로 대체된다. */
  const PEOPLE = [
    {id:"pickle",  name:"피클(다크)", emoji:"⚡", role:"총괄 · 자료 취합·진행",   color:"#8b7cf6", img:"./avatars/pickle.webp"},
    {id:"gemini",  name:"Gemini",    emoji:"🌀", role:"대본·카피·구조 분석",     color:"#4285f4", img:"./avatars/gemini.webp"},
    {id:"cue",     name:"Cue",       emoji:"🔍", role:"트렌드·수치 리서치",      color:"#38bdf8", img:"./avatars/cue.webp"},
    {id:"hark",    name:"Hark",      emoji:"🧐", role:"검증·리스크·조건 확인",   color:"#f0a23c", img:"./avatars/hark.webp"},
    {id:"chatgpt", name:"ChatGPT",   emoji:"🛠️", role:"구조 설계·DB·자동화",     color:"#10a37f", img:"./avatars/chatgpt.webp"},
    {id:"claude",  name:"Claude",    emoji:"✍️", role:"글쓰기·기획 검토",        color:"#d97757", img:"./avatars/claude.webp"},
    {id:"meta_muse",name:"Meta Muse",emoji:"🎨", role:"B롤 영상·이미지",        color:"#e879f9", img:"./avatars/meta_muse.webp"},
    {id:"keyring", name:"Keyring",   emoji:"🔑", role:"신규 합류 · 참관",        color:"#a3e635", img:"./avatars/keyring.webp"}
  ];
  const byId = id => PEOPLE.find(p => p.id === id) || (id === "owner" ? {id:"owner", name:"오너", emoji:"👑", color:"#f5c04a"} : null);

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
  /* holder 안을 캐릭터 썸네일로 채운다. 로드 실패 시 이모지로 조용히 대체 */
  function faceInto(holder, p){
    holder.textContent = "";
    if(!p || !p.img){ holder.textContent = (p && p.emoji) || "•"; return holder; }
    const img = faceImg(p);
    img.addEventListener("error", function(){
      holder.classList.add("face-fallback");
      holder.textContent = p.emoji || "•";
    });
    holder.appendChild(img);
    return holder;
  }
  function faceBox(p, tag, cls){
    const h = document.createElement(tag || "div");
    h.className = cls || "facebox";
    return faceInto(h, p);
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
    orderLog:[]          // 재생 때마다 쌓이는 순서 기록 (검증·복기용)
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

  /* ═══════════════════ 타일 ═══════════════════ */
  const stage = $("#stage");
  const tileRefs = {};

  function buildTiles(ids){
    stage.innerHTML = "";
    Object.keys(tileRefs).forEach(k=>{ delete tileRefs[k]; });
    const list = (ids && ids.length ? ids : AIS).map(id=> byId(id)).filter(Boolean);
    list.forEach(p=>{
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

      const wrap = el("div","stagewrap");
      const bubble = el("div","bubble empty","안건을 고르면 준비해 온 자료가 여기에 열립니다.");
      wrap.append(bubble);

      const foot = el("div","tfoot");
      const wave = el("div","wave");
      for(let i=0;i<7;i++) wave.append(el("i"));
      const roleTag = el("div","who-role");
      roleTag.innerHTML = '<span class="mic">🔇</span>';
      const matbtn = el("button","matbtn ghost","자료 펼치기");
      matbtn.addEventListener("click", ()=> openMat(p.id));
      foot.append(wave, roleTag, matbtn);

      const qv = el("div","qveil");

      /* v4.2 화상 6분할용 얼굴 — 캐릭터 + 이름 + 상태/웨이브 (긴 본문 없음) */
      const vs = el("div","vstage");
      const vbob = el("div","vbob");
      faceInto(vbob, p);
      const vnm = el("div","vnm", p.name);
      const vmeta = el("div","vmeta");
      const vst = el("span","vstate","대기");
      const vw = el("div","vw");
      for(let i=0;i<5;i++) vw.append(el("i"));
      vmeta.append(vst, vw);
      vs.append(vbob, vnm, vmeta);
      const react = el("div","react");

      t.append(head, wrap, foot, vs, react, qv);
      stage.append(t);
      tileRefs[p.id] = {tile:t, state:st, bubble, matbtn, wave, vstate:vst, vbob, react, reactT:null};
    });
  }

  function setTileState(id, kind, label){
    const r = tileRefs[id]; if(!r) return;
    r.tile.classList.remove("speaking","assigned");
    r.state.classList.remove("s-speaking","s-ready","s-done","s-quiet");
    if(kind==="speaking"){ r.tile.classList.add("speaking"); r.state.classList.add("s-speaking"); }
    if(kind==="ready"){ r.tile.classList.add("matready"); r.state.classList.add("s-ready"); }
    if(kind==="assigned"){ r.tile.classList.add("assigned"); r.state.classList.add("s-done"); }
    if(kind==="quiet"){ r.state.classList.add("s-quiet"); }
    r.state.textContent = label || (kind==="speaking"?"발언 중":kind==="ready"?"자료 준비":kind==="assigned"?"배정":kind==="quiet"?"조용":"대기");
    if(r.vstate) r.vstate.textContent = videoLabel(r);
  }
  /* 화상 6분할 타일의 상태 문구 — 화상통화처럼 "듣는 중 / 발언 중"으로 보여 준다 */
  function videoLabel(r){
    if(!r) return "대기";
    if(r.tile.classList.contains("quiet")) return "조용";
    if(r.tile.classList.contains("speaking")) return "발언 중";
    if(state.phase === "roles") return "배정";
    if(!state.agenda) return "대기";
    return "듣는 중";
  }

  function renderBubble(id, tag, text, opts){
    const r = tileRefs[id]; if(!r) return;
    opts = opts || {};
    r.bubble.innerHTML = "";
    r.bubble.classList.remove("empty");
    if(tag) r.bubble.append(el("span","mtag", tag));
    if(opts.role) r.bubble.append(el("span","mrole", opts.role));
    r.bubble.append(el("span","msum", text));
    r.bubble.scrollTop = 0;
    if(opts.showBtn) r.matbtn.classList.remove("ghost");
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

  /* ═══════════════════ 안건 열기 ═══════════════════ */
  function openAgenda(id){
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

    toast("🗂️ 안건 열었습니다 · 주전 " + pc + "인 자료와 " + goal + "라운드 토론이 준비되어 있습니다");
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
        r.bubble.innerHTML = ""; r.bubble.classList.add("empty");
        r.bubble.textContent = "이번 안건 자료 없음";
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

  function focusTile(id){
    /* v4.2.1 — 자동 스크롤은 📝 글로 보기에서만. 🎥 화상 6분할 모드에서는 절대 실행하지 않는다.
       화면 밖으로 나간 카드만 부드럽게 끌어온다(이미 보이면 스크롤 자체를 하지 않아 흔들리지 않는다). */
    if(state.view !== "text") return;
    if(document.body.classList.contains("view-video")) return;
    const r = tileRefs[id];
    if(!r || !r.tile) return;
    const t = r.tile;
    const rect = t.getBoundingClientRect();
    const vh = window.innerHeight || document.documentElement.clientHeight;
    if(rect.top >= 4 && rect.bottom <= vh - 4) return;
    let smooth = true;
    try{ smooth = !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }catch(e){}
    t.scrollIntoView({behavior: smooth ? "smooth" : "auto", block: "nearest"});
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
    for(const id of order){
      if(token !== state.runToken) break;
      await waitIfPaused();
      if(token !== state.runToken) break;
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
    toast("🔔 새 회의 자료가 준비되었습니다 · " + fresh.length + "건");
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
  checkNewReady();

  // URL 파라미터: ?agenda=yt-growth / ?topic=새 주제
  try{
    const q = new URLSearchParams(location.search);
    const ag = q.get("agenda");
    const tp = q.get("topic");
    if(ag && LIB.byId && LIB.byId[ag]) openAgenda(ag);
    else if(tp){ openPlan(); document.getElementById("planTopic").value = tp; }
  }catch(e){}

  const unlockOnce = ()=>{ unlockVoice(); document.removeEventListener("pointerdown", unlockOnce); document.removeEventListener("touchstart", unlockOnce); };
  document.addEventListener("pointerdown", unlockOnce, {passive:true});
  document.addEventListener("touchstart", unlockOnce, {passive:true});

  // 테스트용 훅
  window.__mr4 = {
    state: state,
    setView: setView,
    focusTile: focusTile,
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
    rolesText: rolesText
  };
})();
