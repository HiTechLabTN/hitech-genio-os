import os
from pathlib import Path

print("🚀 Starting Genio OS v6.3 Cyber HQ Deployment...")
workspace = Path("/data/genio-os")
web_dir = workspace / "web" / "static"
web_dir.mkdir(parents=True, exist_ok=True)

html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#020617">
<title>Genio OS v6.3 Futuristic AI Company HQ</title>
<style>
  :root {
    --bg-deep: #020617;
    --bg-glass: rgba(15, 23, 42, 0.85);
    --bg-card: rgba(30, 41, 59, 0.75);
    --cyan: #06b6d4;
    --blue: #3b82f6;
    --purple: #8b5cf6;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #f8fafc;
    --muted: #94a3b8;
    --border: rgba(6, 182, 212, 0.3);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: radial-gradient(circle at 50% 10%, #1e1b4b 0%, var(--bg-deep) 85%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }
  header {
    background: rgba(2, 6, 23, 0.95);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky; top: 0; z-index: 100;
  }
  .brand { display: flex; align-items: center; gap: 10px; font-weight: 900; font-size: 1.15rem; background: linear-gradient(90deg, var(--cyan), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .telemetry { display: flex; gap: 8px; font-size: 0.75rem; align-items: center; flex-wrap: wrap; }
  .pill { background: var(--bg-card); border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; }

  .nav-tabs {
    display: flex; gap: 6px; padding: 8px 16px; background: rgba(2, 6, 23, 0.9); border-bottom: 1px solid rgba(255,255,255,0.08); overflow-x: auto;
  }
  .tab-btn {
    background: var(--bg-card); color: var(--muted); border: 1px solid transparent; padding: 7px 14px; border-radius: 10px; font-weight: 700; font-size: 0.82rem; cursor: pointer; white-space: nowrap; transition: 0.2s;
  }
  .tab-btn:hover, .tab-btn.active { color: #020617; background: linear-gradient(135deg, var(--cyan), var(--blue)); box-shadow: 0 4px 15px rgba(6,182,212,0.4); }

  .studio-section { display: none; padding: 14px; flex: 1; }
  .studio-section.active { display: block; }
  .grid-2 { display: grid; grid-template-columns: 320px 1fr; gap: 14px; }
  .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
  @media (max-width: 960px) { .grid-2 { grid-template-columns: 1fr; } }

  .panel {
    background: var(--bg-glass); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  }
  .panel-title { font-size: 0.9rem; font-weight: 800; color: var(--cyan); border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }

  .office-viewport {
    width: 100%; height: 350px; background: #000; border: 1px solid var(--cyan); border-radius: 12px; position: relative; overflow: hidden; box-shadow: inset 0 0 30px rgba(6,182,212,0.25);
  }
  #threeCanvas { width: 100%; height: 100%; display: block; }
  .office-overlay {
    position: absolute; bottom: 8px; left: 8px; right: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; background: rgba(2,6,23,0.88); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border); backdrop-filter: blur(6px); pointer-events: none;
  }

  .agent-card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 9px; padding: 7px 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; transition: 0.2s;
  }
  .agent-card:hover, .agent-card.active { border-color: var(--cyan); background: rgba(6,182,212,0.12); }
  .badge { font-size: 0.64rem; padding: 2px 6px; border-radius: 99px; background: rgba(139,92,246,0.25); color: #e9d5ff; border: 1px solid rgba(139,92,246,0.4); }

  .live-kawaliss {
    background: #000; border: 1px solid rgba(6,182,212,0.3); border-radius: 9px; padding: 8px 10px; font-family: monospace; font-size: 0.74rem; max-height: 110px; overflow-y: auto; color: #38bdf8; direction: ltr; text-align: left;
  }
  .chat-stream { min-height: 240px; max-height: 40vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 4px; }
  .msg { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-right: 4px solid var(--cyan); border-radius: 9px; padding: 9px; font-size: 0.83rem; line-height: 1.5; }
  .msg.user { border-right-color: var(--amber); background: rgba(245,158,11,0.05); }

  textarea, input, select { width: 100%; background: rgba(2,6,23,0.9); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 8px; font-family: inherit; font-size: 0.83rem; outline: none; }
  .btn { background: linear-gradient(135deg, var(--cyan), var(--blue)); color: #020617; font-weight: 800; border: none; border-radius: 8px; padding: 8px 12px; cursor: pointer; font-size: 0.8rem; transition: 0.2s; }
  .btn.purple { background: linear-gradient(135deg, var(--purple), #ec4899); color: #fff; }
  .btn.secondary { background: rgba(255,255,255,0.06); color: var(--text); border: 1px solid var(--border); }
  .terminal-out { background: #000; color: #10b981; font-family: monospace; font-size: 0.76rem; padding: 10px; border-radius: 9px; min-height: 260px; max-height: 45vh; overflow-y: auto; direction: ltr; text-align: left; white-space: pre-wrap; border: 1px solid rgba(16,185,129,0.3); }
  .file-item { font-family: monospace; font-size: 0.76rem; padding: 6px 8px; background: rgba(255,255,255,0.02); border-radius: 6px; cursor: pointer; display: flex; justify-content: space-between; direction: ltr; }
  .file-item:hover { background: rgba(6,182,212,0.12); }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>

<header>
  <div class="brand">🌌 GENIO OS v6.3 FUTURISTIC HQ</div>
  <div class="telemetry">
    <div class="pill">🧠 RAM: <span id="ramLabel">--</span></div>
    <div class="pill">💾 /data: <span id="diskLabel">--</span></div>
    <div class="pill">👑 CEO Active</div>
  </div>
</header>

<nav class="nav-tabs">
  <button class="tab-btn active" onclick="openTab('tab-office', this)">🏢 المكتب المستقبلي 3D (Cyber HQ)</button>
  <button class="tab-btn" onclick="openTab('tab-ops', this)">👑 المدير التنفيذي & Swarm</button>
  <button class="tab-btn" onclick="openTab('tab-ide', this)">💻 استوديو الكود الحي (Live IDE)</button>
  <button class="tab-btn" onclick="openTab('tab-term', this)">🖥️ طرفية السيرفر</button>
  <button class="tab-btn" onclick="openTab('tab-rag', this)">📚 قاعدة المعرفة (RAG)</button>
  <button class="tab-btn" onclick="openTab('tab-admin', this)">⚙️ لوحة الإدارة والتحكم</button>
</nav>

<section id="tab-office" class="studio-section active">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">👥 طاقم الشركة (Cyber Staff)</div>
      <div id="agentsContainer" style="display:flex;flex-direction:column;gap:6px;"></div>
      <div class="panel-title" style="margin-top:6px;">⚡ بروتوكول العمليات الحية</div>
      <button class="btn purple" onclick="runSwarmLive()">🏢 اجتماع السرب المستقبلي</button>
    </div>
    <div class="panel">
      <div class="panel-title">
        <span>🏢 محاكاة المكتب الافتراضي ثلاثي الأبعاد عالي الدقة (Cyber HQ Floor)</span>
        <span style="color:var(--green);font-size:0.72rem;">● عالم حي بالإنيميشن</span>
      </div>
      <div class="office-viewport">
        <canvas id="threeCanvas"></canvas>
        <div class="office-overlay">
          <span id="hqStatusText">👑 Genio-Rayes: ينسق العمليات عبر الشبكة...</span>
          <span style="color:var(--cyan);">Cyber-Grid v6.3</span>
        </div>
      </div>
      <div class="panel-title" style="margin-top:4px;">💬 التحدث المباشر مع المدير التنفيذي (CEO Hub)</div>
      <div id="chatStream" class="chat-stream">
        <div class="msg">
          🌌 <b>مرحباً بك يا ريس عزمي في المقر المستقبلي Genio OS v6.3!</b><br>
          • تم تصميم المكتب الافتراضي الآن بعالم رقمي متحرك (Cyber-Grid) يضم محطات عمل إضاءات نيون وشاشات هولوجرافية تنبض بالحياة.<br>
          • أرسل أمرك وسيتولى المدير التنفيذي توجيه الأقسام فوراً.
        </div>
      </div>
      <textarea id="promptBox" rows="2" placeholder="أعطِ توجيهاً للمقر المستقبلي..."></textarea>
      <button class="btn" onclick="streamSingleAgentTask()">🚀 إرسال المهمة للمقر</button>
    </div>
  </div>
</section>

<section id="tab-ops" class="studio-section">
  <div class="panel">
    <div class="panel-title"><span>📡 رادار الكواليس المباشر</span></div>
    <div id="kawalissBox" class="live-kawaliss">[System] Cyber HQ Live Stream ready...</div>
    <div class="panel-title" style="margin-top:8px;">💬 سجل العمليات</div>
    <div id="chatStreamOps" class="chat-stream"></div>
  </div>
</section>

<section id="tab-ide" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title"><span>📂 ملفات `/data/genio-os/workspace`</span></div>
      <div id="ideFilesList" style="display:flex;flex-direction:column;gap:6px;max-height:380px;overflow-y:auto;"></div>
    </div>
    <div class="panel">
      <div class="panel-title"><span id="currentEditPath">اختر ملفاً للتعديل</span></div>
      <textarea id="codeEditor" style="font-family:monospace;height:350px;direction:ltr;text-align:left;background:#000;color:#38bdf8;"></textarea>
      <button class="btn" onclick="saveCurrentFile()">💾 حفظ الملف</button>
    </div>
  </div>
</section>

<section id="tab-term" class="studio-section">
  <div class="panel">
    <div class="panel-title"><span>🖥️ طرفية السيرفر</span></div>
    <div id="termOutput" class="terminal-out">hitech@tn:/data/genio-os$ # Terminal Ready...</div>
    <input id="shellInput" type="text" dir="ltr" placeholder="أمر لينكس..." onkeydown="if(event.key==='Enter') executeShell()">
  </div>
</section>

<section id="tab-rag" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">📥 إضافة وثيقة لقاعدة المعرفة</div>
      <input id="ragFilename" type="text" dir="ltr" placeholder="handbook.md">
      <textarea id="ragContent" rows="6" placeholder="دليل الشركة..."></textarea>
      <button class="btn" onclick="saveRagDoc()">📚 حفظ في دليل الشركة</button>
    </div>
    <div class="panel">
      <div class="panel-title">🗂️ الدلائل المدمجة</div>
      <div id="ragDocsList" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  </div>
</section>

<section id="tab-admin" class="studio-section">
  <div class="grid-3">
    <div class="panel">
      <div class="panel-title">⚙️ إعدادات العقدة والنموذج</div>
      <input id="cfgOllamaHost" type="text" dir="ltr">
      <select id="cfgModelSelect" dir="ltr"></select>
      <button class="btn" onclick="saveAdminConfig()">💾 حفظ التغييرات</button>
    </div>
    <div class="panel">
      <div class="panel-title">📦 سحب نماذج جديدة</div>
      <div style="display:flex;gap:6px;">
        <input id="pullModelInput" type="text" dir="ltr" placeholder="deepseek-coder-v2:16b">
        <button class="btn purple" onclick="pullOllamaModel()">⬇️ Pull</button>
      </div>
      <div id="pullStatus" style="font-size:0.8rem;color:var(--amber);"></div>
    </div>
    <div class="panel">
      <div class="panel-title">🔄 التحديث الذكي (GitHub)</div>
      <button class="btn secondary" onclick="checkGitHubUpdates()">🔍 فحص التحديثات</button>
      <button class="btn" onclick="applyGitHubUpdate()">⚡ تطبيق التحديث</button>
      <pre id="updateBox" style="font-size:0.72rem;background:#000;padding:8px;border-radius:6px;direction:ltr;text-align:left;max-height:120px;overflow:auto;">جاهز...</pre>
    </div>
  </div>
</section>

<script>
let selectedAgent = "Genio-Rayes";
let activeFilePath = "";

function openTab(tabId, btn) {
  document.querySelectorAll(".studio-section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).classList.add("active");
  btn.classList.add("active");
  if(tabId === 'tab-office' && !scene) init3DOffice();
}

function logKawaliss(htmlLine, cls = "kawaliss-line") {
  const box = document.getElementById("kawalissBox");
  if(!box) return;
  const d = document.createElement("div");
  d.className = cls;
  d.innerHTML = `[${new Date().toLocaleTimeString()}] ${htmlLine}`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function cleanPromptText(txt) {
  return (txt || "").replace(/\[span_\d+\]\((start|end)_span\)/g, "").trim();
}

async function streamAgentTask(agentId, rawPrompt) {
  const prompt = cleanPromptText(rawPrompt);
  if (!prompt) return;
  const stream = document.getElementById("chatStream");
  const msgDiv = document.createElement("div");
  msgDiv.className = "msg";
  msgDiv.innerHTML = `<div><b>👑 ${agentId} (المدير التنفيذي)</b> <span class="badge" id="liveBadge">⏳ يعالج الطلب...</span></div><div class="live-body" style="margin-top:6px;white-space:pre-wrap;"></div><div class="live-actions" style="margin-top:6px;"></div>`;
  stream.appendChild(msgDiv);
  const bodyEl = msgDiv.querySelector(".live-body");
  const actEl = msgDiv.querySelector(".live-actions");
  const badgeEl = msgDiv.querySelector("#liveBadge");

  try {
    const response = await fetch("/api/task/stream", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({agent_id: agentId, prompt})
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const parts = buffer.split("\\n\\n");
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const ev = JSON.parse(part.slice(6));
        if (ev.event === "stage") logKawaliss(ev.message);
        else if (ev.event === "token") bodyEl.textContent += ev.token;
        else if (ev.event === "action") {
          const a = ev.action;
          if(a.type==="write_file") actEl.innerHTML += `<span class="action-chip" style="background:rgba(16,185,129,0.15);color:#10b981;border:1px solid #10b981;padding:2px 6px;border-radius:4px;font-size:0.7rem;margin-right:4px;">💾 ${a.path}</span>`;
        }
        else if (ev.event === "done") {
          badgeEl.innerText = `✅ اكتملت المهمة (${ev.elapsed_sec}s)`;
          logKawaliss(ev.message);
          refreshAll();
        }
      }
    }
  } catch(e) { logKawaliss(`⚠️ Error: ${e}`); }
}

async function streamSingleAgentTask() {
  const box = document.getElementById("promptBox");
  const raw = box.value.trim();
  if(!raw) return;
  box.value = "";
  document.getElementById("chatStream").innerHTML += `<div class="msg user"><b>🧑‍💻 عزمي (المالك):</b><br>${cleanPromptText(raw)}</div>`;
  document.getElementById("hqStatusText").innerText = `👑 Genio-Rayes: ينفذ الطلب في المقر المستقبلي...`;
  await streamAgentTask("Genio-Rayes", raw);
}

let scene, camera, renderer, cyberAvatars = [];
function init3DOffice() {
  const container = document.getElementById("threeCanvas");
  if(!container) return;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000208);

  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
  camera.position.set(0, 16, 22);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({canvas: container, antialias: true});
  renderer.setSize(container.clientWidth, container.clientHeight);

  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  const pointLight1 = new THREE.PointLight(0x06b6d4, 3, 40);
  pointLight1.position.set(-6, 8, 4);
  scene.add(pointLight1);
  const pointLight2 = new THREE.PointLight(0x8b5cf6, 3, 40);
  pointLight2.position.set(6, 8, -4);
  scene.add(pointLight2);

  const gridHelper = new THREE.GridHelper(30, 30, 0x06b6d4, 0x1e1b4b);
  gridHelper.position.y = -2;
  scene.add(gridHelper);

  const coreGeo = new THREE.CylinderGeometry(1.2, 1.2, 4, 32);
  const coreMat = new THREE.MeshStandardMaterial({color: 0x06b6d4, emissive: 0x06b6d4, emissiveIntensity: 0.8, wireframe: true});
  const corePillar = new THREE.Mesh(coreGeo, coreMat);
  corePillar.position.set(0, 0, 0);
  scene.add(corePillar);

  const workstations = [
    {name: "HR-Director", color: 0x8b5cf6, x: -7, z: -5},
    {name: "Genio-Rayes (CEO)", color: 0x06b6d4, x: 0, z: -7},
    {name: "Dev-Lead", color: 0x3b82f6, x: 7, z: -5},
    {name: "Infra-Ops", color: 0xf59e0b, x: -7, z: 5},
    {name: "QA-Sec", color: 0x10b981, x: 0, z: 7},
    {name: "Vision-UI", color: 0xef4444, x: 7, z: 5}
  ];

  workstations.forEach((ws, idx) => {
    const deskGeo = new THREE.BoxGeometry(2.4, 0.2, 1.4);
    const deskMat = new THREE.MeshStandardMaterial({color: 0x1e293b, roughness: 0.2, metalness: 0.8});
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(ws.x, -1.2, ws.z);
    scene.add(desk);

    const screenGeo = new THREE.BoxGeometry(1.4, 0.9, 0.08);
    const screenMat = new THREE.MeshStandardMaterial({color: ws.color, emissive: ws.color, emissiveIntensity: 0.9});
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.set(ws.x, -0.4, ws.z - 0.4);
    scene.add(screen);

    const charGroup = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({color: ws.color, roughness: 0.3, emissive: ws.color, emissiveIntensity: 0.4});
    
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.6, 0.6), bodyMat);
    head.position.set(0, 0.5, 0);
    charGroup.add(head);

    const body = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.0, 0.5), bodyMat);
    body.position.set(0, -0.3, 0);
    charGroup.add(body);

    charGroup.position.set(ws.x, -0.3, ws.z + 0.3);
    charGroup.userData = {baseY: -0.3, speed: 1.5 + idx * 0.2};
    scene.add(charGroup);
    cyberAvatars.push(charGroup);
  });

  animate3D();
}

function animate3D() {
  requestAnimationFrame(animate3D);
  const time = Date.now() * 0.002;
  cyberAvatars.forEach((avatar, i) => {
    avatar.position.y = avatar.userData.baseY + Math.sin(time * avatar.userData.speed + i) * 0.12;
    avatar.rotation.y = Math.sin(time * 0.5 + i) * 0.2;
  });
  renderer.render(scene, camera);
}

async function refreshAll() {
  try {
    const r = await fetch("/api/status");
    const d = await r.json();
    document.getElementById("ramLabel").innerText = `${d.telemetry.ram_used_gb}/${d.telemetry.ram_total_gb} GB`;
    document.getElementById("diskLabel").innerText = `${d.telemetry.disk_free_gb} GB`;
    document.getElementById("cfgOllamaHost").value = d.telemetry.ollama_host;

    document.getElementById("agentsContainer").innerHTML = Object.entries(d.agents).map(([id, a]) => `
      <div class="agent-card ${id === selectedAgent ? 'active' : ''}" onclick="selectAgent('${id}')">
        <div><b>${a.icon} ${a.title}</b></div>
        <span class="badge">${a.badge}</span>
      </div>
    `).join("");

    document.getElementById("ideFilesList").innerHTML = d.files.map(f => `
      <div class="file-item" onclick="loadFile('${f.path}')"><span>📄 ${f.path}</span><span>${f.size_kb} KB</span></div>
    `).join("");

    document.getElementById("ragDocsList").innerHTML = d.rag_docs.map(doc => `
      <div class="msg" style="padding:8px;"><b>📘 ${doc.name}</b> (${doc.size_kb} KB)</div>
    `).join("");

    const sel = document.getElementById("cfgModelSelect");
    const mList = d.ollama.models.length ? d.ollama.models : [d.telemetry.active_model];
    sel.innerHTML = mList.map(m => `<option value="${m}" ${m===d.telemetry.active_model?'selected':''}>${m}</option>`).join("");
  } catch(e) {}
}

function selectAgent(id) {
  selectedAgent = id;
  document.getElementById("hqStatusText").innerText = `👑 القسم النشط: ${id} تحت إدارة المقر المستقبلي`;
  refreshAll();
}

async function loadFile(path) {
  const r = await fetch("/api/file/read", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path})});
  const d = await r.json();
  if(d.ok) {
    activeFilePath = d.path;
    document.getElementById("currentEditPath").innerText = d.path;
    document.getElementById("codeEditor").value = d.content;
  }
}

async function saveCurrentFile() {
  if(!activeFilePath) return;
  const content = document.getElementById("codeEditor").value;
  await fetch("/api/file/save", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path: activeFilePath, content})});
  refreshAll();
}

async function executeShell() {
  const inp = document.getElementById("shellInput");
  const cmd = inp.value.trim();
  if(!cmd) return;
  inp.value = "";
  const out = document.getElementById("termOutput");
  out.innerText += `\\n\\n$ ${cmd}\\n⏳...`;
  const r = await fetch("/api/shell", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({cmd})});
  const d = await r.json();
  out.innerText = out.innerText.replace("⏳...", d.output || "(Done)");
  out.scrollTop = out.scrollHeight;
}

async function saveRagDoc() {
  const filename = document.getElementById("ragFilename").value.trim();
  const content = document.getElementById("ragContent").value.trim();
  if(!filename || !content) return;
  await fetch("/api/rag/add", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({filename, content})});
  refreshAll();
}

refreshAll();
</script>
</body>
</html>
"""

web_dir.joinpath("index.html").write_text(html_content, encoding="utf-8")
print("✅ Successfully deployed Genio OS v6.3 Futuristic AI Company HQ!")
