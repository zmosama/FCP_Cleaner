#!/usr/bin/env python3
"""
Final Cut Pro Bundle Cleaner - Interactive TUI
===============================================
واجهة تفاعلية لمسح فولدرات Final Cut Pro الكبيرة

التحكم:
    ↑/↓      - التنقل بين الفولدرات
    d        - مسح الفولدر المحدد
    D        - مسح كل الفولدرات
    q        - خروج
    ENTER    - تحديد/إلغاء تحديد
"""

import os
import sys
import curses
import readline
import glob
from pathlib import Path
from typing import List, Dict

# استيراد الوظائف المشتركة
from fcp_common import (
    TARGET_FOLDERS,
    format_size,
    find_fcpbundles,
    delete_folder_safely
)


def analyze_bundle(bundle_path: Path) -> Dict:
    """
    تحليل bundle واحد - نسخة مبسطة للـ TUI
    (النسخة الكاملة في fcp_common.py)
    """
    from fcp_common import find_date_folders, get_folder_size

    result = {
        'bundle_name': bundle_path.name,
        'bundle_path': bundle_path,
        'folders': []
    }

    date_folders = find_date_folders(bundle_path)

    for date_folder in date_folders:
        for target_folder in TARGET_FOLDERS:
            folder_path = date_folder / target_folder
            if folder_path.exists():
                size = get_folder_size(folder_path)
                if size > 0:
                    result['folders'].append({
                        'name': f"{date_folder.name}/{target_folder}",
                        'path': folder_path,
                        'size': size,
                        'deleted': False
                    })

    return result


class InteractiveCleaner:
    def __init__(self, stdscr, projects: List[Dict]):
        self.stdscr = stdscr
        self.projects = projects
        self.current_idx = 0
        self.scroll_offset = 0
        self.selected = set()

        # تجميع كل الفولدرات في قائمة واحدة
        self.items = []
        for project in projects:
            for folder in project['folders']:
                if not folder.get('deleted', False):
                    self.items.append({
                        'project_name': project['bundle_name'],
                        'folder_name': folder['name'],
                        'path': folder['path'],
                        'size': folder['size'],
                        'folder_ref': folder  # reference للتحديث
                    })

        # إعدادات الألوان
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.curs_set(0)  # إخفاء المؤشر

    def get_total_size(self) -> int:
        """حساب المساحة الإجمالية"""
        return sum(item['size'] for item in self.items)

    def get_selected_size(self) -> int:
        """حساب مساحة المحدد"""
        return sum(self.items[i]['size'] for i in self.selected)

    def draw(self):
        """رسم الواجهة"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # العنوان
        title = " Final Cut Pro Cleaner "
        self.stdscr.addstr(0, (width - len(title)) // 2, title,
                          curses.color_pair(1) | curses.A_BOLD)

        # المعلومات
        total_size = self.get_total_size()
        selected_size = self.get_selected_size()

        info_line = f" Items: {len(self.items)} | Total: {format_size(total_size)} | Selected: {format_size(selected_size)} "
        self.stdscr.addstr(1, 0, info_line, curses.color_pair(2))

        # خط فاصل
        self.stdscr.addstr(2, 0, "─" * width)

        # عرض الفولدرات
        visible_height = height - 6

        # التأكد من أن العنصر الحالي في منطقة العرض
        if self.current_idx < self.scroll_offset:
            self.scroll_offset = self.current_idx
        elif self.current_idx >= self.scroll_offset + visible_height:
            self.scroll_offset = self.current_idx - visible_height + 1

        for i in range(visible_height):
            idx = i + self.scroll_offset
            if idx >= len(self.items):
                break

            item = self.items[idx]

            # تحديد اللون
            if idx == self.current_idx:
                color = curses.color_pair(5) | curses.A_BOLD
            elif idx in self.selected:
                color = curses.color_pair(3)
            else:
                color = curses.A_NORMAL

            # رمز التحديد
            mark = "[x]" if idx in self.selected else "[ ]"

            # اسم المشروع والفولدر
            name = f"{item['project_name']}/{item['folder_name']}"
            size = format_size(item['size'])

            # قص النص إذا كان طويل
            max_name_len = width - len(mark) - len(size) - 4
            if len(name) > max_name_len:
                name = name[:max_name_len - 3] + "..."

            line = f"{mark} {name}"

            # إضافة المساحة في النهاية
            spaces = width - len(line) - len(size) - 2
            line = line + " " * spaces + size

            try:
                self.stdscr.addstr(3 + i, 0, line[:width-1], color)
            except curses.error:
                pass

        # خط فاصل
        self.stdscr.addstr(height - 3, 0, "─" * width)

        # التعليمات
        help_text = " ↑/↓:Navigate | SPACE:Select | d:Delete | D:Delete All | q:Quit "
        self.stdscr.addstr(height - 2, 0, help_text, curses.color_pair(1))

        self.stdscr.refresh()

    def confirm_delete(self, message: str) -> bool:
        """طلب تأكيد المسح"""
        height, width = self.stdscr.getmaxyx()

        # رسم نافذة التأكيد
        confirm_h = 7
        confirm_w = min(60, width - 4)
        start_y = (height - confirm_h) // 2
        start_x = (width - confirm_w) // 2

        # خلفية
        confirm_win = curses.newwin(confirm_h, confirm_w, start_y, start_x)
        confirm_win.box()

        # النص
        confirm_win.addstr(1, 2, "Confirm Delete", curses.color_pair(4) | curses.A_BOLD)
        confirm_win.addstr(3, 2, message[:confirm_w - 4])
        confirm_win.addstr(5, 2, "Press 'y' to confirm, 'n' to cancel", curses.color_pair(3))

        confirm_win.refresh()

        # انتظار الرد
        while True:
            key = self.stdscr.getch()
            if key == ord('y') or key == ord('Y'):
                return True
            elif key == ord('n') or key == ord('N') or key == 27:  # ESC
                return False

    def show_message(self, message: str, duration: int = 2000):
        """عرض رسالة مؤقتة"""
        height, width = self.stdscr.getmaxyx()

        msg_win = curses.newwin(5, min(len(message) + 4, width - 4),
                                (height - 5) // 2, (width - min(len(message) + 4, width - 4)) // 2)
        msg_win.box()
        msg_win.addstr(2, 2, message[:width - 8], curses.color_pair(2) | curses.A_BOLD)
        msg_win.refresh()

        curses.napms(duration)

    def delete_selected(self):
        """مسح الفولدرات المحددة"""
        if not self.selected:
            self.show_message("No items selected!", 1000)
            return

        count = len(self.selected)
        size = format_size(self.get_selected_size())

        if not self.confirm_delete(f"Delete {count} folders ({size})?"):
            return

        # المسح
        deleted = 0
        for idx in sorted(self.selected, reverse=True):
            item = self.items[idx]
            success, _ = delete_folder_safely(item['path'])
            if success:
                item['folder_ref']['deleted'] = True
                deleted += 1

        # تحديث القائمة
        self.items = [item for i, item in enumerate(self.items) if i not in self.selected]
        self.selected.clear()
        self.current_idx = min(self.current_idx, len(self.items) - 1)

        self.show_message(f"Deleted {deleted} folders!")

    def delete_current(self):
        """مسح الفولدر الحالي"""
        if not self.items:
            return

        item = self.items[self.current_idx]
        size = format_size(item['size'])

        if not self.confirm_delete(f"Delete {item['folder_name']} ({size})?"):
            return

        success, error_msg = delete_folder_safely(item['path'])
        if success:
            item['folder_ref']['deleted'] = True
            self.items.pop(self.current_idx)
            self.current_idx = min(self.current_idx, len(self.items) - 1)
            self.show_message("Deleted successfully!")
        else:
            self.show_message(f"Failed: {error_msg}", 2000)

    def delete_all(self):
        """مسح كل الفولدرات"""
        if not self.items:
            return

        count = len(self.items)
        size = format_size(self.get_total_size())

        if not self.confirm_delete(f"Delete ALL {count} folders ({size})?"):
            return

        deleted = 0
        for item in self.items:
            success, _ = delete_folder_safely(item['path'])
            if success:
                item['folder_ref']['deleted'] = True
                deleted += 1

        self.items.clear()
        self.selected.clear()
        self.current_idx = 0

        self.show_message(f"Deleted {deleted} folders!")

    def run(self):
        """تشغيل الواجهة التفاعلية"""
        while True:
            self.draw()

            if not self.items:
                self.show_message("All done! Press any key to exit.", 3000)
                self.stdscr.getch()
                break

            key = self.stdscr.getch()

            # التنقل
            if key == curses.KEY_UP:
                self.current_idx = max(0, self.current_idx - 1)
            elif key == curses.KEY_DOWN:
                self.current_idx = min(len(self.items) - 1, self.current_idx + 1)

            # التحديد
            elif key == ord(' ') or key == ord('\n'):
                if self.current_idx in self.selected:
                    self.selected.remove(self.current_idx)
                else:
                    self.selected.add(self.current_idx)

            # المسح
            elif key == ord('d'):
                self.delete_current()
            elif key == ord('D'):
                self.delete_all()

            # الخروج
            elif key == ord('q') or key == ord('Q'):
                break


def main(stdscr, root_path: Path):
    """الدالة الرئيسية"""
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # عرض اللوجو أولاً
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

    logo_lines = logo.strip().split('\n')
    start_y = max(0, (height - len(logo_lines) - 8) // 2)

    # عرض اللوجو
    for i, line in enumerate(logo_lines):
        if start_y + i < height - 6:
            x_pos = max(0, (width - len(line)) // 2)
            try:
                stdscr.addstr(start_y + i, x_pos, line, curses.color_pair(1))
            except curses.error:
                pass

    # عرض رسائل التحميل تحت اللوجو
    loading_y = start_y + len(logo_lines) + 2

    loading_msgs = [
        "Searching for .fcpbundle files...",
        "Analyzing projects...",
        "Calculating sizes..."
    ]

    for i, msg in enumerate(loading_msgs):
        if loading_y + i < height - 1:
            stdscr.addstr(loading_y + i, max(0, (width - len(msg)) // 2), msg)
        stdscr.refresh()

    # البحث والتحليل
    bundles = find_fcpbundles(root_path)

    if not bundles:
        stdscr.clear()
        msg = "No .fcpbundle files found!"
        stdscr.addstr(height // 2, (width - len(msg)) // 2, msg)
        stdscr.addstr(height // 2 + 2, (width - 25) // 2, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        return

    projects = []
    for bundle in bundles:
        analysis = analyze_bundle(bundle)
        if analysis['folders']:
            projects.append(analysis)

    if not projects:
        stdscr.clear()
        msg = "No cleanable folders found!"
        stdscr.addstr(height // 2, (width - len(msg)) // 2, msg)
        stdscr.addstr(height // 2 + 2, (width - 25) // 2, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        return

    # تشغيل الواجهة التفاعلية
    cleaner = InteractiveCleaner(stdscr, projects)
    cleaner.run()


def path_completer(text, state):
    """Tab completion للمسارات"""
    # توسيع ~ إلى المسار الكامل
    text = os.path.expanduser(text)

    # إضافة * للبحث
    if os.path.isdir(text):
        text = os.path.join(text, '*')
    else:
        text = text + '*'

    # البحث عن المطابقات
    matches = glob.glob(text)

    # إضافة / للفولدرات
    matches = [f + '/' if os.path.isdir(f) else f for f in matches]

    try:
        return matches[state]
    except IndexError:
        return None


def setup_readline():
    """إعداد readline للـ tab completion"""
    # تفعيل tab completion
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(path_completer)


if __name__ == "__main__":
    # إعداد tab completion
    setup_readline()

    # طلب المسار من المستخدم
    if len(sys.argv) > 1:
        root_path = Path(sys.argv[1]).expanduser().resolve()
    else:
        print("\n" + "=" * 60)
        print("🎬 Final Cut Pro Bundle Cleaner")
        print("=" * 60)
        print("\nExamples of valid inputs:")
        print("  • 12                    (subfolder in current directory)")
        print("  • .                     (current directory)")
        print("  • ~                     (home directory)")
        print("  • ..                    (parent directory)")
        print("  • cd                    (go to home directory)")
        print("  • cd ~/Desktop          (go to Desktop)")
        print("  • ~/Desktop/Episodes    (home directory path)")
        print("  • /Users/mosama/Videos  (absolute path)")
        print("\n💡 Tip: Press TAB to autocomplete paths (like Terminal!)")
        print("=" * 60)

        while True:
            current_dir = Path.cwd()
            print(f"\nCurrent directory: {current_dir}")
            path_input = input("Enter path to scan (TAB for autocomplete, Enter for current): ").strip()

            if not path_input:
                root_path = current_dir
                break

            # معالجة الاختصارات الخاصة
            if path_input == 'cd' or path_input == 'cd ~' or path_input == '~':
                root_path = Path.home()
                print(f"✓ Using home directory: {root_path}")
                break
            elif path_input == 'cd ..':
                root_path = current_dir.parent
                print(f"✓ Moving to parent: {root_path}")
                break
            elif path_input.startswith('cd '):
                # استخراج المسار بعد cd
                path_input = path_input[3:].strip()

            # توسيع المسار (دعم ~ و .)
            root_path = Path(path_input).expanduser().resolve()

            if root_path.exists():
                break
            else:
                print(f"\n❌ Error: Path does not exist: {root_path}")
                print("💡 Tips:")
                print("   • Press Enter for current directory")
                print("   • Type ~ for home directory")
                print("   • Type .. for parent directory")
                print("   • Use TAB to autocomplete paths")
                retry = input("\nTry again? (y/n): ").strip().lower()
                if retry not in ['y', 'yes', '']:
                    print("\nCancelled.")
                    sys.exit(0)

    if not root_path.exists():
        print(f"\n❌ Error: Path does not exist: {root_path}")
        sys.exit(1)

    print(f"\n✓ Scanning: {root_path}\n")

    # تشغيل الواجهة
    try:
        curses.wrapper(main, root_path)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
