
(function(){
  "use strict";

  /* ═══════════════════ 기본 정의 ═══════════════════ */
  const LIB = window.AGENDA_LIB || {agendas:[], byId:{}};
  const AIS = ["pickle","gemini","cue","hark","chatgpt","claude"];
  const PEOPLE = [
    {id:"pickle",  name:"피클(다크)", emoji:"⚡", role:"총괄 · 자료 취합·진행",   color:"#8b7cf6"},
    {id:"gemini",  name:"Gemini",    emoji:"🌀", role:"대본·카피·구조 분석",     color:"#4285f4"},
    {id:"cue",     name:"Cue",       emoji:"🔍", role:"트렌드·수치 리서치",      color:"#38bdf8"},
    {id:"hark",    name:"Hark",      emoji:"🧐", role:"검증·리스크·조건 확인",   color:"#f0a23c"},
    {id:"chatgpt", name:"ChatGPT",   emoji:"🛠️", role:"구조 설계·DB·자동화",     color:"#10a37f"},
    {id:"claude",  name:"Claude",    emoji:"✍️", role:"글쓰기·기획 검토",        color:"#d97757"}
  ];
  const byId = id => PEOPLE.find(p => p.id === id) || (id === "owner" ? {id:"owner", name:"오너", emoji:"👑", color:"#f5c04a"} : null);

  const K_SPEED = "darkjin_mr4_speed";
  const K_VOICE = "darkjin_mr4_voice";
  const K_SFX   = "darkjin_mr4_sfx";
  const K_REQ   = "darkjin_mr4_requests";
  const K_SEEN  = "darkjin_mr4_seen_ready";
  const K_NOTIFY= "darkjin_mr4_notify";

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
    readSet:{},
    rebutSet:{},
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
    matId:null
  };

  const $ = s => document.querySelector(s);
  const el = (tag, cls, txt) => { const n=document.createElement(tag); if(cls) n.className=cls; if(txt!==undefined) n.textContent=txt; return n; };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const pad = n => String(n).padStart(2,"0");
  const nowHM = () => { const d=new Date(); return pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds()); };
  const nowStamp = () => { const d=new Date(); return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes()); };
  const norm = s => String(s||"").replace(/\s+/g,"").replace(/[.,?!"'·:;()\[\]]/g,"").toLowerCase();

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
    claude:  {pitch:1.14, rate:0.88, tone:"작가 · 느긋"}
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
    stopListening(true); stopInterjectMic(true);
    const first = !state.paused;
    if(first){ state.paused = true; state.pausedAt = Date.now(); }
    AIS.forEach(id=>{
      const r = tileRefs[id]; if(!r) return;
      r.tile.classList.add("quiet");
      r.tile.classList.remove("speaking");
      r.state.classList.remove("s-speaking","s-ready","s-done");
      r.state.classList.add("s-quiet");
      r.state.textContent = "조용";
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
    AIS.forEach(restoreTileState);
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
    const b=document.getElementById("micBtn"); const f=document.getElementById("inputField");
    if(b){ b.classList.toggle("on",on); b.textContent = on?"■ 듣는 중":"🎤 말하기"; }
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
        const input=document.getElementById("reqTopic");
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
    micWant=true; micBase=($("#reqTopic").value||"").trim(); micFinal="";
    toast("🎤 듣는 중 … 주제를 말해 주세요");
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

  function buildTiles(){
    stage.innerHTML = "";
    PEOPLE.forEach(p=>{
      const t = el("div","tile");
      t.dataset.id = p.id;

      const head = el("div","thead");
      const av = el("div","avatar", p.emoji);
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
      t.append(head, wrap, foot, qv);
      stage.append(t);
      tileRefs[p.id] = {tile:t, state:st, bubble, matbtn, wave};
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
  function requests(){
    try{ return JSON.parse(LS.get(K_REQ)||"[]") || []; }catch(e){ return []; }
  }
  function saveRequests(list){ LS.set(K_REQ, JSON.stringify(list.slice(-20))); }
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
      list.append(el("div","qempty","아직 준비 완료된 안건이 없습니다. 아래에서 주제를 요청해 주세요."));
    }
    ready.forEach(a=>{
      const b = el("button","agcard" + (state.agenda && state.agenda.id === a.id ? " active" : ""));
      b.dataset.id = a.id;
      const cnt = a.panels ? Object.keys(a.panels).filter(k=>a.panels[k]).length : 0;
      b.append(el("span","tg", a.tag || "안건"));
      b.append(el("div","tt", a.title));
      b.append(el("div","bf", a.brief || ""));
      const mt = el("div","mt");
      const m1 = el("span"); m1.innerHTML = "자료 <b>"+cnt+"/6</b> 준비 완료";
      mt.append(m1);
      if(a.preparedAt) mt.append(el("span","", "· " + a.preparedAt));
      if(a.preparedBy) mt.append(el("span","", "· " + a.preparedBy));
      b.append(mt);
      b.addEventListener("click", ()=> openAgenda(a.id));
      list.append(b);
    });
    const cntEl = document.getElementById("readyCnt");
    const req = requests();
    const pending = req.filter(r=>!findReadyByTopic(r.topic)).length;
    cntEl.textContent = "준비 완료 " + ready.length + "건" + (pending ? " · 준비 중 " + pending + "건" : "");
    cntEl.classList.toggle("warn", pending > 0);
    renderQueue();
  }

  function renderQueue(){
    const list = document.getElementById("queueList");
    const empty = document.getElementById("queueEmpty");
    const req = requests();
    list.innerHTML = "";
    if(!req.length){ empty.style.display = "block"; return; }
    empty.style.display = "none";
    req.slice().reverse().forEach(r=>{
      const hit = findReadyByTopic(r.topic);
      const li = el("li","qitem" + (hit ? " ready" : ""));
      li.append(el("span","st", hit ? "준비 완료" : "자료 준비 중"));
      li.append(el("span","qt", r.topic));
      if(hit){
        const go = el("button","qb","열기");
        go.addEventListener("click", ()=> openAgenda(hit.id));
        li.append(go);
        const cp = el("button","qb","요청문");
        cp.addEventListener("click", ()=> copyText(requestText(r.topic)));
        li.append(cp);
      }else{
        const cp = el("button","qb","요청문 복사");
        cp.addEventListener("click", ()=> copyText(requestText(r.topic)));
        li.append(cp);
      }
      const x = el("button","qx","✕");
      x.title = "큐에서 빼기";
      x.addEventListener("click", ()=>{
        const cur = requests().filter(v=>v.at !== r.at || v.topic !== r.topic);
        saveRequests(cur); renderPrep(); toast("큐에서 뺐습니다");
      });
      li.append(x);
      list.append(li);
    });
  }

  function requestText(topic){
    return [
      "[회의 안건 요청] 다크진 AI 비서실 · 6분할 회의실",
      "",
      "주제: " + topic,
      "요청: 오너 darkjin / " + nowStamp(),
      "",
      "피클, 이 주제로 6분할 회의실 v4 사전 자료를 준비해 주세요.",
      "- 6인(피클·Gemini·Cue·Hark·ChatGPT·Claude)이 서로 겹치지 않는 사전 조사 자료를 각각 만들 것",
      "- 각 AI 자료: 핵심 요약 1~2문장 / 근거·데이터 2~3개 / 우려·반박 1개 / 제안 1개 / 자료 출처 한 줄",
      "- 확인 가능한 근거와 추정을 구분해서 적을 것",
      "- 결론 후보 2~3개와 후보별 6인 역할 분담을 함께 만들 것",
      "- 다 모이면 work/meeting-room/v4/agendas.js 에 안건을 추가하고 ready:true 로 표시",
      "",
      "자료가 모두 준비되면 '회의 준비 완료'로 알려 주세요. 그때까지 웹에는 '자료 준비 중'으로 남습니다."
    ].join("\n");
  }

  function addRequest(topic){
    const t = String(topic||"").replace(/\s+/g," ").trim();
    if(!t){ toast("주제를 적어 주세요"); return null; }
    const hit = findReadyByTopic(t);
    if(hit){ toast("이미 준비 완료된 안건입니다 · 목록에서 열어 주세요"); openAgenda(hit.id); return hit; }
    const list = requests();
    if(list.some(r=>norm(r.topic) === norm(t))){ toast("이미 큐에 있는 주제입니다"); return null; }
    list.push({topic:t, at:Date.now()});
    saveRequests(list); renderPrep();
    toast("➕ 안건 큐에 등록 — 피클이 자료를 모으면 '준비 완료'로 바뀝니다");
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
    state.readSet = {}; state.rebutSet = {};
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

    renderPrep();
    renderMaterials();
    renderOwnerChips();
    document.getElementById("prepCard").classList.add("has-agenda");
    document.getElementById("prepCard").classList.add("collapsed");
    document.getElementById("curAgendaTitle").textContent = a.title;
    document.getElementById("prepToggle").textContent = "다른 안건 ▾";

    setStep(1);
    setStageHead("1단계","준비된 자료 보기 & 주제 논의", "자료 " + Object.keys(a.panels).length + " / 6", false);
    setLive("자료 열람", "");
    startClock(0);
    SFX.ding();

    showReadyBanner(true);
    document.getElementById("refNote").innerHTML =
      "자료 출처는 각 패널의 <b>자료 펼치기</b>에서 확인할 수 있습니다. " +
      "<b>Meta Muse · Keyring</b>은 이번 안건 자료를 아직 내지 않아 6분할에 넣지 않았습니다.";

    clearMinEmpty();
    minList.innerHTML = ""; minN = 0; minCountEl.textContent = "0건";
    talkList.innerHTML = ""; talkN = 0; talkCountEl.textContent = "0건";
    const te = el("li","talk-empty", "자료 6/6 도착 — 카드를 펼쳐 읽고, 📖 자료 낭독이나 🔁 반박 라운드로 6인의 관점 차이를 확인하세요. 아래 💬 오너 코멘트로 방향을 잡으면 결론 후보가 좁혀집니다.");
    te.id = "talkEmpty"; talkList.append(te);

    addSystem('안건 열람 — "' + a.title + '" (자료 ' + Object.keys(a.panels).length + '/6 · ' + (a.preparedAt||"") + ")");
    addSystem("1단계 · 역할 분담은 결론을 확정한 뒤에 나옵니다");

    $("#reqTopic").value = "";
    toast("🗂️ 안건 열었습니다 · 6인 자료가 준비되어 있습니다");
    const sh = document.getElementById("stageHd");
    if(sh) sh.scrollIntoView({block:"start"});
  }

  function renderMaterials(){
    const a = state.agenda;
    AIS.forEach(id=>{
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
    const rb = document.getElementById("matRebuttal");
    if(p.rebuttal && p.rebuttal.text){
      const to = byId(p.rebuttal.to);
      rb.textContent = "→ " + (to?to.name:p.rebuttal.to) + " : " + p.rebuttal.text;
    } else rb.textContent = "—";
    document.getElementById("matSource").textContent = p.source || "";
    document.getElementById("matModal").classList.add("show");
  }

  /* ═══════════════════ 1단계: 자료 낭독 ═══════════════════ */
  function setBarBusy(v){
    state.busy = !!v;
    ["readBtn","rebutBtn","toConfirmBtn","confirmRoleBtn","backToTalkBtn"].forEach(i=>{
      const b = document.getElementById(i);
      if(b) b.disabled = state.busy;
    });
  }

  async function readAll(){
    if(!state.agenda || state.busy) return;
    setBarBusy(true);
    const token = ++state.runToken;
    state.phase = "materials";
    addSystem("📖 자료 낭독 — 6인이 준비해 온 요약을 차례로 읽습니다");
    for(const id of AIS){
      if(token !== state.runToken) break;
      await waitIfPaused();
      if(token !== state.runToken) break;
      const p = state.agenda.panels[id];
      if(!p) continue;
      renderBubble(id, "준비 자료", p.summary, {showBtn:true});
      await speakLine(id, p.summary, {label:"자료 낭독"});
      if(token !== state.runToken) break;
      if(!state.readSet[id]){ addTalk(id, "read", p.summary); state.readSet[id] = true; }
      setTileState(id,"ready","낭독 완료");
      await psleep(150/state.speed);
    }
    if(token === state.runToken){
      state.phase = "discussion";
      setStep(2);
      setStageHead("1단계","논의 — 반박 라운드로 관점 차이를 확인", "낭독 " + Object.keys(state.readSet).length + " / 6", false);
      setLive("논의 중", "");
      addSystem("자료 낭독 완료 — 이제 반박 라운드로 서로 다른 관점을 확인합니다");
      toast("📖 낭독 끝 · 이제 🔁 반박 라운드로 넘어가세요");
    }
    setBarBusy(false);
  }

  /* ═══════════════════ 1단계: 반박 라운드 ═══════════════════ */
  async function rebuttalRound(){
    if(!state.agenda || state.busy) return;
    setBarBusy(true);
    const token = ++state.runToken;
    state.phase = "discussion";
    setStep(2);
    setStageHead("1단계","논의 — 6인이 서로의 자료에 반박·보완", "반박 0 / 6", false);
    addSystem("🔁 반박 라운드 — 각자 다른 AI의 자료를 짚고 반박합니다");
    let n = 0;
    for(const id of AIS){
      if(token !== state.runToken) break;
      await waitIfPaused();
      if(token !== state.runToken) break;
      const p = state.agenda.panels[id];
      if(!p || !p.rebuttal || !p.rebuttal.text) continue;
      const to = byId(p.rebuttal.to);
      renderBubble(id, "반박 → " + (to?to.name:p.rebuttal.to), p.rebuttal.text, {showBtn:true});
      await speakLine(id, p.rebuttal.text, {label:"반박 중"});
      if(token !== state.runToken) break;
      if(!state.rebutSet[id]){ addTalk(id, "rebut", p.rebuttal.text, {to:p.rebuttal.to}); state.rebutSet[id] = true; }
      setTileState(id,"ready","반박 완료");
      n++;
      setStageHead("1단계","논의 — 6인이 서로의 자료에 반박·보완", "반박 " + n + " / 6", false);
      await psleep(150/state.speed);
    }
    if(token === state.runToken){
      setLive("오너 결정 대기", "owner");
      addSystem("반박 라운드 완료 — 오너가 결론을 확정하면 역할 분담이 나옵니다");
      toast("🔁 반박 6건 끝 · ✅ 결론 확정으로 넘어가세요");
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
    AIS.forEach(id=>{
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
        document.getElementById("cfMeta").textContent = "선택: " + o.id + " · 반박 " + Object.keys(state.rebutSet).length + "건";
      });
      list.append(b);
    });
    document.getElementById("cfMeta").textContent = "결론 후보 " + opts.length + " · 반박 " + Object.keys(state.rebutSet).length + "건 반영";
    document.getElementById("confirmPanel").classList.add("show");
    addSystem("결론 확정 단계 — 오너가 후보를 고르고 역할 분담이 생성됩니다");
    document.getElementById("confirmPanel").scrollIntoView({block:"center", behavior:"smooth"});
  }

  function backToTalk(){
    state.phase = "discussion";
    setStep(2);
    document.getElementById("confirmPanel").classList.remove("show");
    document.getElementById("stage1Bar").style.display = "";
    setLive("논의 중", "");
    toast("↩️ 논의로 돌아왔습니다");
    window.scrollTo({top:0, behavior:"smooth"});
  }

  function confirmRoles(){
    if(!state.agenda) return;
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
    AIS.forEach(id=>{
      const p = byId(id);
      const card = el("div","ac"); card.dataset.id = id;
      const body = el("div");
      body.append(el("div","nm", p.name), el("div","tx", roles[id] || "역할 미정"));
      card.append(el("div","em", p.emoji), body);
      list.append(card);
      renderBubble(id, "맡은 일", roles[id] || "역할 미정", {role:"2단계 · 역할 분담", showBtn:false});
      setTileState(id,"assigned","배정");
      tileRefs[id].matbtn.classList.add("ghost");
    });

    const fin = document.getElementById("finalText");
    fin.textContent = a.closing || "역할 분담대로 진행하고, 결과는 다음 회의에서 복기합니다.";
    document.getElementById("finalBlock").classList.add("show");

    setStageHead("2단계","결론 확정 → 역할 분담", "배정 6 / 6", true);
    setLive("역할 분담 완료", "done");
    addSystem("✅ 결론 확정 — 후보 " + opt.id + " · 역할 6건 배정");
    AIS.forEach(id=>{
      if(roles[id]) addTalk(id,"sys", "배정 — " + roles[id]);
    });
    toast("🧩 역할 분담 완료 · 복사해서 피클에게 넘기세요");
    const sh2 = document.getElementById("stageHd");
    if(sh2) sh2.scrollIntoView({block:"start"});

    const token = state.runToken;
    speakLine("pickle", "결론 확정했습니다. " + opt.title + ". 역할 여섯 개를 나눴습니다.", {label:"결론 확정"})
      .then(()=>{ if(token === state.runToken){ AIS.forEach(id=>{ if(state.phase==="roles") setTileState(id,"assigned","배정"); }); } });
  }

  function newMeeting(){
    state.runToken++;
    state.phase = "idle";
    state.agenda = null; state.option = null; state.ownerDir = "";
    state.notes = []; state.readSet = {}; state.rebutSet = {};
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
    AIS.forEach(id=>{
      const r = tileRefs[id]; if(!r) return;
      r.bubble.innerHTML = ""; r.bubble.classList.add("empty");
      r.bubble.textContent = "안건을 고르면 준비해 온 자료가 여기에 열립니다.";
      r.matbtn.classList.add("ghost");
      setTileState(id,"","대기");
    });
    setStep(0);
    setStageHead("1단계","안건을 고르면 6인이 준비해 온 자료가 열립니다","자료 0 / 6",false);
    setLive("준비실", "");
    renderPrep();
    window.scrollTo({top:0, behavior:"smooth"});
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
    AIS.forEach(id=>{
      const p = byId(id);
      L.push("- " + p.name + " (" + p.role + ") — " + (roles[id] || "미정"));
    });
    L.push("");
    L.push("### 다음 단계");
    L.push(a.closing || "");
    L.push("");
    L.push("### 준비 자료 요약");
    AIS.forEach(id=>{
      const p = a.panels[id]; if(!p) return;
      L.push("- " + byId(id).name + ": " + p.summary);
    });
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
    const cnt = Object.keys(a.panels||{}).length;
    document.getElementById("readyTitle").textContent = "회의 준비 완료 — " + a.title;
    document.getElementById("readySub").textContent = "6인 자료 " + cnt + "/6 · 준비 " + (a.preparedAt||"") + " · " + (a.preparedBy||"");
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

  /* ═══════════════════ 이벤트 ═══════════════════ */
  document.getElementById("readBtn").addEventListener("click", ()=>{ unlockVoice(); readAll(); });
  document.getElementById("rebutBtn").addEventListener("click", ()=>{ unlockVoice(); rebuttalRound(); });
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
    AIS.forEach(id=>{ const r=tileRefs[id]; if(r) r.matbtn.classList.remove("ghost"); });
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
  document.querySelectorAll("[data-close]").forEach(n=> n.addEventListener("click", ()=>{
    if(n.closest("#matModal")) document.getElementById("matModal").classList.remove("show");
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

  document.getElementById("reqCopy").addEventListener("click", ()=>{
    const t = ($("#reqTopic").value||"").trim();
    if(!t){ toast("주제를 먼저 적어 주세요"); return; }
    copyText(requestText(t));
  });
  document.getElementById("reqQueue").addEventListener("click", ()=>{
    const t = ($("#reqTopic").value||"").trim();
    const hit = addRequest(t);
    if(!hit) $("#reqTopic").value = "";
  });
  $("#reqTopic").addEventListener("keydown", e=>{ if(e.key === "Enter"){ e.preventDefault(); document.getElementById("reqQueue").click(); } });

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
    if(e.key === "Escape"){ closeSettings(); document.getElementById("matModal").classList.remove("show"); }
    const tag = (e.target && e.target.tagName) || "";
    if((e.key === "q" || e.key === "Q") && !/input|textarea/i.test(tag)){ if(state.paused) resumeAll(); else quietAll(); }
  });

  /* ═══════════════════ 시작 ═══════════════════ */
  buildTiles();
  setStep(0);
  setStageHead("1단계","안건을 고르면 6인이 준비해 온 자료가 열립니다","자료 0 / 6",false);
  setVoice(state.voiceOn, true);
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
    else if(tp) document.getElementById("reqTopic").value = tp;
  }catch(e){}

  const unlockOnce = ()=>{ unlockVoice(); document.removeEventListener("pointerdown", unlockOnce); document.removeEventListener("touchstart", unlockOnce); };
  document.addEventListener("pointerdown", unlockOnce, {passive:true});
  document.addEventListener("touchstart", unlockOnce, {passive:true});

  // 테스트용 훅
  window.__mr4 = {
    state: state,
    agendaIds: () => (LIB.agendas||[]).map(a=>a.id),
    openAgenda: openAgenda,
    readAll: readAll,
    rebuttalRound: rebuttalRound,
    submitComment: submitComment,
    openConfirm: openConfirm,
    confirmRoles: confirmRoles,
    rolesText: rolesText
  };
})();
