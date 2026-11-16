#!/bin/sh
# يربط الـ hooks متاع .githooks بالريبو الحالي، بلا ما تحتاج تنسخ شي بيدك.
#
#   sh scripts/setup_githooks.sh       # ولا: make hooks
#
# عادي: core.hooksPath = .githooks  (git يشغّل الملفات مباشرة من الريبو)
# noexec (sshfs): git ما يقدرش ينفّذ ملف من الريبو، فنسخوهم لـ
#   ${XDG_DATA_HOME:-$HOME/.local/share}/genio-os/hooks  و نربطو هالمسار.
# في الزوز الحالات: أي clone جديد ياخو نفس الحماية بأمر واحد.

set -eu

root=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "genio: ماشي داخل ريبو git." >&2
  exit 1
}

src="$root/.githooks"
[ -f "$src/commit-msg" ] || {
  echo "genio: ما لقيتش $src/commit-msg" >&2
  exit 1
}

if [ -x "$src/commit-msg" ]; then
  git -C "$root" config --local core.hooksPath ".githooks"
  echo "genio: core.hooksPath = .githooks  ($src)"
  exit 0
fi

# noexec: ننسخو لقرص محلي فيه exec
data="${XDG_DATA_HOME:-$HOME/.local/share}/genio-os/hooks"
mkdir -p "$data"
cp "$src/commit-msg" "$data/commit-msg"
chmod +x "$data/commit-msg" 2>/dev/null || true
git -C "$root" config --local core.hooksPath "$data"
echo "genio: core.hooksPath = $data"
echo "genio: (الريبو على noexec — git ما ينفّذش ملفات منّو، لذلك النسخة تنسخ برّا)"
