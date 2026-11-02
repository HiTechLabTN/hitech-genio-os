#!/usr/bin/env bash
cd /data/genio-os
echo "🔄 جاري فحص وسحب آخر التحديثات من مستودع GitHub..."
git pull origin main

echo -e "\n\033[38;5;51m=============================================================================="
echo "📋 تقرير التحديثات الأخيرة (Changelog & New Features):"
echo -e "==============================================================================\033[0m"
git log -n 3 --pretty=format:"  - %s (%ar by %an)"
echo -e "\n\033[38;5;51m==============================================================================\033[0m"

# Restart service to apply changes
sudo systemctl restart genio-os.service
TS_MY_IP=$(tailscale ip -4 2>/dev/null | head -n 1 || hostname -I | awk '{print $1}')
PORT=$(grep -oP '"port":\s*\K[0-9]+' config.json 2>/dev/null || echo "8095")

echo -e "\n\033[38;5;46m\033[1m🎉 مريقل! تم تحديث وتشغيل Genio OS بنجاح.\033[0m"
echo -e "  🌐 واجهة الويب والموبايل (عبر المتصفح أو هاتفك RedMagic):"
echo -e "     👉 http://${TS_MY_IP}:${PORT}"
echo -e "     👉 http://$(hostname):${PORT}"
echo -e "\n  💻 واجهة الكونسول التفاعلية (Terminal TUI):"
echo -e "     👉 اكتب في أي وقت: \033[33mgenio\033[0m"
echo -e "  🔄 لتحديث المنصة في المستقبل بضغطة زر:"
echo -e "     👉 \033[33mgenio-update\033[0m"
echo -e "\033[38;5;51m==============================================================================\033[0m"
