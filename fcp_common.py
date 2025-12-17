#!/usr/bin/env python3
"""
Final Cut Pro Bundle Cleaner - Common Functions
================================================
مكتبة مشتركة لكل السكربتات - تجنب تكرار الكود

الوظائف:
    - البحث عن .fcpbundle files
    - حساب أحجام الفولدرات (محسّن)
    - تحليل المشاريع
    - مسح آمن للفولدرات
    - تنسيق الأحجام
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime


# الفولدرات المستهدفة للمسح (تتعمل تاني تلقائياً)
TARGET_FOLDERS = [
    "Analysis Files",
    "Render Files",
    "Transcoded Media"
]


def format_size(size_bytes: int) -> str:
    """
    تحويل الحجم من بايت إلى وحدة قابلة للقراءة

    Args:
        size_bytes: الحجم بالبايت

    Returns:
        نص منسق (مثل: "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_folder_size(folder_path: Path, progress_callback=None) -> int:
    """
    حساب حجم الفولدر بالبايت (محسّن للأداء)

    استخدام os.walk() بدلاً من rglob() - أسرع بكثير!

    Args:
        folder_path: مسار الفولدر
        progress_callback: دالة اختيارية لتتبع التقدم (للـ UI)

    Returns:
        الحجم الإجمالي بالبايت
    """
    total = 0
    file_count = 0

    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            # تخطي المجلدات المخفية
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]

            for filename in filenames:
                if filename.startswith('.'):
                    continue

                try:
                    filepath = os.path.join(dirpath, filename)
                    total += os.path.getsize(filepath)
                    file_count += 1

                    # تحديث progress كل 100 ملف
                    if progress_callback and file_count % 100 == 0:
                        progress_callback(file_count, total)

                except (OSError, FileNotFoundError):
                    # ملف محذوف أو مش موجود - تخطيه
                    continue

    except (PermissionError, OSError):
        # مفيش صلاحية - نرجع اللي قدرنا نحسبه
        pass

    return total


def find_fcpbundles(root_path: Path, progress_callback=None) -> List[Path]:
    """
    البحث عن كل ملفات .fcpbundle في المسار وsubfolders

    Args:
        root_path: المسار الرئيسي للبحث فيه
        progress_callback: دالة اختيارية للتحديث (يستقبل bundle_path)

    Returns:
        قائمة بمسارات الـ bundles (مرتبة أبجدياً)
    """
    bundles = []

    try:
        for item in root_path.rglob("*.fcpbundle"):
            if item.is_dir():
                bundles.append(item)
                if progress_callback:
                    progress_callback(item)

    except (PermissionError, OSError) as e:
        # في حالة عدم القدرة على الوصول
        pass

    return sorted(bundles)


def find_date_folders(bundle_path: Path) -> List[Path]:
    """
    البحث عن فولدرات التاريخ داخل الـ bundle

    فولدر التاريخ هو اللي فيه CurrentVersion.fcpevent

    Args:
        bundle_path: مسار الـ .fcpbundle

    Returns:
        قائمة بفولدرات التاريخ
    """
    date_folders = []

    try:
        for item in bundle_path.iterdir():
            # تخطي الملفات والفولدرات المخفية
            if not item.is_dir() or item.name.startswith('.'):
                continue

            # التحقق من وجود CurrentVersion.fcpevent
            if (item / "CurrentVersion.fcpevent").exists():
                date_folders.append(item)

    except (PermissionError, OSError):
        pass

    return date_folders


def analyze_bundle(bundle_path: Path, progress_callback=None) -> Dict:
    """
    تحليل bundle واحد واكتشاف الفولدرات القابلة للمسح

    Args:
        bundle_path: مسار الـ .fcpbundle
        progress_callback: دالة اختيارية للتحديث

    Returns:
        قاموس يحتوي على:
        - bundle_name: اسم المشروع
        - bundle_path: المسار الكامل
        - date_folders: قائمة بفولدرات التاريخ وما بها
        - total_size: الحجم الإجمالي
        - cleanable_size: الحجم القابل للمسح
    """
    result = {
        'bundle_name': bundle_path.name,
        'bundle_path': bundle_path,
        'date_folders': [],
        'total_size': 0,
        'cleanable_size': 0
    }

    date_folders = find_date_folders(bundle_path)

    for date_folder in date_folders:
        date_info = {
            'date_name': date_folder.name,
            'folders': {}
        }

        for target_folder in TARGET_FOLDERS:
            folder_path = date_folder / target_folder

            if folder_path.exists():
                if progress_callback:
                    progress_callback(f"Analyzing {target_folder}...")

                size = get_folder_size(folder_path)

                if size > 0:
                    date_info['folders'][target_folder] = {
                        'path': folder_path,
                        'size': size
                    }
                    result['cleanable_size'] += size

        # فقط أضف date_folder لو فيه حاجة قابلة للمسح
        if date_info['folders']:
            result['date_folders'].append(date_info)

    return result


def delete_folder_safely(folder_path: Path) -> Tuple[bool, str]:
    """
    مسح فولدر بطريقة آمنة مع معالجة الأخطاء

    Args:
        folder_path: مسار الفولدر المراد مسحه

    Returns:
        (نجح/فشل, رسالة الخطأ إن وجد)
    """
    try:
        shutil.rmtree(folder_path)
        return True, ""

    except PermissionError:
        return False, "Permission denied - check file permissions"

    except FileNotFoundError:
        # الملف مش موجود - يعتبر نجاح
        return True, "Already deleted"

    except OSError as e:
        return False, f"OS Error: {str(e)}"

    except Exception as e:
        return False, f"Unknown error: {str(e)}"


def get_folder_count(folder_path: Path) -> int:
    """
    حساب عدد الملفات في فولدر

    Args:
        folder_path: مسار الفولدر

    Returns:
        عدد الملفات
    """
    count = 0
    try:
        for _, _, filenames in os.walk(folder_path):
            count += len(filenames)
    except (PermissionError, OSError):
        pass
    return count


def validate_path(path_str: str) -> Tuple[bool, Optional[Path], str]:
    """
    التحقق من صحة المسار

    Args:
        path_str: نص المسار

    Returns:
        (صحيح/خطأ, Path object, رسالة خطأ)
    """
    if not path_str or not path_str.strip():
        return False, None, "Path is empty"

    try:
        path = Path(path_str).expanduser().resolve()

        if not path.exists():
            return False, None, f"Path does not exist: {path}"

        if not path.is_dir():
            return False, None, f"Path is not a directory: {path}"

        # محاولة القراءة - تأكد من الصلاحيات
        try:
            list(path.iterdir())
        except PermissionError:
            return False, None, f"Permission denied: {path}"

        return True, path, ""

    except Exception as e:
        return False, None, f"Invalid path: {str(e)}"


class ScanProgress:
    """
    كلاس بسيط لتتبع تقدم عملية المسح
    """

    def __init__(self):
        self.bundles_found = 0
        self.bundles_analyzed = 0
        self.current_bundle = None
        self.total_size = 0
        self.start_time = datetime.now()

    def update_bundle_found(self, bundle_path: Path):
        """تحديث عند إيجاد bundle جديد"""
        self.bundles_found += 1
        self.current_bundle = bundle_path.name

    def update_bundle_analyzed(self, size: int):
        """تحديث عند انتهاء تحليل bundle"""
        self.bundles_analyzed += 1
        self.total_size += size

    def get_elapsed_time(self) -> str:
        """الحصول على الوقت المنقضي"""
        elapsed = datetime.now() - self.start_time
        return f"{elapsed.seconds}s"

    def __str__(self) -> str:
        """نص توضيحي للتقدم"""
        return (f"Found: {self.bundles_found} | "
                f"Analyzed: {self.bundles_analyzed} | "
                f"Size: {format_size(self.total_size)}")


# Export public API
__all__ = [
    'TARGET_FOLDERS',
    'format_size',
    'get_folder_size',
    'find_fcpbundles',
    'find_date_folders',
    'analyze_bundle',
    'delete_folder_safely',
    'get_folder_count',
    'validate_path',
    'ScanProgress'
]
