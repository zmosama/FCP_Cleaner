#!/bin/bash

# Final Cut Pro Cleaner - Interactive Mode
# Double-click to run

# الحصول على مسار هذا الملف
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# تشغيل السكربت التفاعلي مباشرة
# السكربت هيسأل عن المسار بنفسه
python3 "$SCRIPT_DIR/fcp_clean.py"
