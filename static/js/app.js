const $ = (id) => document.getElementById(id);
const views = {chat: $("chatView"), docs: $("docsView"), eval: $("evalView")};
function showView(name) {
  Object.entries(views).forEach(([key, el]) => el.classList.toggle("hidden", key !== name));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  ({chat:$("chatNav"),docs:$("docsNav"),eval:$("evalNav")})[name].classList.add("active");
  $("pageTitle").textContent = ({chat:"Ask CampusMitra",docs:"Knowledge documents",eval:"System evaluation"})[name];
  if (name === "docs") loadDocuments();
}
$("chatNav").onclick = () => showView("chat");
$("docsNav").onclick = () => showView("docs");
$("evalNav").onclick = () => showView("eval");

async function refreshStatus() {
  try {
    const r = await fetch("/api/status"); const d = await r.json();
    $("statusText").textContent = d.document_count + " documents · " + d.chunk_count + " chunks";
  } catch { $("statusText").textContent = "Server connection issue"; }
}
function addMessage(text, type, sources=[]) {
  const wrap = document.createElement("div"); wrap.className = "message " + type;
  if (type === "bot") {
    const avatar = document.createElement("div"); avatar.className = "message-avatar"; avatar.textContent = "✦"; wrap.appendChild(avatar);
  }
  const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = text;
  if (sources.length) {
    const sourceBox = document.createElement("div"); sourceBox.className = "sources";
    const heading = document.createElement("b"); heading.textContent = "Sources used"; sourceBox.appendChild(heading);
    sources.forEach(s => {
      const item = document.createElement("div"); item.className = "source-item";
      const name = document.createElement("b"); name.textContent = s.filename;
      const detail = document.createElement("small"); detail.textContent = `Chunk ${s.chunk_id} · similarity ${s.similarity} · ${s.excerpt}`;
      item.append(name, detail); sourceBox.appendChild(item);
    });
    bubble.appendChild(sourceBox);
  }
  wrap.appendChild(bubble); $("messages").appendChild(wrap);
  wrap.scrollIntoView({behavior:"smooth",block:"nearest"});
}
async function ask(question) {
  if (!question.trim()) return;
  addMessage(question, "user"); $("questionInput").value = ""; $("sendButton").disabled = true;
  const loading = document.createElement("div"); loading.className = "message bot";
  loading.innerHTML = '<div class="message-avatar">✦</div><div class="bubble">Searching university documents…</div>';
  $("messages").appendChild(loading);
  try {
    const r = await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});
    const d = await r.json(); loading.remove();
    if (!r.ok) throw new Error(d.error || "Request failed");
    addMessage(d.answer + (d.response_time_seconds !== undefined ? `\n\nResponse time: ${d.response_time_seconds}s · Mode: ${d.mode}` : ""), "bot", d.sources || []);
  } catch(e) { loading.remove(); addMessage("Sorry, " + e.message, "bot"); }
  finally { $("sendButton").disabled = false; $("questionInput").focus(); }
}
$("chatForm").addEventListener("submit", e => {e.preventDefault(); ask($("questionInput").value);});
$("questionInput").addEventListener("keydown", e => {if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();$("chatForm").requestSubmit();}});
document.querySelectorAll(".suggestion").forEach(b => b.onclick = () => ask(b.dataset.question));

$("chooseFile").onclick = () => $("fileInput").click();
$("fileInput").onchange = async () => {
  const file = $("fileInput").files[0]; if (!file) return;
  $("uploadStatus").textContent = "Uploading, extracting and indexing…";
  const form = new FormData(); form.append("file",file);
  try {
    const r = await fetch("/api/upload",{method:"POST",body:form}); const d = await r.json();
    if (!r.ok) throw new Error(d.error);
    $("uploadStatus").textContent = d.message + ` (${d.chunks_added} chunks)`;
    loadDocuments(); refreshStatus();
  } catch(e) {$("uploadStatus").textContent = "Error: " + e.message;}
  $("fileInput").value = "";
};
async function loadDocuments() {
  try {
    const r = await fetch("/api/documents"); const d = await r.json();
    $("docCount").textContent = `${d.documents.length} document(s) indexed`;
    const list = $("documentList"); list.innerHTML = "";
    if (!d.documents.length) {list.innerHTML = '<div class="document-row">No documents uploaded yet.</div>';return;}
    d.documents.forEach(doc => {
      const row = document.createElement("div"); row.className = "document-row";
      const name = document.createElement("b"); name.textContent = "▤  " + doc.filename;
      const count = document.createElement("small"); count.textContent = doc.chunks + " chunks";
      row.append(name,count); list.appendChild(row);
    });
  } catch(e) {$("docCount").textContent = "Unable to load documents";}
}
$("rebuildBtn").onclick = async () => {
  $("rebuildBtn").disabled = true; $("rebuildBtn").textContent = "Rebuilding…";
  try {const r=await fetch("/api/rebuild",{method:"POST"});const d=await r.json();if(!r.ok)throw new Error(d.error);$("uploadStatus").textContent=d.message;loadDocuments();refreshStatus();}
  catch(e){$("uploadStatus").textContent="Error: "+e.message;}
  finally{$("rebuildBtn").disabled=false;$("rebuildBtn").textContent="↻ Rebuild index";}
};
$("runEvalBtn").onclick = async () => {
  $("runEvalBtn").disabled=true;$("runEvalBtn").textContent="Evaluating…";$("evalResults").innerHTML="<p>Running test questions. This may take a moment…</p>";
  try {
    const r=await fetch("/api/evaluate",{method:"POST"});const d=await r.json();if(!r.ok)throw new Error(d.error);
    $("evalResults").innerHTML="";
    const grid=document.createElement("div");grid.className="metric-grid";
    [["Correctness proxy",d.correctness_proxy_percent+"%"],["Grounded responses",d.grounded_response_percent+"%"],["Average response time",d.average_response_time_seconds+"s"]].forEach(([label,value])=>{const card=document.createElement("div");card.className="metric";const l=document.createElement("span");l.textContent=label;const v=document.createElement("strong");v.textContent=value;card.append(l,v);grid.append(card);});
    $("evalResults").append(grid);
    const note=document.createElement("p");note.className="note-box";note.textContent=d.method_note;$("evalResults").append(note);
    const table=document.createElement("table");table.className="result-table";table.innerHTML="<thead><tr><th>Question</th><th>Keyword coverage</th><th>Grounded</th><th>Time</th></tr></thead>";
    const body=document.createElement("tbody");
    d.results.forEach(x=>{const tr=document.createElement("tr");[x.question,(x.keyword_coverage*100).toFixed(1)+"%",x.grounded?"Yes":"No",x.response_time_seconds+"s"].forEach((v,i)=>{const td=document.createElement("td");td.textContent=v;if(i===2)td.className=x.grounded?"good":"bad";tr.append(td);});body.append(tr);});
    table.append(body);$("evalResults").append(table);
  } catch(e){$("evalResults").textContent="Evaluation failed: "+e.message;}
  finally{$("runEvalBtn").disabled=false;$("runEvalBtn").textContent="Run evaluation";}
};
refreshStatus();
