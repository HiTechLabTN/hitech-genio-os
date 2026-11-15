import io
import zipfile
import mimetypes
from pathlib import Path

ROOT = Path("/data/genio-os")
SERVER_PY = ROOT / "web" / "server.py"
INDEX_HTML = ROOT / "web" / "static" / "index.html"

print("🚀 Deploying Genio OS v7.0 Voxel AI Company HQ...")

# 1. ترقية الباك-أند لدعم المعاينة الحية (Images/Video/HTML) وتصدير ZIP
if SERVER_PY.exists():
    srv_txt = SERVER_PY.read_text(encoding="utf-8")
    if "/api/workspace/zip" not in srv_txt:
        extra_api = r'''
import io
import zipfile
import mimetypes
from fastapi.responses import StreamingResponse, FileResponse

@app.get("/api/file/raw")
async def get_raw_file(path: str, download: bool = False):
    target = (WORKSPACE_DIR / path).resolve()
    if not str(target).startswith(str(WORKSPACE_DIR.resolve())) or not target.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)
    mime, _ = mimetypes.guess_type(str(target))
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{target.name}"'
    return FileResponse(str(target), media_type=mime or "application/octet-stream", headers=headers)

@app.get("/api/workspace/zip")
async def export_workspace_zip(folder: str = ""):
    target_dir = (WORKSPACE_DIR / folder).resolve()
    if not str(target_dir).startswith(str(WORKSPACE_DIR.resolve())) or not target_dir.exists():
        target_dir = WORKSPACE_DIR.resolve()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if target_dir.is_file():
            zf.write(target_dir, target_dir.name)
        else:
            for p in target_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(target_dir))
    buf.seek(0)
    zip_name = f"{target_dir.name or 'workspace'}_project.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )
'''
        SERVER_PY.write_text(srv_txt + "\n" + extra_api, encoding="utf-8")
        print("✅ Backend patched with /api/file/raw and /api/workspace/zip")

# 2. كتابة واجهة Genio OS v7.0 Voxel HQ الكاملة
html_v7 = r'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#020617">
<title>Genio OS v7.0 — Voxel AI Company HQ</title>
<style>
  :root {
    --bg-deep: #020617;
    --bg-glass: rgba(15, 23, 42, 0.9);
    --bg-card: rgba(30, 41, 59, 0.8);
    --cyan: #00f2fe;
    --blue: #3b82f6;
    --purple: #a855f7;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #f8fafc;
    --muted: #94a3b8;
    --border: rgba(0, 242, 254, 0.3);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, var(--bg-deep) 85%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }
  header {
    background: rgba(2, 6, 23, 0.96);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    position: sticky; top: 0; z-index: 100;
  }
  .brand { font-weight: 900; font-size: 1.05rem; background: linear-gradient(90deg, var(--cyan), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .telemetry { display: flex; gap: 6px; font-size: 0.72rem; align-items: center; flex-wrap: wrap; }
  .pill { background: var(--bg-card); border: 1px solid var(--border); padding: 3px 9px; border-radius: 999px; }

  .nav-tabs {
    display: flex; gap: 6px; padding: 8px 12px; background: rgba(2, 6, 23, 0.92); border-bottom: 1px solid rgba(255,255,255,0.08); overflow-x: auto;
  }
  .tab-btn {
    background: var(--bg-card); color: var(--muted); border: 1px solid transparent; padding: 7px 12px; border-radius: 10px; font-weight: 700; font-size: 0.8rem; cursor: pointer; white-space: nowrap; transition: 0.2s;
  }
  .tab-btn:hover, .tab-btn.active { color: #020617; background: linear-gradient(135deg, var(--cyan), var(--blue)); box-shadow: 0 4px 14px rgba(0,242,254,0.35); }

  .studio-section { display: none; padding: 12px; flex: 1; }
  .studio-section.active { display: block; }
  .grid-2 { display: grid; grid-template-columns: 320px 1fr; gap: 12px; }
  .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 12px; }
  @media (max-width: 960px) { .grid-2 { grid-template-columns: 1fr; } }

  .panel {
    background: var(--bg-glass); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  }
  .panel-title { font-size: 0.86rem; font-weight: 800; color: var(--cyan); border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }

  .office-viewport {
    width: 100%; height: 410px; background: #040814; border: 1px solid var(--cyan); border-radius: 12px; position: relative; overflow: hidden; box-shadow: inset 0 0 35px rgba(0,242,254,0.2);
  }
  #threeCanvas { width: 100%; height: 100%; display: block; touch-action: none; }
  .office-hud {
    position: absolute; top: 8px; left: 8px; right: 8px; display: flex; justify-content: space-between; align-items: center; pointer-events: none; gap: 6px; flex-wrap: wrap;
  }
  .hud-tag {
    background: rgba(2,6,23,0.88); border: 1px solid var(--border); padding: 4px 10px; border-radius: 8px; font-size: 0.72rem; pointer-events: auto; cursor: pointer; color: var(--text);
  }
  .office-overlay {
    position: absolute; bottom: 8px; left: 8px; right: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 0.74rem; background: rgba(2,6,23,0.92); padding: 7px 11px; border-radius: 8px; border: 1px solid var(--border);
  }

  .agent-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 9px; padding: 8px 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; transition: 0.2s;
  }
  .agent-card:hover, .agent-card.active { border-color: var(--cyan); background: rgba(0,242,254,0.14); }
  .status-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; background: var(--green); box-shadow: 0 0 8px var(--green); margin-left: 6px; }
  . badge { font-size: 0.64rem; padding: 2px 6px; border-radius: 99px; background: rgba(168,85,247,0.25); color: #e9d5ff; border: 1px solid rgba(168,85,247,0.4); }

  .live-kawaliss {
    background: #010409; border: 1px solid rgba(0,242,254,0.3); border-radius: 9px; padding: 8px 10px; font-family: monospace; font-size: 0.73rem; max-height: 130px; overflow-y: auto; color: #38bdf8; direction: ltr; text-align: left;
  }
  .chat-stream { min-height: 210px; max-height: 40vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 4px; }
  .msg { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-right: 4px solid var(--cyan); border-radius: 9px; padding: 9px; font-size: 0.82rem; line-height: 1.55; }
  .msg.user { border-right-color: var(--amber); background: rgba(245,158,11,0.07); }

  textarea, input, select { width: 100%; background: rgba(2,6,23,0.92); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 8px; font-family: inherit; font-size: 0.82rem; outline: none; }
  .btn { background: linear-gradient(135deg, var(--cyan), var(--blue)); color: #020617; font-weight: 800; border: none; border-radius: 8px; padding: 8px 12px; cursor: pointer; font-size: 0.78rem; transition: 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 5px; text-decoration: none; }
  .btn.purple { background: linear-gradient(135deg, var(--purple), #ec4899); color: #fff; }
  .btn.green { background: linear-gradient(135deg, var(--green), #059669); color: #020617; }
  .btn.secondary { background: rgba(255,255,255,0.07); color: var(--text); border: 1px solid var(--border); }

  .terminal-out { background: #000; color: #10b981; font-family: monospace; font-size: 0.76rem; padding: 10px; border-radius: 9px; min-height: 260px; max-height: 48vh; overflow-y: auto; direction: ltr; text-align: left; white-space: pre-wrap; border: 1px solid rgba(16,185,129,0.3); }
  .file-item { font-family: monospace; font-size: 0.75rem; padding: 7px 9px; background: rgba(255,255,255,0.03); border-radius: 7px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; direction: ltr; border: 1px solid transparent; }
  .file-item:hover, .file-item.active { background: rgba(0,242,254,0.14); border-color: var(--cyan); }
  .preview-box { background: #060b16; border: 1px solid var(--border); border-radius: 10px; padding: 12px; min-height: 220px; max-height: 420px; overflow: auto; direction: ltr; text-align: left; }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>

<header>
  <div class="brand">🏛️ GENIO OS v7.0 — VOXEL AI COMPANY HQ</div>
  <div class="telemetry">
    <div class="pill">🧠 RAM: <span id="ramLabel">--</span></div>
    <div class="pill">💾 /data: <span id="diskLabel">--</span></div>
    <div class="pill">🤖 Model: <span id="modelLabel">--</span></div>
    <div class="pill">📘 Playbooks: <span id="pbLabel">0</span></div>
  </div>
</header>

<nav class="nav-tabs">
  <button class="tab-btn active" onclick="openTab('tab-office', this)">🏢 المقر الحي 3D (Voxel HQ)</button>
  <button class="tab-btn" onclick="openTab('tab-ide', this)">📂 استوديو المشاريع والمعاينة و ZIP</button>
  <button class="tab-btn" onclick="openTab('tab-ops', this)">📡 رادار الكواليس والذاكرة (JSONL)</button>
  <button class="tab-btn" onclick="openTab('tab-term', this)">🖥️ طرفية السيرفر</button>
  <button class="tab-btn" onclick="openTab('tab-rag', this)">📚 دستور الشركة (Handbook)</button>
  <button class="tab-btn" onclick="openTab('tab-admin', this)">⚙️ الإدارة والنماذج (Admin)</button>
</nav>

<section id="tab-office" class="studio-section active">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">
        <span>👥 أقسام الشركة ومستوياتهم</span>
        <span class="badge">Live HQ</span>
      </div>
      <div id="agentsContainer" style="display:flex;flex-direction:column;gap:6px;"></div>

      <div class="panel-title" style="margin-top:6px;">⚡ بروتوكول الشركة الحي</div>
      <button class="btn purple" onclick="runSwarmLive()">🐝 اجتماع الشركة وتوزيع المهمة</button>
      <button class="btn secondary" onclick="demoWalkToCEO('Dev-Lead')">🚶‍♂️ محاكاة مشي الموظف لتسليم التقرير للـ CEO</button>

      <div class="panel-title" style="margin-top:6px;">📡 رادار الكواليس المباشر</div>
      <div id="kawalissBox" class="live-kawaliss">[Voxel HQ v7.0] جميع الموظفين في مكاتبهم...</div>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span>🎮 عالم الشركة الافتراضي Voxel 3D (اسحب لتدوير الكاميرا)</span>
        <span style="color:var(--green);font-size:0.75rem;">● اللمبات والشاشات متفاعلة</span>
      </div>

      <div class="office-viewport" id="viewportBox">
        <canvas id="threeCanvas"></canvas>
        <div class="office-hud">
          <button class="hud-tag" onclick="resetCamera()">🎥 نظرة عامة للشركة</button>
          <button class="hud-tag" onclick="focusAgent3D('Genio-Rayes')">👑 جناح المدير التنفيذي</button>
          <button class="hud-tag" onclick="focusAgent3D('Dev-Lead')">💻 قسم التطوير</button>
          <button class="hud-tag" onclick="focusAgent3D('HR-Director')">👔 قسم الموارد البشرية</button>
        </div>
        <div class="office-overlay">
          <span id="hqStatusText">👑 المدير التنفيذي (Genio-Rayes): مستعد لاستلام مشروعك الجديد...</span>
          <span style="color:var(--cyan);font-family:monospace;">Voxel Engine v7.0</span>
        </div>
      </div>

      <div class="panel-title" style="margin-top:4px;">
        <span>💬 التحدث مع المدير التنفيذي أو القسم المختار (<span id="curAgentName">Genio-Rayes</span>)</span>
      </div>
      <div id="chatStream" class="chat-stream">
        <div class="msg">
          👑 <b>مرحباً بك يا ريس عزمي في Genio OS v7.0 Voxel AI Company HQ!</b><br>
          • كل موظف الآن يملك مكتباً، لمبة حالة تضيء وقت العمل، وجسم Voxel كامل يتحرك ويمشي للمدير التنفيذي لتسليم التقرير فور انتهاء المهمة.<br>
          • في تبويب <b>استوديو المشاريع</b> يمكنك مشاهدة الصور والفيديوهات والـ HTML والـ Markdown مباشرة، أو تحميل أي مشروع بصيغة <b>ZIP</b>!
        </div>
      </div>
      <textarea id="promptBox" rows="2" placeholder="اكتب مشروعك للمدير التنفيذي..."></textarea>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn" style="flex:2;" onclick="streamSingleAgentTask()">🚀 إرسال للوكيل المختار</button>
        <button class="btn purple" style="flex:1;" onclick="runSwarmLive()">🐝 تنفيذ بالسرب الكامل</button>
      </div>
    </div>
  </div>
</section>

<section id="tab-ide" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">
        <span>📂 ملفات ومشاريع Workspace</span>
        <button class="btn secondary" style="padding:3px 8px;font-size:0.7rem;" onclick="refreshAll()">🔄 تحديث</button>
      </div>
      <div style="display:flex;gap:6px;">
        <input id="zipFolderInput" type="text" dir="ltr" placeholder="اسم مجلد المشروع (أو فارغ للكل)">
        <button class="btn green" onclick="exportZipFolder()">📦 تصدير ZIP</button>
      </div>
      <div id="ideFilesList" style="display:flex;flex-direction:column;gap:5px;max-height:430px;overflow-y:auto;"></div>
    </div>

    <div class="panel">
      <div class="panel-title">
        <span id="currentEditPath" style="font-family:monospace;">اختر ملفاً للمعاينة أو التعديل</span>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <button class="btn secondary" onclick="togglePreviewMode()">👁️ معاينة حية / كود</button>
          <a id="downloadFileBtn" class="btn green" href="#" target="_blank" style="display:none;">⬇️ تحميل الملف</a>
          <button class="btn" onclick="saveCurrentFile()">💾 حفظ</button>
        </div>
      </div>
      <div id="multimodalPreview" class="preview-box" style="display:none;"></div>
      <textarea id="codeEditor" style="font-family:monospace;height:360px;direction:ltr;text-align:left;background:#02040a;color:#38bdf8;"></textarea>
    </div>
  </div>
</section>

<section id="tab-ops" class="studio-section">
  <div class="panel">
    <div class="panel-title">
      <span>🧠 سجل الخبرات التطوري (experience_ledger.jsonl)</span>
      <button class="btn secondary" onclick="loadMemoryLedger()">🔄 تحديث السجل</button>
    </div>
    <pre id="ledgerViewer" dir="ltr" style="background:#010409;color:#38bdf8;padding:10px;border-radius:8px;font-size:0.74rem;max-height:480px;overflow:auto;"></pre>
  </div>
</section>

<section id="tab-term" class="studio-section">
  <div class="panel">
    <div class="panel-title"><span>🖥️ طرفية السيرفر المباشرة (tn)</span></div>
    <div id="termOutput" class="terminal-out">hitech@tn:/data/genio-os$ # جاهز...</div>
    <div style="display:flex;gap:8px;">
      <input id="shellInput" type="text" dir="ltr" placeholder="أمر لينكس..." onkeydown="if(event.key==='Enter') executeShell()">
      <button class="btn" onclick="executeShell()">▶️ تنفيذ</button>
    </div>
  </div>
</section>

<section id="tab-rag" class="studio-section">
  <div class="grid-2">
    <div class="panel">
      <div class="panel-title">📥 إضافة قاعدة لدستور الشركة (Handbook)</div>
      <input id="ragFilename" type="text" dir="ltr" placeholder="team_handbook.md">
      <textarea id="ragContent" rows="6" placeholder="قواعد الشركة ووصف المهام..."></textarea>
      <button class="btn" onclick="saveRagDoc()">📚 حفظ في الدستور</button>
    </div>
    <div class="panel">
      <div class="panel-title">🗂️ وثائق الدستور المدمجة</div>
      <div id="ragDocsList" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  </div>
</section>

<section id="tab-admin" class="studio-section">
  <div class="grid-3">
    <div class="panel">
      <div class="panel-title">⚙️ إعدادات عقدة Ollama والنماذج</div>
      <input id="cfgOllamaHost" type="text" dir="ltr">
      <select id="cfgModelSelect" dir="ltr"></select>
      <label style="font-size:0.75rem;color:var(--muted);">Temperature: <span id="tempVal">0.2</span></label>
      <input id="cfgTemp" type="range" min="0" max="1" step="0.05" value="0.2" oninput="document.getElementById('tempVal').innerText=this.value">
      <button class="btn" onclick="saveAdminConfig()">💾 حفظ الإعدادات</button>
      <div id="adminSaveMsg" style="font-size:0.75rem;color:var(--green);"></div>
    </div>
    <div class="panel">
      <div class="panel-title">📦 سحب نموذج جديد</div>
      <div style="display:flex;gap:6px;">
        <input id="pullModelInput" type="text" dir="ltr" placeholder="qwen2.5-coder:14b">
        <button class="btn purple" onclick="pullOllamaModel()">⬇️ Pull</button>
      </div>
      <div id="pullStatus" style="font-size:0.78rem;color:var(--amber);"></div>
    </div>
    <div class="panel">
      <div class="panel-title">🔄 مزامنة GitHub</div>
      <div style="display:flex;gap:6px;">
        <button class="btn secondary" onclick="checkGitHubUpdates()">🔍 فحص</button>
        <button class="btn" onclick="applyGitHubUpdate()">⚡ تحديث</button>
      </div>
      <pre id="updateBox" style="font-size:0.72rem;background:#000;padding:8px;border-radius:6px;direction:ltr;text-align:left;max-height:140px;overflow:auto;">جاهز...</pre>
    </div>
  </div>
</section>

<script>
let selectedAgent = "Genio-Rayes";
let activeFilePath = "";
let previewMode = true;

function openTab(tabId, btn) {
  document.querySelectorAll(".studio-section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).classList.add("active");
  btn.classList.add("active");
  if(tabId === "tab-office") {
    if(!scene) init3DOffice();
    onResize3D();
  }
  if(tabId === "tab-ops") loadMemoryLedger();
}

function logKawaliss(msg) {
  const box = document.getElementById("kawalissBox");
  if(!box) return;
  const d = document.createElement("div");
  d.innerHTML = `[${new Date().toLocaleTimeString()}] ${msg}`;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function cleanPromptText(txt) {
  return (txt || "").replace(/\[span_\d+\]\((start|end)_span\)/g, "").trim();
}

let scene, camera, renderer;
let avatarMap = {};
let camAngle = 0, camRadius = 21, camHeight = 15;
let camTarget = new THREE.Vector3(0, 0, 0);
let isDragging = false, prevX = 0, prevY = 0;

const HQ_ROOMS = [
  {id: "Genio-Rayes", label: "👑 CEO SUITE", color: 0x00f2fe, x: 0, z: -6.5},
  {id: "HR-Director", label: "👔 HR & TALENT", color: 0xa855f7, x: -7.5, z: -5.5},
  {id: "Dev-Lead", label: "💻 DEV STUDIO", color: 0x3b82f6, x: 7.5, z: -5.5},
  {id: "Infra-Ops", label: "⚙️ INFRA OPS", color: 0xf59e0b, x: -7.5, z: 5.0},
  {id: "QA-Sec", label: "🛡️ QA & SECURITY", color: 0x10b981, x: 0, z: 6.5},
  {id: "Vision-UI", label: "🎨 3D VISION UI", color: 0xef4444, x: 7.5, z: 5.0}
];

function makeTextSprite(text, hexColor) {
  const canvas = document.createElement("canvas");
  canvas.width = 512; canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(2, 6, 23, 0.88)";
  ctx.strokeStyle = hexColor;
  ctx.lineWidth = 6;
  ctx.strokeRect(12, 12, 488, 104);
  ctx.fillRect(12, 12, 488, 104);
  ctx.font = "bold 36px Segoe UI, sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 256, 64);
  const tex = new THREE.CanvasTexture(canvas);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: tex, transparent: true}));
  sp.scale.set(3.8, 0.95, 1);
  return sp;
}

function buildVoxelCharacter(colorHex) {
  const group = new THREE.Group();
  const mainMat = new THREE.MeshStandardMaterial({color: colorHex, roughness: 0.3});
  const skinMat = new THREE.MeshStandardMaterial({color: 0xfde047, roughness: 0.4});
  const darkMat = new THREE.MeshStandardMaterial({color: 0x1e293b, roughness: 0.6});
  const eyeMat = new THREE.MeshBasicMaterial({color: 0x00f2fe});

  const legGeo = new THREE.BoxGeometry(0.28, 0.6, 0.28);
  const leftLeg = new THREE.Mesh(legGeo, darkMat); leftLeg.position.set(-0.18, 0.3, 0);
  const rightLeg = new THREE.Mesh(legGeo, darkMat); rightLeg.position.set(0.18, 0.3, 0);
  group.add(leftLeg, rightLeg);

  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.85, 0.4), mainMat);
  torso.position.set(0, 0.95, 0);
  group.add(torso);

  const head = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.62, 0.62), skinMat);
  head.position.set(0, 1.72, 0);
  group.add(head);

  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.14, 0.06), eyeMat);
  visor.position.set(0, 1.75, -0.32);
  group.add(visor);

  const armGeo = new THREE.BoxGeometry(0.24, 0.72, 0.24);
  const leftArm = new THREE.Mesh(armGeo, mainMat); leftArm.position.set(-0.5, 1.0, 0);
  const rightArm = new THREE.Mesh(armGeo, mainMat); rightArm.position.set(0.5, 1.0, 0);
  group.add(leftArm, rightArm);

  group.userData = {leftArm, rightArm, leftLeg, rightLeg, head};
  return group;
}

function init3DOffice() {
  const container = document.getElementById("threeCanvas");
  const box = document.getElementById("viewportBox");
  if(!container || !box) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x030712);

  camera = new THREE.PerspectiveCamera(45, box.clientWidth / box.clientHeight, 0.1, 1000);
  updateCameraPosition();

  renderer = new THREE.WebGLRenderer({canvas: container, antialias: true});
  renderer.setSize(box.clientWidth, box.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const dirLight = new THREE.DirectionalLight(0x38bdf8, 1.1);
  dirLight.position.set(10, 22, 12);
  scene.add(dirLight);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(26, 22),
    new THREE.MeshStandardMaterial({color: 0x091024, roughness: 0.8})
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  const grid = new THREE.GridHelper(26, 26, 0x00f2fe, 0x1e293b);
  grid.position.y = 0.02;
  scene.add(grid);

  const carpet = new THREE.Mesh(
    new THREE.PlaneGeometry(2.6, 13),
    new THREE.MeshBasicMaterial({color: 0x00f2fe, transparent: true, opacity: 0.18})
  );
  carpet.rotation.x = -Math.PI / 2;
  carpet.position.set(0, 0.03, 0);
  scene.add(carpet);

  HQ_ROOMS.forEach((rm, idx) => {
    const roomGroup = new THREE.Group();
    roomGroup.position.set(rm.x, 0, rm.z);

    const pad = new THREE.Mesh(
      new THREE.BoxGeometry(5.2, 0.08, 4.2),
      new THREE.MeshStandardMaterial({color: 0x0f172a, roughness: 0.5})
    );
    pad.position.y = 0.04;
    roomGroup.add(pad);

    const wallMat = new THREE.MeshStandardMaterial({color: rm.color, emissive: rm.color, emissiveIntensity: 0.25, transparent: true, opacity: 0.45});
    const backWall = new THREE.Mesh(new THREE.BoxGeometry(5.2, 1.5, 0.12), wallMat);
    backWall.position.set(0, 0.75, -2.05);
    roomGroup.add(backWall);

    const desk = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 0.75, 1.1),
      new THREE.MeshStandardMaterial({color: 0x334155, roughness: 0.4})
    );
    desk.position.set(0, 0.38, -0.4);
    roomGroup.add(desk);

    const monitor = new THREE.Mesh(
      new THREE.BoxGeometry(1.15, 0.72, 0.09),
      new THREE.MeshStandardMaterial({color: rm.color, emissive: rm.color, emissiveIntensity: 0.85})
    );
    monitor.position.set(0, 1.12, -0.65);
    roomGroup.add(monitor);

    const lamp = new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 16, 16),
      new THREE.MeshStandardMaterial({color: 0x10b981, emissive: 0x10b981, emissiveIntensity: 0.9})
    );
    lamp.position.set(1.4, 2.2, -0.5);
    roomGroup.add(lamp);

    const hexStr = "#" + rm.color.toString(16).padStart(6, "0");
    const banner = makeTextSprite(rm.label, hexStr);
    banner.position.set(0, 3.1, -0.4);
    roomGroup.add(banner);

    scene.add(roomGroup);

    const charMesh = buildVoxelCharacter(rm.color);
    charMesh.position.set(rm.x, 0.08, rm.z + 0.55);
    scene.add(charMesh);

    avatarMap[rm.id] = {
      mesh: charMesh,
      homeX: rm.x,
      homeZ: rm.z + 0.55,
      targetX: rm.x,
      targetZ: rm.z + 0.55,
      state: "idle",
      lamp: lamp,
      monitor: monitor,
      phase: idx * 1.1
    };
  });

  container.addEventListener("pointerdown", e => { isDragging = true; prevX = e.clientX; prevY = e.clientY; });
  window.addEventListener("pointerup", () => { isDragging = false; });
  window.addEventListener("pointermove", e => {
    if(!isDragging) return;
    const dx = e.clientX - prevX;
    const dy = e.clientY - prevY;
    prevX = e.clientX; prevY = e.clientY;
    camAngle -= dx * 0.008;
    camHeight = Math.max(5, Math.min(26, camHeight + dy * 0.06));
    updateCameraPosition();
  });

  window.addEventListener("resize", onResize3D);
  animate3D();
}

function updateCameraPosition() {
  if(!camera) return;
  camera.position.x = camTarget.x + Math.sin(camAngle) * camRadius;
  camera.position.z = camTarget.z + Math.cos(camAngle) * camRadius;
  camera.position.y = camHeight;
  camera.lookAt(camTarget);
}

function resetCamera() {
  camTarget.set(0, 0, 0); camRadius = 21; camHeight = 15; camAngle = 0;
  updateCameraPosition();
}

function focusAgent3D(agentId) {
  const rm = HQ_ROOMS.find(r => r.id === agentId);
  if(!rm) return;
  camTarget.set(rm.x, 1.0, rm.z); camRadius = 9.5; camHeight = 6.5;
  updateCameraPosition();
  selectAgent(agentId);
}

function onResize3D() {
  const box = document.getElementById("viewportBox");
  if(!renderer || !camera || !box || box.clientWidth === 0) return;
  camera.aspect = box.clientWidth / box.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(box.clientWidth, box.clientHeight);
}

function setAgentVisualState(agentId, state) {
  const av = avatarMap[agentId];
  if(!av) return;
  av.state = state;
  if(state === "working") {
    av.lamp.material.color.setHex(0xf59e0b);
    av.lamp.material.emissive.setHex(0xf59e0b);
  } else if(state === "walking") {
    av.lamp.material.color.setHex(0x00f2fe);
    av.lamp.material.emissive.setHex(0x00f2fe);
  } else {
    av.lamp.material.color.setHex(0x10b981);
    av.lamp.material.emissive.setHex(0x10b981);
  }
}

function demoWalkToCEO(agentId = "Dev-Lead") {
  const av = avatarMap[agentId];
  const ceo = avatarMap["Genio-Rayes"];
  if(!av || !ceo || agentId === "Genio-Rayes") return;
  setAgentVisualState(agentId, "walking");
  av.targetX = ceo.homeX;
  av.targetZ = ceo.homeZ + 1.8;
  document.getElementById("hqStatusText").innerText = `🚶‍♂️ ${agentId} يمشي الآن لمكتب المدير التنفيذي لتسليم التقرير...`;
  setTimeout(() => {
    av.targetX = av.homeX;
    av.targetZ = av.homeZ;
    setTimeout(() => {
      setAgentVisualState(agentId, "idle");
      document.getElementById("hqStatusText").innerText = `✅ ${agentId} سلّم التقرير للمدير التنفيذي وعاد لمكتبه!`;
    }, 2200);
  }, 2600);
}

function animate3D() {
  requestAnimationFrame(animate3D);
  const t = Date.now() * 0.005;
  Object.values(avatarMap).forEach(av => {
    const parts = av.mesh.userData;
    const dx = av.targetX - av.mesh.position.x;
    const dz = av.targetZ - av.mesh.position.z;
    const dist = Math.hypot(dx, dz);
    if(dist > 0.08) {
      av.mesh.position.x += dx * 0.06;
      av.mesh.position.z += dz * 0.06;
      av.mesh.rotation.y = Math.atan2(-dx, -dz);
      parts.leftLeg.rotation.x = Math.sin(t * 2.5) * 0.6;
      parts.rightLeg.rotation.x = -Math.sin(t * 2.5) * 0.6;
      parts.leftArm.rotation.x = -Math.sin(t * 2.5) * 0.5;
      parts.rightArm.rotation.x = Math.sin(t * 2.5) * 0.5;
    } else {
      av.mesh.rotation.y = 0;
      parts.leftLeg.rotation.x = 0; parts.rightLeg.rotation.x = 0;
      if(av.state === "working") {
        parts.leftArm.rotation.x = -0.7 + Math.sin(t * 5) * 0.25;
        parts.rightArm.rotation.x = -0.7 - Math.sin(t * 5) * 0.25;
        parts.head.rotation.y = Math.sin(t * 2) * 0.18;
      } else {
        parts.leftArm.rotation.x = Math.sin(t * 0.5 + av.phase) * 0.06;
        parts.rightArm.rotation.x = -Math.sin(t * 0.5 + av.phase) * 0.06;
        parts.head.rotation.y = Math.sin(t * 0.4 + av.phase) * 0.1;
      }
    }
  });
  if(renderer && scene && camera) renderer.render(scene, camera);
}

async function streamAgentTask(agentId, rawPrompt) {
  const prompt = cleanPromptText(rawPrompt);
  if (!prompt) return;
  setAgentVisualState(agentId, "working");
  document.getElementById("hqStatusText").innerText = `⚡ ${agentId} يشتغل الآن على المهمة في مكتبه...`;

  const stream = document.getElementById("chatStream");
  const msgDiv = document.createElement("div");
  msgDiv.className = "msg";
  msgDiv.innerHTML = `<div><b>🤖 ${agentId}</b> <span class="badge" id="liveBadge">⏳ يشتغل...</span></div><div class="live-body" style="margin-top:6px;white-space:pre-wrap;"></div><div class="live-actions" style="margin-top:6px;display:flex;gap:5px;flex-wrap:wrap;"></div>`;
  stream.appendChild(msgDiv);
  stream.scrollTop = stream.scrollHeight;

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
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const ev = JSON.parse(part.slice(6));
        if (ev.event === "stage") logKawaliss(ev.message);
        else if (ev.event === "token") {
          bodyEl.textContent += ev.token;
          stream.scrollTop = stream.scrollHeight;
        }
        else if (ev.event === "action") {
          const a = ev.action;
          if(a.type==="write_file") actEl.innerHTML += `<span class="badge" style="background:rgba(16,185,129,0.2);color:#10b981;">💾 ${a.path}</span>`;
          else if(a.type==="run_cmd") actEl.innerHTML += `<span class="badge">⚙️ ${a.cmd}</span>`;
        }
        else if (ev.event === "done") {
          badgeEl.innerText = `✅ تم (${ev.elapsed_sec}s)`;
          logKawaliss(ev.message);
          demoWalkToCEO(agentId);
          setAgentVisualState(agentId, "idle");
          refreshAll();
        }
      }
    }
  } catch(e) {
    setAgentVisualState(agentId, "idle");
    logKawaliss(`⚠️ Error: ${e}`);
  }
}

async function streamSingleAgentTask() {
  const box = document.getElementById("promptBox");
  const raw = box.value.trim();
  if(!raw) return;
  box.value = "";
  document.getElementById("chatStream").innerHTML += `<div class="msg user"><b>🧑‍💻 عزمي (المالك):</b><br>${cleanPromptText(raw)}</div>`;
  await streamAgentTask(selectedAgent, `${raw}\n\nIMPORTANT: Save all files inside a dedicated project folder using <write_file path="project_folder/file.ext">...</write_file>.`);
}

async function runSwarmLive() {
  const box = document.getElementById("promptBox");
  const mission = cleanPromptText(box.value.trim()) || "Build a complete modular web app inside folder 'voxel_project/' with index.html, app.py, and README.md";
  box.value = "";
  document.getElementById("chatStream").innerHTML += `<div class="msg user"><b>🐝 مهمة الشركة المتكاملة:</b><br>${mission}</div>`;
  await streamAgentTask("Genio-Rayes", `STEP 1 (CEO): Plan project folder structure and write README.md using <write_file path="..."> for:\n${mission}`);
  await streamAgentTask("Dev-Lead", `STEP 2 (Dev-Lead): Write all code files using <write_file path="..."> for:\n${mission}`);
  await streamAgentTask("QA-Sec", `STEP 3 (QA-Sec): Verify all files using <run_cmd>...</run_cmd> for:\n${mission}`);
}

async function loadFile(path) {
  activeFilePath = path;
  document.getElementById("currentEditPath").innerText = path;
  const dlBtn = document.getElementById("downloadFileBtn");
  dlBtn.style.display = "inline-flex";
  dlBtn.href = `/api/file/raw?path=${encodeURIComponent(path)}&download=true`;

  const ext = path.split(".").pop().toLowerCase();
  const prevBox = document.getElementById("multimodalPreview");
  const codeBox = document.getElementById("codeEditor");

  if(["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) {
    prevBox.style.display = "block"; codeBox.style.display = "none";
    prevBox.innerHTML = `<div style="text-align:center;"><img src="/api/file/raw?path=${encodeURIComponent(path)}" style="max-width:100%;max-height:380px;border-radius:8px;"></div>`;
    return;
  }
  if(["mp4", "webm", "ogg", "mov"].includes(ext)) {
    prevBox.style.display = "block"; codeBox.style.display = "none";
    prevBox.innerHTML = `<video controls style="width:100%;max-height:380px;border-radius:8px;"><source src="/api/file/raw?path=${encodeURIComponent(path)}"></video>`;
    return;
  }

  const r = await fetch("/api/file/read", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path})});
  const d = await r.json();
  if(!d.ok) return;
  codeBox.value = d.content;

  if(previewMode && ext === "md" && window.marked) {
    prevBox.style.display = "block"; codeBox.style.display = "none";
    prevBox.innerHTML = marked.parse(d.content);
  } else if(previewMode && ["html", "htm"].includes(ext)) {
    prevBox.style.display = "block"; codeBox.style.display = "none";
    prevBox.innerHTML = `<iframe src="/api/file/raw?path=${encodeURIComponent(path)}" style="width:100%;height:360px;border:none;border-radius:8px;background:#fff;"></iframe>`;
  } else {
    prevBox.style.display = "none"; codeBox.style.display = "block";
  }
}

function togglePreviewMode() {
  previewMode = !previewMode;
  if(activeFilePath) loadFile(activeFilePath);
}

function exportZipFolder() {
  const folder = document.getElementById("zipFolderInput").value.trim();
  window.open(`/api/workspace/zip?folder=${encodeURIComponent(folder)}`, "_blank");
}

async function saveCurrentFile() {
  if(!activeFilePath) return;
  const content = document.getElementById("codeEditor").value;
  await fetch("/api/file/save", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({path: activeFilePath, content})});
  loadFile(activeFilePath);
  refreshAll();
}

async function refreshAll() {
  try {
    const r = await fetch("/api/status");
    const d = await r.json();
    document.getElementById("ramLabel").innerText = `${d.telemetry.ram_used_gb}/${d.telemetry.ram_total_gb} GB`;
    document.getElementById("diskLabel").innerText = `${d.telemetry.disk_free_gb} GB`;
    document.getElementById("modelLabel").innerText = d.telemetry.active_model;
    if(d.telemetry.memory_stats) document.getElementById("pbLabel").innerText = d.telemetry.memory_stats.playbooks_count;
    document.getElementById("cfgOllamaHost").value = d.telemetry.ollama_host;

    document.getElementById("agentsContainer").innerHTML = Object.entries(d.agents).map(([id, a]) => `
      <div class="agent-card ${id === selectedAgent ? 'active' : ''}" onclick="focusAgent3D('${id}')">
        <div><span class="status-dot"></span><b>${a.icon} ${id}</b> <span style="font-size:0.72rem;color:var(--muted);">(${a.badge})</span></div>
        <span class="badge">Lv.5</span>
      </div>
    `).join("");

    document.getElementById("ideFilesList").innerHTML = d.files.map(f => `
      <div class="file-item ${f.path === activeFilePath ? 'active' : ''}" onclick="loadFile('${f.path}')">
        <span>📄 ${f.path}</span>
        <span style="color:var(--muted);">${f.size_kb} KB</span>
      </div>
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
  document.getElementById("curAgentName").innerText = id;
  document.getElementById("hqStatusText").innerText = `👑 القسم المختار: ${id}`;
  refreshAll();
}

async function loadMemoryLedger() {
  const r = await fetch("/api/memory");
  const d = await r.json();
  document.getElementById("ledgerViewer").textContent = (d.ledger || []).map(x => JSON.stringify(x, null, 2)).join("\n-----------------\n");
}

async function executeShell() {
  const inp = document.getElementById("shellInput");
  const cmd = inp.value.trim();
  if(!cmd) return;
  inp.value = "";
  const out = document.getElementById("termOutput");
  out.innerText += `\n\n$ ${cmd}\n⏳...`;
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
  document.getElementById("ragFilename").value = "";
  document.getElementById("ragContent").value = "";
  refreshAll();
}

async function saveAdminConfig() {
  await fetch("/api/config", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      ollama_host: document.getElementById("cfgOllamaHost").value,
      primary_model: document.getElementById("cfgModelSelect").value,
      temperature: parseFloat(document.getElementById("cfgTemp").value),
      num_ctx: 8192
    })
  });
  document.getElementById("adminSaveMsg").innerText = "✅ تم الحفظ!";
  refreshAll();
}

async function pullOllamaModel() {
  const name = document.getElementById("pullModelInput").value.trim();
  if(!name) return;
  document.getElementById("pullStatus").innerText = "⏳ جاري السحب...";
  const r = await fetch("/api/models/pull", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({model_name: name})});
  const d = await r.json();
  document.getElementById("pullStatus").innerText = d.ok ? "✅ اكتمل السحب!" : "❌ خطأ";
  refreshAll();
}

async function checkGitHubUpdates() {
  const r = await fetch("/api/update/check");
  const d = await r.json();
  document.getElementById("updateBox").innerText = JSON.stringify(d, null, 2);
}

async function applyGitHubUpdate() {
  const r = await fetch("/api/update/apply", {method: "POST"});
  const d = await r.json();
  document.getElementById("updateBox").innerText = d.output || d.error || "Done";
}

window.addEventListener("DOMContentLoaded", () => {
  init3DOffice();
  refreshAll();
});
</script>
</body>
</html>
'''

INDEX_HTML.write_text(html_v7, encoding="utf-8")
print("✅ Successfully deployed Genio OS v7.0 Voxel AI Company HQ!")
