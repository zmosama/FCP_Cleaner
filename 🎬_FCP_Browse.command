#!/bin/bash

# Final Cut Pro Cleaner - Interactive File Browser
# Double-click to run

# الحصول على مسار هذا الملف
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# تشغيل المتصفح التفاعلي مباشرة
python3 "$SCRIPT_DIR/fcp_browse.py"
