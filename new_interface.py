# new_interface.py - App principal con sistema de 2 vistas + vault (F3)
import os
import sys
import json
import random
import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QFileDialog
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt

from files import setup_file_handling, void_line
from controls import setup_controls
from line_ring import LineRing
from circular_view import CircularView
from widgets import CustomLineEdit
from views import NormalView


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULT_CONFIG = {
    "void_dir": "",
    "book_dir": "",
    "active_file": "",
    "void_key": "enter",
    "font_family": "Consolas",
    "font_size": 11,
    "text_color": "#ffffff",
    "keybindings": {
        "view_f1": "F1",
        "view_f2": "F2",
        "view_f3": "F3",
        "view_f4": "F4",
        "quit": "Escape",
        "rebase": "Ctrl+9",
        "reshuffle": "Ctrl+R",
        "opacity_up": "Ctrl+Up",
        "opacity_down": "Ctrl+Down",
        "file_prev": "Alt+Up",
        "file_next": "Alt+Down",
        "swap_up": "Alt+Up",
        "swap_down": "Alt+Down",
        "para_prev": "PageUp",
        "para_next": "PageDown",
        "pick_active_file": "Ctrl+F2",
        "pick_book_dir": "Ctrl+F3",
        "pick_dir": "Ctrl+F4",
        "screenshot": "F12",
        "open_screenshots": "Ctrl+F12",
        "print_doc": "Ctrl+P"
    }
}

_KEY_MAP = {
    'Up': Qt.Key.Key_Up, 'Down': Qt.Key.Key_Down,
    'Left': Qt.Key.Key_Left, 'Right': Qt.Key.Key_Right,
    'Escape': Qt.Key.Key_Escape, 'Return': Qt.Key.Key_Return,
    'Enter': Qt.Key.Key_Return, 'Space': Qt.Key.Key_Space,
    'F1': Qt.Key.Key_F1, 'F2': Qt.Key.Key_F2, 'F3': Qt.Key.Key_F3,
    'F4': Qt.Key.Key_F4, 'F5': Qt.Key.Key_F5, 'F6': Qt.Key.Key_F6,
    'F12': Qt.Key.Key_F12,
    'PageUp': Qt.Key.Key_PageUp, 'PageDown': Qt.Key.Key_PageDown,
    '0': Qt.Key.Key_0, '9': Qt.Key.Key_9, 'R': Qt.Key.Key_R, 'P': Qt.Key.Key_P,
    '.': Qt.Key.Key_Period, '*': Qt.Key.Key_Asterisk,
}

_MOD_MAP = {
    'Ctrl': Qt.KeyboardModifier.ControlModifier,
    'Alt': Qt.KeyboardModifier.AltModifier,
    'Shift': Qt.KeyboardModifier.ShiftModifier,
}


def _parse_keybinding(s):
    """'Ctrl+Up' → (Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier)"""
    parts = s.split('+')
    key_str = parts[-1]
    mods = Qt.KeyboardModifier.NoModifier
    for part in parts[:-1]:
        mods |= _MOD_MAP.get(part, Qt.KeyboardModifier.NoModifier)
    return _KEY_MAP.get(key_str), mods


def _load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            config = dict(DEFAULT_CONFIG)
            config.update(data)
            merged_kb = dict(DEFAULT_CONFIG['keybindings'])
            merged_kb.update(data.get('keybindings', {}))
            config['keybindings'] = merged_kb
            return config
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
    return dict(DEFAULT_CONFIG)


def _save_config(config):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving config: {e}")


class FullscreenCircleApp(QMainWindow):
    """
    F1: center entry — write/navigate active file
    F2: circular view — edit/swap active file lines
    F3: book browser — navigate/reorder files in current book folder
    F4: vault browser — browse shuffled lines from void folder, pick into active file
    """

    def __init__(self):
        super().__init__()

        self.config = _load_config()
        self._kb = {
            action: _parse_keybinding(ks)
            for action, ks in self.config.get('keybindings', {}).items()
        }

        # Resolve void_dir: config → dialog
        void_dir = self.config.get('void_dir', '')
        if not void_dir or not os.path.isdir(void_dir):
            void_dir = self._pick_void_directory()
            if not void_dir:
                sys.exit(0)
            self.config['void_dir'] = void_dir
            _save_config(self.config)

        self.void_dir = void_dir

        # Resolve book_dir: config → default to void_dir
        book_dir = self.config.get('book_dir', '')
        if not book_dir or not os.path.isdir(book_dir):
            book_dir = void_dir
        self.book_dir = book_dir

        # Resolve active_file: config → default to book_dir/0.txt
        active_file = self.config.get('active_file', '')
        if not active_file or not os.path.isfile(active_file):
            active_file = os.path.join(self.book_dir, '0.txt')
        self.book_files = []    # ordered list of .txt filenames in book_dir
        self.book_ring = LineRing()

        self.opacity = 1.0
        self.txt_files = []
        self.current_file_index = 0
        self.current_view = 0  # 0=F1, 1=F2, 2=F3(book), 3=F4(vault)
        self.use_spacebar_for_void = self.config.get('void_key', 'enter') == 'space'
        self._pending_vault_remove = False  # True when staging a vault line in F1
        self._para_focus = False            # True when in paragraph focus mode
        self._para_focus_content = []       # Ordered list of absolute ring indices for focused paragraph

        # Font / color from config
        _font_family = self.config.get('font_family', 'Consolas')
        _font_size = int(self.config.get('font_size', 11))
        _text_color = self.config.get('text_color', '#ffffff')
        self._app_font = QFont(_font_family, _font_size)

        # Window setup
        self.setWindowTitle("Voider")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.setStyleSheet("background-color: black; color: white;")

        # Entry (F1)
        self.entry = CustomLineEdit(self)
        self.entry.setFont(self._app_font)
        self.entry.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {_text_color};
                border: none;
                selection-background-color: {_text_color};
                selection-color: black;
            }}
        """)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.setFocus()

        # Doc ring (active file lines, ordered) and vault ring (void files, shuffled)
        self.line_ring = LineRing()
        self.vault_ring = LineRing()

        # View stack
        self.stack = QStackedWidget()
        self.normal_view = NormalView(self)
        self.circular_view = None   # F2: CircularView over doc ring
        self.book_view = None       # F3: CircularView over book_ring (filenames)
        self.vault_view = None      # F4: CircularView over vault ring
        self.stack.addWidget(self.normal_view)

        # File setup — active file is configurable (defaults to book_dir/0.txt)
        self.current_file_path = active_file
        self.void_file_path = os.path.join(self.void_dir, '0.txt')  # fallback for file commands
        os.makedirs(self.book_dir, exist_ok=True)
        if not os.path.exists(self.current_file_path):
            open(self.current_file_path, 'w', encoding='utf-8').close()

        self.scan_txt_files()
        setup_file_handling(self)
        setup_controls(self)

        self.load_doc_lines()
        self.load_vault_lines()
        self._load_book_order()

        # Void key connection
        self._print_void_mode_status()
        self._void_enter_connection = None
        self._void_space_connection = None
        self._connect_void_key()

        self.init_ui()
        self.switch_to_view(0)
        self.entry.clear()

    # ── Directory picker ──────────────────────────────────────────────────────

    def _pick_void_directory(self):
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Void Directory",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        return path or None

    def change_void_directory(self):
        new_dir = self._pick_void_directory()
        if not new_dir or new_dir == self.void_dir:
            return
        self.void_dir = new_dir
        self.void_file_path = os.path.join(self.void_dir, '0.txt')
        self.config['void_dir'] = new_dir
        _save_config(self.config)
        os.makedirs(self.void_dir, exist_ok=True)

        self.scan_txt_files()
        self.load_vault_lines()
        self.switch_to_view(self.current_view)
        print(f"📁 Void dir changed to: {new_dir}")

    # ── Loaders ───────────────────────────────────────────────────────────────

    def load_doc_lines(self):
        """Load active file into the doc ring (ordered, no shuffle). Preserves index."""
        doc_path = self.current_file_path
        lines = []
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                for raw in f:
                    s = raw.strip()
                    if s:
                        lines.append(s)
        except Exception as e:
            print(f"⚠️ Error reading {os.path.basename(doc_path)}: {e}")
        # Ensure a leading dot so the last paragraph and first paragraph
        # are always separated when wrapping around the ring.
        if lines and lines[0] != '.':
            lines.insert(0, '.')
        old_index = self.line_ring.index if self.line_ring.lines else 0
        self.line_ring = LineRing(lines or ["."])
        self.line_ring.index = min(old_index, len(self.line_ring.lines) - 1)
        if self.circular_view:
            self.circular_view.ring = self.line_ring
            self.circular_view._offset = 0.0
        print(f"📄 {len(lines)} lines loaded from {os.path.basename(doc_path)}")

    def load_vault_lines(self):
        """Load all .txt files except 0.txt into vault ring (shuffled)."""
        all_lines = []
        for root, _, files in os.walk(self.void_dir):
            for fname in sorted(files):
                if fname.lower().endswith('.txt') and fname.lower() != '0.txt':
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            for raw in f:
                                s = raw.strip()
                                if s and s != '.':
                                    all_lines.append(s)
                    except Exception as e:
                        print(f"⚠️ Error reading {fpath}: {e}")
        if not all_lines:
            all_lines = [""]
        else:
            random.shuffle(all_lines)
        self.vault_ring = LineRing(all_lines)
        if self.vault_view:
            self.vault_view.ring = self.vault_ring
            self.vault_view._offset = 0.0
        print(f"🔀 {len(all_lines)} vault lines loaded (shuffled)")

    # ── Config / keybinding helpers ───────────────────────────────────────────

    def _matches(self, key, modifiers, action):
        kb = self._kb.get(action)
        return kb is not None and key == kb[0] and modifiers == kb[1]

    # ── Void key ─────────────────────────────────────────────────────────────

    def _print_void_mode_status(self):
        print("VOID MODE:", "Spacebar" if self.use_spacebar_for_void else "Enter")

    def _connect_void_key(self):
        self._disconnect_void_key()
        if self.use_spacebar_for_void:
            self._void_space_connection = self.entry.spacePressed.connect(self._handle_void_line)
        else:
            self._void_enter_connection = self.entry.returnPressed.connect(self._handle_void_line)

    def _handle_void_line(self):
        void_line(self)
        # Reload doc ring and position near the just-written line
        self.load_doc_lines()
        if hasattr(self, 'last_inserted_index') and self.last_inserted_index is not None:
            self.line_ring.index = min(self.last_inserted_index, len(self.line_ring.lines) - 1)

    def _disconnect_void_key(self):
        if self._void_enter_connection:
            try:
                self.entry.returnPressed.disconnect(self._void_enter_connection)
            except Exception:
                pass
            self._void_enter_connection = None
        if self._void_space_connection:
            try:
                self.entry.spacePressed.disconnect(self._void_space_connection)
            except Exception:
                pass
            self._void_space_connection = None

    def toggle_void_key_mode(self):
        self.use_spacebar_for_void = not self.use_spacebar_for_void
        self.config['void_key'] = 'space' if self.use_spacebar_for_void else 'enter'
        _save_config(self.config)
        self._print_void_mode_status()
        self._connect_void_key()

    # ── Views ─────────────────────────────────────────────────────────────────

    def switch_to_view(self, view_index):
        # Cancel staged vault line if user navigates away without voiding
        if view_index == 3:
            self._pending_vault_remove = False
        old_view = self.current_view
        self.current_view = view_index
        print(f"📍 F{old_view+1} → F{view_index+1} | Index: {self.line_ring.index} | Line: '{self.line_ring.current()}'")

        if view_index == 0:  # F1 — write/navigate active file
            if self.circular_view:
                self.circular_view.edit_mode = False
                self.circular_view.editor.hide()
            if self.book_view:
                self.book_view.edit_mode = False
                self.book_view.editor.hide()
            self.stack.setCurrentWidget(self.normal_view)
            self.entry.show()
            self.entry.raise_()
            # Anchor F1 to the line currently selected in F2
            if old_view == 1 and self.line_ring.current() != '.':
                self.current_active_line_index = self.line_ring.index
                self.last_inserted_index = self.line_ring.index
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(len(self.entry.text()))
            self.entry.setFocus()

        elif view_index == 1:  # F2 — circular doc view
            if not self.circular_view:
                self.circular_view = CircularView(self.line_ring, self)
                self.circular_view.setFont(self._app_font)
                self.circular_view.editor.returnPressed.disconnect()
                self.circular_view.editor.returnPressed.connect(self._doc_confirm_edit)
                self.circular_view.editor.textEdited.connect(self._doc_live_save)
                self.circular_view.editor.upPressed.connect(lambda: self._doc_navigate(-1))
                self.circular_view.editor.downPressed.connect(lambda: self._doc_navigate(1))
                self.circular_view.editor.backspaceAtStart.connect(self._doc_join_prev)
                self.circular_view.editor.splitAtCursor.connect(self._doc_split_line)
                self.stack.addWidget(self.circular_view)
            else:
                self.circular_view.ring = self.line_ring
                self.circular_view._offset = 0.0

            self.stack.setCurrentWidget(self.circular_view)
            self.entry.hide()
            self.circular_view.update()
            self._doc_show_editor()

        elif view_index == 2:  # F3 — book browser
            self._load_book_order()
            if not self.book_view:
                self.book_view = CircularView(self.book_ring, self)
                self.book_view.setFont(self._app_font)
                self.book_view.editor.returnPressed.disconnect()
                self.book_view.editor.returnPressed.connect(self._book_confirm_edit)
                self.book_view.editor.splitAtCursor.connect(lambda pos: self._book_confirm_edit())
                self.book_view.editor.upPressed.connect(lambda: self._book_navigate(-1))
                self.book_view.editor.downPressed.connect(lambda: self._book_navigate(1))
                self.stack.addWidget(self.book_view)
            else:
                self.book_view.ring = self.book_ring
                self.book_view._offset = 0.0
            # Sync cursor to active file
            active_fname = os.path.basename(self.current_file_path)
            if active_fname in self.book_files:
                self.book_ring.index = self.book_files.index(active_fname)
            self.stack.setCurrentWidget(self.book_view)
            self.entry.hide()
            self.book_view.update()
            self._book_show_editor()

        elif view_index == 3:  # F4 — vault browser
            if not self.vault_view:
                self.vault_view = CircularView(self.vault_ring, self)
                self.vault_view.setFont(self._app_font)
                self.vault_view.editor.returnPressed.disconnect()
                self.vault_view.editor.returnPressed.connect(self._vault_confirm_edit)
                self.vault_view.editor.upPressed.connect(lambda: self._vault_navigate(-1))
                self.vault_view.editor.downPressed.connect(lambda: self._vault_navigate(1))
                self.stack.addWidget(self.vault_view)
            else:
                self.vault_view.ring = self.vault_ring
                self.vault_view._offset = 0.0

            self.stack.setCurrentWidget(self.vault_view)
            self.entry.hide()
            self.vault_view.update()
            self._vault_show_editor()

    def auto_save_circular(self):
        """Save doc ring state to active file."""
        doc_path = self.current_file_path
        try:
            with open(doc_path, 'w', encoding='utf-8') as f:
                for line in self.line_ring.lines:
                    f.write(line + '\n')
            print(f"💾 Saved to 0.txt (index={self.line_ring.index})")
        except Exception as e:
            print(f"❌ Save error: {e}")

    # ── Book order ────────────────────────────────────────────────────────────

    def _load_book_order(self):
        """Load ordered file list from _book_order.json, appending any unlisted files."""
        order_path = os.path.join(self.book_dir, '_book_order.json')
        try:
            actual = sorted(f for f in os.listdir(self.book_dir)
                            if f.lower().endswith('.txt'))
        except Exception:
            actual = []
        actual_set = set(actual)
        if os.path.exists(order_path):
            try:
                with open(order_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                ordered = [f for f in saved if f in actual_set]
                remaining = [f for f in actual if f not in set(ordered)]
                self.book_files = ordered + remaining
            except Exception:
                self.book_files = actual
        else:
            self.book_files = actual
        self._rebuild_book_ring()
        print(f"📚 Book: {len(self.book_files)} files in {os.path.basename(self.book_dir)}")

    def _save_book_order(self):
        order_path = os.path.join(self.book_dir, '_book_order.json')
        try:
            with open(order_path, 'w', encoding='utf-8') as f:
                json.dump(self.book_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving book order: {e}")

    def _rebuild_book_ring(self):
        display = [os.path.splitext(f)[0] for f in self.book_files]
        self.book_ring = LineRing(display if display else ["(empty)"])
        if self.book_view:
            self.book_view.ring = self.book_ring
            self.book_view._offset = 0.0

    def _set_active_file(self, path):
        """Change active file (and book_dir if it changed), reload doc ring."""
        self.current_file_path = path
        new_book_dir = os.path.dirname(os.path.abspath(path))
        if new_book_dir != self.book_dir:
            self.book_dir = new_book_dir
            self.config['book_dir'] = new_book_dir
            self._load_book_order()
        self.config['active_file'] = path
        _save_config(self.config)
        os.makedirs(self.book_dir, exist_ok=True)
        if not os.path.exists(path):
            open(path, 'w', encoding='utf-8').close()
        self.load_doc_lines()
        # Reset navigation state for new file
        self.current_active_line_index = None
        self.last_inserted_index = None
        print(f"📄 Active: {os.path.basename(path)}")

    # ── Book directory / file pickers ─────────────────────────────────────────

    def pick_active_file(self):
        """Ctrl+F2: pick any .txt file → sets active file + book folder."""
        path, _ = QFileDialog.getOpenFileName(
            None, "Select Active File",
            self.book_dir,
            "Text files (*.txt)"
        )
        if not path or not os.path.isfile(path):
            return
        self._set_active_file(path)
        self.switch_to_view(self.current_view)

    def pick_book_directory(self):
        """Ctrl+F3: pick book folder, switch active file if it's outside new folder."""
        path = QFileDialog.getExistingDirectory(
            None, "Select Book Folder",
            self.book_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if not path or not os.path.isdir(path):
            return
        self.book_dir = path
        self.config['book_dir'] = path
        _save_config(self.config)
        self._load_book_order()
        # If active file is outside the new book_dir, switch to first book file
        norm_path = os.path.normpath(path)
        norm_active = os.path.normpath(os.path.dirname(self.current_file_path))
        if norm_active != norm_path:
            if self.book_files:
                self._set_active_file(os.path.join(self.book_dir, self.book_files[0]))
            else:
                new_active = os.path.join(self.book_dir, '0.txt')
                open(new_active, 'a', encoding='utf-8').close()
                self._set_active_file(new_active)
                self._load_book_order()
        print(f"📁 Book dir: {path}")
        self.switch_to_view(self.current_view)

    def _doc_show_editor(self):
        """Show F2 editor with current doc line, cursor at start."""
        if not self.line_ring.lines:
            return
        view = self.circular_view
        view.edit_mode = True
        center_y = view.height() // 2
        editor_width = min(view.width() - 100, 800)
        view.editor.setFixedWidth(editor_width)
        view.editor.move(
            (view.width() - editor_width) // 2,
            center_y - view.editor.sizeHint().height() // 2
        )
        view.editor.setText(self.line_ring.current())
        view.editor.setCursorPosition(0)
        view.editor.setReadOnly(self.line_ring.current() == '.')
        view.editor.show()
        view.editor.setFocus()
        view.update()

    def _doc_navigate(self, delta):
        """Move doc ring and update F2 editor text."""
        if self._para_focus and self._para_focus_content:
            content = self._para_focus_content
            cur = self.line_ring.index
            pos = content.index(cur) if cur in content else 0
            self.line_ring.index = content[(pos + delta) % len(content)]
        else:
            self.line_ring.move(delta)
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(self.line_ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.editor.setReadOnly(self.line_ring.current() == '.')
        self.circular_view.update()

    def _doc_live_save(self, text):
        """Save on every keystroke in F2 editor."""
        if text.strip():
            self.line_ring.lines[self.line_ring.index] = text
            self.auto_save_circular()
            self.circular_view.update()

    def _doc_confirm_edit(self):
        """Enter in F2: focus mode on dot, go to F1 anchored on text line."""
        if self.line_ring.current() == '.' and not self._para_focus:
            self._enter_para_focus()
        else:
            # Switch to F1 empty, anchor insertions below current line
            idx = self.line_ring.index
            self._exit_para_focus() if self._para_focus else None
            self.current_active_line_index = None
            self.last_inserted_index = idx
            self.switch_to_view(0)
            self.entry.clear()

    def _enter_para_focus(self):
        ring = self.line_ring
        n = len(ring.lines)
        dot_idx = ring.index
        content = []
        i = (dot_idx + 1) % n
        for _ in range(n - 1):
            if ring.lines[i] == '.':
                break
            content.append(i)
            i = (i + 1) % n
        if not content:
            return
        self._para_focus = True
        self._para_focus_content = content
        self.circular_view.focus_indices = set(content) | {dot_idx}
        ring.index = content[0]
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.editor.setReadOnly(False)
        self.circular_view.update()

    def _exit_para_focus(self):
        self._para_focus = False
        self._para_focus_content = []
        self.circular_view.focus_indices = None
        # Return to the dot that precedes this paragraph
        ring = self.line_ring
        n = len(ring.lines)
        idx = (ring.index - 1) % n
        for _ in range(n):
            if ring.lines[idx] == '.':
                ring.index = idx
                break
            idx = (idx - 1) % n
        self._doc_show_editor()

    def _vault_show_editor(self):
        """Show the vault inline editor with the current vault line, cursor at start."""
        if not self.vault_ring.lines:
            return
        view = self.vault_view
        view.edit_mode = True
        center_y = view.height() // 2
        editor_width = min(view.width() - 100, 800)
        view.editor.setFixedWidth(editor_width)
        view.editor.move(
            (view.width() - editor_width) // 2,
            center_y - view.editor.sizeHint().height() // 2
        )
        view.editor.setText(self.vault_ring.current())
        view.editor.setCursorPosition(0)
        view.editor.show()
        view.editor.setFocus()
        view.update()

    # ── Book browser (F3) ─────────────────────────────────────────────────────

    def _book_show_editor(self):
        """Show F3 editor with current filename (no extension), cursor at start."""
        if not self.book_ring.lines:
            return
        view = self.book_view
        view.edit_mode = True
        center_y = view.height() // 2
        editor_width = min(view.width() - 100, 800)
        view.editor.setFixedWidth(editor_width)
        view.editor.move(
            (view.width() - editor_width) // 2,
            center_y - view.editor.sizeHint().height() // 2
        )
        view.editor.setText(self.book_ring.current())
        view.editor.setCursorPosition(0)
        view.editor.setReadOnly(False)
        view.editor.show()
        view.editor.setFocus()
        view.update()

    def _book_navigate(self, delta):
        """Non-looping navigation through book files."""
        new_idx = self.book_ring.index + delta
        if new_idx < 0 or new_idx >= len(self.book_ring.lines):
            return  # stop at boundaries
        self.book_ring.index = new_idx
        self.book_view._offset = 0.0
        self.book_view.editor.setText(self.book_ring.current())
        self.book_view.editor.setCursorPosition(0)
        self.book_view.update()

    def _book_confirm_edit(self):
        """Enter in F3: rename file if name changed, then activate it."""
        idx = self.book_ring.index
        if idx >= len(self.book_files):
            return
        new_name = self.book_view.editor.text().strip()
        if not new_name:
            return
        old_fname = self.book_files[idx]
        new_fname = new_name + '.txt'
        if new_fname != old_fname:
            old_path = os.path.join(self.book_dir, old_fname)
            new_path = os.path.join(self.book_dir, new_fname)
            try:
                os.rename(old_path, new_path)
                if self.current_file_path == old_path:
                    self.current_file_path = new_path
                    self.config['active_file'] = new_path
                    _save_config(self.config)
                self.book_files[idx] = new_fname
                self.book_ring.lines[idx] = new_name
                self._save_book_order()
                print(f"📝 Renamed: {old_fname} → {new_fname}")
            except Exception as e:
                print(f"⚠️ Rename failed: {e}")
                return
        self._set_active_file(os.path.join(self.book_dir, self.book_files[idx]))
        self.switch_to_view(0)

    def _book_swap_up(self):
        idx = self.book_ring.index
        if idx <= 0:
            return
        self.book_files[idx], self.book_files[idx-1] = self.book_files[idx-1], self.book_files[idx]
        self.book_ring.lines[idx], self.book_ring.lines[idx-1] = self.book_ring.lines[idx-1], self.book_ring.lines[idx]
        self.book_ring.index = idx - 1
        self._save_book_order()
        self.book_view._offset = 0.0
        self.book_view.editor.setText(self.book_ring.current())
        self.book_view.editor.setCursorPosition(0)
        self.book_view.update()

    def _book_swap_down(self):
        idx = self.book_ring.index
        if idx >= len(self.book_files) - 1:
            return
        self.book_files[idx], self.book_files[idx+1] = self.book_files[idx+1], self.book_files[idx]
        self.book_ring.lines[idx], self.book_ring.lines[idx+1] = self.book_ring.lines[idx+1], self.book_ring.lines[idx]
        self.book_ring.index = idx + 1
        self._save_book_order()
        self.book_view._offset = 0.0
        self.book_view.editor.setText(self.book_ring.current())
        self.book_view.editor.setCursorPosition(0)
        self.book_view.update()

    def _book_rebase(self):
        """Ctrl+9 in F3: rotate book_files so selected file becomes first."""
        idx = self.book_ring.index
        if idx == 0:
            return
        self.book_files = self.book_files[idx:] + self.book_files[:idx]
        self.book_ring.lines = [os.path.splitext(f)[0] for f in self.book_files]
        self.book_ring.index = 0
        self._save_book_order()
        self.book_view._offset = 0.0
        self.book_view.editor.setText(self.book_ring.current())
        self.book_view.editor.setCursorPosition(0)
        self.book_view.update()
        print(f"📚 Rebase: '{self.book_files[0]}' is now first")

    def print_book(self):
        """Ctrl+P in F3: print all chapters in order via system dialog."""
        from PyQt6.QtGui import QTextDocument
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        html_parts = ['<html><body style="color:black;background:white;'
                      'font-family:Consolas,monospace;">']
        for i, fname in enumerate(self.book_files):
            fpath = os.path.join(self.book_dir, fname)
            title = os.path.splitext(fname)[0]
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip() and l.strip() != '.']
            except Exception:
                lines = []
            if i > 0:
                html_parts.append('<div style="page-break-before:always;"></div>')
            html_parts.append(
                f'<h2 style="text-align:center;margin:3em 0 2em;">{title}</h2>'
            )
            for line in lines:
                html_parts.append(
                    f'<p style="text-align:center;margin:0.4em 0;">{line}</p>'
                )
        html_parts.append('</body></html>')
        doc = QTextDocument()
        doc.setHtml(''.join(html_parts))
        doc.print_(printer)

    def _vault_navigate(self, delta):
        """Move vault ring and update inline editor text."""
        self.vault_ring.move(delta)
        self.vault_view._offset = 0.0
        self.vault_view.editor.setText(self.vault_ring.current())
        self.vault_view.editor.setCursorPosition(0)
        self.vault_view.update()

    def _vault_confirm_edit(self):
        """Send editor text to doc ring, remove vault line, load next into editor."""
        view = self.vault_view
        new_text = view.editor.text().strip()
        if not new_text:
            return
        insert_pos = self.line_ring.index + 1
        self.line_ring.lines.insert(insert_pos, new_text)
        self.line_ring.index = insert_pos
        self.vault_ring.remove_current()
        self.auto_save_circular()
        view._offset = 0.0
        view.update()
        print(f"✅ Vault→Doc[{insert_pos}]: '{new_text}'")
        # Load next vault line into editor (or hide if vault empty)
        if self.vault_ring.lines and self.vault_ring.current():
            view.editor.setText(self.vault_ring.current())
            view.editor.setCursorPosition(0)
            view.editor.setFocus()
        else:
            view.editor.hide()
            view.edit_mode = False

    def take_screenshot(self):
        """F12: Capture the full screen and save to void_dir/screenshots/."""
        screen = self.screen()
        pixmap = screen.grabWindow(0)
        screenshots_dir = os.path.join(self.void_dir, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(screenshots_dir, f"snap_{ts}.png")
        pixmap.save(path)
        print(f"📸 Screenshot: {path}")

    def print_doc(self):
        """Ctrl+P: Print all lines from 0.txt, centered on the page."""
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        doc_path = os.path.join(self.void_dir, '0.txt')
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
        except Exception as e:
            print(f"❌ Print error reading file: {e}")
            return

        from PyQt6.QtGui import QPainter, QFontMetrics
        painter = QPainter(printer)
        font = QFont(self._app_font.family(), 14)
        painter.setFont(font)
        fm = QFontMetrics(font)
        page_w = painter.viewport().width()
        page_h = painter.viewport().height()
        line_height = fm.height() + 4

        if page_h <= 0 or line_height <= 0:
            painter.end()
            print("❌ Print error: invalid page dimensions")
            return

        y = line_height
        for line in lines:
            if y + line_height > page_h:
                printer.newPage()
                y = line_height
            painter.drawText(0, y, page_w, line_height, Qt.AlignmentFlag.AlignCenter, line)
            y += line_height

        painter.end()
        print(f"🖨️ Printed {len(lines)} lines from 0.txt")

    def open_screenshots_folder(self):
        """Ctrl+F12: Open the screenshots folder in the system file explorer."""
        screenshots_dir = os.path.join(self.void_dir, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        os.startfile(screenshots_dir)

    # ── File navigation ───────────────────────────────────────────────────────

    def scan_txt_files(self):
        dir_path = self.void_dir
        self.txt_files = sorted(
            os.path.join(dir_path, f)
            for f in os.listdir(dir_path)
            if f.lower().endswith('.txt') and os.path.isfile(os.path.join(dir_path, f))
        )
        if self.current_file_path not in self.txt_files:
            self.txt_files.append(self.current_file_path)
            self.txt_files.sort()
        self.current_file_index = self.txt_files.index(self.current_file_path)

    def switch_to_file(self, file_path):
        if not os.path.exists(file_path):
            open(file_path, 'w', encoding='utf-8').close()
        self.current_file_path = file_path
        self.current_file_index = self.txt_files.index(file_path)
        print(f"📂 Write target: {os.path.basename(file_path)}")
        if self.current_view == 0:
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)

    def show_previous_file(self):
        if not self.txt_files:
            return
        self.current_file_index = (self.current_file_index - 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def show_next_file(self):
        if not self.txt_files:
            return
        self.current_file_index = (self.current_file_index + 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    # ── Swap operations (F2 doc lines only) ──────────────────────────────────

    def _find_move_target(self, start, delta):
        """Find nearest non-dot index in direction delta (wrapping).
        Returns (index, wrapped) where wrapped=True means the boundary was crossed."""
        n = len(self.line_ring.lines)
        idx = (start + delta) % n
        for _ in range(n - 1):
            if self.line_ring.lines[idx] != '.':
                wrapped = (delta == -1 and idx > start) or (delta == 1 and idx < start)
                return idx, wrapped
            idx = (idx + delta) % n
        return None, False

    def _swap_line_in_focus(self, delta):
        """Swap line within para focus content, wrapping circularly inside the paragraph."""
        content = self._para_focus_content
        if not content:
            return
        lines = self.line_ring.lines
        cur = self.line_ring.index
        pos = content.index(cur) if cur in content else 0
        other_pos = (pos + delta) % len(content)
        other = content[other_pos]
        lines[cur], lines[other] = lines[other], lines[cur]
        # Update focus_content indices to follow swapped positions
        self._para_focus_content[pos], self._para_focus_content[other_pos] = \
            self._para_focus_content[other_pos], self._para_focus_content[pos]
        self.line_ring.index = other
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(self.line_ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.update()

    def swap_line_up(self):
        if len(self.line_ring.lines) < 2:
            return
        if self._para_focus:
            self._swap_line_in_focus(-1)
            return
        cur = self.line_ring.index
        prev, wrapped = self._find_move_target(cur, -1)
        if prev is None:
            return
        lines = self.line_ring.lines
        if not wrapped:
            lines[cur], lines[prev] = lines[prev], lines[cur]
            self.line_ring.index = prev
        else:
            line = lines.pop(cur)
            lines.append(line)
            self.line_ring.index = len(lines) - 1
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(self.line_ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.update()

    def swap_line_down(self):
        if len(self.line_ring.lines) < 2:
            return
        if self._para_focus:
            self._swap_line_in_focus(+1)
            return
        cur = self.line_ring.index
        nxt, wrapped = self._find_move_target(cur, +1)
        if nxt is None:
            return
        lines = self.line_ring.lines
        if not wrapped:
            lines[cur], lines[nxt] = lines[nxt], lines[cur]
            self.line_ring.index = nxt
        else:
            line = lines.pop(cur)
            insert_at = next((i for i, l in enumerate(lines) if l != '.'), 0)
            lines.insert(insert_at, line)
            self.line_ring.index = insert_at
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(self.line_ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.update()

    # ── Paragraph helpers ─────────────────────────────────────────────────────
    # Model: each '.' is a paragraph separator. _paragraphs_from_ring extracts
    # paragraph content arrays (no dots). _rebuild_ring_from_paragraphs puts them
    # back, always emitting a dot before each paragraph. This makes circular
    # paragraph operations (including wrapping first↔last) natural.

    def _paragraphs_from_ring(self):
        """Return (dot_indices, paragraphs) where paragraphs[k] is the list of
        content lines between dot_indices[k] and the next dot (or end)."""
        lines = self.line_ring.lines
        dot_indices = [i for i, l in enumerate(lines) if l == '.']
        if not dot_indices:
            return [], [list(lines)]
        paragraphs = []
        for k, d in enumerate(dot_indices):
            next_d = dot_indices[k + 1] if k + 1 < len(dot_indices) else len(lines)
            paragraphs.append(list(lines[d + 1:next_d]))
        return dot_indices, paragraphs

    def _rebuild_ring_from_paragraphs(self, paragraphs):
        """Rebuild ring.lines from paragraph content arrays, inserting a dot before each."""
        new_lines = []
        for para in paragraphs:
            new_lines.append('.')
            new_lines.extend(para)
        self.line_ring.lines = new_lines

    def _dot_line_index(self, para_idx, paragraphs):
        """Return the line index of the dot that precedes paragraphs[para_idx]."""
        return sum(1 + len(paragraphs[j]) for j in range(para_idx))

    def goto_prev_dot(self):
        ring = self.line_ring
        n = len(ring.lines)
        if n == 0:
            return
        idx = (ring.index - 1) % n
        for _ in range(n):
            if ring.lines[idx] == '.':
                ring.index = idx
                return
            idx = (idx - 1) % n

    def goto_next_dot(self):
        ring = self.line_ring
        n = len(ring.lines)
        if n == 0:
            return
        idx = (ring.index + 1) % n
        for _ in range(n):
            if ring.lines[idx] == '.':
                ring.index = idx
                return
            idx = (idx + 1) % n

    def _move_paragraph(self, k, paragraphs, direction):
        """Move paragraph k up (-1) or down (+1). At boundaries: move, not swap."""
        n = len(paragraphs)
        if n <= 1:
            return
        other_k = k + direction
        wrapped = other_k < 0 or other_k >= n
        if not wrapped:
            # Normal: swap adjacent paragraphs
            paragraphs[k], paragraphs[other_k] = paragraphs[other_k], paragraphs[k]
            dest = other_k
        else:
            # Boundary: remove and insert at the other end
            para = paragraphs.pop(k)
            if direction == -1:
                paragraphs.append(para)   # first → becomes last
                dest = len(paragraphs) - 1
            else:
                paragraphs.insert(0, para)  # last → becomes first
                dest = 0
        self._rebuild_ring_from_paragraphs(paragraphs)
        self.line_ring.index = self._dot_line_index(dest, paragraphs)
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.editor.setText(self.line_ring.current())
        self.circular_view.editor.setCursorPosition(0)
        self.circular_view.update()

    def _current_para_idx(self):
        """Return the paragraph index (k) whose dot is at ring.index, or None."""
        _, paragraphs = self._paragraphs_from_ring()
        for k in range(len(paragraphs)):
            if self._dot_line_index(k, paragraphs) == self.line_ring.index:
                return k, paragraphs
        return None, None

    def swap_paragraph_up(self):
        if not self.line_ring.lines or self.line_ring.current() != '.':
            return
        k, paragraphs = self._current_para_idx()
        if k is None:
            return
        self._move_paragraph(k, paragraphs, -1)

    def swap_paragraph_down(self):
        if not self.line_ring.lines or self.line_ring.current() != '.':
            return
        k, paragraphs = self._current_para_idx()
        if k is None:
            return
        self._move_paragraph(k, paragraphs, +1)

    def rebase_to_index_zero(self):
        """Ctrl+9: Rotate current paragraph so current line becomes first after its dot."""
        if self.current_view != 1:
            print("⚠️ Rebase only available in F2")
            return
        ring = self.line_ring
        if ring.current() == '.':
            return
        _, paragraphs = self._paragraphs_from_ring()
        for k, para in enumerate(paragraphs):
            dot_pos = self._dot_line_index(k, paragraphs)
            next_dot = dot_pos + 1 + len(para)
            if dot_pos < ring.index < next_dot:
                offset = ring.index - dot_pos - 1
                paragraphs[k] = para[offset:] + para[:offset]
                self._rebuild_ring_from_paragraphs(paragraphs)
                ring.index = self._dot_line_index(k, paragraphs) + 1
                self.auto_save_circular()
                self.circular_view._offset = 0.0
                self.circular_view.editor.setText(ring.current())
                self.circular_view.editor.setCursorPosition(0)
                self.circular_view.update()
                print(f"💾 Rebase paragraph | '{ring.current()[:50]}'")
                return

    # ── UI init ───────────────────────────────────────────────────────────────

    def init_ui(self):
        self.showFullScreen()
        self.setCentralWidget(self.stack)
        self._reposition_entry()

    def _reposition_entry(self):
        w = self.width()
        h = self.height()
        if w == 0 or h == 0:
            return
        entry_width = min(w, h) - 90
        entry_height = self.entry.sizeHint().height()
        self.entry.setFixedWidth(entry_width)
        self.entry.move(w // 2 - entry_width // 2, h // 2 - entry_height // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_entry()

    # ── Key routing ───────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        # Global: view switching
        if self._matches(key, mods, 'view_f1'):
            self.switch_to_view(0); event.accept(); return
        if self._matches(key, mods, 'view_f2'):
            self.switch_to_view(1); event.accept(); return
        if self._matches(key, mods, 'view_f3'):
            self.switch_to_view(2); event.accept(); return
        if self._matches(key, mods, 'view_f4'):
            self.switch_to_view(3); event.accept(); return

        # Global: rebase (F2 only, enforced inside; F3 handled view-specifically)
        if self._matches(key, mods, 'rebase') and self.current_view != 2:
            self.rebase_to_index_zero(); event.accept(); return

        # Global: reshuffle vault
        if self._matches(key, mods, 'reshuffle'):
            self.load_vault_lines()
            if self.current_view == 3 and self.vault_view:
                self.vault_view.update()
            event.accept(); return

        # Global: file/folder pickers
        if self._matches(key, mods, 'pick_active_file'):
            self.pick_active_file(); event.accept(); return
        if self._matches(key, mods, 'pick_book_dir'):
            self.pick_book_directory(); event.accept(); return
        if self._matches(key, mods, 'pick_dir'):
            self.change_void_directory(); event.accept(); return

        # Print book (F3 only)
        if self._matches(key, mods, 'print_doc') and self.current_view == 2:
            self.print_book(); event.accept(); return

        # Global: screenshot / open folder
        if self._matches(key, mods, 'screenshot'):
            self.take_screenshot(); event.accept(); return
        if self._matches(key, mods, 'open_screenshots'):
            self.open_screenshots_folder(); event.accept(); return

        # Global: opacity
        if self._matches(key, mods, 'opacity_up'):
            self.opacity = min(1.0, self.opacity + 0.1)
            self.setWindowOpacity(self.opacity)
            event.accept(); return
        if self._matches(key, mods, 'opacity_down'):
            self.opacity = max(0.0, self.opacity - 0.1)
            self.setWindowOpacity(self.opacity)
            event.accept(); return

        # View-specific
        if self.current_view == 0:
            self._handle_f1_keys(key, mods)
        elif self.current_view == 1:
            self._handle_f2_keys(key, mods, event)
        elif self.current_view == 2:
            self._handle_f3_keys(key, mods, event)
        elif self.current_view == 3:
            self._handle_f4_keys(key, mods, event)

    def _handle_f1_keys(self, key, mods):
        if self._matches(key, mods, 'quit'):
            self.close()
        elif self._matches(key, mods, 'file_prev'):
            self.show_previous_file()
        elif self._matches(key, mods, 'file_next'):
            self.show_next_file()
        elif self._matches(key, mods, 'para_prev'):
            self.goto_prev_dot()
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.current_active_line_index = self.line_ring.index
        elif self._matches(key, mods, 'para_next'):
            self.goto_next_dot()
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.current_active_line_index = self.line_ring.index
        elif key == Qt.Key.Key_Up and mods == Qt.KeyboardModifier.NoModifier:
            # If entry is empty and ring is already at the last sent line, show it first
            if not self.entry.text() and self.current_active_line_index is None:
                pass  # don't move, just show current
            else:
                self.line_ring.move(-1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(len(self.entry.text()))
            self.current_active_line_index = self.line_ring.index
            print(f"⬆️ F1: index={self.line_ring.index}")
        elif key == Qt.Key.Key_Down and mods == Qt.KeyboardModifier.NoModifier:
            self.line_ring.move(1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.current_active_line_index = self.line_ring.index
            print(f"⬇️ F1: index={self.line_ring.index}")

    def _handle_f2_keys(self, key, mods, event):
        # Up/Down/Enter handled by circular_view.editor signals.
        if self._matches(key, mods, 'swap_up'):
            if self.line_ring.current() == '.':
                self.swap_paragraph_up()
            else:
                self.swap_line_up()
            event.accept()
        elif self._matches(key, mods, 'swap_down'):
            if self.line_ring.current() == '.':
                self.swap_paragraph_down()
            else:
                self.swap_line_down()
            event.accept()
        elif self._matches(key, mods, 'para_prev'):
            self.goto_prev_dot()
            self._doc_show_editor()
            event.accept()
        elif self._matches(key, mods, 'para_next'):
            self.goto_next_dot()
            self._doc_show_editor()
            event.accept()
        elif key == Qt.Key.Key_Escape:
            if self._para_focus:
                self._exit_para_focus()
            else:
                self.switch_to_view(0)

    def _handle_f3_keys(self, key, mods, event):
        # Up/Down/Enter handled by book_view.editor signals.
        if key == Qt.Key.Key_Escape:
            self.switch_to_view(0)
        elif self._matches(key, mods, 'swap_up'):
            self._book_swap_up(); event.accept()
        elif self._matches(key, mods, 'swap_down'):
            self._book_swap_down(); event.accept()
        elif self._matches(key, mods, 'rebase'):
            self._book_rebase(); event.accept()
        elif self._matches(key, mods, 'quit'):
            self.close()

    def _handle_f4_keys(self, key, mods, event):
        # Up/Down/Enter handled by vault_view.editor signals.
        if key == Qt.Key.Key_Escape:
            self.vault_view.edit_mode = False
            self.vault_view.editor.hide()
            self.switch_to_view(0)
        elif self._matches(key, mods, 'quit'):
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FullscreenCircleApp()
    sys.exit(app.exec())
