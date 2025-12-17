#!/bin/bash

# Final Cut Pro Backup Cleaner - Wrapper Script
# الاستخدام:
#   ./clean.sh [--dry-run|--auto]

# المسار الافتراضي (فولدر شهر 12)
DEFAULT_PATH="12"

# الحصول على مسار السكربت
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/fcp_cleaner.py"

# التحقق من وجود السكربت
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ خطأ: لم يتم العثور على fcp_cleaner.py"
    exit 1
fi

# تشغيل السكربت
python3 "$PYTHON_SCRIPT" "$DEFAULT_PATH" "$@"
