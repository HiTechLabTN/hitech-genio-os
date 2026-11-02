# ⚡ Genio OS (`hitech-genio-os`) — Autonomous Local AI Enterprise


منصة ذكاء اصطناعي محلية ومستقلة 100% صممت في **HiTech Lab TN** لتعويض `OpenBot` و `OpenCode` بدون أي قيود استخدام يومية (Zero Rate Limits).


## 🚀 المميزات الرئيسية
- **هندسة موزعة عبر Tailscale:** تفصل بين عقدة التخزين والتطبيقات (`/data/genio-os` على السيرفر `tn`) وعقدة المعالجة الرسومية (`Ollama` على `Legion`).
- **تنفيذ حقيقي للملفات والأوامر:** الوكلاء (`Genio-Rayes`, `Dev-Lead`, `Infra-Ops`, `QA-Sec`, `Vision-UI`) يكتبون الكود مباشرة على القرص ويفحصونه برمجياً.
- **واجهة ويب وموبايل (PWA) + واجهة طرفية (Rich TUI):** تحكم كامل من الهاتف المحمول (RedMagic) أو المتصفح على المنفذ `8090`.


## 🛠️ التثبيت السريع على أي ماكينة (1-Command Install)
```bash
git clone https://github.com/HiTechLabTN/hitech-genio-os.git /data/genio-os
cd /data/genio-os
bash install_genio_os.sh
```
