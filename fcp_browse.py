#!/usr/bin/env python3
"""
Final Cut Pro Bundle Cleaner - Interactive File Browser
========================================================
تصفح الملفات تفاعلياً زي الترمنال، واختار المسار اللي عايزه

التحكم:
    ↑/↓      - التنقل بين الفولدرات
    ENTER    - الدخول في الفولدر / اختيار المسار
    BACKSPACE - الرجوع للفولدر الأعلى
    q        - خروج
    s        - بدء المسح في المسار الحالي
"""

import sys
import curses
from pathlib import Path
from typing import List, Dict

# استيراد الوظائف المشتركة
from fcp_common import (
    TARGET_FOLDERS,
    format_size,
    find_fcpbundles,
    find_date_folders,
    get_folder_size,
    delete_folder_safely
)


def analyze_bundle(bundle_path: Path) -> Dict:
    """تحليل bundle - نسخة مبسطة للمتصفح"""
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


class FileBrowser:
    """متصفح الملفات التفاعلي"""

    def __init__(self, stdscr, start_path: Path):
        self.stdscr = stdscr
        self.current_path = start_path.resolve()
        self.current_idx = 0
        self.scroll_offset = 0
        self.selected_path = None

        # الألوان
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.curs_set(0)

    def get_items(self) -> List[Dict]:
        """الحصول على المجلدات في المسار الحالي"""
        items = []

        try:
            # إضافة .. للرجوع
            if self.current_path != self.current_path.parent:
                items.append({
                    'name': '..',
                    'path': self.current_path.parent,
                    'is_parent': True,
                    'is_dir': True
                })

            # قراءة المجلدات
            for item in sorted(self.current_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    items.append({
                        'name': item.name,
                        'path': item,
                        'is_parent': False,
                        'is_dir': True
                    })

        except PermissionError:
            pass

        return items

    def draw(self):
        """رسم الواجهة"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # العنوان
        title = " File Browser - Navigate to your FCP projects folder "
        self.stdscr.addstr(0, 0, title[:width-1], curses.color_pair(1) | curses.A_BOLD)

        # المسار الحالي
        path_str = f" {self.current_path} "
        self.stdscr.addstr(1, 0, path_str[:width-1], curses.color_pair(2))

        # خط فاصل
        self.stdscr.addstr(2, 0, "─" * width)

        # الحصول على العناصر
        items = self.get_items()

        if not items:
            self.stdscr.addstr(4, 2, "Empty directory or no permission", curses.color_pair(4))
        else:
            visible_height = height - 6

            # التأكد من العنصر الحالي في النطاق
            if self.current_idx >= len(items):
                self.current_idx = len(items) - 1
            if self.current_idx < 0:
                self.current_idx = 0

            if self.current_idx < self.scroll_offset:
                self.scroll_offset = self.current_idx
            elif self.current_idx >= self.scroll_offset + visible_height:
                self.scroll_offset = self.current_idx - visible_height + 1

            # عرض العناصر
            for i in range(visible_height):
                idx = i + self.scroll_offset
                if idx >= len(items):
                    break

                item = items[idx]

                # اختيار اللون
                if idx == self.current_idx:
                    color = curses.color_pair(5) | curses.A_BOLD
                else:
                    color = curses.A_NORMAL

                # الرمز
                if item.get('is_parent'):
                    icon = "↑ "
                    name = item['name'] + " (go back)"
                else:
                    icon = "📁 "
                    name = item['name']

                line = f"{icon}{name}"

                try:
                    self.stdscr.addstr(3 + i, 2, line[:width-3], color)
                except curses.error:
                    pass

        # خط فاصل
        self.stdscr.addstr(height - 3, 0, "─" * width)

        # التعليمات
        help_line = " ↑/↓:Navigate | ENTER:Open/Select | BACKSPACE:Back | s:Scan Here | q:Quit "
        self.stdscr.addstr(height - 2, 0, help_line[:width-1], curses.color_pair(3))

        self.stdscr.refresh()

    def run(self) -> Path:
        """تشغيل المتصفح"""
        items = self.get_items()

        while True:
            self.draw()
            items = self.get_items()

            if not items:
                key = self.stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    return None
                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                    if self.current_path != self.current_path.parent:
                        self.current_path = self.current_path.parent
                        self.current_idx = 0
                        self.scroll_offset = 0
                continue

            key = self.stdscr.getch()

            # التنقل
            if key == curses.KEY_UP:
                self.current_idx = max(0, self.current_idx - 1)

            elif key == curses.KEY_DOWN:
                self.current_idx = min(len(items) - 1, self.current_idx + 1)

            # فتح / اختيار
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                if 0 <= self.current_idx < len(items):
                    selected = items[self.current_idx]
                    self.current_path = selected['path']
                    self.current_idx = 0
                    self.scroll_offset = 0

            # الرجوع
            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                if self.current_path != self.current_path.parent:
                    self.current_path = self.current_path.parent
                    self.current_idx = 0
                    self.scroll_offset = 0

            # بدء المسح
            elif key == ord('s') or key == ord('S'):
                return self.current_path

            # الخروج
            elif key == ord('q') or key == ord('Q'):
                return None


class InteractiveCleaner:
    """نفس الكلاس من السكربت السابق"""

    def __init__(self, stdscr, projects: List[Dict]):
        self.stdscr = stdscr
        self.projects = projects
        self.current_idx = 0
        self.scroll_offset = 0
        self.selected = set()

        self.items = []
        for project in projects:
            for folder in project['folders']:
                if not folder.get('deleted', False):
                    self.items.append({
                        'project_name': project['bundle_name'],
                        'folder_name': folder['name'],
                        'path': folder['path'],
                        'size': folder['size'],
                        'folder_ref': folder
                    })

        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)

        curses.curs_set(0)

    def get_total_size(self) -> int:
        return sum(item['size'] for item in self.items)

    def get_selected_size(self) -> int:
        return sum(self.items[i]['size'] for i in self.selected)

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        title = " Final Cut Pro Cleaner "
        self.stdscr.addstr(0, (width - len(title)) // 2, title,
                          curses.color_pair(1) | curses.A_BOLD)

        total_size = self.get_total_size()
        selected_size = self.get_selected_size()

        info_line = f" Items: {len(self.items)} | Total: {format_size(total_size)} | Selected: {format_size(selected_size)} "
        self.stdscr.addstr(1, 0, info_line, curses.color_pair(2))

        self.stdscr.addstr(2, 0, "─" * width)

        visible_height = height - 6

        if self.current_idx < self.scroll_offset:
            self.scroll_offset = self.current_idx
        elif self.current_idx >= self.scroll_offset + visible_height:
            self.scroll_offset = self.current_idx - visible_height + 1

        for i in range(visible_height):
            idx = i + self.scroll_offset
            if idx >= len(self.items):
                break

            item = self.items[idx]

            if idx == self.current_idx:
                color = curses.color_pair(5) | curses.A_BOLD
            elif idx in self.selected:
                color = curses.color_pair(3)
            else:
                color = curses.A_NORMAL

            mark = "[x]" if idx in self.selected else "[ ]"
            name = f"{item['project_name']}/{item['folder_name']}"
            size = format_size(item['size'])

            max_name_len = width - len(mark) - len(size) - 4
            if len(name) > max_name_len:
                name = name[:max_name_len - 3] + "..."

            line = f"{mark} {name}"
            spaces = width - len(line) - len(size) - 2
            line = line + " " * spaces + size

            try:
                self.stdscr.addstr(3 + i, 0, line[:width-1], color)
            except curses.error:
                pass

        self.stdscr.addstr(height - 3, 0, "─" * width)

        help_text = " ↑/↓:Navigate | SPACE:Select | d:Delete | D:Delete All | b:Back | q:Quit "
        self.stdscr.addstr(height - 2, 0, help_text, curses.color_pair(1))

        self.stdscr.refresh()

    def confirm_delete(self, message: str) -> bool:
        """رسالة تأكيد واضحة مع خلفية سوداء كاملة"""
        height, width = self.stdscr.getmaxyx()

        # مسح الشاشة بالكامل - خلفية سوداء
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(0))
        self.stdscr.refresh()

        # رسم صندوق كبير في المنتصف
        confirm_h = 11
        confirm_w = min(70, width - 4)
        start_y = (height - confirm_h) // 2
        start_x = (width - confirm_w) // 2

        # إنشاء نافذة للصندوق
        confirm_win = curses.newwin(confirm_h, confirm_w, start_y, start_x)

        # تلوين الخلفية بالأحمر
        confirm_win.bkgd(' ', curses.color_pair(4))
        confirm_win.box()

        # العنوان
        title = " CONFIRM DELETE "
        confirm_win.addstr(1, (confirm_w - len(title)) // 2, title,
                          curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE)

        # فراغ
        confirm_win.addstr(2, 2, " " * (confirm_w - 4))

        # الرسالة
        # تقسيم الرسالة لو طويلة
        if len(message) > confirm_w - 6:
            msg_part = message[:confirm_w - 6]
        else:
            msg_part = message

        confirm_win.addstr(4, (confirm_w - len(msg_part)) // 2, msg_part, curses.A_BOLD)

        # فراغ
        confirm_win.addstr(5, 2, " " * (confirm_w - 4))
        confirm_win.addstr(6, 2, " " * (confirm_w - 4))

        # التعليمات
        y_text = "Press 'y' to DELETE"
        n_text = "Press 'n' to CANCEL"
        confirm_win.addstr(7, (confirm_w - len(y_text)) // 2, y_text,
                          curses.color_pair(4) | curses.A_BOLD)
        confirm_win.addstr(8, (confirm_w - len(n_text)) // 2, n_text,
                          curses.color_pair(2) | curses.A_BOLD)

        confirm_win.refresh()

        while True:
            key = confirm_win.getch()
            if key == ord('y') or key == ord('Y'):
                return True
            elif key == ord('n') or key == ord('N') or key == 27:
                return False

    def show_message(self, message: str, duration: int = 2000):
        """رسالة واضحة بعد العملية مع خلفية سوداء"""
        height, width = self.stdscr.getmaxyx()

        # مسح الشاشة بالكامل - خلفية سوداء
        self.stdscr.clear()
        self.stdscr.bkgd(' ', curses.color_pair(0))
        self.stdscr.refresh()

        # رسم صندوق كبير
        msg_h = 7
        msg_w = min(len(message) + 10, width - 4, 60)
        start_y = (height - msg_h) // 2
        start_x = (width - msg_w) // 2

        msg_win = curses.newwin(msg_h, msg_w, start_y, start_x)

        # تلوين الخلفية بالأخضر
        msg_win.bkgd(' ', curses.color_pair(2))
        msg_win.box()

        # الرسالة في المنتصف
        msg_win.addstr(3, (msg_w - len(message)) // 2, message,
                      curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)

        msg_win.refresh()

        curses.napms(duration)

    def delete_selected_items(self):
        """مسح كل الفولدرات المحددة"""
        if not self.selected:
            self.show_message("No items selected!", 1000)
            return

        count = len(self.selected)
        total_size = sum(self.items[i]['size'] for i in self.selected)
        size_str = format_size(total_size)

        if not self.confirm_delete(f"Delete {count} folders ({size_str})?"):
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
        self.current_idx = min(self.current_idx, len(self.items) - 1) if self.items else 0

        self.show_message(f"Deleted {deleted} folders!")

    def delete_current(self):
        """مسح الفولدر الحالي أو المحددة"""
        if not self.items:
            return

        # لو فيه selected items - امسحهم
        if self.selected:
            self.delete_selected_items()
            return

        # لو مفيش selected - امسح الـ current فقط
        item = self.items[self.current_idx]
        size = format_size(item['size'])

        if not self.confirm_delete(f"Delete {item['folder_name']} ({size})?"):
            return

        success, error_msg = delete_folder_safely(item['path'])
        if success:
            item['folder_ref']['deleted'] = True
            self.items.pop(self.current_idx)
            self.current_idx = min(self.current_idx, len(self.items) - 1) if self.items else 0
            self.show_message("Deleted successfully!")
        else:
            self.show_message(f"Failed: {error_msg}", 2000)

    def delete_all(self):
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
        """تشغيل الواجهة - يرجع True لو عايز يرجع للمتصفح"""
        while True:
            self.draw()

            if not self.items:
                # خلصنا كل الملفات - نسأل المستخدم
                height, width = self.stdscr.getmaxyx()

                # مسح الشاشة بالكامل - خلفية سوداء
                self.stdscr.clear()
                self.stdscr.bkgd(' ', curses.color_pair(0))
                self.stdscr.refresh()

                confirm_h = 13
                confirm_w = min(70, width - 4)
                start_y = (height - confirm_h) // 2
                start_x = (width - confirm_w) // 2

                msg_win = curses.newwin(confirm_h, confirm_w, start_y, start_x)

                # تلوين الخلفية بالأخضر
                msg_win.bkgd(' ', curses.color_pair(2))
                msg_win.box()

                # العنوان
                title = " ALL DONE! "
                msg_win.addstr(2, (confirm_w - len(title)) // 2, title,
                              curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)

                # الرسالة
                msg = "All cleanable folders processed."
                msg_win.addstr(5, (confirm_w - len(msg)) // 2, msg, curses.A_BOLD)

                # فراغ
                msg_win.addstr(6, 2, " " * (confirm_w - 4))
                msg_win.addstr(7, 2, " " * (confirm_w - 4))

                # الخيارات - في المنتصف
                b_text = "Press 'b' to go back to browser"
                q_text = "Press 'q' to quit program"
                msg_win.addstr(8, (confirm_w - len(b_text)) // 2, b_text,
                              curses.color_pair(3) | curses.A_BOLD)
                msg_win.addstr(9, (confirm_w - len(q_text)) // 2, q_text,
                              curses.color_pair(4) | curses.A_BOLD)

                msg_win.refresh()

                while True:
                    key = msg_win.getch()
                    if key == ord('b') or key == ord('B'):
                        return True  # رجوع للمتصفح
                    elif key == ord('q') or key == ord('Q'):
                        return False  # خروج

            # الحصول على input من المستخدم
            key = self.stdscr.getch()

            # التنقل
            if key == curses.KEY_UP:
                self.current_idx = max(0, self.current_idx - 1)
            elif key == curses.KEY_DOWN:
                self.current_idx = min(len(self.items) - 1, self.current_idx + 1)
            elif key == ord(' ') or key == ord('\n'):
                if self.current_idx in self.selected:
                    self.selected.remove(self.current_idx)
                else:
                    self.selected.add(self.current_idx)
            elif key == ord('d'):
                self.delete_current()
            elif key == ord('D'):
                self.delete_all()
            elif key == ord('b') or key == ord('B'):
                return True  # رجوع للمتصفح
            elif key == ord('q') or key == ord('Q'):
                return False  # خروج نهائي


def main(stdscr):
    """الدالة الرئيسية"""
    # تهيئة الألوان
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

    height, width = stdscr.getmaxyx()

    # عرض شاشة الترحيب مع اللوجو
    stdscr.clear()

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

    logo_lines = logo.strip().split('\n')
    start_y = max(0, (height - len(logo_lines) - 6) // 2)

    # عرض اللوجو
    for i, line in enumerate(logo_lines):
        if start_y + i < height - 4:
            # مركز كل سطر
            x_pos = max(0, (width - len(line)) // 2)
            try:
                stdscr.addstr(start_y + i, x_pos, line, curses.color_pair(1))
            except curses.error:
                pass

    # عرض الرسائل تحت اللوجو
    welcome_y = start_y + len(logo_lines) + 1

    welcome = "Welcome to Final Cut Pro Cleaner"
    if welcome_y < height - 3:
        stdscr.addstr(welcome_y, max(0, (width - len(welcome)) // 2), welcome,
                      curses.color_pair(1) | curses.A_BOLD)

    msg = "Navigate to your FCP projects folder..."
    if welcome_y + 1 < height - 2:
        stdscr.addstr(welcome_y + 1, max(0, (width - len(msg)) // 2), msg)

    msg2 = "Press any key to start"
    if welcome_y + 3 < height - 1:
        stdscr.addstr(welcome_y + 3, max(0, (width - len(msg2)) // 2), msg2,
                      curses.color_pair(2))

    stdscr.refresh()
    stdscr.getch()

    # Loop رئيسي - يرجع للمتصفح لو المستخدم ضغط b
    current_path = Path.home()

    while True:
        # فتح متصفح الملفات
        browser = FileBrowser(stdscr, current_path)
        selected_path = browser.run()

        if not selected_path:
            # المستخدم ضغط q - خروج نهائي
            return

        # حفظ المسار الحالي
        current_path = selected_path

        # شاشة التحميل
        stdscr.clear()

        loading_msgs = [
            "Searching for .fcpbundle files...",
            "Analyzing projects...",
            "Calculating sizes..."
        ]

        for i, msg in enumerate(loading_msgs):
            stdscr.addstr(height // 2 + i, (width - len(msg)) // 2, msg)
            stdscr.refresh()

        # البحث والتحليل
        bundles = find_fcpbundles(selected_path)

        if not bundles:
            stdscr.clear()

            # رسم صندوق واضح
            msg_h = 11
            msg_w = 60
            start_y = (height - msg_h) // 2
            start_x = (width - msg_w) // 2

            msg_win = curses.newwin(msg_h, msg_w, start_y, start_x)
            msg_win.bkgd(' ', curses.color_pair(4))
            msg_win.box()

            # العنوان
            title = " NO PROJECTS FOUND "
            msg_win.addstr(2, (msg_w - len(title)) // 2, title,
                          curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE)

            # الرسالة
            msg = "No .fcpbundle files in this location."
            msg_win.addstr(5, (msg_w - len(msg)) // 2, msg, curses.A_BOLD)

            # الخيارات
            msg_win.addstr(7, 4, "Press 'b' to go back", curses.color_pair(3) | curses.A_BOLD)
            msg_win.addstr(8, 4, "Press 'q' to quit", curses.color_pair(4) | curses.A_BOLD)

            msg_win.refresh()

            key = msg_win.getch()
            if key == ord('b') or key == ord('B'):
                continue  # رجوع للمتصفح
            else:
                return  # خروج

        projects = []
        for bundle in bundles:
            analysis = analyze_bundle(bundle)
            if analysis['folders']:
                projects.append(analysis)

        if not projects:
            stdscr.clear()

            # رسم صندوق واضح
            msg_h = 13
            msg_w = 70
            start_y = (height - msg_h) // 2
            start_x = (width - msg_w) // 2

            msg_win = curses.newwin(msg_h, msg_w, start_y, start_x)
            msg_win.bkgd(' ', curses.color_pair(3))
            msg_win.box()

            # العنوان
            title = " NO CLEANABLE FOLDERS "
            msg_win.addstr(2, (msg_w - len(title)) // 2, title,
                          curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)

            # الرسالة
            msg1 = "No Analysis Files, Render Files, or Transcoded Media found."
            msg2 = "These projects are already clean!"
            msg_win.addstr(5, (msg_w - len(msg1)) // 2, msg1, curses.A_BOLD)
            msg_win.addstr(6, (msg_w - len(msg2)) // 2, msg2, curses.A_BOLD)

            # الخيارات
            msg_win.addstr(9, 4, "Press 'b' to try another location", curses.color_pair(2) | curses.A_BOLD)
            msg_win.addstr(10, 4, "Press 'q' to quit", curses.color_pair(4) | curses.A_BOLD)

            msg_win.refresh()

            key = msg_win.getch()
            if key == ord('b') or key == ord('B'):
                continue  # رجوع للمتصفح
            else:
                return  # خروج

        # تشغيل الواجهة
        cleaner = InteractiveCleaner(stdscr, projects)
        should_go_back = cleaner.run()

        if not should_go_back:
            # المستخدم ضغط q أو خلص كل حاجة - خروج
            return
        # else: المستخدم ضغط b - هنرجع للمتصفح في اللوب


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
