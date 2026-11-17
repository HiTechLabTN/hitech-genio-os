# نشر Genio OS على سيرفر TN — go.hitech.tn

المسار المعتاد: الكود و البيانات في **`/data/genio-os`**، uvicorn على
`127.0.0.1:8099`، و `go.hitech.tn` قدّامو Cloudflare Access.

```
المتصفّح → Cloudflare (TLS + Access) → cloudflared ولا nginx → uvicorn 127.0.0.1:8099
```

## 1) التثبيت / التحديث

```bash
sudo mkdir -p /data/genio-os && sudo chown genio:genio /data/genio-os
sudo -u genio git clone https://github.com/HiTechLabTN/hitech-genio-os.git /data/genio-os
cd /data/genio-os
sudo -u genio make install          # venv + المتطلّبات
sudo -u genio make hooks            # حماية رسائل الكوميت
sudo -u genio make test             # لازم يعدّي كامل
```

`GENIO_DATA_DIR=/data/genio-os` هو نفس المجلّد: قاعدة `genio.db`، `workspace/`،
`memory/`، `rag_docs/` يولّيو فيه.

## 2) الخدمة (systemd)

```bash
sudo cp deployment/genio-os.service /etc/systemd/system/genio-os.service
sudo systemctl daemon-reload && sudo systemctl enable --now genio-os
systemctl status genio-os --no-pager
curl -s http://127.0.0.1:8099/api/health
```

## 3) الواجهة على go.hitech.tn

**أ) cloudflared tunnel (الأبسط، بلا nginx):**

```bash
cloudflared tunnel route dns genio go.hitech.tn
# ~/.cloudflared/config.yml
#   tunnel: <id>
#   ingress:
#     - hostname: go.hitech.tn
#       service: http://127.0.0.1:8099
#     - service: http_status:404
sudo systemctl restart cloudflared
```

**ب) nginx (إذا تحبّ buffering/timeouts مضبوطين):**

```bash
sudo cp deployment/nginx-go.hitech.tn.conf /etc/nginx/sites-available/go.hitech.tn
sudo ln -sf /etc/nginx/sites-available/go.hitech.tn /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# و cloudflared يوجّه لـ http://127.0.0.1:8090
```

## 3.1) نسخة احتياطية يومية + استرجاع

```bash
sudo cp deployment/genio-backup.service deployment/genio-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now genio-backup.timer
systemctl list-timers genio-backup.timer --no-pager

sudo -u genio make backup     # تجربة يدوية توّا
sudo -u genio make backups    # لائحة النسخ
```

النسخة تحوي `config.json` + `memory/genio.db` (snapshot متّسق عبر sqlite backup API)
+ `memory/` + `workspace/` + `rag_docs/`, مع `manifest.json` (عدد الملفات و الحسابات
و commit) و `.sha256` جنبها. الاحتفاظ: `GENIO_BACKUP_KEEP=14` نسخة و
`GENIO_BACKUP_DAYS=30` (يتحذفو الأقدم تلقائيًا).

**استرجاع مجرّب** (ما يدهسش داتا بلا `--force`):

```bash
sudo -u genio bash scripts/restore.sh --from latest --into /tmp/genio-restore --dry-run
sudo -u genio bash scripts/restore.sh --from latest --into /tmp/genio-restore
#   ✅ عدد الملفات مطابق (N)   ✅ عدد الحسابات مطابق (M)
# للاسترجاع الحقيقي:
sudo systemctl stop genio-os
sudo -u genio bash scripts/restore.sh --from latest --into /data/genio-os --force
sudo systemctl start genio-os && make verify-prod
```

## 3.2) الوصول عبر الدومين بلا ما تعرف CIDR متاع البروكسي

ما تحتاجش تحسب CIDR: القاعدة في `core/security.py` —

```
الطلب مقبول كان:
  1) الـ peer = loopback                      (cloudflared/nginx على نفس الجهاز)
  2) ولا الـ peer في security.trusted_networks  (10/8، 172.16/12، 192.168/16)
     و الطلب فيه هيدر Cloudflare واحد على الأقل:
     CF-Connecting-IP / Cf-Access-Jwt-Assertion / CF-Ray / CF-Visitor / True-Client-IP
  3) ولا الـ peer في security.trusted_proxies  (CIDR صريح كان تحب تقفل أكثر)
```

يعني tunnel يكلّم من `172.17.0.2` ولا `10.0.0.5` مع `CF-Connecting-IP` → يخدم
وحدو. أما طلب من `203.0.113.5` حتى لو زيّد `CF-Connecting-IP: 127.0.0.1` → **403**
(الحماية ما تتبناش على هيدر وحدو).

```bash
# كان الـ tunnel على شبكة غريبة (Tailscale/WireGuard 100.64/10 مثلاً):
GENIO_TRUSTED_NETWORKS=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10
# ولا قفلها على بروكسي واحد:
GENIO_TRUSTED_PROXIES=172.20.0.2/32
```

## 4) علاش المنصّة كانت تنقص برشا حوايج وراء البروكسي

| المشكل | قبل | توّا |
|---|---|---|
| IP الزائر | `127.0.0.1` للكل (سجل المحاولات و audit غالط) | `core/proxy.py` يقرا `CF-Connecting-IP` / `X-Forwarded-For` — **غير** كي الطلب جاي من بروكسي loopback |
| كوكي الجلسة | `Secure` ما تتحطّش (uvicorn يشوف http) | تتحطّ كي `X-Forwarded-Proto: https` ولا `CF-Visitor` ولا `CF-Connecting-IP` موجود |
| SSE `/api/task/stream` | بلا headers، ممكن يتخزّن ولا يتـbuffer | `Cache-Control: no-cache, no-transform` + `X-Accel-Buffering: no` |
| `/api/*` | loopback-only إلا كان `GENIO_API_TOKEN` | يتقبل الطلب كان جاء من **loopback**، ولا من **شبكة داخلية + أثر Cloudflare** (`trusted_networks`)، ولا من CIDR صريح (`trusted_proxies`). طلب من الإنترنت يبقى 403 حتى بـ هيدرات CF مزيّفة |
| شاشة الدخول | كانت تعرض أسماء مفاتيح (`auth.title.login`) كي الكاتالوغ ما يتجابش | صارت تعرض نص عادي، و سبب الرفض متاع السيرفر (مع IP الـ peer) يبان تحت |

> الهيدرات المزيّفة من الإنترنت ما تتصدّقش: إذا الـ peer ماشي loopback،
> `client_ip()` يرجّع IP الـ peer بروحو و يتجاهل `CF-Connecting-IP`.

## 5) تحقّق آلي: `make verify-prod`

```bash
cd /data/genio-os
GENIO_VERIFY_EMAIL='azmi@hitech.tn' GENIO_VERIFY_PASSWORD='…' make verify-prod
```

يفحص و يطبع PASS/FAIL لكل واحد، و exit code 0 غير كي الكل يعدّي:

| # | الفحص | كيفاش |
|---|---|---|
| 1 | الكود = `origin/main` | `git rev-list --left-right --count HEAD...origin/main` = `0 0` + شجرة نظيفة + الملفات الحرجة |
| 2 | `/api/status` | version، node، workspace داخل مجلد التثبيت |
| 3 | الواجهة | `GET /` = 200 + `data-i18n="v8.tab.office"` + locale switcher |
| 4 | `/api/i18n` | ar-TN/ar → rtl، fr/en → ltr، مفاتيح `v8.*` |
| 5 | SSE | `text/event-stream` + `X-Accel-Buffering: no` + `no-cache` |
| 6 | الكوكي | `Secure` + `HttpOnly` عبر `X-Forwarded-Proto: https` |
| 7 | IP الحقيقي | محاولة فاشلة بإيميل `verify-probe@…` + `CF-Connecting-IP: 203.0.113.77` → لازم تتسجّل في `login_attempts` |
| 8 | الدومين | `go.hitech.tn` = 200 ولا 302 لـ Cloudflare Access |

زائد: `sh scripts/verify_production.sh --code-only` (git و ملفات برك، بلا شبكة)،
و `--no-public` كان تحبّ تتجنّب الدومين.

متغيّرات: `GENIO_INSTALL_DIR` (افتراضي `/data/genio-os`)، `GENIO_VERIFY_URL`
(افتراضي `http://127.0.0.1:8099`)، `GENIO_PUBLIC_URL` (افتراضي `https://go.hitech.tn`).

## 6) تحقّق يدوي بعد النشر

```bash
# 1) الخدمة محليًا
curl -s http://127.0.0.1:8099/api/health

# 2) عبر الدومين (لازم 200 بعد ما تدخل Cloudflare Access، ولا 302 قبل الدخول)
curl -sI https://go.hitech.tn/ | head -3

# 3) الـ i18n و الـ API يخدمو من الدومين
curl -s https://go.hitech.tn/api/i18n/fr | head -c 120

# 4) SSE ما يتـbufferش (لازم event-stream + no-cache + no buffering)
curl -sI -X POST https://go.hitech.tn/api/task/stream \
  -H 'Content-Type: application/json' -d '{"prompt":"ping"}' | grep -iE 'content-type|cache-control|x-accel'

# 5) اللوغ ما فيهش 127.0.0.1 لكل حد
sudo journalctl -u genio-os -n 50 | grep -o 'ip=[0-9.]*' | sort | uniq -c
```
