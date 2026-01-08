<script>
(function(){
  const $ = (id)=>document.getElementById(id);

  // ---------- tiny utils ----------
  function toast(title, msg){
    const t = $("toast");
    $("toastTitle").textContent = title;
    $("toastMsg").textContent = msg;
    t.style.display = "block";
    clearTimeout(toast._t);
    toast._t = setTimeout(()=> t.style.display = "none", 3600);
  }
  function safeJson(raw){
    try { return JSON.parse(raw); } catch { return null; }
  }
  function uid(){
    return Math.random().toString(16).slice(2) + Date.now().toString(16);
  }
  function lsGet(key, fallback){
    try{
      const v = localStorage.getItem(key);
      return v ? JSON.parse(v) : fallback;
    }catch{ return fallback; }
  }
  function lsSet(key, val){
    localStorage.setItem(key, JSON.stringify(val));
  }
  function bytes(n){
    if(!Number.isFinite(n)) return "";
    const u = ["B","KB","MB","GB"];
    let i=0, x=n;
    while(x>=1024 && i<u.length-1){ x/=1024; i++; }
    return (i===0? x : x.toFixed(1)) + " " + u[i];
  }

  // ---------- state (localStorage scaffolding) ----------
  const STATE_KEY = "bn_state_v1";

  function getState(){
    return lsGet(STATE_KEY, {
      studentName: (localStorage.getItem("bn_student_name") || "Student"),
      plan: "PRO",
      projects: [
        { id:"p1", name:"Anatomy — Unit 3 Review", status:"ACTIVE", updated:"yesterday" },
        { id:"p2", name:"Math — Fractions & Ratios", status:"DRAFT", updated:"2d ago" },
        { id:"p3", name:"Chemistry — Periodic Trends", status:"NEEDS LOVE", updated:"3d ago" }
      ],
      folders: [
        { id:"f1", name:"Notes" },
        { id:"f2", name:"Uploads" },
        { id:"f3", name:"Quizzes" }
      ],
      files: [],
      activeProjectId: "p1",
      activeFolderId: "f1"
    });
  }
  function setState(s){ lsSet(STATE_KEY, s); }

  function activeProject(state){
    return state.projects.find(p=>p.id===state.activeProjectId) || null;
  }
  function activeFolder(state){
    return state.folders.find(f=>f.id===state.activeFolderId) || null;
  }

  // ---------- Tutor modal ----------
  function ensureTutorModal(){
    if ($("tutorModal")) return;

    const wrap = document.createElement("div");
    wrap.id = "tutorModal";
    wrap.style.cssText = `
      position:fixed; inset:0; display:none; z-index:60;
      background:rgba(0,0,0,.55); backdrop-filter: blur(8px);
      padding:14px;
    `;
    wrap.innerHTML = `
      <div style="
        max-width:980px; margin:4vh auto; border:1px solid rgba(230,242,236,.12);
        border-radius:22px; background:rgba(10,18,13,.92); box-shadow: 0 22px 60px rgba(0,0,0,.55);
        overflow:hidden;">
        <div style="padding:14px 16px; border-bottom:1px solid rgba(230,242,236,.10); display:flex; align-items:center; justify-content:space-between; gap:10px;">
          <div style="font-weight:950; letter-spacing:.2px;">Tutor Session • Dr. Botonic</div>
          <div style="display:flex; gap:8px;">
            <button id="tutorClear" class="btn secondary" type="button">Clear</button>
            <button id="tutorClose" class="btn" type="button">Close</button>
          </div>
        </div>
        <div style="display:grid; grid-template-columns: 1fr 320px; gap:12px; padding:14px;">
          <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); overflow:hidden;">
            <div id="tutorChat" style="height:52vh; overflow:auto; padding:12px;">
              <div style="opacity:.75; font-size:13px; line-height:1.45;">
                Ask anything. I’ll answer like a real tutor: clear, step-by-step, no fluff.
              </div>
            </div>
            <div style="border-top:1px solid rgba(230,242,236,.10); padding:10px; display:flex; gap:10px; flex-wrap:wrap;">
              <input id="tutorInput" class="input" placeholder="Type your question…" />
              <button id="tutorSend" class="btn" type="button">Send</button>
            </div>
          </div>

          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); padding:12px;">
              <div style="font-weight:950; font-size:13px; letter-spacing:.2px;">Session Context</div>
              <div style="margin-top:10px; font-size:12px; color:rgba(230,242,236,.70); line-height:1.4;">
                <div><b>Project:</b> <span id="ctxProject">—</span></div>
                <div style="margin-top:6px;"><b>Folder:</b> <span id="ctxFolder">—</span></div>
              </div>
            </div>

            <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); padding:12px;">
              <div style="font-weight:950; font-size:13px; letter-spacing:.2px;">Quick Actions</div>
              <div style="margin-top:10px; display:flex; flex-direction:column; gap:10px;">
                <button id="qaQuiz" class="btn secondary" type="button">Generate quick quiz</button>
                <button id="qaPlan" class="btn secondary" type="button">Build a 7-day plan</button>
                <button id="qaExplain" class="btn secondary" type="button">Explain like I’m 12</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(wrap);

    wrap.addEventListener("click", (e)=>{ if(e.target === wrap) closeTutor(); });
    $("tutorClose").addEventListener("click", closeTutor);

    $("tutorClear").addEventListener("click", ()=>{
      lsSet("bn_chat_history", []);
      $("tutorChat").innerHTML = `<div style="opacity:.75; font-size:13px; line-height:1.45;">Cleared. Ask anything.</div>`;
      toast("Session cleared", "Chat history cleared for this device.");
    });

    $("tutorSend").addEventListener("click", ()=> sendTutor());
    $("tutorInput").addEventListener("keydown", (e)=>{ if(e.key === "Enter") sendTutor(); });

    $("qaQuiz").addEventListener("click", ()=>{ $("tutorInput").value = "Make me a quick quiz on my current topic. Ask 5 questions first to calibrate me."; $("tutorInput").focus(); });
    $("qaPlan").addEventListener("click", ()=>{ $("tutorInput").value = "Build me a 7-day study plan with 30-60 minute sessions and checkpoints."; $("tutorInput").focus(); });
    $("qaExplain").addEventListener("click", ()=>{
      const cur = $("tutorInput").value.trim();
      $("tutorInput").value = cur ? `Explain this like I'm 12: ${cur}` : "Explain the concept like I'm 12, with a simple example.";
      $("tutorInput").focus();
    });
  }

  function openTutor(){
    ensureTutorModal();
    $("tutorModal").style.display = "block";
    document.body.style.overflow = "hidden";
    syncContext();
    loadTutorHistory();
    setTimeout(()=> $("tutorInput").focus(), 50);
  }
  function closeTutor(){
    $("tutorModal").style.display = "none";
    document.body.style.overflow = "";
  }

  // FIXED: real context from IDs
  function syncContext(){
    const state = getState();
    const p = activeProject(state);
    const f = activeFolder(state);
    if ($("ctxProject")) $("ctxProject").textContent = p?.name || "—";
    if ($("ctxFolder")) $("ctxFolder").textContent  = f?.name || "—";
  }

  // ---------- Workspace modal (Projects / Files / Settings) ----------
  function ensureWorkspaceModal(){
    if ($("wsModal")) return;

    const wrap = document.createElement("div");
    wrap.id = "wsModal";
    wrap.style.cssText = `
      position:fixed; inset:0; display:none; z-index:65;
      background:rgba(0,0,0,.55); backdrop-filter: blur(8px);
      padding:14px;
    `;
    wrap.innerHTML = `
      <div style="
        max-width:980px; margin:4vh auto; border:1px solid rgba(230,242,236,.12);
        border-radius:22px; background:rgba(10,18,13,.92); box-shadow: 0 22px 60px rgba(0,0,0,.55);
        overflow:hidden;">
        <div style="padding:14px 16px; border-bottom:1px solid rgba(230,242,236,.10); display:flex; align-items:center; justify-content:space-between; gap:10px;">
          <div style="font-weight:950; letter-spacing:.2px;">Workspace</div>
          <div style="display:flex; gap:8px;">
            <button id="wsClose" class="btn" type="button">Close</button>
          </div>
        </div>

        <div style="padding:12px 16px; border-bottom:1px solid rgba(230,242,236,.10); display:flex; gap:8px; flex-wrap:wrap;">
          <button id="wsTabProjects" class="btn secondary" type="button">Projects</button>
          <button id="wsTabFiles" class="btn secondary" type="button">Files</button>
          <button id="wsTabSettings" class="btn secondary" type="button">Settings</button>
          <div style="margin-left:auto; display:flex; gap:8px; flex-wrap:wrap;">
            <button id="wsNewProject" class="btn secondary" type="button">New project</button>
            <button id="wsNewFolder" class="btn secondary" type="button">New folder</button>
            <button id="wsUpload" class="btn" type="button">Upload</button>
          </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 320px; gap:12px; padding:14px;">
          <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); padding:12px; min-height:52vh;">
            <div id="wsMain"></div>
          </div>
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); padding:12px;">
              <div style="font-weight:950; font-size:13px; letter-spacing:.2px;">Active Context</div>
              <div style="margin-top:10px; font-size:12px; color:rgba(230,242,236,.75); line-height:1.5;">
                <div><b>Project:</b> <span id="wsCtxProject">—</span></div>
                <div><b>Folder:</b> <span id="wsCtxFolder">—</span></div>
                <div style="margin-top:8px;"><b>Plan:</b> <span id="wsCtxPlan">—</span></div>
              </div>
            </div>

            <div style="border:1px solid rgba(230,242,236,.10); border-radius:18px; background:rgba(255,255,255,.03); padding:12px;">
              <div style="font-weight:950; font-size:13px; letter-spacing:.2px;">Power Moves</div>
              <div style="margin-top:10px; display:flex; flex-direction:column; gap:10px;">
                <button id="wsExport" class="btn secondary" type="button">Export local data</button>
                <button id="wsClearAll" class="btn secondary" type="button">Clear local data</button>
              </div>
              <div style="margin-top:10px; font-size:11px; color:rgba(230,242,236,.55); line-height:1.35;">
                Local storage is temporary. Next step: Supabase (real student accounts + storage).
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(wrap);

    wrap.addEventListener("click", (e)=>{ if(e.target === wrap) closeWorkspace(); });
    $("wsClose").addEventListener("click", closeWorkspace);

    $("wsTabProjects").addEventListener("click", ()=> renderWorkspace("projects"));
    $("wsTabFiles").addEventListener("click", ()=> renderWorkspace("files"));
    $("wsTabSettings").addEventListener("click", ()=> renderWorkspace("settings"));

    $("wsNewProject").addEventListener("click", ()=> createProject());
    $("wsNewFolder").addEventListener("click", ()=> createFolder());
    $("wsUpload").addEventListener("click", ()=> uploadFiles());

    $("wsExport").addEventListener("click", ()=>{
      const s = getState();
      const blob = new Blob([JSON.stringify(s, null, 2)], { type:"application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "botnology-local-data.json";
      a.click();
      toast("Exported", "Downloaded local workspace data.");
    });

    $("wsClearAll").addEventListener("click", ()=>{
      if(!confirm("Clear ALL local workspace data on this device?")) return;
      localStorage.removeItem(STATE_KEY);
      localStorage.removeItem("bn_chat_history");
      localStorage.removeItem("bn_student_name");
      toast("Cleared", "Local data wiped. Refreshing state…");
      renderProjectCardsFromState();
      renderWorkspace("projects");
      syncContext();
    });
  }

  function openWorkspace(tab){
    ensureWorkspaceModal();
    $("wsModal").style.display = "block";
    document.body.style.overflow = "hidden";
    renderWorkspace(tab || "projects");
  }
  function closeWorkspace(){
    $("wsModal").style.display = "none";
    document.body.style.overflow = "";
  }

  function renderWorkspace(tab){
    const s = getState();
    const p = activeProject(s);
    const f = activeFolder(s);

    $("wsCtxProject").textContent = p?.name || "—";
    $("wsCtxFolder").textContent  = f?.name || "—";
    $("wsCtxPlan").textContent    = s.plan || "—";

    // tab button emphasis
    const tabs = ["Projects","Files","Settings"];
    tabs.forEach(t=>{
      const el = $("wsTab"+t);
      if(el){
        el.classList.add("secondary");
        el.style.borderColor = "rgba(230,242,236,.14)";
      }
    });

    const main = $("wsMain");
    if(!main) return;

    if(tab === "projects"){
      $("wsTabProjects").style.borderColor = "rgba(191,230,208,.55)";

      const rows = s.projects.map(pr => `
        <div data-pid="${pr.id}" style="border:1px solid rgba(230,242,236,.10); border-radius:16px; padding:12px; background:rgba(255,255,255,.03); display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:10px; cursor:pointer;">
          <div style="min-width:0;">
            <div style="font-weight:950; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(pr.name)}</div>
            <div style="margin-top:6px; font-size:12px; color:rgba(230,242,236,.62);">Status: ${escapeHtml(pr.status)} • Updated: ${escapeHtml(pr.updated || "")}</div>
          </div>
          <div style="display:flex; gap:8px; flex:0 0 auto;">
            <button data-act="rename" data-pid="${pr.id}" class="btn secondary" type="button" style="padding:8px 10px; border-radius:12px; font-size:12px;">Rename</button>
            <button data-act="delete" data-pid="${pr.id}" class="btn secondary" type="button" style="padding:8px 10px; border-radius:12px; font-size:12px;">Delete</button>
          </div>
        </div>
      `).join("");

      main.innerHTML = `
        <div style="font-weight:950; letter-spacing:.2px; margin-bottom:10px;">Projects</div>
        ${rows || `<div style="opacity:.75;">No projects yet.</div>`}
        <div style="margin-top:12px; font-size:11px; color:rgba(230,242,236,.55);">Click a project to set it active.</div>
      `;

      // click handlers
      main.querySelectorAll("[data-pid]").forEach(el=>{
        el.addEventListener("click", (e)=>{
          const pid = el.getAttribute("data-pid");
          // ignore button clicks (handled below)
          if(e.target && e.target.getAttribute && e.target.getAttribute("data-act")) return;
          const s2 = getState();
          s2.activeProjectId = pid;
          setState(s2);
          toast("Project selected", activeProject(s2)?.name || "Selected");
          syncContext();
          renderProjectCardsFromState();
          renderWorkspace("projects");
        });
      });

      main.querySelectorAll("button[data-act]").forEach(btn=>{
        btn.addEventListener("click", (e)=>{
          e.preventDefault(); e.stopPropagation();
          const act = btn.getAttribute("data-act");
          const pid = btn.getAttribute("data-pid");
          if(act === "rename"){
            const s2 = getState();
            const pr = s2.projects.find(x=>x.id===pid);
            if(!pr) return;
            const name = prompt("Rename project:", pr.name);
            if(!name) return;
            pr.name = name.trim();
            pr.updated = "now";
            setState(s2);
            toast("Renamed", pr.name);
            renderProjectCardsFromState();
            renderWorkspace("projects");
            syncContext();
          } else if(act === "delete"){
            const s2 = getState();
            const pr = s2.projects.find(x=>x.id===pid);
            if(!pr) return;
            if(!confirm(`Delete project "${pr.name}"?`)) return;
            s2.projects = s2.projects.filter(x=>x.id!==pid);
            if(s2.activeProjectId === pid){
              s2.activeProjectId = (s2.projects[0]?.id || "");
            }
            setState(s2);
            toast("Deleted", "Project removed.");
            renderProjectCardsFromState();
            renderWorkspace("projects");
            syncContext();
          }
        });
      });

      return;
    }

    if(tab === "files"){
      $("wsTabFiles").style.borderColor = "rgba(191,230,208,.55)";

      const files = s.files || [];
      const rows = files.map(fl => `
        <div style="border:1px solid rgba(230,242,236,.10); border-radius:16px; padding:12px; background:rgba(255,255,255,.03); display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:10px;">
          <div style="min-width:0;">
            <div style="font-weight:950; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(fl.name)}</div>
            <div style="margin-top:6px; font-size:12px; color:rgba(230,242,236,.62);">
              ${escapeHtml(fl.type || "file")} • ${bytes(fl.size)} • Added ${new Date(fl.added).toLocaleString()}
            </div>
          </div>
          <button data-del="${fl.id}" class="btn secondary" type="button" style="padding:8px 10px; border-radius:12px; font-size:12px;">Remove</button>
        </div>
      `).join("");

      main.innerHTML = `
        <div style="font-weight:950; letter-spacing:.2px; margin-bottom:10px;">Files (local)</div>
        ${rows || `<div style="opacity:.75;">No uploads yet. Hit “Upload”.</div>`}
        <div style="margin-top:12px; font-size:11px; color:rgba(230,242,236,.55);">Next phase: Supabase Storage (private per student).</div>
      `;

      main.querySelectorAll("button[data-del]").forEach(btn=>{
        btn.addEventListener("click", ()=>{
          const id = btn.getAttribute("data-del");
          const s2 = getState();
          s2.files = (s2.files || []).filter(x=>x.id !== id);
          setState(s2);
          toast("Removed", "File removed from local list.");
          renderWorkspace("files");
        });
      });

      return;
    }

    if(tab === "settings"){
      $("wsTabSettings").style.borderColor = "rgba(191,230,208,.55)";

      main.innerHTML = `
        <div style="font-weight:950; letter-spacing:.2px; margin-bottom:10px;">Settings</div>

        <div style="border:1px solid rgba(230,242,236,.10); border-radius:16px; padding:12px; background:rgba(255,255,255,.03);">
          <div style="font-weight:900; font-size:13px;">Student name</div>
          <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
            <input id="setName" class="input" style="flex:1; min-width:220px;" value="${escapeHtml(s.studentName || "Student")}" />
            <button id="saveName" class="btn" type="button">Save</button>
          </div>
        </div>

        <div style="margin-top:10px; border:1px solid rgba(230,242,236,.10); border-radius:16px; padding:12px; background:rgba(255,255,255,.03);">
          <div style="font-weight:900; font-size:13px;">Plan (visual only for now)</div>
          <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
            <select id="setPlan" class="input" style="min-width:240px;">
              ${["FREE","SEMI_PRO","PRO","YEARLY_PRO"].map(x => `<option ${s.plan===x?"selected":""}>${x}</option>`).join("")}
            </select>
            <button id="savePlan" class="btn" type="button">Save</button>
          </div>
          <div style="margin-top:10px; font-size:11px; color:rgba(230,242,236,.55);">
            Next phase: real plan from Stripe + Supabase profile.
          </div>
        </div>
      `;

      $("saveName").addEventListener("click", ()=>{
        const name = ($("setName").value || "").trim();
        if(!name) return toast("No name", "Enter a name first.");
        const s2 = getState();
        s2.studentName = name;
        setState(s2);
        localStorage.setItem("bn_student_name", name);
        $("studentName").textContent = name;
        toast("Saved", "Updated student name.");
      });

      $("savePlan").addEventListener("click", ()=>{
        const plan = ($("setPlan").value || "PRO").trim();
        const s2 = getState();
        s2.plan = plan;
        setState(s2);
        $("planPill").textContent = `PLAN: ${plan}`;
        toast("Saved", "Updated plan (UI only).");
      });

      return;
    }
  }

  function escapeHtml(s){
    return String(s ?? "")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#039;");
  }

  function createProject(){
    const name = prompt("New project name:", "New Project");
    if(!name) return;

    const s = getState();
    const id = "p_" + uid().slice(0,8);
    s.projects.unshift({ id, name: name.trim(), status:"DRAFT", updated:"now" });
    s.activeProjectId = id;
    setState(s);

    renderProjectCardsFromState();
    syncContext();
    toast("Project created", `"${name.trim()}" is now active.`);
    renderWorkspace("projects");
  }

  function createFolder(){
    const name = prompt("Folder name:", "New Folder");
    if(!name) return;

    const s = getState();
    const id = "f_" + uid().slice(0,8);
    s.folders.push({ id, name: name.trim() });
    s.activeFolderId = id;
    setState(s);

    syncContext();
    toast("Folder created", `"${name.trim()}" is now active.`);
    renderWorkspace("projects");
  }

  function uploadFiles(){
    const inp = document.createElement("input");
    inp.type = "file";
    inp.multiple = true;
    inp.onchange = ()=>{
      const files = Array.from(inp.files || []);
      if(!files.length) return;

      const s = getState();
      const proj = activeProject(s);
      const folder = activeFolder(s);
      files.forEach(f=>{
        s.files.unshift({
          id:"file_" + uid().slice(0,10),
          name: f.name,
          size: f.size,
          type: f.type || "file",
          projectId: proj?.id || null,
          folderId: folder?.id || null,
          added: Date.now()
        });
      });
      setState(s);
      toast("Files added", `Added ${files.length} file(s). (Local-only for now)`);
      renderWorkspace("files");
    };
    inp.click();
  }

  // ---------- Tutor chat ----------
  function renderChatMessage(role, text){
    const box = $("tutorChat");
    const row = document.createElement("div");
    row.style.margin = "10px 0";
    row.style.display = "flex";
    row.style.justifyContent = role === "user" ? "flex-end" : "flex-start";
    const bubble = document.createElement("div");
    bubble.style.maxWidth = "78%";
    bubble.style.padding = "10px 12px";
    bubble.style.borderRadius = "16px";
    bubble.style.border = "1px solid rgba(230,242,236,.10)";
    bubble.style.background = role === "user" ? "rgba(191,230,208,.10)" : "rgba(255,255,255,.03)";
    bubble.style.color = "rgba(230,242,236,.92)";
    bubble.style.fontSize = "13px";
    bubble.style.lineHeight = "1.45";
    bubble.textContent = text;
    row.appendChild(bubble);
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
  }

  function loadTutorHistory(){
    const hist = lsGet("bn_chat_history", []);
    const box = $("tutorChat");
    box.innerHTML = `<div style="opacity:.75; font-size:13px; line-height:1.45;">Ask anything. I’ll answer like a real tutor: clear, step-by-step, no fluff.</div>`;
    hist.forEach(m => renderChatMessage(m.role, m.text));
    syncContext();
  }

  async function sendTutor(){
    const inp = $("tutorInput");
    const q = (inp.value || "").trim();
    if(!q) return;

    inp.value = "";
    renderChatMessage("user", q);

    const state = getState();
    const ctx = {
      project: activeProject(state)?.name || "",
      folder: activeFolder(state)?.name || "",
      plan: state.plan || "PRO"
    };

    const hist = lsGet("bn_chat_history", []);
    hist.push({ role:"user", text:q, ts: Date.now(), ctx });
    lsSet("bn_chat_history", hist.slice(-60));

    try{
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify({ message: q, context: ctx })
      });

      const raw = await res.text();
      const data = safeJson(raw) || { reply: raw };

      if(!res.ok){
        renderChatMessage("assistant", "Error: " + (data.detail || data.error || raw || "Request failed"));
        return;
      }

      const reply = (data.reply || data.message || "").toString().trim() || "No reply returned.";
      renderChatMessage("assistant", reply);

      const hist2 = lsGet("bn_chat_history", []);
      hist2.push({ role:"assistant", text: reply, ts: Date.now(), ctx });
      lsSet("bn_chat_history", hist2.slice(-60));

    } catch(e){
      renderChatMessage("assistant", "Network error: " + String(e));
    }
  }

  // ---------- UI init ----------
  const now = new Date();
  const hr = now.getHours();
  const greet = hr < 12 ? "Good morning" : hr < 18 ? "Good afternoon" : "Good evening";
  $("heroTitle").textContent = `${greet}. Ready to level up?`;

  // nav links (pretty URLs)
  $("navHome").setAttribute("href", "/");
  $("navBilling").setAttribute("href", "/pricing");

  // avatar fallback
  $("botonicImg")?.addEventListener("error", ()=>{
    $("botonicImg").src =
      "data:image/svg+xml;charset=utf-8," +
      encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
        <rect width="100%" height="100%" fill="rgba(191,230,208,.08)"/>
        <text x="50%" y="52%" dominant-baseline="middle" text-anchor="middle"
          fill="rgba(230,242,236,.7)" font-family="Arial" font-size="14">Dr. Botonic</text>
      </svg>`);
  });

  // Stamp
  const stamp = now.toLocaleString(undefined, { weekday:"short", month:"short", day:"numeric", hour:"numeric", minute:"2-digit" });
  $("progressStamp").textContent = "Updated " + stamp;

  // progress bars
  const goal = 35;
  $("goalPct").textContent = goal;
  $("goalBar").style.width = Math.max(8, Math.min(100, goal)) + "%";

  const trend = 12;
  $("trendVal").textContent = `+${trend}`;
  $("trendBar").style.width = Math.max(10, Math.min(100, 35 + trend)) + "%";

  // Set name/plan from state
  const s0 = getState();
  $("studentName").textContent = s0.studentName || "Student";
  $("planPill").textContent = `PLAN: ${s0.plan || "PRO"}`;

  // Checkout hint
  const params = new URLSearchParams(window.location.search);
  const checkout = params.get("checkout");
  if(checkout === "success"){
    $("checkoutHint").textContent = "Checkout confirmed. Your workspace is unlocked. 🚀";
    toast("Subscription activated", "Premium mode engaged.");
  } else if(checkout === "cancel"){
    $("checkoutHint").textContent = "Checkout canceled. You can retry anytime from Billing.";
    toast("Checkout canceled", "Nothing was charged.");
  } else {
    $("checkoutHint").textContent = "Tip: This panel will reflect plan changes once we wire real accounts.";
  }

  // API health check
  async function checkAPI(){
    try{
      const r = await fetch("/api/health", { cache: "no-store" });
      if(!r.ok) throw new Error("HTTP " + r.status);
      await r.json();

      $("apiPill").textContent = "API: OK";
      $("apiPill").classList.remove("dim");
      $("apiStatusText").textContent = "Operational";
      $("apiBar").style.width = "92%";
    }catch(e){
      $("apiPill").textContent = "API: DOWN";
      $("apiPill").style.borderColor = "rgba(255,180,180,.28)";
      $("apiPill").style.background = "rgba(255,180,180,.08)";
      $("apiPill").style.color = "rgba(255,210,210,.95)";
      $("apiStatusText").textContent = "Degraded";
      $("apiBar").style.width = "26%";
    }
  }
  checkAPI();

  // Render the 3 project cards using actual state (so clicks always match)
  function renderProjectCardsFromState(){
    const s = getState();
    const slots = [
      { el: $("proj1"), badge: "ok" },
      { el: $("proj2"), badge: "" },
      { el: $("proj3"), badge: "warn" }
    ];
    const list = (s.projects || []).slice(0,3);

    list.forEach((p, i)=>{
      const slot = slots[i];
      if(!slot?.el) return;

      const title = slot.el.querySelector(".title");
      const desc  = slot.el.querySelector(".desc");
      const badge = slot.el.querySelector(".badge");

      if(title) title.textContent = p.name;
      if(desc)  desc.textContent  = `Status: ${p.status} • Updated: ${p.updated || "—"}`;
      if(badge){
        badge.classList.remove("ok","warn");
        if(p.status === "ACTIVE") badge.classList.add("ok");
        if(p.status === "NEEDS LOVE") badge.classList.add("warn");
        badge.textContent = p.status;
      }

      slot.el.onclick = ()=>{
        const s2 = getState();
        s2.activeProjectId = p.id;
        setState(s2);
        toast("Project selected", p.name);
        syncContext();
        // also open workspace projects tab for power users
        openWorkspace("projects");
      };
    });
  }
  renderProjectCardsFromState();

  // ---------- Buttons ----------
  $("btnStart").addEventListener("click", ()=> openTutor());

  $("btnResume").addEventListener("click", ()=>{
    const hist = lsGet("bn_chat_history", []);
    openTutor();
    if(!hist.length) toast("No session found", "Start a session first. I’ll remember it on this device.");
    else toast("Resumed", "Loaded your last session from this device.");
  });

  $("btnNewProject").addEventListener("click", ()=> createProject());

  $("btnAsk").addEventListener("click", ()=>{
    const q = $("quickPrompt").value.trim();
    if(!q){ toast("Need a prompt", "Type a question first."); return; }
    openTutor();
    $("tutorInput").value = q;
    $("quickPrompt").value = "";
    sendTutor();
  });

  $("btnUpload").addEventListener("click", ()=>{ openWorkspace("files"); uploadFiles(); });
  $("btnNewFolder").addEventListener("click", ()=>{ openWorkspace("projects"); createFolder(); });
  $("btnOpenWorkspace").addEventListener("click", ()=> openWorkspace("projects"));

  // Recs
  $("rec1").addEventListener("click", ()=>{ openTutor(); $("tutorInput").value = "Run a 12-minute micro-session on my weakest concept. Start by asking 3 diagnostic questions."; $("tutorInput").focus(); });
  $("rec2").addEventListener("click", ()=>{ openTutor(); $("tutorInput").value = "Give me a quick quiz on anatomy core systems. Adaptive difficulty."; $("tutorInput").focus(); });
  $("rec3").addEventListener("click", ()=>{ openTutor(); $("tutorInput").value = "Build a study plan for this week around my schedule. Ask what days/times I can study."; $("tutorInput").focus(); });

  // Sidebar (NOW real)
  $("navProjects").addEventListener("click", (e)=>{ e.preventDefault(); openWorkspace("projects"); });
  $("navFiles").addEventListener("click", (e)=>{ e.preventDefault(); openWorkspace("files"); });
  $("navSettings").addEventListener("click", (e)=>{ e.preventDefault(); openWorkspace("settings"); });

  // Final: keep context always accurate
  syncContext();

})();
</script>