# ⚡ Genio OS — منصّة AI محلية (HiTech Lab TN)

منصّة **local-first**: البيانات والكود والذاكرة يبقاو في جهازك، بلا اشتراكات وبلا سحابة إجبارية.
العربي/الدارجة أوّلًا، **RTL** مضبوط، وخدمة offline مع **Ollama** محلي.

---

## 🚀 التشغيل السريع

```bash
git clone https://github.com/HiTechLabTN/hitech-genio-os.git
cd hitech-genio-os
make install      # venv + المتطلّبات
make hooks        # تفعيل .githooks/commit-msg
make test         # 191 اختبار
make run          # http://127.0.0.1:8099
```

### 🛰️ النشر على go.hitech.tn (سيرفر TN: `/data/genio-os`)

الكود و البيانات في `/data/genio-os`، و المنصّة ورى **Cloudflare Access**:
خطوات التثبيت، الـ systemd unit، الـ nginx/cloudflared، و أوامر التحقّق في
[`deployment/README.md`](deployment/README.md). المنصّة تقرا `CF-Connecting-IP`
و `X-Forwarded-Proto` غير كي الطلب جاي من بروكسي محلي، فـ IP الزائر و الكوكي
`Secure` و SSE كاملين يخدمو ورى Cloudflare.

### 🔒 حماية هوية الكوميتات

الريبو فيه `.githooks/commit-msg` يحيّد أي `Co-authored-by:` / `Signed-off-by:` /
`Generated with …` من رسالة الكوميت. كل clone جديد يفعّلو بأمر واحد:

```bash
make hooks        # = sh scripts/setup_githooks.sh
```

`core.hooksPath` ولّى على `.githooks` عادي، وإلا — كي الريبو على **noexec** (sshfs)
و git ما يقدرش ينفّذ ملف منّو — السكريبت ينسخ الهوك لـ `~/.local/share/genio-os/hooks`
ويربط هالمسار. في الزوز الحالات نفس الحماية.

### 🐍 وين يتخلق الـ venv؟

`make install` يختار المسار وحدو (`scripts/venv_path.sh`):

| الحالة | المسار |
|---|---|
| نظام ملفات عادي | `./venv` داخل الريبو |
| الريبو على **sshfs / noexec** | `$XDG_DATA_HOME/genio-os/venv` ولا `~/.local/share/genio-os/venv` |
| `GENIO_VENV=/مسار make install` | المسار اللي تعطيه إنت |

علاش: الـ venv فيه ملفات `.so` (psutil، pydantic-core…) و`noexec` يمنع تحميلهم،
فتطلع `failed to map segment from shared object`. `make venv` يطبع المسار المستعمل،
و`make test` يستعملو تلقائيًا — ما تحتاجش تكتب `./venv/bin/python` بيدك.

إذا `python3 -m venv` فشل (Debian بلا `python3-venv`)، السكريبت يعمل `--without-pip`
ويجيب pip من النظام — نفس اللي يعملو الإنسطالور.

أو بالـ Docker:

```bash
echo "GENIO_API_TOKEN=$(openssl rand -hex 24)" > .env
docker compose up -d
```

---

## 🔐 الأمان — الافتراضي مقفول

| الحاجة | الافتراضي | كيفاش تبدّلها |
|---|---|---|
| الربط (bind) | `127.0.0.1` فقط | `security.host` ولا `GENIO_HOST` |
| `/api/*` | للمحلي فقط | حطّ `security.api_token` ولا `GENIO_API_TOKEN` |
| `/api/shell` | **مقفول** | `security.enable_shell` ولا `GENIO_ENABLE_SHELL=1` |
| `/api/update/apply` | **مقفول** | `security.enable_update` |
| أوّل حساب | `POST /api/auth/bootstrap` (owner) | بعدو كل `/api` تحتاج جلسة + CSRF |

التوكن يتزاد تلقائيًا في كل طلب `/api` إذا كان في `localStorage.genio_token`
(تنجّم تدخل بـ `?token=...` مرّة وحدة والواجهة تحفظو).

---

## 🧩 شنوّة موجود

- **حسابات وأدوار** (`owner/admin/member/viewer`) + **workspace معزول** لكل مستعمل.
- **Onboarding 7 أسئلة** → persona pack + mode + أدوات + model policy + safety.
- **3 أوضاع**: محادثة / تطوير / مؤسسة.
- **Tool Registry**: schema + permission (`safe/confirm/dangerous`) + **sandbox** + **audit**.
- **موافقات**: الأوامر الخطرة ما تتنفّذش بلا ما توافق (202 → decide).
- **Model Router**: chat/code/vision/embeddings + fallback واضح إذا الموديل ما موجودش.
- **RAG محلي** بـ citations و**تراخيص** مسجّلة لكل مصدر.
- **Vibe Studio**: 6 قوالب (`landing`, `react-vite`, `fastapi`, `next`, `flutter`, `expo`)،
  mission بـ DAG (PM → Architect → Coder → QA)، preview، ZIP، وdeploy plans.
- **Skill packs** بـ **eval gate**: ما يتفعّلش pack إلا إذا عدّى الـ evals.
- **مؤسسات**: أعضاء، أدوار، تقرير استعمال، **CSV audit**.
- **i18n/RTL**: `ar-TN`, `ar`, `fr`, `en` — 198 مفتاح، والاتجاه data ماشي guess.
  login / onboarding / studio **و6 tabs متاع v8** (office/IDE/logs/terminal/rag/admin)
  كامل مربوطين بـ `data-i18n` + switcher + `dir` من `/api/i18n`.

---

## 🗺️ الـ API (مختصر)

```
POST /api/auth/bootstrap | /api/auth/login | /api/auth/logout
GET  /api/me            | PATCH /api/me/profile
GET  /api/personas      | POST /api/onboarding/submit | POST /api/mode
GET  /api/experience    | GET  /api/router/plan
GET  /api/tools         | POST /api/tools/{name}/invoke
GET  /api/approvals     | POST /api/approvals/{id}/decide
GET  /api/audit         | GET  /api/admin/audit/export
POST /api/rag/ingest    | POST /api/rag/search | GET /api/rag/sources
GET  /api/i18n/{locale}
GET  /api/orgs          | POST /api/orgs | GET /api/orgs/{id}/report
GET  /api/projects      | POST /api/projects | POST /api/projects/{id}/mission
GET  /api/projects/{id}/preview | /export | POST /deploy-plan
GET  /api/skillpacks    | POST /api/skillpacks/{name}/eval | /enable
```

---

## 🛠️ الصيانة

```bash
make test      # pytest
make compile   # compileall
make backup    # tar للذاكرة + workspace + config في backups/ (آخر 7)
```

- **قاعدة البيانات**: `memory/genio.db` (SQLite، برا git).
- **اللوجز**: `logs/`، **الذاكرة**: `memory/`، **المشاريع**: `workspace/users/<slug>/projects/`.
- **systemd**: `deployment/genio-os.service` — **Docker**: `docker-compose.yml`.

---

## 📚 الوثائق

| الملف | شنوّة فيه |
|---|---|
| `docs/PLAN_MISE_A_NIVEAU.md` | خطة v1 — الوحدات والمراحل التقنية |
| `docs/PLAN_v2_AI_COMPANY.md` | خطة v2 — المنتج والـ Sprints |
| `docs/SECURITY_AUDIT_2026-11-13.md` | التدقيق الأمني |
| `docs/RAPPORT_2026-11-15.md` | تقرير حالة الريبو |
| `docs/PHASES_2026-11-15.md` | شنوّة تنفّذ من الخطّتين + كيفاش تتحقّق |
