#!/usr/bin/env python3
"""
Final Cut Pro Bundle Cleaner
=============================
سكربت لمسح الفولدرات الكبيرة (Analysis Files, Render Files, Transcoded Media)
من مشاريع Final Cut Pro للباك أب

الاستخدام:
    python3 fcp_cleaner.py [المسار] [--auto] [--dry-run]

الخيارات:
    --auto      مسح تلقائي لكل الفولدرات بدون تأكيد
    --dry-run   عرض التقرير فقط بدون مسح

إذا لم تحدد مسار، سيستخدم المجلد الحالي

الفولدرات المستهدفة: Analysis Files, Render Files, Transcoded Media
"""

import sys
from pathlib import Path
from typing import List, Dict

# استيراد الوظائف المشتركة
from fcp_common import (
    TARGET_FOLDERS,
    format_size,
    find_fcpbundles,
    analyze_bundle,
    delete_folder_safely
)


def print_analysis(projects: List[Dict]):
    """طباعة تقرير التحليل"""
    print("\n" + "="*70)
    print("📊 تقرير تحليل مشاريع Final Cut Pro")
    print("="*70 + "\n")

    total_cleanable = 0
    project_count = 0

    for idx, project in enumerate(projects, 1):
        if project['cleanable_size'] == 0:
            continue

        project_count += 1
        print(f"[{idx}] المشروع: {project['bundle_name']}")
        print(f"    المسار: {project['bundle_path']}")

        for date_folder in project['date_folders']:
            print(f"\n    📁 التاريخ: {date_folder['date_name']}")

            for folder_name, info in date_folder['folders'].items():
                size_str = format_size(info['size'])
                print(f"       • {folder_name}: {size_str}")
                total_cleanable += info['size']

        print(f"\n    💾 إجمالي قابل للمسح: {format_size(project['cleanable_size'])}")
        print("    " + "─"*60)

    print("\n" + "="*70)
    print(f"📦 إجمالي المشاريع التي تحتوي على ملفات قابلة للمسح: {project_count}")
    print(f"🗑️  إجمالي المساحة القابلة للتوفير: {format_size(total_cleanable)}")
    print("="*70 + "\n")


def confirm_deletion(message: str) -> bool:
    """طلب تأكيد من المستخدم"""
    while True:
        response = input(f"{message} (yes/no): ").lower().strip()
        if response in ['yes', 'y', 'نعم']:
            return True
        elif response in ['no', 'n', 'لا']:
            return False
        print("⚠️  من فضلك أدخل yes أو no")




def interactive_menu(projects: List[Dict]):
    """القائمة التفاعلية للمسح"""
    # فلترة المشاريع التي تحتوي على ملفات قابلة للمسح
    cleanable_projects = [p for p in projects if p['cleanable_size'] > 0]

    if not cleanable_projects:
        print("\n✅ لا توجد ملفات قابلة للمسح!")
        return

    while True:
        print("\n" + "="*70)
        print("🎯 الخيارات:")
        print("="*70)
        print("[1] مسح فولدر معين من مشروع معين")
        print("[2] مسح كل الفولدرات الكبيرة من مشروع معين")
        print("[3] مسح كل الفولدرات الكبيرة من كل المشاريع")
        print("[4] عرض التقرير مرة أخرى")
        print("[0] خروج")
        print("="*70)

        choice = input("\n👉 اختر: ").strip()

        if choice == '0':
            print("\n👋 تم الإنهاء بنجاح!")
            break

        elif choice == '1':
            delete_specific_folder(cleanable_projects)

        elif choice == '2':
            delete_project_folders(cleanable_projects)

        elif choice == '3':
            delete_all_folders(cleanable_projects)

        elif choice == '4':
            print_analysis(projects)

        else:
            print("⚠️  اختيار غير صحيح!")


def delete_specific_folder(projects: List[Dict]):
    """مسح فولدر معين من مشروع معين"""
    print("\n📋 المشاريع المتاحة:")
    for idx, project in enumerate(projects, 1):
        print(f"[{idx}] {project['bundle_name']} ({format_size(project['cleanable_size'])})")

    try:
        project_idx = int(input("\n👉 اختر رقم المشروع: ")) - 1
        if project_idx < 0 or project_idx >= len(projects):
            print("❌ رقم المشروع غير صحيح!")
            return
    except ValueError:
        print("❌ من فضلك أدخل رقم!")
        return

    project = projects[project_idx]

    # عرض الفولدرات المتاحة
    all_folders = []
    for date_folder in project['date_folders']:
        for folder_name, info in date_folder['folders'].items():
            all_folders.append({
                'name': f"{date_folder['date_name']}/{folder_name}",
                'path': info['path'],
                'size': info['size']
            })

    print("\n📁 الفولدرات المتاحة:")
    for idx, folder in enumerate(all_folders, 1):
        print(f"[{idx}] {folder['name']} ({format_size(folder['size'])})")

    try:
        folder_idx = int(input("\n👉 اختر رقم الفولدر: ")) - 1
        if folder_idx < 0 or folder_idx >= len(all_folders):
            print("❌ رقم الفولدر غير صحيح!")
            return
    except ValueError:
        print("❌ من فضلك أدخل رقم!")
        return

    folder = all_folders[folder_idx]

    if confirm_deletion(f"⚠️  هل أنت متأكد من مسح {folder['name']}؟"):
        print(f"🗑️  جاري المسح...")
        success, error_msg = delete_folder_safely(folder['path'])
        if success:
            print(f"✅ تم المسح بنجاح! تم توفير {format_size(folder['size'])}")
        else:
            print(f"❌ فشل المسح: {error_msg}")


def delete_project_folders(projects: List[Dict]):
    """مسح كل الفولدرات الكبيرة من مشروع معين"""
    print("\n📋 المشاريع المتاحة:")
    for idx, project in enumerate(projects, 1):
        print(f"[{idx}] {project['bundle_name']} ({format_size(project['cleanable_size'])})")

    try:
        project_idx = int(input("\n👉 اختر رقم المشروع: ")) - 1
        if project_idx < 0 or project_idx >= len(projects):
            print("❌ رقم المشروع غير صحيح!")
            return
    except ValueError:
        print("❌ من فضلك أدخل رقم!")
        return

    project = projects[project_idx]

    print(f"\n⚠️  سيتم مسح الفولدرات التالية من {project['bundle_name']}:")
    for date_folder in project['date_folders']:
        for folder_name, info in date_folder['folders'].items():
            print(f"   • {date_folder['date_name']}/{folder_name} ({format_size(info['size'])})")

    print(f"\n💾 إجمالي المساحة التي سيتم توفيرها: {format_size(project['cleanable_size'])}")

    if confirm_deletion("⚠️  هل أنت متأكد من المسح؟"):
        deleted_count = 0
        total_freed = 0

        for date_folder in project['date_folders']:
            for folder_name, info in date_folder['folders'].items():
                print(f"🗑️  جاري مسح {folder_name}...")
                success, error_msg = delete_folder_safely(info['path'])
                if success:
                    deleted_count += 1
                    total_freed += info['size']
                    print(f"   ✅ تم")
                else:
                    print(f"   ❌ فشل: {error_msg}")

        print(f"\n✅ تم مسح {deleted_count} فولدر! تم توفير {format_size(total_freed)}")


def delete_all_folders(projects: List[Dict], skip_confirm: bool = False):
    """مسح كل الفولدرات الكبيرة من كل المشاريع"""
    total_size = sum(p['cleanable_size'] for p in projects)

    print(f"\n⚠️  سيتم مسح كل الفولدرات الكبيرة من {len(projects)} مشروع")
    print(f"💾 إجمالي المساحة التي سيتم توفيرها: {format_size(total_size)}")

    if not skip_confirm:
        if not confirm_deletion("⚠️⚠️  هل أنت متأكد تماماً من المسح الشامل؟"):
            print("❌ تم الإلغاء")
            return

        # تأكيد ثاني
        if not confirm_deletion("⚠️  تأكيد نهائي - لا يمكن التراجع!"):
            print("❌ تم الإلغاء")
            return
    else:
        print("⚡ جاري المسح التلقائي...\n")

    deleted_count = 0
    total_freed = 0

    for project in projects:
        print(f"\n📦 معالجة: {project['bundle_name']}")

        for date_folder in project['date_folders']:
            for folder_name, info in date_folder['folders'].items():
                print(f"   🗑️  مسح {folder_name}...")
                success, error_msg = delete_folder_safely(info['path'])
                if success:
                    deleted_count += 1
                    total_freed += info['size']
                    print(f"      ✅ تم")
                else:
                    print(f"      ❌ فشل: {error_msg}")

    print(f"\n🎉 اكتمل! تم مسح {deleted_count} فولدر من {len(projects)} مشروع")
    print(f"💾 تم توفير: {format_size(total_freed)}")


def main():
    """الدالة الرئيسية"""
    # عرض اللوجو
    logo = """
     ------------------------------------------------------------
   ----------------------------------------------------------------
  ------------------------------------------------------------------
  ------------------------------------------------------------------
  --------##############----##############-----#############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############----##############----##############--------
  --------##############-----############*----##############--------
  --------##############----------------------##############--------
  --------##############----------------------##############--------
  --------##############----------------------##############--------
  --------##############----------------------##############--------
  --------##############----------------------##############--------
  --------##############----------------------##############--------
  --------##############-----------------------#############--------
  ------------------------------------------------------------------
  ------------------------------------------------------------------
   ----------------------------------------------------------------
     ------------------------------------------------------------
    """
    print(logo)
    print("\n" + "="*70)
    print("           🎬 Final Cut Pro Bundle Cleaner")
    print("="*70)

    # معالجة الـ command line arguments
    args = sys.argv[1:]
    auto_mode = '--auto' in args
    dry_run = '--dry-run' in args

    # إزالة الـ flags من الـ args
    path_args = [arg for arg in args if not arg.startswith('--')]

    # تحديد المسار
    if path_args:
        root_path = Path(path_args[0])
    else:
        root_path = Path.cwd()

    if not root_path.exists():
        print(f"❌ المسار غير موجود: {root_path}")
        sys.exit(1)

    print(f"\n📂 المسار: {root_path}")

    if dry_run:
        print("🔍 وضع المعاينة (Dry Run) - لن يتم المسح")
    elif auto_mode:
        print("⚡ الوضع التلقائي - سيتم المسح بدون تأكيد")

    print("🔍 جاري البحث عن مشاريع Final Cut Pro...")

    # البحث عن المشاريع
    bundles = find_fcpbundles(root_path)

    if not bundles:
        print("\n❌ لم يتم العثور على أي مشاريع .fcpbundle!")
        sys.exit(0)

    print(f"✅ تم العثور على {len(bundles)} مشروع\n")
    print("⏳ جاري تحليل المشاريع...")

    # تحليل المشاريع
    projects = []
    for bundle in bundles:
        analysis = analyze_bundle(bundle)
        projects.append(analysis)

    # عرض التقرير
    print_analysis(projects)

    # اختيار الوضع
    if dry_run:
        print("\n✅ انتهى وضع المعاينة")
        return
    elif auto_mode:
        # مسح تلقائي
        cleanable_projects = [p for p in projects if p['cleanable_size'] > 0]
        if cleanable_projects:
            delete_all_folders(cleanable_projects, skip_confirm=True)
        else:
            print("\n✅ لا توجد ملفات قابلة للمسح!")
    else:
        # القائمة التفاعلية
        interactive_menu(projects)


if __name__ == "__main__":
    main()
