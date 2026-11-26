
(() => {
  window.__spoken = [];
  class MockUtterance { constructor(t){ this.text=t; this.lang=''; this.pitch=1; this.rate=1; this.volume=1; } }
  window.SpeechSynthesisUtterance = MockUtterance;
  const voices=[{name:'Test Korean A',lang:'ko-KR'},{name:'Test Korean B',lang:'ko-KR'},{name:'Test Korean C',lang:'ko-KR'}];
  const synth={ speaking:false,pending:false,paused:false,_t:null,
    getVoices(){return voices;},
    speak(u){ window.__spoken.push(u.text); this.speaking=true; this.pending=false;
      setTimeout(()=>{ if(u.onstart) u.onstart(); },3);
      clearTimeout(this._t); this._t=setTimeout(()=>{ this.speaking=false; if(u.onend) u.onend(); },25); },
    cancel(){ this.speaking=false; this.pending=false; },
    pause(){ this.paused=true; }, resume(){ this.paused=false; }
  };
  Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
  class MockSR { constructor(){ window.__sr=this; } start(){} stop(){ if(this.onend) this.onend(); } abort(){ if(this.onend) this.onend(); } }
  window.SpeechRecognition=MockSR; window.webkitSpeechRecognition=MockSR;
  // v4.2 — scrollIntoView(smooth) 호출 감시 (iOS 떨림 원인 제거 확인용)
  window.__siv=[];
  const __siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(o){ window.__siv.push((o&&o.behavior)||"auto"); return __siv.apply(this, arguments); };
})();
