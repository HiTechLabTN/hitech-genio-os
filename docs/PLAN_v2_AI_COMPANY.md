# Genio OS v9 — «شركة AI في علبة» 🏭
## خطة المنتج والتنفيذ — الإصدار 2.0 (13 نوفمبر 2026)

> هذه الوثيقة تطوّر [خطة الميزان v1](PLAN_MISE_A_NIVEAU.md): الـ v1 فيها التفاصيل التقنية للمراحل والوحدات، وهذي فيها **الرؤية الجديدة والمنتج وترتيب التنفيذ**.
> الحالة: **في انتظار GO**. ما نتنفّذش حتى تأكّد.

---

## 0. الفكرة في سطر واحد

> منصّة **محلية** بالدارجة: تكتب فكرة في 3 سطور، تجيك **تطبيق ويب ولا موبايل يخدم**، بفريق وكلاء متخصّصين، يتعلّمو من كل مشروع ومن أحدث الحلول open-source — بلا إنترنت، بلا فورفي، وبلا اشتراكات.

---

## 1. علاش local-first = **قوّتك**، ماشي عيبك

القيود اللي عندك (ما فمّاش دفع دولي، ما فمّاش اشتراكات) هي بالضبط اللي تولّي **ميزة تنافسية**:

- **خصوصية وسيادة بيانات**: الكود والبيانات ما تخرجش. هذا وحدو يبيع للمؤسسات والقطاع العمومي.
- **بلا تكلفة شهرية**: ماشي كي Cursor/Claude/Lovable/Replit. المستعمل التونسي ينجّم يخدم بجهاز عادي.
- **offline**: الإنترنت يطيح؟ المنصّة تخدم.
- **دارجة تونسية**: ما فمّاش منصّة عالمية تتكلّم دارجة وتفهم سياق السوق التونسي.
- **تعلّم ذاتي محلي**: تتحسّن من مشاريعك، ماشي من بيانات ناس آخرين.

**المنافسة:** عالميًا فمّا أدوات vibe coding قوية، لكنها مدفوعة، أونلاين، وإنجليزية. إحنا: **رخيص، محلي، دارجة، ويخصّ Tunisia**.

---

## 2. المنتج في 3 مستويات

| المستوى | لمن | شنوّة ياخذ | الفلوس |
|---|---|---|---|
| **Genio Community** | مطوّرين، طلبة، أي تونسي | نسخة محلية كاملة، 3 أوضاع، skill packs أساسية، بلا حدود | مجاني |
| **Genio Pro** | freelancers، صغار المقاولات | تثبيت، قوالب جاهزة، skill packs متقدّمة، تدريب، دعم | خدمة بالدينار |
| **Genio Enterprise** | مؤسسات، شركات | on-prem، multi-tenant، SSO، audit، تكاملات داخلية، SLA | عقد سنوي TND |

**نموذج الفلوس:** ما نبيعش اشتراك شهري إجباري (ماشي ممكن قانونيًا). نبيع **خدمات**: تثبيت + تكوين + تطوير مخصّص + صيانة + دعم. والمؤسسة تخلص بالدينار بعقد.

---

## 3. المعمار: «الشركة» مش «بوت»

### 3.1 الأقسام (Departments / Skill Packs)

كل اختصاص = **Skill Pack** مستقل، قابل للتحديث والتقييم:

| القسم | الدور | أمثلة على الأدوات |
|---|---|---|
| Product (PM) | يحوّل الفكرة لـ PRD + مهام | تحليل طلب، كتابة spec، تحويل لمهام |
| Architecture | ستاك + هيكل المشروع | اختيار تقنيات، مخطط قاعدة بيانات |
| UI/UX | تصميم + design system | توليد شاشات، tokens، accessibility |
| Frontend Web | React/Next/Vite | scaffold، components، preview |
| Mobile | Flutter / React Native / Expo | شاشات، build، معاينة |
| Backend | FastAPI / Node / DB | API، auth، models، migrations |
| QA | اختبارات + إصلاح | pytest، playwright، coverage |
| Security | فحص ثغرات + صلاحيات | secrets scan، dependency audit |
| DevOps | نشر + monitoring | docker، CI، SSH deploy، logs |
| Docs | توثيق + شرح بالدارجة | README، user guide |

### 3.2 شكل الـ Skill Pack

```
skill_packs/
  frontend_web/
    manifest.yaml      # الاسم، الإصدار، المصادر، التراخيص
    prompt.md          # شخصية + قواعد القسم
    knowledge/         # digest من الوثائق الرسمية (مع citations)
    templates/         # قوالب جاهزة
    evals/             # مهام تقييم + checks
    tools.yaml         # الأدوات المسموحة
```

### 3.3 التنسيق (Orchestration)
- **Mission** = فكرة المستعمل.
- **Task DAG**: PM يقسّم لمهام مترابطة؛ كل مهمة عندها owner + artifacts + review gate.
- **Handoff**: كل قسم يسلّم artifacts (spec، code، tests) لللي بعده.
- **Review gates**: QA/Security ما يخلّيوش الكود يعدّي بلا اختبارات.
- **Workspace معزول** لكل مشروع + git محلي + preview.

---

## 4. حلقة التعلّم الذاتي — **الفرق الحقيقي**

4 حلقات، وكل واحدة عندها حدود وأمان:

### 4.1 تعلّم من الخدمة (Mission Learning)
كل مهمة → سجل خبرة: شنوّة نجح، شنوّة فشل، الحل النهائي. يتحوّل لـ **playbook** قابل للاستعمال في المهام الجاية. (موجود جزئيًا في v8 — نطوّروه لـ structured lessons).

### 4.2 امتصاص المعرفة (Knowledge Ingestion)
لكل اختصاص: مصادر محدّدة (وثائق رسمية، GitHub releases، changelogs، awesome lists).
- Pipeline: جلب → تلخيص → digest مع **citations** → تحديث `knowledge/`.
- **التراخيص**: نسجّل ترخيص كل مصدر؛ ما ننسخوش كود محمي.
- جدولة أسبوعية + changelog للفرق.

### 4.3 التقييم (Evaluation)
- **Benchmark suite** لكل اختصاص (مهام معروفة + checks آلية).
- أي تحديث لـ skill pack **ما يتفعّلش** إلا إذا عدّى الـ evals.
- A/B بين نسختين.

### 4.4 التطوّر (Evolution)
- وكيل «Upgrade Agent» يقترح تحسينات للـ prompts/الأدوات.
- **Human approval** إجباري + rollback بنقرة.
- ما فمّاش self-modification حرّ — الأمان قبل الذكاء.

---

## 5. تجربة Vibe Coding (اللي تحبّها إنت)

**المسار الكامل:**
1. تكتب بالدارجة: «نحب تطبيق متجر إلكتروني صغير، فيه منتجات وسلّة ودفع عند الاستلام».
2. PM يكتب PRD + Architecture يختار الستاك.
3. Coder يبني scaffold ثم الملفات ملف بملف.
4. المنصّة تشغّل: `npm install && build` + tests، وتصلّح الأخطاء لوحدها (self-heal).
5. **Preview حي** في المتصفّح + تعديل بالشات («بدّل اللون»، «زيد صفحة»).
6. QA + Security gates.
7. **Export**: ZIP / git repo / نشر على VPS.
8. تعلّم: lessons + playbooks تتسجّل.

**للموبايل:** قوالب Flutter / Expo، معاينة عبر build ويب / QR، وتصدير مشروع كامل.

**جودة إجبارية:** typecheck + lint + tests + فحص أسرار قبل أي «تمّ».

---

## 6. نموذج الخدمة للمؤسسات

- **on-premise**: نثبّتو في سيرفر الشركة؛ البيانات تبقى عندها.
- تكاملات: LDAP/AD لاحقًا، ربط بقاعدة بيانات داخلية، استيراد وثائق.
- **تدريب الفريق** + دعم + صيانة + تحديثات.
- **تقارير استعمال** وaudit للمدير.
- تسعير بالدينار بعقد سنوي (بدون اشتراكات دولية).

---

## 7. خطة التنفيذ — 6 Sprints

> كل Sprint عندو مخرج ملموس ومعيار قبول. الترتيب إجباري.

### Sprint 0 — الأساس (1–2 يوم)
تنظيف الريبو، commit للإصلاحات، CI، أمان فوري (127.0.0.1 + token + تعطيل shell)، backup.
**قبول:** clone جديد + أمر واحد = يخدم؛ CI أخضر.

### Sprint 1 — Vibe Studio MVP (3–5 أيام) ← **أول قيمة حقيقية**
- wizard مشروع جديد + 4 قوالب: `landing` (HTML)، `react-vite`، `fastapi`، `next`.
- فريق مصغّر: PM → Architect → Coder → QA (DAG بسيط).
- Task board حي + streaming + preview ويب + terminal.
- git init + commit تلقائي لكل مرحلة.
- **قبول:** طلب بالدارجة (3 سطور) → تطبيق ويب يخدم + tests يعدّيو + preview.

### Sprint 2 — التعلّم والمعرفة (4–6 أيام)
- skill packs v1 (frontend/backend/qa) + evals.
- knowledge ingestion (5 مصادر لكل اختصاص) + citations + license log.
- mission learning → playbooks منظّمة.
- **قبول:** تحديث skill pack ما يتفعّلش بلا ما يعدّي evals.

### Sprint 3 — المستخدمين والشخصية (3–5 أيام)
- SQLite + auth + أدوار + عزل workspace.
- onboarding 7 أسئلة + persona packs + 3 أوضاع.
- **قبول:** مستعملين معزولين + مستعمل جديد يوصل في < 90 ثانية لإعداد مناسب.

### Sprint 4 — الموبايل والنشر (4–6 أيام)
- قوالب Flutter / Expo + معاينة + تصدير.
- deploy: static hosting محلي، VPS عبر SSH، docker.
- **قبول:** من فكرة لتطبيق موبايل يبني + APK preview (إذا العتاد يسمح).

### Sprint 5 — Enterprise + التغليف (4–6 أيام)
- orgs، فرق، audit، تقارير، quotas.
- docker compose + installer جديد + docs + demo data.
- **قبول:** org 5 أعضاء + تقرير + تثبيت من صفر < 10 دقائق.

**التقدير الإجمالي: 20–30 جلسة.**

---

## 8. المخاطر

- **جودة النماذج المحلية**: 14B ينجّم يغلط في مشاريع كبيرة. الحل: قوالب + بناء تدريجي + tests + self-heal + تقسيم لمهام صغيرة.
- **العتاد**: Legion وحدو. الحل: طابور مهام + نماذج صغيرة للمهام الخفيفة + health checks.
- **الأمان**: shell بلا sandbox = خطر. الحل: allowlist + موافقات + isolation.
- **التراخيص**: ingestion لازم يحترم الترخيص. الحل: digest + citations، ماشي نسخ كود.
- **Scope creep**: 6 sprints كثيرة. نلزمو الترتيب وما نزيدوش قبل ما نكمّلو.

---

## 9. القرارات المقترحة (افتراضاتي — صحّحلي إذا غالط)

1. **الهجين**: المنصّة local-first، وزيد instance مركزي متاعك لمن ما عندوش عتاد.
2. **البداية 20–50 مستعمل** → SQLite كافي، Postgres لاحقًا.
3. **Ollama على Legion فقط**، بلا cloud fallback (قانونيًا واقتصاديًا)، مع طابور.
4. **Community مجاني + خدمات Enterprise بالدينار**.
5. **الدارجة أساس** + فرنسي/إنجليزي للمصطلحات + switcher.
6. **أول تجربة: Vibe Coding** (Dev mode) — هذا اللي يهمّك توّا.

---

## 10. Sprint 1 — المهام بالتفصيل (اللي نبداو بيه)

**Backend**
- `POST /api/projects` (create + template)
- `GET /api/projects` + `GET /api/projects/{id}`
- `POST /api/projects/{id}/mission` (SSE)
- task DAG storage + status
- `git init/commit` helper
- preview static server per project

**Agents**
- PM prompt + PRD schema
- Architect prompt + stack decision
- Coder prompt + file-write tools
- QA prompt + run tests + fix loop
- DAG executor (بدون تعقيد زايد)

**Frontend**
- Projects dashboard
- New project wizard (4 قوالب)
- Mission view: chat + live tasks + file tree + editor + preview
- RTL كامل + دارجة

**Ops**
- templates داخل `templates/`
- pytest smoke tests
- seed demo project

**معيار القبول النهائي:** مستعمل يكتب طلب بالدارجة → في أقل من 10 دقائق عندو مشروع React يخدم، فيه 3 صفحات على الأقل، tests basic يعدّيو، وpreview حي.

---

## 11. اللي نحتاجو منك

- **GO** على الخطة (ولا صحّح الافتراضات في القسم 9).
- تأكيد: نبداو **Sprint 0 + Sprint 1** في نفس الجلسة؟
- العتاد: وين باش نطوّرو؟ (هاد الجهاز ولا Legion؟) — يبدّل سرعة التجارب.

---

## 12. البنية والعلامة: 3 بوابات لنفس المنظومة

| النطاق | الدور | الجمهور | الحالة |
|---|---|---|---|
| **hitechlab.tn** | واجهة الشركة (B2B): خدمات هندسة، SaaS، FinTech، سحابة، Devis، أعمال | مؤسسات وشركات | ✅ حيّة — احترافية، عربي RTL |
| **go.hitech.tn** | منصّة **Genio** (Community/Pro): المستخدم يدخل ويخدم | مطوّرين، freelancers، طلبة | ⚠️ حيّة لكن بلا auth + bug إنتاج |
| **5dmat.tn** | منتج/مرجع: ميكرو-آب offline | مجتمع تونسي | ✅ حيّة — «خدمات.تي أن» |

**الربط بينهم (Brand Architecture):**
- `hitechlab.tn` ← واجهة الثقة والبيع: «جرّب Genio مجانًا» → `go.hitech.tn`، و«اطلب عرض」 للـ enterprise.
- `go.hitech.tn` ← المنتج: تسجيل، onboarding، بناء التطبيقات، ودعم يفتح تذكرة.
- `5dmat.tn` ← دليل قدرة + بوابة مجتمع: «شوف كيفاش بنينا 5dmat بـ Genio» → CTA.

**تقنيًا:**
- حساب واحد (SSO) لاحقًا بين البوابات.
- Cloudflare: Tunnel للـ origin + Access للمنصّة + WAF.
- analytics بسيطة (بلا تتبّع شخصي) + SEO عربي.
- كل النطاقات على نفس الـ stack (FastAPI + static) باش الصيانة تكون وحدة.

**الوضع الحالي للإنتاج (من التدقيق):** الواجهة v8 ظاهرة، لكن الـ backend فيه bug (`/api/file/raw` = 500) وبلا auth على `/api/shell`. **قبل أي حاجة: [التدقيق الأمني](SECURITY_AUDIT_2026-11-13.md).**
