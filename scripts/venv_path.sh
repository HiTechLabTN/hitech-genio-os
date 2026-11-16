#!/bin/sh
# وين نخليو الـ venv؟
#
#   - داخل الريبو (./venv) هو الافتراضي.
#   - برّا الريبو إذا المجلّد على نظام ملفات ما يسمحش بالتنفيذ (noexec)،
#     خاطر venv فيه ملفات .so (psutil, pydantic-core…) ما تنجّمش تتحمّل.
#     sshfs يعمل هكّا بالضبط.
#   - GENIO_VENV يفرض المسار، بلا ما نسألو.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)

if [ -n "${GENIO_VENV:-}" ]; then
    printf '%s\n' "$GENIO_VENV"
    exit 0
fi

mnt=$(df -P "$root" 2>/dev/null | awk 'NR==2 {print $6}')
opts=""
if [ -n "${mnt:-}" ]; then
    # كامل الـ mounts اللي تغطّي المجلّد (autofs + sshfs مثلًا) — إذا وحدة فيهم
    # noexec، الـ .so ما تخدمش.
    opts=$(mount 2>/dev/null | grep -F " on ${mnt} type " | sed -n 's/.*(\(.*\))/\1/p' | tr '\n' ',')
fi

case ",${opts}" in
    *,noexec,*)
        printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/genio-os/venv"
        ;;
    *)
        printf '%s\n' "$root/venv"
        ;;
esac
