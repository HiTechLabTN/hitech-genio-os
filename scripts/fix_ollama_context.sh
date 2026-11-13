#!/usr/bin/env bash
# =============================================================================
# Genio OS — إصلاح context وزمن تحميل Ollama (idempotent)
# الاستعمال من جهاز آخر:
#   ssh -t pop-os 'bash -s' < scripts/fix_ollama_context.sh
# ولا مباشرة على pop-os:
#   bash scripts/fix_ollama_context.sh
# =============================================================================
set -uo pipefail

CTX="${OLLAMA_TARGET_CTX:-32768}"
MODELS=(gemma4:12b qwen2.5-coder:14b qwen2.5vl:7b)

say()  { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✅ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠️  %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m❌ %s\033[0m\n' "$*"; exit 1; }

# -----------------------------------------------------------------------------
say "1/5 — التحقّق من Ollama"
# -----------------------------------------------------------------------------
command -v ollama >/dev/null 2>&1 || die "ollama غير موجود في PATH على هذا الجهاز."
ollama --version 2>/dev/null || true
curl -sf -m 5 http://127.0.0.1:11434/api/version >/dev/null 2>&1 \
  || die "Ollama ما يجاوبش على 127.0.0.1:11434 — شغّلو أوّلًا (ollama serve / systemctl start ollama)."
ok "Ollama يجاوب: $(curl -s -m 5 http://127.0.0.1:11434/api/version)"

# -----------------------------------------------------------------------------
say "2/5 — إعداد systemd (context=$CTX, VRAM-friendly)"
# -----------------------------------------------------------------------------
UNIT=""
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files 2>/dev/null | grep -qE '^ollama\.service'; then
    UNIT="ollama.service"
  fi
fi

if [ -n "$UNIT" ] && systemctl is-active --quiet "$UNIT" 2>/dev/null; then
  sudo mkdir -p "/etc/systemd/system/${UNIT}.d"
  sudo tee "/etc/systemd/system/${UNIT}.d/99-genio-context.conf" >/dev/null <<EOF
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=$CTX"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=30m"
EOF
  sudo systemctl daemon-reload
  sudo systemctl restart "$UNIT" || die "فشل restart متاع $UNIT"
  sleep 3
  systemctl is-active --quiet "$UNIT" && ok "systemd: $UNIT نشط مع الإعداد الجديد" || die "الخدمة ما رجعتش تنشط"
else
  warn "Ollama ماشي تحت systemd (ولا ماشي نشط)."
  if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -qi ollama; then
    warn "Ollama يخدم في Docker — أعد تشغيل الحاوية بهالأمر:"
    echo "  docker rm -f ollama && docker run -d --gpus all -v ollama:/root/.ollama -p 11434:11434 \\"
    echo "    -e OLLAMA_CONTEXT_LENGTH=$CTX -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_MAX_LOADED_MODELS=1 \\"
    echo "    --restart unless-stopped --name ollama ollama/ollama"
  else
    warn "شغّلو يدويًا بـ:"
    echo "  OLLAMA_CONTEXT_LENGTH=$CTX OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 ollama serve"
  fi
fi

# -----------------------------------------------------------------------------
say "3/5 — التحقّق من الـ context الفعلي"
# -----------------------------------------------------------------------------
curl -s -m 180 http://127.0.0.1:11434/api/chat \
  -d "{\"model\":\"${MODELS[0]}\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"options\":{\"num_predict\":1}}" \
  >/dev/null 2>&1 || warn "طلب الاختبار فشل (الموديل ${MODELS[0]} يمكن ما موجودش)."

CTX_REAL="$(curl -s -m 10 http://127.0.0.1:11434/api/ps 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    ms=d.get("models") or []
    print(ms[0].get("context_length") or 0 if ms else 0)
except Exception:
    print(0)
' 2>/dev/null)"
[ -z "$CTX_REAL" ] && CTX_REAL=0
echo "context_length الفعلي = $CTX_REAL  |  المطلوب = $CTX"

if [ "$CTX_REAL" -ge "$CTX" ] 2>/dev/null; then
  ok "الـ context تطبّق بنجاح."
else
  warn "الـ env ما تفعّلش — نصنعو نسخ derivées بـ num_ctx مضمّن (خطة B)."
  for m in "${MODELS[@]}"; do
    if ollama show "$m" >/dev/null 2>&1; then
      base="${m%%:*}"; tag="${m##*:}"
      new="${base}:${tag}-32k"
      printf 'FROM %s\nPARAMETER num_ctx %s\n' "$m" "$CTX" > /tmp/genio-modelfile
      if ollama create "$new" -f /tmp/genio-modelfile >/dev/null 2>&1; then
        ok "إنشاء $new"
      else
        warn "فشل إنشاء $new"
      fi
    else
      echo "   ⏭️  $m غير موجود — تخطّي"
    fi
  done
  echo
  echo "→ في DSH: Models → الموديل → بدّل الاسم إلى النسخة اللي فيها -32k، وحدّد Context=32768 وMax output=8192."
fi

# -----------------------------------------------------------------------------
say "4/5 — GPU"
# -----------------------------------------------------------------------------
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
else
  echo "nvidia-smi غير موجود."
fi

# -----------------------------------------------------------------------------
say "5/5 — الخلاصة"
# -----------------------------------------------------------------------------
ollama ps 2>/dev/null || true
echo
ok "سالينا. إذا الـ context مازال صغير: استعمل الموديلات -32k في DSH، وأعد تشغيل Ollama."
