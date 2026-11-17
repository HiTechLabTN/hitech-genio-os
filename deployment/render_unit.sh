#!/bin/sh
# ==============================================================================
# يطبع نسخة من وحدة systemd بـ User=/Group= متاع حساب موجود.
#
#   sh deployment/render_unit.sh deployment/genio-os.service hitech > /tmp/genio-os.service
#   sh deployment/render_unit.sh deployment/genio-backup.service hitech
#
# علاش: الوحدات مكتوبة بـ User=genio (حساب خدمة)، أما برشا سيرفرات ما فمّاش
# فيها genio و المالك هو حساب آخر. هذا السكربت ما يخلّيش نسخة يدوية تتفرّق
# على الريبو.
# ==============================================================================
set -eu

if [ $# -ne 2 ]; then
    echo "الاستعمال: $0 <unit-file> <user>" >&2
    exit 2
fi

unit="$1"
user="$2"

[ -f "$unit" ] || { echo "ما لقيتش الوحدة: $unit" >&2; exit 2; }
id "$user" >/dev/null 2>&1 || { echo "ما فمّاش يوزر: $user" >&2; exit 2; }

group="$(id -gn "$user" 2>/dev/null || echo "$user")"

sed -e "s/^User=.*/User=${user}/" -e "s/^Group=.*/Group=${group}/" "$unit"
