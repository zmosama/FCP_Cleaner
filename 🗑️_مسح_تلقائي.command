#!/bin/bash

# Final Cut Pro Cleaner - المسح التلقائي
# Double-click لتشغيل السكربت

# الحصول على مسار هذا الملف
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

clear
echo "════════════════════════════════════════════════════════"
echo "🗑️  Final Cut Pro Backup Cleaner - المسح التلقائي"
echo "════════════════════════════════════════════════════════"
echo ""
echo "⚠️  تحذير: سيتم مسح الفولدرات التالية:"
echo "   • Analysis Files"
echo "   • Render Files"
echo "   • Transcoded Media"
echo ""
echo "هذه الملفات يمكن إعادة إنشائها من Final Cut Pro"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""

# طلب تأكيد
read -p "هل أنت متأكد من المتابعة؟ (yes/no): " confirm

if [[ "$confirm" != "yes" && "$confirm" != "y" && "$confirm" != "نعم" ]]; then
    echo ""
    echo "❌ تم الإلغاء"
    echo ""
    echo "اضغط أي زر للخروج..."
    read -n 1 -s
    exit 0
fi

echo ""
echo "جاري المسح..."
echo ""

# تشغيل السكربت في وضع المسح التلقائي
python3 fcp_cleaner.py 12 --auto

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ اكتمل المسح بنجاح!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "اضغط أي زر للخروج..."
read -n 1 -s
