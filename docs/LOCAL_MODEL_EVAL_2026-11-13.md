# تقييم تجربة الموديل المحلي على DSH — 13 نوفمبر 2026

> **الهدف:** تجربة تشغيل DSH على Ollama المحلي (pop-os) بدل السحابة، وقياس الجدوى.
> **الخلاصة:** ✅ **قابل للاستعمال** — لكن مع 3 إصلاحات صغيرة.

---

## 1. المعطيات

- **المزوّد:** `ollama-popos` (DSH → `http://pop-os:11434/v1`، OpenAI Chat Completions).
- **الموديلات:** جرّب `genio-fast14b:latest` ثم `gemma4:12b`.
- **المشروع اللي تحلّل:** `HiTechLab.TN` — monorepo (Portal + ArtisanOS): Prisma/PostgreSQL 16 + Redis 7 + Nginx + Docker + PWA offline + MikroTik hotspot.
- **الجلسة:** 4 turns، 16 step، 12 tool call.

## 2. الأرقام (من سجل الجلسة)

| المرحلة | النتيجة |
|---|---|
| Turn 1 و 2 | ❌ فشلو فورًا: `No API key for provider: ollama-popos` (8 دقايق ضايعين) |
| Turn 3 | ✅ 13 step في **2m14s** — قرا README + Prisma schema + docker-compose + app/index.html وقدّم تحليل |
| Turn 4 | ✅ 31s — كمّل التحليل |
| Tool calls | 12 نداء: **5 فاشلين** بسبب schema + 7 ناجحين |
| نهاية Turn 3 | ⚠️ `max-tokens` — الجواب تقصّ في الوسط |

**السرعة مُقبولة:** 13 step في دقيقتين على 12B = ممتاز للتحليل والقراءة، ماشي للسكرتة الثقيلة.

## 3. شنوّة نجح فعليًا

- العربية/الدارجة: **مستوى عالي** — فصيح ومفهوم، بلا خلط، مع تنظيم واضح.
- فهم الكود: قرا `schema.prisma` وفهم **multi-tenancy** (modQrOrdering، modWifiHotspot، ألوان/لوجو لكل tenant).
- توصيات صحيحة: تشفير `mikrotikSecret`، object storage للّوجوهات، conflict resolution للـ offline sync.
- استعمال الأدوات: بعد التصحيح، `bash` خدم مزيان وقرا الملفات الصح.

## 4. المشاكل والحلول

### أ) `No API key for provider` (قاتلة في البداية)
pi-ai يحتاج مفتاح حتى مع Ollama. **الحل:** في صفحة Models، خلي API key = أي قيمة (مثلاً `ollama`). ✅ (تعمل).

### ب) schema متاع الأدوات (5 محاولات فاشلة)
الموديل بعث `{"command": "...", "justification": "..."}` بينما أداة `bash` تطلب **`description`**.
**الحلول:**
- ‏اكتب في إعدادات الشخصية/التعليمات: «كل نداء أداة لازم يحتوي **كل** الحقول المطلوبة بأسمائها بالضبط؛ `bash` يطلب `description` و`command`.»
- ‏ولا جرّب `qwen2.5-coder:14b` (عادة أدق في tool schemas).
- ‏ولا خلّي DSH يصلّح: إعادة المحاولة الذاتية موجودة، لكن كل محاولة تكلّف ~3-6 ثواني.

### ج) `max-tokens` قصّ الجواب
زيد **max output tokens** في إعدادات الموديل (Models → الموديل → capacity): من الافتراضي إلى **8192**. وخلي السياق 32K (تحت 24GB VRAM).

### د) context
Ollama افتراضيًا 4K تحت 24GB VRAM — قليل برشة على prompts متاع DSH. زيد:
```bash
# على pop-os
sudo systemctl edit ollama
# [Service]
# Environment="OLLAMA_CONTEXT_LENGTH=32768"
sudo systemctl restart ollama
```

## 5. التوصية: متى تستعمل شنوّة

| المهمة | الموديل |
|---|---|
| تحليل مشاريع، مراجعة كود، شرح بالدارجة | `gemma4:12b` (محلي) ✅ |
| توليد كود ملف-بملف + tests | `qwen2.5-coder:14b` (محلي) |
| صور/لقطات شاشة | `qwen2.5vl:7b` / `minicpm-v` |
| agentic متعدّد الملفات، تخطيط معماري، مراجعة أمنية | السحابة (DSH/deepseek) — دقة أعلى |
| المهام الكثيرة/الطويلة | محلي (بلا تكلفة) |

## 6. ملاحظات على المشروع نفسه (زيادة على تحليل الموديل)

الموديل حلّل مزيان، ونزيد 3 نقاط:
1. **Multi-tenancy في Prisma**: تأكّد من tenant scoping مركزي (middleware) + اختبارات تمنع تسريب بين tenants.
2. **Offline-first**: لازم **idempotency keys** للطلبات + طابور sync + حلّ تعارض بالسياسة (آخر كتابة تفوز / merge حسب المجال).
3. **أسرار MikroTik**: تشفير على مستوى التطبيق (KMS/age) ماشي فقط على مستوى DB، وrotate دوري.

---

**الخلاصة:** الموديل المحلي **ينجم يخدم** كمساعد تحليل ومراجعة بالدارجة على جهازك. مع الإصلاحات فوق، تولّي تجربة يومية معقولة — والسحابة تبقى للقرارات الكبيرة.
