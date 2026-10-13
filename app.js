const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, body, method) {
  const r = await fetch("/api/" + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : { method: method || "GET" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || "Server error");
  return data;
}

/* Tabs */
$("#tabs").addEventListener("click", (e) => {
  const t = e.target.dataset.tab;
  if (!t) return;
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b === e.target));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("on", p.id === t));
  if (t === "plan") loadProgress();
});

/* Notes */
let docs = [];
const selected = new Set();
const ids = () => (selected.size ? [...selected] : null);

async function loadDocs() {
  docs = await api("docs");
  $("#docs").innerHTML = docs.map((d) =>
    `<li><label><input type="checkbox" data-id="${d.id}" ${selected.has(d.id) ? "checked" : ""} style="flex:0 0 auto"> ${esc(d.name)}</label>
     <button data-del="${d.id}" title="Hatao" aria-label="${esc(d.name)} hatao">×</button></li>`).join("");
  $("#docHint").style.display = docs.length ? "block" : "none";
}
$("#docs").addEventListener("change", (e) => {
  const id = Number(e.target.dataset.id);
  e.target.checked ? selected.add(id) : selected.delete(id);
});
$("#docs").addEventListener("click", async (e) => {
  const id = e.target.dataset.del;
  if (!id || !confirm("Ye notes hata dein?")) return;
  await api("docs/" + id, null, "DELETE");
  selected.delete(Number(id));
  loadDocs();
});

async function upload(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  $("#drop b").textContent = "Upload ho raha hai...";
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail);
    await loadDocs();
  } catch (err) { alert(err.message); }
  $("#drop b").textContent = "Notes upload karo";
}
$("#file").addEventListener("change", (e) => upload(e.target.files[0]));
const drop = $("#drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); upload(e.dataTransfer.files[0]); });

/* Chat */
let history = [];
function bubble(cls, text, src) {
  const log = $("#log");
  log.querySelector(".empty")?.remove();
  const d = document.createElement("div");
  d.className = "b " + cls;
  d.textContent = text;
  if (src && src.length) { const s = document.createElement("span"); s.className = "src"; s.textContent = "Source: " + src.join(", "); d.appendChild(s); }
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}
async function send() {
  const m = $("#msg").value.trim();
  if (!m) return;
  $("#msg").value = "";
  bubble("u", m);
  const wait = bubble("a", "Soch raha hoon...");
  $("#send").disabled = true;
  try {
    const r = await api("chat", { message: m, history, doc_ids: ids() });
    wait.remove();
    bubble("a", r.answer, r.sources);
    history.push({ role: "user", content: m }, { role: "assistant", content: r.answer });
  } catch (e) { wait.textContent = e.message; wait.classList.add("err"); }
  $("#send").disabled = false;
}
$("#send").onclick = send;
$("#msg").addEventListener("keydown", (e) => e.key === "Enter" && send());

/* Voice (browser ka Web Speech API, Chrome/Edge mein chalta hai) */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) { $("#mic").style.display = "none"; }
else {
  const rec = new SR();
  rec.lang = "hi-IN";
  rec.onresult = (e) => { $("#msg").value = e.results[0][0].transcript; send(); };
  rec.onend = () => { $("#mic").classList.remove("rec"); $("#mic").textContent = "Bolo"; };
  $("#mic").onclick = () => { $("#mic").classList.add("rec"); $("#mic").textContent = "Sun raha hoon..."; rec.start(); };
}

/* Quiz */
$("#qGo").onclick = async () => {
  const out = $("#qOut");
  out.innerHTML = '<p class="hint">Quiz ban raha hai...</p>';
  $("#qGo").disabled = true;
  try {
    const qs = await api("quiz", { doc_ids: ids(), count: Number($("#qCount").value), topic: $("#qTopic").value.trim() || null });
    renderQuiz(qs);
  } catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; }
  $("#qGo").disabled = false;
};
function renderQuiz(qs) {
  let score = 0, done = 0;
  const out = $("#qOut");
  out.innerHTML = '<div class="score" id="score"></div>';
  qs.forEach((q, qi) => {
    const box = document.createElement("div");
    box.className = "q";
    box.innerHTML = `<p>${qi + 1}. ${esc(q.question)}</p>` + q.options.map((o, i) => `<button class="opt" data-i="${i}">${esc(o)}</button>`).join("") + '<div class="why" hidden></div>';
    let answered = false;
    box.addEventListener("click", (e) => {
      const b = e.target.closest(".opt");
      if (!b || answered) return;
      answered = true;
      const pick = Number(b.dataset.i), ok = pick === q.answer;
      box.querySelectorAll(".opt").forEach((x, i) => { if (i === q.answer) x.classList.add("right"); else if (i === pick) x.classList.add("wrong"); });
      const why = box.querySelector(".why");
      why.hidden = false;
      why.textContent = (ok ? "Sahi! " : "Galat. ") + (q.explanation || "");
      done++; if (ok) score++;
      api("attempt", { topic: q.topic || "General", correct: ok }).catch(() => {});
      if (done === qs.length) $("#score").textContent = `Score: ${score} / ${qs.length}`;
    });
    out.appendChild(box);
  });
}

/* Flashcards */
$("#fGo").onclick = async () => {
  const out = $("#fOut");
  out.innerHTML = '<p class="hint">Flashcards ban rahe hain...</p>';
  $("#fGo").disabled = true;
  try {
    const cs = await api("flashcards", { doc_ids: ids(), count: Number($("#fCount").value), topic: $("#fTopic").value.trim() || null });
    out.innerHTML = '<div class="grid">' + cs.map((c) => `<button class="fc"><i class="ft">${esc(c.front)}</i><i class="bk">${esc(c.back)}</i></button>`).join("") + "</div>";
    out.querySelectorAll(".fc").forEach((el) => (el.onclick = () => el.classList.toggle("flip")));
  } catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; }
  $("#fGo").disabled = false;
};

/* Progress + plan */
async function loadProgress() {
  const p = await api("progress");
  if (!p.topics.length) return;
  $("#prog").innerHTML = p.topics.map((t) =>
    `<div class="row"><span>${esc(t.topic)}</span><div class="track"><div class="fill ${t.pct < 60 ? "low" : ""}" style="width:${t.pct}%"></div></div><span>${t.pct}% (${t.right}/${t.total})</span></div>`).join("");
}
$("#pGo").onclick = async () => {
  $("#pOut").textContent = "Plan ban raha hai...";
  $("#pGo").disabled = true;
  try {
    const r = await api("plan", { days_left: Number($("#days").value), hours_per_day: Number($("#hours").value), doc_ids: ids() });
    $("#pOut").textContent = r.plan;
  } catch (e) { $("#pOut").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
  $("#pGo").disabled = false;
};

loadDocs();
