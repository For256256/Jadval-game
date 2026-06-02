// ===== بازی جدول کلمات فارسی =====
const TOTAL_LEVELS = 10;
const LEVEL_NAMES = ["آسان","ساده","مبتدی","متوسط","پیشرفته","دشوار","چالش","حرفه‌ای","استاد","افسانه‌ای"];

let state = {
  level: 1,
  data: null,
  dir: "across",
  activeClue: null,
  solved: {},          // "across-3" => true
  score: 0,
  unlocked: 1,
  done: {},            // level => true (رمز کشف شده)
};

const fa = n => String(n).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
const $ = id => document.getElementById(id);

// ---------- ذخیره/بازیابی پیشرفت (در حافظه، نه localStorage) ----------
function saveProgress(){ /* درون‌حافظه‌ای؛ بدون ذخیره دائمی طبق محدودیت محیط */ }

// ---------- بارگذاری مرحله ----------
async function loadLevel(n){
  state.level = n;
  state.dir = "across";
  state.activeClue = null;
  state.solved = {};
  $("grid").className = "loading";
  $("grid").innerHTML = '<div class="spinner"></div>آماده‌سازی جدول…';
  $("entry").style.display = "none";
  try{
    const r = await fetch(`/api/level/${n}`);
    const d = await r.json();
    if(d.error){ toast(d.error,"bad"); return; }
    state.data = d;
    renderLevels();
    renderBoard();
    renderClues();
    updateStats();
  }catch(e){ toast("خطا در ارتباط با سرور","bad"); }
}

// ---------- نوار مراحل ----------
function renderLevels(){
  const box = $("levels");
  box.innerHTML = "";
  for(let i=1;i<=TOTAL_LEVELS;i++){
    const el = document.createElement("div");
    el.className = "lvl";
    if(i===state.level) el.classList.add("active");
    if(state.done[i]) el.classList.add("done");
    if(i>state.unlocked) el.classList.add("locked");
    el.innerHTML = `<div class="n">${fa(i)}</div><div class="t">${LEVEL_NAMES[i-1]}</div>`;
    el.onclick = ()=>{ if(i<=state.unlocked) loadLevel(i); else toast("ابتدا مراحل قبل را کامل کن","bad"); };
    box.appendChild(el);
  }
}

// ---------- رسم جدول ----------
function renderBoard(){
  const d = state.data;
  $("board-name").textContent = `مرحلهٔ ${fa(d.level)} — ${d.name}`;
  $("board-count").textContent = `${fa(d.word_count)} کلمه`;
  const g = $("grid");
  g.className = "grid";
  g.style.gridTemplateColumns = `repeat(${d.cols}, var(--tile))`;
  g.innerHTML = "";
  const keySet = new Set((d.secret?.key_cells||[]).map(k=>k.row+","+k.col));
  for(let r=0;r<d.rows;r++){
    for(let c=0;c<d.cols;c++){
      const cell = d.grid[r][c];
      const div = document.createElement("div");
      div.className = "cell " + (cell? "open":"block");
      div.dataset.r = r; div.dataset.c = c;
      if(cell){
        if(cell.num) div.innerHTML += `<span class="num">${fa(cell.num)}</span>`;
        const ltr = document.createElement("div");
        ltr.className = "ltr"; ltr.dataset.pos = r+"_"+c;
        div.appendChild(ltr);
        div.onclick = ()=>onCellClick(r,c);
      }
      g.appendChild(div);
    }
  }
  updateProgress();
}

function cellAt(r,c){ return document.querySelector(`.cell[data-r="${r}"][data-c="${c}"]`); }

// کلیک روی خانه: نزدیک‌ترین سرنخ در جهت فعلی را انتخاب کن
function onCellClick(r,c){
  const d = state.data;
  const list = state.dir==="across"? d.across : d.down;
  let found = list.find(cl=>{
    if(state.dir==="across") return cl.row===r && c>=cl.col && c<cl.col+cl.len;
    return cl.col===c && r>=cl.row && r<cl.row+cl.len;
  });
  if(!found){
    // جهت دیگر را امتحان کن
    const other = state.dir==="across"? d.down : d.across;
    const od = state.dir==="across"? "down":"across";
    found = other.find(cl=>{
      if(od==="across") return cl.row===r && c>=cl.col && c<cl.col+cl.len;
      return cl.col===c && r>=cl.row && r<cl.row+cl.len;
    });
    if(found){ state.dir=od; switchTab(od); }
  }
  if(found) selectClue(found);
}

// ---------- سرنخ‌ها ----------
function renderClues(){
  const d = state.data;
  const list = state.dir==="across"? d.across : d.down;
  const box = $("clues");
  box.innerHTML = "";
  list.forEach(cl=>{
    const key = state.dir+"-"+cl.num;
    const el = document.createElement("div");
    el.className = "clue" + (state.solved[key]?" solved":"") + (state.activeClue&&state.activeClue.num===cl.num?" active":"");
    el.innerHTML = `<div class="cnum">${fa(cl.num)}</div>
      <div><div class="ctext">${cl.clue}</div><div class="clen">${fa(cl.len)} حرف</div></div>`;
    el.onclick = ()=>selectClue(cl);
    box.appendChild(el);
  });
}

function switchTab(dir){
  state.dir = dir;
  $("tab-across").classList.toggle("active", dir==="across");
  $("tab-down").classList.toggle("active", dir==="down");
  state.activeClue = null;
  $("entry").style.display = "none";
  clearHighlights();
  renderClues();
}

function clearHighlights(){
  document.querySelectorAll(".cell.sel,.cell.inword").forEach(e=>e.classList.remove("sel","inword"));
}

function clueCells(cl){
  const cells = [];
  for(let i=0;i<cl.len;i++){
    const r = cl.row + (state.dir==="down"?i:0);
    const c = cl.col + (state.dir==="across"?i:0);
    cells.push([r,c]);
  }
  return cells;
}

function selectClue(cl){
  state.activeClue = cl;
  renderClues();
  clearHighlights();
  clueCells(cl).forEach(([r,c],i)=>{
    const cell = cellAt(r,c);
    if(cell) cell.classList.add(i===0?"sel":"inword");
  });
  // ساخت جعبه‌های ورودی
  const entry = $("entry");
  entry.style.display = "block";
  $("entry-clue").textContent = `${state.dir==="across"?"افقی":"عمودی"} ${fa(cl.num)}: ${cl.clue}`;
  $("entry-meta").textContent = `${fa(cl.len)} حرف`;
  const boxes = $("boxes");
  boxes.innerHTML = "";
  const solvedKey = state.dir+"-"+cl.num;
  for(let i=0;i<cl.len;i++){
    const inp = document.createElement("input");
    inp.maxLength = 1; inp.dataset.i = i; inp.inputMode="text";
    // اگر قبلاً حل شده، حرف صحیح را نمایش بده
    const r = cl.row + (state.dir==="down"?i:0);
    const c = cl.col + (state.dir==="across"?i:0);
    const existing = document.querySelector(`.ltr[data-pos="${r}_${c}"]`)?.textContent;
    if(existing){ inp.value = existing; if(state.solved[solvedKey]) inp.classList.add("ok"); }
    inp.oninput = e=>{
      const v = e.target.value;
      if(v){ const nx = boxes.querySelector(`input[data-i="${i+1}"]`); if(nx) nx.focus(); }
    };
    inp.onkeydown = e=>{
      if(e.key==="Backspace" && !e.target.value){ const pv = boxes.querySelector(`input[data-i="${i-1}"]`); if(pv) pv.focus(); }
      if(e.key==="Enter") submitWord();
    };
    boxes.appendChild(inp);
  }
  setTimeout(()=>boxes.querySelector('input')?.focus(),50);
}

// ---------- ثبت پاسخ ----------
async function submitWord(){
  const cl = state.activeClue;
  if(!cl) return;
  const inputs = [...$("boxes").querySelectorAll("input")];
  const answer = inputs.map(i=>i.value).join("").trim();
  if(answer.length < cl.len){ toast("همهٔ خانه‌ها را پر کن","bad"); return; }
  try{
    const r = await fetch("/api/check",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({level:state.level,dir:state.dir,num:cl.num,answer})
    });
    const res = await r.json();
    if(res.correct){
      inputs.forEach(i=>i.classList.add("ok"));
      const key = state.dir+"-"+cl.num;
      state.solved[key] = true;
      state.score += cl.len * 10;
      // نوشتن حروف روی جدول
      clueCells(cl).forEach(([rr,cc],idx)=>{
        const ltr = document.querySelector(`.ltr[data-pos="${rr}_${cc}"]`);
        if(ltr){ ltr.textContent = inputs[idx].value; cellAt(rr,cc)?.classList.add("correct"); }
      });
      toast("آفرین! درست بود ✓","good");
      updateStats(); renderClues(); updateProgress();
      checkLevelComplete();
    }else{
      inputs.forEach(i=>{i.classList.add("bad");setTimeout(()=>i.classList.remove("bad"),400)});
      toast("نادرست است، دوباره تلاش کن","bad");
    }
  }catch(e){ toast("خطا در بررسی","bad"); }
}

// ---------- راهنما ----------
async function getHint(){
  const cl = state.activeClue;
  if(!cl) return;
  const inputs = [...$("boxes").querySelectorAll("input")];
  let pos = inputs.findIndex(i=>!i.value);
  if(pos<0) pos = 0;
  try{
    const r = await fetch("/api/reveal",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({level:state.level,dir:state.dir,num:cl.num,pos})
    });
    const res = await r.json();
    if(res.letter){
      inputs[pos].value = res.letter;
      const nx = inputs[pos+1]; if(nx) nx.focus();
      state.score = Math.max(0, state.score-5);
      updateStats();
      toast("یک حرف آشکار شد (−۵ امتیاز)");
    }
  }catch(e){}
}

// ---------- پیشرفت ----------
function updateProgress(){
  const d = state.data; if(!d) return;
  const total = d.across.length + d.down.length;
  const solved = Object.keys(state.solved).length;
  $("progress").style.width = (total? (solved/total*100):0) + "%";
}

function updateStats(){
  $("stat-level").textContent = fa(state.level);
  $("stat-score").textContent = fa(state.score);
}

// ---------- پایان مرحله ----------
function checkLevelComplete(){
  const d = state.data;
  const total = d.across.length + d.down.length;
  if(Object.keys(state.solved).length >= total){
    // نمایش خانه‌های کلیدی رمز
    (d.secret?.key_cells||[]).forEach(k=>{
      const cell = cellAt(k.row,k.col);
      if(cell){ cell.classList.add("key"); const dot=document.createElement("div"); dot.className="keydot"; cell.appendChild(dot); }
    });
    setTimeout(openSecret, 800);
  }
}

// ---------- مرحلهٔ کشف رمز ----------
function openSecret(){
  const sec = state.data.secret;
  if(!sec){ winLevel(); return; }
  $("secret-hint").textContent = sec.hint;
  const box = $("secret-boxes");
  box.innerHTML = "";
  for(let i=0;i<sec.length;i++){
    const inp = document.createElement("input");
    inp.maxLength=1; inp.dataset.i=i;
    inp.oninput = e=>{ if(e.target.value){ const nx=box.querySelector(`input[data-i="${i+1}"]`); if(nx) nx.focus(); } };
    inp.onkeydown = e=>{ if(e.key==="Enter") submitSecret(); 
      if(e.key==="Backspace"&&!e.target.value){const pv=box.querySelector(`input[data-i="${i-1}"]`);if(pv)pv.focus();} };
    box.appendChild(inp);
  }
  $("secret-modal").classList.add("show");
  setTimeout(()=>box.querySelector("input")?.focus(),300);
}

async function submitSecret(){
  const box = $("secret-boxes");
  const inputs = [...box.querySelectorAll("input")];
  const answer = inputs.map(i=>i.value).join("").trim();
  if(answer.length < state.data.secret.length){ toast("همهٔ خانه‌ها را پر کن","bad"); return; }
  try{
    const r = await fetch("/api/check_secret",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({level:state.level,answer})
    });
    const res = await r.json();
    if(res.correct){
      state.score += 100;
      state.done[state.level] = true;
      $("secret-modal").classList.remove("show");
      updateStats();
      winLevel();
    }else{
      inputs.forEach(i=>{i.style.borderColor="var(--rose)";setTimeout(()=>i.style.borderColor="",400)});
      toast("رمز نادرست است","bad");
    }
  }catch(e){ toast("خطا","bad"); }
}

let secretHintPos = 0;
async function secretHint(){
  const sec = state.data.secret;
  const box = $("secret-boxes");
  const inputs = [...box.querySelectorAll("input")];
  let pos = inputs.findIndex(i=>!i.value);
  if(pos<0) pos=0;
  // از key_cells استفاده می‌کنیم: حرف همان موقعیت
  const kc = sec.key_cells[pos];
  // حرف را از روی جدول حل‌شده می‌خوانیم
  const ltr = document.querySelector(`.ltr[data-pos="${kc.row}_${kc.col}"]`)?.textContent;
  if(ltr){ inputs[pos].value = ltr; const nx=inputs[pos+1]; if(nx) nx.focus(); state.score=Math.max(0,state.score-10); updateStats(); }
}

function winLevel(){
  if(state.level < TOTAL_LEVELS && state.unlocked < state.level+1) state.unlocked = state.level+1;
  renderLevels();
  const last = state.level >= TOTAL_LEVELS;
  $("win-title").textContent = last? "🎉 تبریک! بازی را کامل کردی!" : "رمز کشف شد!";
  $("win-text").textContent = last
    ? `همهٔ ۱۰ مرحله را با امتیاز ${fa(state.score)} به پایان رساندی. تو یک استاد جدول هستی!`
    : `عالی بود! امتیاز فعلی: ${fa(state.score)}. آمادهٔ مرحلهٔ بعد؟`;
  $("win-next").textContent = last? "شروع دوباره" : "مرحلهٔ بعد ←";
  $("win-modal").classList.add("show");
}

// ---------- رویدادها ----------
$("tab-across").onclick = ()=>switchTab("across");
$("tab-down").onclick = ()=>switchTab("down");
$("btn-go").onclick = submitWord;
$("btn-hint").onclick = getHint;
$("secret-go").onclick = submitSecret;
$("secret-hint-btn").onclick = secretHint;
$("win-next").onclick = ()=>{
  $("win-modal").classList.remove("show");
  if(state.level < TOTAL_LEVELS) loadLevel(state.level+1);
  else { state.score=0; state.done={}; state.unlocked=1; loadLevel(1); }
};

function toast(msg,type=""){
  const t = $("toast");
  t.textContent = msg; t.className = "toast show "+type;
  clearTimeout(t._t);
  t._t = setTimeout(()=>t.classList.remove("show"),2200);
}

// ---------- شروع ----------
loadLevel(1);

// ثبت سرویس‌ورکر برای PWA
if("serviceWorker" in navigator){
  navigator.serviceWorker.register("/sw.js").catch(()=>{});
}
