# خطة الميزان (Mise à niveau) — Genio OS v9
## منصّة AI تونسية، محلية، متعدّدة الاستعمالات، وتتكيّف مع كل مستعمل

> **الوثيقة المرجعية — الإصدار 1.0 — 13 نوفمبر 2026**
> الحالة: **في انتظار الموافقة**. ما نتنفّذش حتى تقول «موافق» ولا تبدّل شي في الخطة.
> ملاحظة: الملف مكتوب بالدارجة التونسية والعربي، والمصطلحات التقنية بالفرنسي/الإنجليزي. للمعاينة الصحيحة استعمل VS Code ولا GitHub (يدعمو RTL).

---

## 1. الرؤية

منصّة AI **محلية** (البيانات ما تخرجش من عندك)، **متعدّدة الاستعمالات** (شات عادي، تطوير و DevOps، مؤسّسات)، و**تتكيّف مع كل مستعمل** حسب شخصيتو، أهدافو، مستواه التقني، ولغتو.

أول سوق: **تونس**. يعني: دارجة، عربي، فرنسي، RTL مضبوط، اشتغال offline، وموارد محدودة (Ollama محلي على Legion).

---

## 2. تشخيص الوضع الحالي (v8) — بصدق

**اللي موجود ويخدم:**
- `FastAPI` + صفحة وحدة `web/static/index.html` (1160 سطر) + محرّك `core/engine.py` (579 سطر).
- 6 وكلاء/شخصيات ثابتة في `AGENTS_REGISTRY` (El Rayes، Dev-Lead، Infra-Ops، QA-Sec، Vision-UI، HR-Director).
- أدوات مبنية على parsing نصي: `<write_file>`, `<run_cmd>`, `<learn_rule>`.
- SSE streaming حي + self-heal (حتى 2 محاولات) + ذاكرة JSONL + playbooks.
- Web IDE + طرفية + RAG + إدارة نماذج + خريطة 3D Voxel.
- واجهة معرّبة RTL + Ollama على `pop-os:11434` (16 نموذج متاح).

**اللي ناقص (وهذا موضوع الخطة):**
- **مستعمل واحد فقط**: `config.json` واحد، بلا `users`، بلا authentication، بلا عزل workspace.
- **بلا onboarding**: ما فمّاش كيفاش نعرفو شنوّة يحب المستعمل.
- **بلا شخصيات ديناميكية**: الوكلاء fixe، ماشي مشتقّين من بروفيل.
- **أدوات بلا صلاحيات**: `/api/shell` ينفّذ أي أمر، بلا sandbox، بلا موافقة، بلا audit.
- **واجهة واحدة للكل**: 6 tabs موجّهة للمطوّر، ماشي للمواطن العادي ولا للمؤسسة.
- **بلا tests ولا CI**: أي تعديل ينجّم يكسّر المنصّة بلا ما نعرفو.

**مشاكل حرجة (بعضها تصلّح اليوم محليًا، بلا commit):**
1. `WORKSPACE_DIR` غير معرّف في `web/server.py` → `NameError` على `/api/file/raw` و `/api/workspace/zip`. **تصلّح.**
2. `config.json` يشير لـ `/data/genio-os` (غير متاح/read-only على أجهزة أخرى) → المنصّة ما تقلعش. **تصلّح** بـ fallback ذكي.
3. **مصدرين للحقيقة**: `install_genio_os.sh` (v5 قديم) يعاود يكتب `engine.py`/`server.py`/`index.html` بنسخة قديمة → أي `clone + install` يعطي v5 ويرجّع الـ bug. **لازم حل.**
4. `deploy_v8_voxel_map.py` يولّد `index.html` — أي تعديل مباشر في `index.html` يتغسّل. **لازم قرار.**
5. `/api/shell` بلا auth ومربوط على `0.0.0.0` → **RCE** إذا المنصّة تتعرّض للشبكة.
6. الـ installer يعمل `git add . && git commit && git push` تلقائي → runtime state (memory/logs) تتcommit في الريبو. **خطر.**

---

## 3. المبادئ المعمارية

1. **مصدر حقيقة واحد**: الريبو. الـ installer ما يولّدش كود؛ ينقل/يثبّت فقط.
2. **Local-first + خصوصية**: كل شي محلي. ما فمّاش إرسال بيانات lخارج بلا موافقة صريحة.
3. **الأدوات عبـر Registry**: كل أداة عندها schema، permission level، audit. ماشي parsing نصي حرّ.
4. **الشخصية = إعداد مشتق**: persona = دالة(بروفيل + استعمال سابق)، ماشي hardcodé في الكود.
5. **ما نزيدوش ميزة بلا اختبار**: كل وحدة جديدة = test + معيار قبول.
6. **الدارجة ماشي ترجمة**: سياسة ردود (register + tone + مصطلحات) داخل الشخصية نفسها.

---

## 4. الوحدات (Modules)

### 4.1 الهوية والمستخدمين (Auth & Users)
- `SQLite` (بلا سيرفر زايد، local، سهل backup). لاحقًا `Postgres` اختياري للمؤسسات.
- جلسات `HttpOnly` cookie + `CSRF` + `argon2` للكلمات السرّ.
- أدوار: `owner`, `admin`, `member`, `viewer`.
- Workspace وذاكرة معزولة لكل مستعمل/منظّمة.
- Admin bootstrap من CLI (أول مستعمل = owner).

### 4.2 الاستقبال (Onboarding) ومحرّك الشخصية
- Wizard في **7 خطوات، أقل من 90 ثانية**، قابل للتخطّي، ويتعدّل من الإعدادات.
- الأسئلة المقترحة:
  1. شنوّة تخدم؟ (طالب/موظّف/حرّ/صاحب مشروع/مؤسسة)
  2. شنوّة تحب تعمل بالـ AI؟ (chat عام، كتابة، كود، تحليل بيانات، تسويق، دعم عملاء، إدارة مشاريع…)
  3. مستواك التقني؟ (مبتدئ/متوسّط/متقدّم)
  4. اللغة المفضّلة: دارجة / عربي فصحى / فرنسي / إنجليزي
  5. وين يخدم الـ AI؟ (جهازك / سيرفر الشركة / offline)
  6. عندك بيانات حسّاسة؟ (عادي/متوسّط/عالٍ)
  7. شنوّة أهم أداة تحب تلقاها جاهزة؟ (اختياري، متعدّد)
- المخرج: `profile` + `persona_pack` + `mode` + `tools` + `model_policy` + `safety`.
- **Persona packs** (مكتبة جاهزة، كل واحد يحدّد: system prompt، tone، tools، UI، models، safety):
  `chat_general`, `student`, `developer`, `devops`, `business_analyst`, `support_agent`, `content_creator`, `enterprise_admin`.
- التكييف الذكي: بعد N جلسات، المنصّة تقترح تبديل pack ولا تفعيل أداة (بموافقة المستعمل).
- المستعمل ينجّم يبدّل الـ mode/pack وقت ما يحب (ما نحبسوش).

**مثال بروفيل (JSON):**
```json
{
  "user_id": "u_001",
  "locale": "ar-TN",
  "register": "derja",
  "technical_level": "intermediate",
  "role": "freelance_dev",
  "sectors": ["web", "ecommerce"],
  "goals": ["build_web_apps", "automate_admin"],
  "env": "laptop_offline",
  "data_sensitivity": "medium",
  "persona_pack": "dev_lead",
  "mode": "dev",
  "model_policy": {
    "chat": "qwen2.5:7b-instruct",
    "code": "qwen2.5-coder:14b",
    "vision": "minicpm-v"
  },
  "tools": ["files", "shell_sandboxed", "git", "tests"],
  "safety": {
    "shell": "confirm",
    "write": "allow_workspace",
    "network": "allowlist"
  }
}
```

### 4.3 الأوضاع (Experiences) — «polyvalent»
- **Mode Chat**: واجهة نقية، سجل محادثات، markdown، صور (vision)، بلا طرفية ولا كود. للمواطن العادي.
- **Mode Dev & DevOps**: الاستوديو الحالي محسّن (وكلاء، IDE، طرفية، RAG، self-heal). للمطوّرين والـ ops.
- **Mode Enterprise**: dashboard، فريق، قاعدة معرفة مشتركة، موافقات، تقارير، audit. للمؤسسات.
- الـ mode يبدّل الواجهة + الأدوات + الشخصية + النموذج الافتراضي. نفس الـ backend.

### 4.4 سجل الأدوات (Tool Registry) + Sandbox
- كل أداة:
```python
class Tool:
    name: str
    description: str
    params: dict                       # JSON Schema
    permission: Literal["safe", "confirm", "dangerous"]
    def run(self, ctx: ToolContext, **kwargs) -> ToolResult: ...
```
- ثلاث مستويات: `safe` (قراءة)، `confirm` (كتابة/أوامر عادية)، `dangerous` (حذف/نشر/شبكة) → approval queue.
- Sandbox: cwd = workspace، timeout، command allowlist، بلا شبكة افتراضيًا.
- **Audit log** لكل نداء: من، شنوّة، وقتاش، النتيجة.
- ترحيل الأدوات الحالية (`write_file`, `run_cmd`, `learn_rule`) تدريجيًا مع backward compat.
- Packs: `chat`, `dev`, `devops`, `enterprise` (كل pack فيه الأدوات اللازمة).

### 4.5 الذكاء والتخصيص
- **Model Router**: نوع المهمّة → النموذج (chat سريع، code، vision، embeddings) + fallback إذا Legion طايح.
- **RAG**: embeddings + vector store محلي (sqlite-vec/chroma)، مصادر لكل مستعمل/منظّمة.
- **ذاكرة**: قصيرة (الجلسة) + طويلة (per-user)، قابلة للتصدير/الحذف (خصوصية).
- **تعلّم من الاستعمال**: playbooks مشتركة، اقتراحات، tone adaptation.
- **سياسة الردود**: دارجة حسب البروفيل، مصطلحات تقنية بالفرنسي/الإنجليزي، RTL صحيح.

### 4.6 اللغة والـ RTL
- نظام locales: `ar-TN` (دارجة)، `ar`، `fr`، `en` + switcher.
- كل النصوص في ملفات ترجمة (ما فمّاش نصوص hardcodée في الـ HTML).
- RTL audit: اتجاه الحقول، الأرقام، التواريخ، أسماء الملفات، الكود.
- سياسة الدارجة: system prompt + glossary + أمثلة (few-shot) + fallback للفصحى إذا المستعمل حبّ.

### 4.7 المؤسسات (Enterprise)
- منظمات (orgs)، فرق، أدوار، حصص (quotas)، تقارير استعمال.
- قاعدة معرفة مشتركة + موافقات + audit export.
- `SSO` لاحقًا (LDAP/OIDC) — ماشي في v1.
- Backup/restore + data residency (كل شي محلي).

### 4.8 التشغيل (Ops)
- `docker-compose.yml` + `systemd` unit داخل الريبو.
- installer جديد: يثبّت فقط، ما يولّدش كود.
- CI: `py_compile` + `pytest` + boot smoke + frontend build.
- `/healthz` + `/metrics` + لوجز rotative.
- Backup تلقائي للـ memory/workspace/SQLite.

---

## 5. المخطّط التقني المختصر

**جداول SQLite:**
`users`, `profiles`, `sessions`, `orgs`, `org_members`, `workspaces`, `conversations`, `messages`, `tool_grants`, `audit_log`, `usage_events`, `rag_sources`, `rag_chunks`, `feedback`.

**API جديدة (مبدئية):**
```
POST /api/auth/login      POST /api/auth/logout     GET /api/me
GET  /api/me/profile      PATCH /api/me/profile
POST /api/onboarding/submit
GET  /api/personas        POST /api/mode
GET  /api/chat/stream     (SSE)
POST /api/tools/{name}/invoke        # محمي بالصلاحيات + approval
GET  /api/admin/users     GET /api/admin/audit
```

**بنية الملفات المقترحة:**
```
core/
  engine.py            # المحرّك الحالي (نقسمو لخدمات صغيرة)
  personas/            # packs + resolve()
  tools/               # registry + tools المتوفّرة
  auth/                # users, sessions, rbac
  db.py                # SQLite + migrations
web/
  server.py            # يبقى app + routers
  routers/             # auth, chat, files, admin, tools
  static/              # UI (source of truth هنا، ماشي مولّد)
docs/                  # الخطط والوثائق
tests/                 # pytest + playwright
docker-compose.yml
.github/workflows/ci.yml
```

---

## 6. المراحل (Phases)

> التقدير إرشادي (جلسات عمل). الترتيب إلزامي: كل مرحلة تبنى على اللي قبلها.

### المرحلة 0 — تثبيت الأساس (1–2 جلسة)
- commit الإصلاحات الحالية + tag `v8-stable`.
- تنظيف الريبو: حذف `{core,web` و `evolved}`، أرشفة السكريبتات القديمة في `archive/`، `.gitignore` للـ runtime state.
- توحيد مصدر الحقيقة: إما نحدّث الـ installer ولا نحذفه ونعوّضو بـ `Makefile`/docker.
- CI أساسي (compile + boot smoke).
- تأمين فوري: bind على `127.0.0.1`، token، تعطيل `/api/shell` افتراضيًا.
- Backup تلقائي للذاكرة والـ workspace.
**معيار القبول:** `git clone` جديد + أمر واحد = المنصّة تخدم، والـ CI أخضر.

### المرحلة 1 — الهوية والمستخدمين (3–5 جلسات)
SQLite + migrations، auth + roles + sessions + CSRF، بروفيل، workspace معزول، admin bootstrap.
**معيار القبول:** مستعملين 2 ما يشوفوش بعضهم؛ admin يشوف الكل؛ tests تغطّي auth.

### المرحلة 2 — Onboarding + Persona (3–4 جلسات)
Wizard + API، مكتبة persona packs، mode switching، اقتراحات تكييف.
**معيار القبول:** مستعمل جديد يكمّل الاستقبال في أقل من 90 ثانية ويحصل على واجهة/أدوات مناسبة.

### المرحلة 3 — Tool Registry + Sandbox (4–6 جلسات)
Registry + permissions + approval + audit؛ ترحيل الأدوات الحالية؛ allowlist + timeout.
**معيار القبول:** كل أداة مسجّلة ومسجّلة في audit؛ أمر خطر ما يتنفّذش بلا موافقة.

### المرحلة 4 — الأوضاع الثلاثة + الذكاء (5–7 جلسات)
Chat UI، Dev/DevOps mode، Enterprise dashboard أولي، Model router + fallback، embeddings + RAG.
**معيار القبول:** 3 وضعيات تخدم على نفس الـ backend؛ إذا Ollama طاح، رسالة واضحة + fallback.

### المرحلة 5 — التعريب والـ RTL الكامل (2–3 جلسات)
i18n + switcher، سياسة الدارجة، RTL audit، تواريخ/أرقام/ملفات.
**معيار القبول:** كل شاشة بالدارجة والفرنسي بلا انقلاب اتجاه.

### المرحلة 6 — Enterprise (4–6 جلسات)
orgs، فرق، قاعدة معرفة مشتركة، حصص، تقارير، audit export، backup.
**معيار القبول:** org فيه 5 أعضاء بصلاحيات مختلفة + تقرير استعمال.

### المرحلة 7 — التغليف والإطلاق (3–4 جلسات)
docker + systemd + installer جديد، docs، demo، monitoring.
**معيار القبول:** تثبيت من صفر في أقل من 10 دقائق.

**المجموع التقريبي: 25–35 جلسة عمل** (حسب السرعة والمراجعات).

---

## 7. المخاطر والحدود

- **جودة الدارجة في النماذج**: النماذج المحلية متوسّطة في الدارجة. الحل: few-shot + glossary + قبول خلط دارجة/فصحى، مع إمكانية التبديل.
- **العتاد**: Ollama على `Legion` (GPU)؛ لازم health check وfallback دايماً.
- **الأمان**: أي فتح على الشبكة = خطر. الافتراضي `127.0.0.1` + token، والـ shell مقفول.
- **Scope creep**: الخطة طويلة؛ نلزمو المراحل وما نخلطوش.
- **التوافق**: الـ installer القديم والـ UI المولّد لازم يتبدّلو، وإلا كل تعديل يتغسّل.

---

## 8. القرارات اللي نحتاجها منك (قبل المرحلة 0)

1. **نشر مركزي ولا محلي؟** سيرفر واحد متاعك يخدم الجميع، ولا كل مستعمل يثبّت عندو نسخة؟ (يبدّل تصميم الـ auth والعزل).
2. **قدّاش مستعمل في المرحلة الأولى؟** (10 / 100 / 1000) — يحدّد SQLite ولا Postgres.
3. **العتاد**: Ollama يبقى على Legion فقط؟ نحتاج cloud fallback (API مدفوع) ولا لا؟
4. **الفلوس**: المنصّة مجانية، ولا فمّا اشتراك/باقات؟
5. **اللغة الأساسية**: دارجة كأساس مع فرنسي، ولا فرنسي كأساس؟ (يبدّل النصوص الافتراضية).
6. **أول تجربة نطلقوها**: Chat عام، ولا Dev/DevOps، ولا Enterprise؟ (نبدأ بالـ persona pack متاعها).

---

## 9. المرحلة 0 بالتفصيل — اللي نعملوه أول ما توافق

1. نعمل commit للإصلاحات (2 ملفّات) + tag `v8-stable`.
2. ننظّف الريبو (المجلّدات الغريبة + السكريبتات القديمة → `archive/` + `.gitignore`).
3. نصلّح الـ installer ولا نحذفه (قرارك) باش ما يرجّعش v5.
4. نكتب CI basics (GitHub Actions).
5. نأمّن: `127.0.0.1` + token + تعطيل shell افتراضيًا.
6. Backup script بسيط.
7. نثبّت قاعدة الـ tests.

**بعدها ندخلو المرحلة 1.**
