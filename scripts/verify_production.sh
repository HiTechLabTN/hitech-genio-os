#!/bin/sh
# verify_production.sh — إثبات إن اللي في /data/genio-os هو اللي يخدم على go.hitech.tn
#
#   make verify-prod                      # = sh scripts/verify_production.sh
#   GENIO_VERIFY_EMAIL=… GENIO_VERIFY_PASSWORD=… sh scripts/verify_production.sh
#   sh scripts/verify_production.sh --code-only     # بلا شبكة (git + ملفات)
#
# الفحوصات:
#   1) الكود: HEAD = origin/main (0 0) و الملفات الحرجة موجودة
#   2) /api/status: version، workspace داخل مجلد التثبيت
#   3) الواجهة: / ترجع 200 و فيها علامة النسخة الجديدة (data-i18n + v8 tabs)
#   4) /api/i18n: ar-TN → rtl، fr/en → ltr، مفاتيح v8 موجودة
#   5) SSE: text/event-stream + X-Accel-Buffering: no + Cache-Control: no-cache
#   6) كوكي الجلسة: Secure + HttpOnly عبر X-Forwarded-Proto: https
#   7) IP الحقيقي: محاولة فاشلة بـ CF-Connecting-IP تتسجّل في login_attempts
#   8) الدومين العام: go.hitech.tn يرد (200 ولا 302 لـ Cloudflare Access)
#
# مخرج: تقرير PASS/FAIL/SKIP، exit 0 كي الكل يعدّي، 1 كي فمّاش فشل، 2 خطأ استعمال.

set -u

INSTALL_DIR="${GENIO_INSTALL_DIR:-/data/genio-os}"
LOCAL_URL="${GENIO_VERIFY_URL:-http://127.0.0.1:8099}"
PUBLIC_URL="${GENIO_PUBLIC_URL:-https://go.hitech.tn}"
EMAIL="${GENIO_VERIFY_EMAIL:-}"
PASSWORD="${GENIO_VERIFY_PASSWORD:-}"
CODE_ONLY=0
SKIP_PUBLIC=0

for arg in "$@"; do
  case "$arg" in
    --code-only) CODE_ONLY=1 ;;
    --no-public) SKIP_PUBLIC=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "verify: arg غير معروف: $arg" >&2; exit 2 ;;
  esac
done

PASS=0
FAIL=0
SKIP=0
PROBLEMS=""

pass() { PASS=$((PASS + 1)); printf '  ✅ %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); PROBLEMS="$PROBLEMS\n  - $*"; printf '  ❌ %s\n' "$*"; }
skip() { SKIP=$((SKIP + 1)); printf '  ⏭️  %s\n' "$*"; }
head1() { printf '\n\033[1m%s\033[0m\n' "$*"; }

PY=""
if [ -x "$INSTALL_DIR/venv/bin/python" ]; then
  PY="$INSTALL_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
fi

json_key() { # json_key <file> <top-level> <full.key>  (المفاتيح فيها نقاط)
  [ -f "$1" ] && [ -n "$PY" ] || { printf ''; return 0; }
  "$PY" -c 'import json, sys
try:
    block = json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]
except Exception:
    print(""); raise SystemExit
print(block.get(sys.argv[3], "") if isinstance(block, dict) else "")' "$1" "$2" "$3" 2>/dev/null
}


json_get() { # json_get <file> <dotted.path>
  [ -f "$1" ] && [ -n "$PY" ] || { printf ''; return 0; }
  "$PY" -c 'import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    print(""); raise SystemExit
for part in sys.argv[2].split("."):
    data = data.get(part) if isinstance(data, dict) else None
print("" if data is None else data)' "$1" "$2" 2>/dev/null
}

printf '══════════════════════════════════════════════\n'
printf ' Genio OS — تحقّق الإنتاج\n'
printf ' مجلد التثبيت : %s\n' "$INSTALL_DIR"
printf ' العنوان المحلي: %s\n' "$LOCAL_URL"
printf ' الدومين العام : %s\n' "$PUBLIC_URL"
printf ' التاريخ       : %s\n' "$(date -u '+%Y-%m-%d %H:%M:%SZ')"
printf '══════════════════════════════════════════════\n'

# ---------------------------------------------------------------------------
head1 "1) الكود: HEAD مقابل origin/main"
if [ ! -d "$INSTALL_DIR/.git" ]; then
  fail "ما فمّاش ريبو git في $INSTALL_DIR"
else
  git -C "$INSTALL_DIR" fetch --quiet origin main 2>/dev/null || true
  HEAD_SHA=$(git -C "$INSTALL_DIR" rev-parse HEAD 2>/dev/null || echo "")
  ORIGIN_SHA=$(git -C "$INSTALL_DIR" rev-parse origin/main 2>/dev/null || echo "")
  if [ -z "$HEAD_SHA" ] || [ -z "$ORIGIN_SHA" ]; then
    fail "ما قدرتش نقرا HEAD / origin/main"
  elif [ "$HEAD_SHA" = "$ORIGIN_SHA" ]; then
    pass "HEAD = origin/main = $(echo "$HEAD_SHA" | cut -c1-7)"
  else
    counts=$(git -C "$INSTALL_DIR" rev-list --left-right --count HEAD...origin/main 2>/dev/null)
    ahead=$(echo "$counts" | awk '{print $1}')
    behind=$(echo "$counts" | awk '{print $2}')
    fail "الكود ماشي متزامن: ahead=$ahead behind=$behind (HEAD $(echo "$HEAD_SHA" | cut -c1-7) ≠ origin $(echo "$ORIGIN_SHA" | cut -c1-7)) — شغّل update_genio.sh"
  fi

  dirty=$(git -C "$INSTALL_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [ "$dirty" = "0" ]; then
    pass "الشجرة نظيفة (0 ملف متبدّل)"
  else
    skip "الشجرة فيها $dirty ملف متبدّل (ممكن تكون ملفات وقت التشغيل)"
  fi

  for f in core/proxy.py web/server.py web/static/index.html scripts/setup_githooks.sh .githooks/commit-msg; do
    [ -f "$INSTALL_DIR/$f" ] && pass "موجود: $f" || fail "ناقص: $f (نسخة قديمة؟)"
  done

  hooks=$(git -C "$INSTALL_DIR" config --get core.hooksPath 2>/dev/null || echo "")
  [ -n "$hooks" ] && pass "core.hooksPath مضبوط: $hooks" || skip "core.hooksPath غير مضبوط (make hooks)"
fi

# جلسة للفحوصات اللي تحتاج تسجيل دخول (status/i18n البعض محمي)
HAVE_SESSION=0
CSRF=""
TOKEN=""
if [ -n "$EMAIL" ] && [ -n "$PASSWORD" ]; then
  curl -sS --max-time 20 -D /tmp/genio-verify-login.h -o /tmp/genio-verify-login.json \
    -X POST "$LOCAL_URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -H 'X-Forwarded-Proto: https' \
    -H 'CF-Connecting-IP: 203.0.113.77' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" 2>/dev/null || true
  CSRF=$(json_get /tmp/genio-verify-login.json csrf)
  TOKEN=$(sed -n 's/^[Ss]et-[Cc]ookie: *genio_session=\([^;]*\).*/\1/p' /tmp/genio-verify-login.h 2>/dev/null | head -1)
  if [ -n "$CSRF" ]; then
    HAVE_SESSION=1
  else
    fail "login فشل: $(head -c 120 /tmp/genio-verify-login.json 2>/dev/null)"
  fi
fi

if [ "$CODE_ONLY" = "1" ]; then
  head1 "خلاصة (--code-only)"
  printf '  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
  [ "$FAIL" = "0" ] && exit 0 || exit 1
fi

# ---------------------------------------------------------------------------
head1 "2) الخدمة: /api/status"
curl -sS --max-time 20 -H "Cookie: genio_session=$TOKEN" "$LOCAL_URL/api/status" -o /tmp/genio-verify-status.json 2>/dev/null || true
if [ "$HAVE_SESSION" = "0" ] && [ -n "$EMAIL" ]; then
  skip "/api/status يحتاج جلسة و الدخول فشل"
elif [ ! -s /tmp/genio-verify-status.json ]; then
  fail "ما وصلش جواب من $LOCAL_URL/api/status — الخدمة واقفة؟ (systemctl status genio-os)"
else
  VERSION=$(json_get /tmp/genio-verify-status.json telemetry.version)
  NODE=$(json_get /tmp/genio-verify-status.json telemetry.node)
  WORKSPACE=$(json_get /tmp/genio-verify-status.json telemetry.workspace)
  [ -n "$VERSION" ] && pass "version = $VERSION" || fail "ما لقيتش version في /api/status"
  [ -n "$NODE" ] && pass "node = $NODE"
  case "$WORKSPACE" in
    "$INSTALL_DIR"/*) pass "workspace داخل التثبيت: $WORKSPACE" ;;
    "") skip "workspace غير مذكور في الـ status" ;;
    *) fail "workspace برّا $INSTALL_DIR: $WORKSPACE" ;;
  esac
fi

# ---------------------------------------------------------------------------
head1 "3) الواجهة: /"
INDEX=$(curl -sS --max-time 25 -o /tmp/genio-verify-index.html -w '%{http_code}' "$LOCAL_URL/" 2>/dev/null || echo "000")
if [ "$INDEX" = "200" ]; then
  pass "GET / = 200"
  if grep -q 'data-i18n="v8.tab.office"' /tmp/genio-verify-index.html 2>/dev/null; then
    pass "الواجهة فيها الـ 6 tabs الجداد (data-i18n)"
  else
    fail "الواجهة قديمة: ما فمّاش data-i18n=\"v8.tab.office\""
  fi
  grep -q 'gioLocale' /tmp/genio-verify-index.html 2>/dev/null \
    && pass "locale switcher موجود" || fail "locale switcher ناقص"
  rm -f /tmp/genio-verify-index.html
else
  fail "GET / رجّع $INDEX"
fi

# ---------------------------------------------------------------------------
head1 "4) الكاتالوغ: /api/i18n"
for pair in "ar-TN:rtl" "ar:rtl" "fr:ltr" "en:ltr"; do
  code=${pair%%:*}
  want=${pair##*:}
  curl -sS --max-time 15 "$LOCAL_URL/api/i18n/$code" -o "/tmp/genio-verify-$code.json" 2>/dev/null || true
  dir=$(json_get "/tmp/genio-verify-$code.json" dir)
  if [ "$dir" = "$want" ]; then
    pass "$code → dir=$dir"
  else
    fail "$code → dir='$dir' (المتوقّع $want)"
  fi
done
CLAUSE=$(json_key /tmp/genio-verify-fr.json strings v8.tab.office)
[ -n "$CLAUSE" ] && pass "مفاتيح v8 موجودة (v8.tab.office = \"$CLAUSE\")" || fail "v8.tab.office ناقص في fr — كاتالوغ قديم"

# ---------------------------------------------------------------------------
head1 "5-7) الجلسة، SSE، و IP الحقيقي"
if [ "$HAVE_SESSION" = "0" ]; then
  skip "GENIO_VERIFY_EMAIL / GENIO_VERIFY_PASSWORD ما عطاوناش ولا الدخول فشل — تخطّينا الجلسة/SSE/IP"
else
  if [ -n "$CSRF" ]; then
    pass "login ناجح (CSRF موجود)"
  else
    fail "login فشل: $(head -c 120 /tmp/genio-verify-login.json 2>/dev/null)"
  fi

  if grep -qi '^set-cookie:.*Secure' /tmp/genio-verify-login.h 2>/dev/null; then
    pass "كوكي الجلسة Secure (TLS يتكسّر في Cloudflare)"
  else
    fail "الكوكي ماشي Secure — النسخة القديمة ولا البروكسي ما يمرّرش X-Forwarded-Proto"
  fi
  grep -qi '^set-cookie:.*HttpOnly' /tmp/genio-verify-login.h 2>/dev/null \
    && pass "الكوكي HttpOnly" || fail "الكوكي ماشي HttpOnly"

  if [ -n "$CSRF" ]; then
    curl -sS --max-time 25 -D /tmp/genio-verify-sse.h -o /dev/null \
      -X POST "$LOCAL_URL/api/task/stream" \
      -H 'Content-Type: application/json' \
      -H "X-Genio-CSRF: $CSRF" \
      -H "Cookie: genio_session=$TOKEN" \
      -d '{"prompt":"verify probe"}' 2>/dev/null || true

    grep -qi 'content-type: text/event-stream' /tmp/genio-verify-sse.h 2>/dev/null \
      && pass "SSE: content-type = text/event-stream" || fail "SSE: content-type غالط (الـ endpoint ماشي SSE)"
    grep -qi 'x-accel-buffering: no' /tmp/genio-verify-sse.h 2>/dev/null \
      && pass "SSE: X-Accel-Buffering: no" || fail "SSE: X-Accel-Buffering ناقص (buffering عبر nginx)"
    grep -qi 'cache-control:.*no-cache' /tmp/genio-verify-sse.h 2>/dev/null \
      && pass "SSE: Cache-Control: no-cache" || fail "SSE: Cache-Control ناقص"
  fi

  # IP الحقيقي: محاولة فاشلة بإيميل مؤقّت + IP اختباري (TEST-NET-3)
  PROBE_EMAIL="verify-probe@invalid.genio.local"
  curl -sS --max-time 15 -o /dev/null -X POST "$LOCAL_URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -H 'X-Forwarded-Proto: https' \
    -H 'CF-Connecting-IP: 203.0.113.77' \
    -d "{\"email\":\"$PROBE_EMAIL\",\"password\":\"wrong\"}" 2>/dev/null || true

  if [ -z "$PY" ]; then
    skip "ما فمّاش python لقراءة قاعدة البيانات — تخطّينا فحص IP"
  else
    IP_RESULT=$("$PY" -c 'import os, sqlite3, sys
root = sys.argv[1]
paths = []
for base, _dirs, files in os.walk(root):
    paths.extend(os.path.join(base, f) for f in files if f.endswith(".db"))
for path in paths:
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type=\"table\"")}
        if "login_attempts" not in tables:
            continue
        rows = [r[0] for r in conn.execute("select ip from login_attempts where email like \"verify-probe%\" order by created_at desc limit 5")]
        if rows:
            print("|".join(rows))
            break
    except Exception:
        continue' "$INSTALL_DIR" 2>/dev/null)
    case "$IP_RESULT" in
      *203.0.113.77*) pass "IP الحقيقي تسجّل في login_attempts (203.0.113.77، ماشي 127.0.0.1)" ;;
      "") fail "ما لقيتش محاولة مسجّلة في login_attempts — الجدول ولا الـ IP غالط" ;;
      *) fail "login_attempts سجّل '$IP_RESULT' بدل 203.0.113.77" ;;
    esac
  fi
  rm -f /tmp/genio-verify-login.h /tmp/genio-verify-login.json /tmp/genio-verify-sse.h /tmp/genio-verify-status.json
fi

# ---------------------------------------------------------------------------
if [ "$SKIP_PUBLIC" = "0" ]; then
  head1 "8) الدومين العام: $PUBLIC_URL"
  CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "$PUBLIC_URL/" 2>/dev/null || echo "000")
  case "$CODE" in
    200) pass "GET $PUBLIC_URL/ = 200 (واصل للـ origin)" ;;
    302|403)
      LOC=$(curl -sSI --max-time 25 "$PUBLIC_URL/" 2>/dev/null | grep -i '^location' | head -1)
      case "$LOC" in
        *cloudflareaccess*) pass "GET $PUBLIC_URL/ = $CODE → Cloudflare Access يحمي (سليم)" ;;
        *) fail "GET $PUBLIC_URL/ = $CODE و location غير متوقّع: $LOC" ;;
      esac
      ;;
    000) fail "ما قدرتش نوصل لـ $PUBLIC_URL (شبكة؟ DNS؟ tunnel واقف؟)" ;;
    *) fail "GET $PUBLIC_URL/ = $CODE" ;;
  esac

  API_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "$PUBLIC_URL/api/i18n/fr" 2>/dev/null || echo "000")
  case "$API_CODE" in
    200) pass "API عبر الدومين = 200" ;;
    302|403) pass "API عبر الدومين = $API_CODE (Access يحمي، سليم)" ;;
    *) fail "API عبر الدومين = $API_CODE" ;;
  esac
fi

# ---------------------------------------------------------------------------
head1 "الخلاصة"
printf '  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
if [ "$FAIL" -gt 0 ]; then
  printf '  المشاكل:\n%b\n' "$PROBLEMS"
  exit 1
fi
printf '  ✅ الإنتاج مطابق للريبو و كل الفحوصات عدّاو.\n'
exit 0
