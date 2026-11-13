# سياسة «المحلي أوّلًا» في DSH — دليل التشغيل

> الهدف: نستعملو الموديلات المحلية (Ollama على `pop-os`) في أغلب الخدمة، ونستعملو السحابة (default model) كان كي المحلي ما ينجحش — بلا ما نخسّرو الجودة، ومع توفير كبير في الـ tokens.

---

## 1. المكوّنات الثلاثة

| المكوّن | وين | شنوّة يعمل |
|---|---|---|
| تعليمات عامة | `~/.dsh/AGENTS.md` | يفرض السياسة على كل جلسة جديدة: delegate للمحلي + verification + escalation |
| إعداد Subagent | DSH → **Plugins → Subagent** | يسمح للوكيل يختار `ollama-popos` للمهام الفرعية |
| سكريبت context | `scripts/fix_ollama_context.sh` | يصلّح context=32768 + يرتّب VRAM على pop-os |

---

## 2. الخطوات (بالترتيب)

### أ) إعداد Subagent في DSH
1. ‏Settings → **Plugins** → **Subagent** (في مجموعة Official).
2. ‏في **Model selection**: فعّل الـ toggle.
3. ‏علّم الـ routes:
   - ‏`ollama-popos` / `gemma4:12b`
   - ‏`ollama-popos` / `qwen2.5-coder:14b`
   - ‏`ollama-popos` / `qwen2.5vl:7b`
4. ‏**Save**.

> ‏مهم: الإعداد يتسجّل وقت **إنشاء جلسة جديدة**. يعني لازم تفتح **محادثة جديدة** باش يخدم.

### ب) إعداد context على pop-os
```bash
ssh -t pop-os 'bash -s' < /home/hitech/Data_TN/genio-os/scripts/fix_ollama_context.sh
```
‏السكريبت: يحطّ `OLLAMA_CONTEXT_LENGTH=32768` + `NUM_PARALLEL=1` + `MAX_LOADED_MODELS=1` في systemd، يعاود يشغّل، **يتحقّق** من الـ context الفعلي، وإذا الـ env ما تفعّلش يصنع نسخ `-32k` بـ `num_ctx` مضمّن.

### ج) إعدادات الموديل في DSH
‏Models → لكل موديل محلي:
- ‏**Context window:** `32768`
- ‏**Max output tokens:** `8192`

---

## 3. القاعدة (موجودة في `~/.dsh/AGENTS.md`)

**‏يفوّض للمحلي:** قراءة/استكشاف، تلخيص، صياغة boilerplate، tests، ترجمة، مراجعة أولية.
**‏ما يفوّضش:** أمن، معماريّة، destructive، تغييرات متعددة الملفات، الجواب النهائي للمستخدم.
**‏بوّابة الجودة (إجبارية):** إذا المخرج فارغ/غالط/فيه مسارات مخترعة/نداء أداة غالط → retry واحد محلي → وإلا **السحابة تعاود الخدمة**.
**‏قاعدة التوفير:** الوكيل المحلي يقرا المدخلات الكبيرة ويرجّع خلاصة قصيرة؛ السحابة تراجع الخلاصة فقط.

---

## 4. حدود الحل الحالي

- DSH **ما عندوش fallback أوتوماتيكي** بين مزوّدين: كل طلب model-request كيتم على route واحد، و`dsh-llm-retry` يعاود على نفس المزوّد فقط.
- الحل الحالي = **طبقة سياسة + subagents**: المحلي يخدم، والسحابة تتحقّق وتصيفط.
- الحل الجذري = **Model Router** في Genio (Sprint 4): يحاول محلي → يقيّم آليًا (schema/tests/confidence) → يرقّي للسحابة. وإلا plugin DSH مخصّص (أكثر تعقيدًا وخطر على الاستقرار).
