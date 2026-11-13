# تدقيق أمني عاجل — go.hitech.tn
**التاريخ:** 13 نوفمبر 2026 — **الخطورة:** 🔴 حرجة — **الإجراء:** فوري (دقائق)

> النتيجة في سطر: **المنصّة الحية مفتوحة للعالم بلا authentication**، وفيها endpoints خطيرة تنجّم تسمح بتنفيذ أوامر على السيرفر. لازم تسكّر **توّا**، قبل أي تطوير جديد.

---

## 1. الأدلة (فحص غير تدخّلي، بلا تنفيذ أوامر)

| الفحص | النتيجة | المعنى |
|---|---|---|
| `GET https://go.hitech.tn/` | 200 | الواجهة v8 ظاهرة للعامّة |
| `GET /api/status` | 200 (67KB) | يكشف telemetry كامل: `workspace=/data/genio-os/workspace`، RAM، النماذج، الذاكرة |
| `GET /api/memory` | 200 (53KB) | يكشف الـ playbooks + error resolutions + ledger |
| `GET /api/update/check` | 200 | يكشف حالة git والمستودع |
| `POST /api/shell` | 422 (`Field required`) | **الـ endpoint موجود وبلا auth** — أي واحد ينجّم ينفّذ أوامر لينكس |
| `GET /api/file/raw` | 500 | الـ `WORKSPACE_DIR` bug موجود في الإنتاج (preview/تحميل ميّت) |
| `GET /api/workspace/zip` | 500 | الـ ZIP export ميّت في الإنتاج |
| `POST /api/file/save` / `/api/file/delete` / `/api/task` / `/api/update/apply` | مفتوحة | كتابة/حذف ملفات، تشغيل مهام، `git pull` — كلها بلا auth |
| Login / Token / Rate limit | ❌ ما فمّاش | — |

**ملاحظة:** Cloudflare موجود (CDN + HTTPS) لكن ما فمّاش `Access` ولا `WAF` على الـ API.

---

## 2. الخطر الحقيقي

1. **RCE (تنفيذ أوامر عن بعد):** `/api/shell` = أي واحد في العالم ينجّم يشغّل أوامر على سيرفر `tn` بنفس صلاحيات الخدمة.
2. **تلاعب بالملفات:** قراءة/كتابة/حذف أي ملف في `workspace` (كود مشاريع + بيانات).
3. **استنزاف الموارد:** تشغيل مهام Ollama مكلفة (حجب الخدمة غير مباشر).
4. **تسريب داخلي:** المسارات، الذاكرة، حالة git، telemetry.
5. **إذا السيرفر فيه مفاتيح/بيانات عملاء:** الخطر يتضاعف.

**ملاحظة قانونية/تجارية:** `hitechlab.tn` تبيع خدمات FinTech وربط بوابات دفع و«فاتورة رسمية». أي حادث أمني هنا يضرّ الثقة والسمعة — التأمين ماشي اختياري.

---

## 3. إصلاح فوري (دقائق، بلا كود)

### الخيار الأسرع — Cloudflare Zero Trust Access (مجاني حتى 50 مستعمل)
1. `dash.cloudflare.com` → **Zero Trust** → **Access** → **Applications** → **Add an application** → **Self-hosted**.
2. Application domain: `go.hitech.tn`.
3. Policy: **Allow** → **Emails** (إيميلك + إيميل الفريق) + **One-time PIN**.
4. Save.

بعدها حتى حدّ ما يوصل للمنصّة بلا كود OTP على الإيميل.

### زيد WAF Rule (احتياط)
`Security` → `WAF` → `Custom rules` → Block:
- `Method = POST` و `Path in (/api/shell, /api/file/save, /api/file/delete, /api/task, /api/update/apply)`
- إلا إذا `IP = IP متاعك`.

---

## 4. إصلاح في الكود (قبل أي فتح للجمهور)

1. **commit** للإصلاحين (اللي عملناهم محليًا): `WORKSPACE_DIR` + مسارات `/data` → `git pull` على `tn` → `systemctl restart genio-os.service`.
2. تعطيل `/api/shell` افتراضيًا (env var + صلاحية admin فقط).
3. Token/جلسة بسيطة لكل الـ API + rate limit.
4. ربط الـ origin على `127.0.0.1` + **Cloudflare Tunnel** (بلا فتح بورت للعالم).
5. نسخة backup قبل كل تحديث + `audit log` لكل أمر.

---

## 5. ما نعملوش (حتى بعد الإصلاح)

- ما نجرّبوش `/api/shell` بأوامر حقيقية على الإنتاج.
- ما نفتحوش المنصّة للجمهور قبل auth.
- ما نخلّيوش `/api/update/apply` عمومي (git pull عن بعد = خطر).

---

## 6. ترتيب الأولويات الجديد

- **P0 (اليوم):** Cloudflare Access + WAF block + نشر الإصلاحين.
- **P1 (هذا الأسبوع):** auth بسيط + قفل `/api/shell` + backup.
- **P2:** Sprint 1 (Vibe Studio) على أساس آمن.

> ملاحظة: الـ 500 على `/api/file/raw` و`/api/workspace/zip` يعني **نفس الـ bug اللي تصلّح محليًا** طايح في الإنتاج. أول `git pull + restart` يرجّع الـ preview والـ ZIP للخدمة.
