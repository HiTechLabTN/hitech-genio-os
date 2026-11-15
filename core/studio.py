"""Vibe Studio — Plan v2 §5 / §10.

A mission turns a short idea into a working project skeleton with a task DAG
(PM → Architect → Coder → QA). The scaffolding is deterministic and local: no
model call is required to get a running project, and the DAG records exactly
what was produced so the UI can show it.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "landing": {
        "label": "صفحة هبوط (HTML)",
        "stack": "HTML + CSS",
        "files": ["index.html"],
    },
    "react-vite": {
        "label": "React + Vite",
        "stack": "React 18, Vite, JavaScript",
        "files": ["package.json", "index.html", "vite.config.js", "src/main.jsx", "src/App.jsx"],
    },
    "fastapi": {
        "label": "FastAPI",
        "stack": "Python, FastAPI, pytest",
        "files": ["main.py", "requirements.txt", "test_main.py"],
    },
    "next": {
        "label": "Next.js",
        "stack": "Next.js (App Router), React",
        "files": ["package.json", "next.config.mjs", "app/layout.tsx", "app/page.tsx"],
    },
    "flutter": {
        "label": "Flutter",
        "stack": "Flutter, Dart",
        "files": ["pubspec.yaml", "lib/main.dart"],
    },
    "expo": {
        "label": "React Native (Expo)",
        "stack": "Expo, React Native",
        "files": ["package.json", "App.js", "app.json"],
    },
}

MOBILE_TEMPLATES = {"flutter", "expo"}
STAGES = ("pm", "architect", "coder", "qa")


class StudioError(ValueError):
    """Invalid project operation."""


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\u0600-\u06FF]+", "-", (value or "").strip().lower()).strip("-")
    return (cleaned or "project")[:50]


def _html(idea: str, name: str) -> str:
    title = idea.strip().splitlines()[0][:80] if idea.strip() else name
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --ink:#0f172a; --brand:#2563eb; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; color:var(--ink); line-height:1.7; }}
  header {{ padding:56px 20px; text-align:center; background:linear-gradient(135deg,#eff6ff,#f8fafc); }}
  h1 {{ font-size:2rem; margin-bottom:12px; }}
  main {{ max-width:760px; margin:0 auto; padding:32px 20px; }}
  .cards {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }}
  .card {{ border:1px solid #e2e8f0; border-radius:14px; padding:18px; }}
  a.button {{ display:inline-block; margin-top:20px; background:var(--brand); color:#fff; padding:12px 22px; border-radius:10px; text-decoration:none; }}
  footer {{ text-align:center; padding:24px; color:#64748b; font-size:.9rem; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{idea.strip() or "مشروع جديد من Genio Studio"}</p>
  <a class="button" href="#contact">تواصل معنا</a>
</header>
<main>
  <div class="cards">
    <div class="card"><h2>الخدمات</h2><p>اكتب هنا الخدمات اللي تقدّمها.</p></div>
    <div class="card"><h2>علاش إحنا</h2><p>اكتب الميزات اللي تفرّقك على المنافسين.</p></div>
    <div class="card"><h2>التواصل</h2><p id="contact">الإيميل والهاتف.</p></div>
  </div>
</main>
<footer>© {time.strftime('%Y')} {name}</footer>
</body>
</html>
"""


def _react_files(idea: str, name: str) -> Dict[str, str]:
    return {
        "package.json": json.dumps(
            {
                "name": slugify(name),
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
                "devDependencies": {"vite": "^5.4.0", "@vitejs/plugin-react": "^4.3.1"},
            },
            indent=2,
        ),
        "index.html": '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head><meta charset="utf-8"><title>'
        + name
        + '</title></head>\n<body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body>\n</html>\n',
        "vite.config.js": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\nexport default defineConfig({ plugins: [react()] });\n',
        "src/main.jsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App.jsx";\n\nReactDOM.createRoot(document.getElementById("root")).render(<App />);\n',
        "src/App.jsx": 'const features = ["الخدمات", "علاش إحنا", "التواصل"];\n\nexport default function App() {\n  return (\n    <main dir="rtl" style={{ fontFamily: "Segoe UI, sans-serif", padding: 32 }}>\n      <h1>'
        + (idea.strip().splitlines()[0][:80] if idea.strip() else name)
        + '</h1>\n      <ul>\n        {features.map((f) => <li key={f}>{f}</li>)}\n      </ul>\n    </main>\n  );\n}\n',
    }


def _fastapi_files(idea: str, name: str) -> Dict[str, str]:
    return {
        "main.py": '"""' + (idea.strip() or name) + '"""\nfrom fastapi import FastAPI\n\napp = FastAPI(title="'
        + name
        + '")\n\n\n@app.get("/healthz")\ndef healthz():\n    return {"ok": True}\n\n\n@app.get("/")\ndef index():\n    return {"message": "'
        + name
        + '"}\n',
        "requirements.txt": "fastapi>=0.110.0\nuvicorn[standard]>=0.29.0\nhttpx>=0.27.0\npytest>=8.0\n",
        "test_main.py": "from fastapi.testclient import TestClient\n\nfrom main import app\n\n\ndef test_healthz():\n    assert TestClient(app).get(\"/healthz\").json() == {\"ok\": True}\n",
    }


def _next_files(idea: str, name: str) -> Dict[str, str]:
    return {
        "package.json": json.dumps(
            {
                "name": slugify(name),
                "private": True,
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
                "dependencies": {"next": "^14.2.0", "react": "^18.3.1", "react-dom": "^18.3.1"},
            },
            indent=2,
        ),
        "next.config.mjs": "/** @type {import('next').NextConfig} */\nconst nextConfig = {};\n\nexport default nextConfig;\n",
        "app/layout.tsx": 'export const metadata = { title: "'
        + name
        + '" };\n\nexport default function RootLayout({ children }: { children: React.ReactNode }) {\n  return (\n    <html lang="ar" dir="rtl">\n      <body>{children}</body>\n    </html>\n  );\n}\n',
        "app/page.tsx": "export default function Page() {\n  return (\n    <main style={{ padding: 32 }}>\n      <h1>"
        + (idea.strip().splitlines()[0][:80] if idea.strip() else name)
        + "</h1>\n    </main>\n  );\n}\n",
    }


def _flutter_files(idea: str, name: str) -> Dict[str, str]:
    return {
        "pubspec.yaml": f"name: {slugify(name).replace('-', '_')}\ndescription: {idea.strip()[:100] or name}\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\ndependencies:\n  flutter:\n    sdk: flutter\n",
        "lib/main.dart": 'import "package:flutter/material.dart";\n\nvoid main() => runApp(const GenioApp());\n\nclass GenioApp extends StatelessWidget {\n  const GenioApp({super.key});\n\n  @override\n  Widget build(BuildContext context) {\n    return MaterialApp(\n      title: "'
        + name
        + '",\n      home: Scaffold(\n        appBar: AppBar(title: const Text("'
        + name
        + '")),\n        body: const Center(child: Text("'
        + (idea.strip()[:60] or "Genio Studio")
        + '")),\n      ),\n    );\n  }\n}\n',
    }


def _expo_files(idea: str, name: str) -> Dict[str, str]:
    return {
        "package.json": json.dumps(
            {
                "name": slugify(name),
                "private": True,
                "main": "App.js",
                "scripts": {"start": "expo start", "android": "expo start --android"},
                "dependencies": {
                    "expo": "~51.0.0",
                    "react": "18.2.0",
                    "react-native": "0.74.5",
                },
            },
            indent=2,
        ),
        "App.js": 'import { StatusBar } from "expo-status-bar";\nimport { StyleSheet, Text, View } from "react-native";\n\nexport default function App() {\n  return (\n    <View style={styles.container}>\n      <Text style={styles.title}>'
        + name
        + "</Text>\n      <Text>"
        + (idea.strip()[:80] or "Genio Studio")
        + '</Text>\n      <StatusBar style="auto" />\n    </View>\n  );\n}\n\nconst styles = StyleSheet.create({\n  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },\n  title: { fontSize: 22, fontWeight: "700", marginBottom: 8 },\n});\n',
        "app.json": json.dumps(
            {"expo": {"name": name, "slug": slugify(name), "version": "1.0.0"}}, indent=2
        ),
    }


RENDERERS: Dict[str, Callable[[str, str], Dict[str, str]]] = {
    "landing": lambda idea, name: {"index.html": _html(idea, name)},
    "react-vite": _react_files,
    "fastapi": _fastapi_files,
    "next": _next_files,
    "flutter": _flutter_files,
    "expo": _expo_files,
}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def _project_slug(conn: sqlite3.Connection, user_id: int, name: str) -> str:
    base = slugify(name)
    slug, counter = base, 1
    while conn.execute(
        "SELECT 1 FROM projects WHERE user_id = ? AND slug = ?", (user_id, slug)
    ).fetchone():
        counter += 1
        slug = f"{base}-{counter}"
    return slug


def project_dir(workspace: Path, slug: str) -> Path:
    return Path(workspace) / "projects" / slug


def create_project(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    workspace: Path,
    name: str,
    template: str,
    idea: str = "",
) -> Dict[str, Any]:
    if template not in TEMPLATES:
        raise StudioError(f"قالب غير معروف: {template}")
    name = (name or "").strip() or TEMPLATES[template]["label"]
    slug = _project_slug(conn, user_id, name)
    root = project_dir(workspace, slug)
    root.mkdir(parents=True, exist_ok=True)

    files = RENDERERS[template](idea, name)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    (root / "README.md").write_text(
        f"# {name}\n\n- قالب: {TEMPLATES[template]['label']}\n- stack: {TEMPLATES[template]['stack']}\n\n{idea.strip()}\n",
        encoding="utf-8",
    )

    cursor = conn.execute(
        """INSERT INTO projects (user_id, name, template, slug, idea, tasks, created_at)
           VALUES (?, ?, ?, ?, ?, '[]', ?)""",
        (user_id, name, template, slug, idea.strip(), time.time()),
    )
    project = get_project(conn, user_id, int(cursor.lastrowid))
    if project is None:  # pragma: no cover - insert just succeeded
        raise StudioError("ما قدرناش نسجّلو المشروع")
    return project


def get_project(conn: sqlite3.Connection, user_id: int, project_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
    ).fetchone()
    if row is None:
        return None
    project = dict(row)
    project["tasks"] = json.loads(project.get("tasks") or "[]")
    project["stack"] = TEMPLATES.get(project["template"], {}).get("stack", "")
    project["mobile"] = project["template"] in MOBILE_TEMPLATES
    return project


def list_projects(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT id FROM projects WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    return [p for p in (get_project(conn, user_id, row["id"]) for row in rows) if p]


def run_mission(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    workspace: Path,
    project: Dict[str, Any],
    idea: str = "",
) -> Dict[str, Any]:
    """Deterministic PM → Architect → Coder → QA pass over the project."""
    root = project_dir(workspace, project["slug"])
    brief = (idea or project.get("idea") or "").strip()
    stack = TEMPLATES.get(project["template"], {}).get("stack", "")
    tasks: List[Dict[str, Any]] = []

    # PM — spec
    (root / "SPEC.md").write_text(
        f"# {project['name']}\n\n## الفكرة\n{brief or 'مشروع جديد'}\n\n"
        f"## المعايير\n- يخدم محليًا\n- stack: {stack}\n- tests أساسية تخدم\n",
        encoding="utf-8",
    )
    tasks.append({"stage": "pm", "status": "done", "artifact": "SPEC.md"})

    # Architect — decision recorded next to the code
    (root / "ARCHITECTURE.md").write_text(
        f"# Architecture\n\n- Template: {project['template']}\n- Stack: {stack}\n"
        f"- Files: {', '.join(TEMPLATES[project['template']]['files'])}\n",
        encoding="utf-8",
    )
    tasks.append({"stage": "architect", "status": "done", "artifact": "ARCHITECTURE.md"})

    # Coder — verify the scaffold is actually on disk
    written = [name for name in TEMPLATES[project["template"]]["files"] if (root / name).is_file()]
    if not written:
        raise StudioError("ما فمّاش حتى ملف في المشروع")
    tasks.append(
        {"stage": "coder", "status": "done", "artifact": ", ".join(written), "files": len(written)}
    )

    # QA — cheap structural checks that mean something without npm/pip
    problems: List[str] = []
    for name in written:
        if (root / name).stat().st_size == 0:
            problems.append(f"{name} فارغ")
    if project["template"] in {"react-vite", "next", "expo"}:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        if not package.get("scripts"):
            problems.append("package.json بلا scripts")
    if project["template"] == "fastapi":
        if "healthz" not in (root / "main.py").read_text(encoding="utf-8"):
            problems.append("main.py بلا /healthz")
    tasks.append(
        {
            "stage": "qa",
            "status": "done" if not problems else "failed",
            "artifact": "structural checks",
            "problems": problems,
        }
    )

    conn.execute(
        "UPDATE projects SET tasks = ?, idea = ? WHERE id = ?",
        (json.dumps(tasks, ensure_ascii=False), brief, project["id"]),
    )
    updated = get_project(conn, user_id, project["id"]) or project
    return {
        "project": updated,
        "tasks": tasks,
        "passed": not problems,
        "next": (
            "npm install && npm run dev" if project["template"] in {"react-vite", "next", "expo"}
            else "pip install -r requirements.txt && uvicorn main:app --reload" if project["template"] == "fastapi"
            else "افتح index.html في المتصفّح"
        ),
    }


def read_project_file(workspace: Path, project_slug: str, relative: str) -> Path:
    root = project_dir(workspace, project_slug).resolve()
    target = (root / (relative or "index.html")).resolve()
    if target != root and root not in target.parents:
        raise StudioError("المسار خارج المشروع")
    if not target.is_file():
        raise StudioError("الملف ما موجودش")
    return target


def deploy_plan(project: Dict[str, Any], target: str) -> Dict[str, Any]:
    """Steps a human can run; nothing is executed here."""
    template = project["template"]
    if target == "static":
        commands = ["npm install", "npm run build"] if template in {"react-vite", "next"} else []
        return {
            "target": "static",
            "steps": commands + ["cp -r dist/* /var/www/html/  # ولا أي static host"],
            "notes": "خدمة ملفات ثابتة فقط، بلا backend.",
        }
    if target == "docker":
        return {
            "target": "docker",
            "steps": [
                "docker build -t " + slugify(project["name"]) + " .",
                "docker run -p 127.0.0.1:8080:80 " + slugify(project["name"]),
            ],
            "notes": "لازم Dockerfile في الجذر قبل الـ build.",
        }
    if target == "vps":
        return {
            "target": "vps",
            "steps": [
                "rsync -av --exclude node_modules ./ user@vps:/srv/" + slugify(project["name"]),
                "ssh user@vps 'cd /srv/" + slugify(project["name"]) + " && npm install --omit=dev'",
                "ssh user@vps 'systemctl restart " + slugify(project["name"]) + "'",
            ],
            "notes": "النشر عبر SSH يحتاج مفتاح ومستخدم منفصل.",
        }
    raise StudioError(f"هدف نشر غير معروف: {target}")
