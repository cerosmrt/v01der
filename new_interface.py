# new_interface.py - App principal con sistema de 2 vistas + vault (F3)
import os
import sys
import json
import random
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QFileDialog
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
    "void_key": "enter",
    "keybindings": {
        "view_f1": "F1",
        "view_f2": "F2",
        "view_f3": "F3",
        "quit": "Escape",
        "rebase": "Ctrl+9",
        "reshuffle": "Ctrl+R",
        "opacity_up": "Ctrl+Up",
        "opacity_down": "Ctrl+Down",
        "file_prev": "Alt+Up",
        "file_next": "Alt+Down",
        "swap_up": "Alt+Up",
        "swap_down": "Alt+Down",
        "pick_dir": "F4"
    }
}

_KEY_MAP = {
    'Up': Qt.Key.Key_Up, 'Down': Qt.Key.Key_Down,
    'Left': Qt.Key.Key_Left, 'Right': Qt.Key.Key_Right,
    'Escape': Qt.Key.Key_Escape, 'Return': Qt.Key.Key_Return,
    'Enter': Qt.Key.Key_Return, 'Space': Qt.Key.Key_Space,
    'F1': Qt.Key.Key_F1, 'F2': Qt.Key.Key_F2, 'F3': Qt.Key.Key_F3,
    'F4': Qt.Key.Key_F4, 'F5': Qt.Key.Key_F5, 'F6': Qt.Key.Key_F6,
    '0': Qt.Key.Key_0, '9': Qt.Key.Key_9, 'R': Qt.Key.Key_R,
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
    F1: center entry — write/navigate 0.txt lines
    F2: circular view — edit/swap 0.txt lines
    F3: vault browser — browse shuffled lines from other files, pick into 0.txt
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
        self.opacity = 1.0
        self.txt_files = []
        self.current_file_index = 0
        self.current_view = 0  # 0=F1, 1=F2, 2=F3
        self.use_spacebar_for_void = self.config.get('void_key', 'enter') == 'space'

        # Window setup
        self.setWindowTitle("Voider")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.setStyleSheet("background-color: black; color: white;")

        # Entry (F1)
        self.entry = CustomLineEdit(self)
        self.entry.setFont(QFont("Consolas", 11))
        self.entry.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: white;
                border: none;
                selection-background-color: white;
                selection-color: black;
            }
        """)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.setFocus()

        # Doc ring (0.txt lines, ordered) and vault ring (other files, shuffled)
        self.line_ring = LineRing()
        self.vault_ring = LineRing()

        # View stack
        self.stack = QStackedWidget()
        self.normal_view = NormalView(self)
        self.circular_view = None   # F2: CircularView over doc ring
        self.vault_view = None      # F3: CircularView over vault ring
        self.stack.addWidget(self.normal_view)

        # File setup — write target is always 0.txt
        self.current_file_path = os.path.join(self.void_dir, '0.txt')
        self.void_file_path = self.current_file_path
        os.makedirs(self.void_dir, exist_ok=True)
        if not os.path.exists(self.current_file_path):
            open(self.current_file_path, 'w', encoding='utf-8').close()

        self.scan_txt_files()
        setup_file_handling(self)
        setup_controls(self)

        self.load_doc_lines()
        self.load_vault_lines()

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
        self.config['void_dir'] = new_dir
        _save_config(self.config)

        self.current_file_path = os.path.join(self.void_dir, '0.txt')
        self.void_file_path = self.current_file_path
        os.makedirs(self.void_dir, exist_ok=True)
        if not os.path.exists(self.current_file_path):
            open(self.current_file_path, 'w', encoding='utf-8').close()

        self.scan_txt_files()
        self.load_doc_lines()
        self.load_vault_lines()
        self.switch_to_view(self.current_view)
        print(f"📁 Void dir changed to: {new_dir}")

    # ── Loaders ───────────────────────────────────────────────────────────────

    def load_doc_lines(self):
        """Load 0.txt into the doc ring (ordered, no shuffle). Preserves index."""
        doc_path = os.path.join(self.void_dir, '0.txt')
        lines = []
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                for raw in f:
                    s = raw.strip()
                    if s and s != '.':
                        lines.append(s)
        except Exception as e:
            print(f"⚠️ Error reading 0.txt: {e}")
        old_index = self.line_ring.index if self.line_ring.lines else 0
        self.line_ring = LineRing(lines or [""])
        self.line_ring.index = min(old_index, len(self.line_ring.lines) - 1)
        if self.circular_view:
            self.circular_view.ring = self.line_ring
            self.circular_view._offset = 0.0
        print(f"📄 {len(lines)} lines loaded from 0.txt")

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
        # Reload doc ring so F1 Up/Down and F2 reflect the written line
        self.load_doc_lines()
        self.line_ring.index = max(0, len(self.line_ring.lines) - 1)

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
        old_view = self.current_view
        self.current_view = view_index
        print(f"📍 F{old_view+1} → F{view_index+1} | Index: {self.line_ring.index} | Line: '{self.line_ring.current()}'")

        if view_index == 0:  # F1 — write/navigate 0.txt
            self.stack.setCurrentWidget(self.normal_view)
            self.entry.show()
            self.entry.raise_()
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.entry.setFocus()

        elif view_index == 1:  # F2 — circular doc view
            if not self.circular_view:
                self.circular_view = CircularView(self.line_ring, self)
                self.circular_view.setFont(QFont("Consolas", 11))
                self.circular_view.line_saved.connect(self.auto_save_circular)
                self.stack.addWidget(self.circular_view)
            else:
                self.circular_view.ring = self.line_ring
                self.circular_view._offset = 0.0

            self.stack.setCurrentWidget(self.circular_view)
            self.entry.hide()
            self.circular_view.setFocus()
            self.circular_view.update()

        elif view_index == 2:  # F3 — vault browser
            if not self.vault_view:
                self.vault_view = CircularView(self.vault_ring, self)
                self.vault_view.setFont(QFont("Consolas", 11))
                self.stack.addWidget(self.vault_view)
            else:
                self.vault_view.ring = self.vault_ring
                self.vault_view._offset = 0.0

            self.stack.setCurrentWidget(self.vault_view)
            self.entry.hide()
            self.vault_view.setFocus()
            self.vault_view.update()

    def auto_save_circular(self):
        """Save doc ring state to 0.txt."""
        doc_path = os.path.join(self.void_dir, '0.txt')
        try:
            with open(doc_path, 'w', encoding='utf-8') as f:
                for line in self.line_ring.lines:
                    f.write(line + '\n')
            print(f"💾 Saved to 0.txt (index={self.line_ring.index})")
        except Exception as e:
            print(f"❌ Save error: {e}")

    def take_from_vault(self):
        """
        Insert the current vault line into the doc ring after current position,
        save 0.txt, and remove the line from the vault.
        """
        if not self.vault_ring.lines or self.vault_ring.current() == "":
            return
        line = self.vault_ring.current()
        # Insert into doc after current index
        insert_pos = self.line_ring.index + 1
        self.line_ring.lines.insert(insert_pos, line)
        # Remove from vault (ring adjusts index automatically)
        self.vault_ring.remove_current()
        # Persist doc to disk
        self.auto_save_circular()
        # Refresh vault view display
        if self.vault_view:
            self.vault_view._offset = 0.0
            self.vault_view.update()
        print(f"✅ Vault→Doc[{insert_pos}]: '{line}'")

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

    def swap_line_up(self):
        if len(self.line_ring.lines) < 2:
            return
        cur = self.line_ring.index
        prev = (cur - 1) % len(self.line_ring.lines)
        self.line_ring.lines[cur], self.line_ring.lines[prev] = \
            self.line_ring.lines[prev], self.line_ring.lines[cur]
        self.line_ring.index = prev
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.update()
        print(f"⬆️ Swap: {cur} ↔ {prev}")

    def swap_line_down(self):
        if len(self.line_ring.lines) < 2:
            return
        cur = self.line_ring.index
        nxt = (cur + 1) % len(self.line_ring.lines)
        self.line_ring.lines[cur], self.line_ring.lines[nxt] = \
            self.line_ring.lines[nxt], self.line_ring.lines[cur]
        self.line_ring.index = nxt
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.update()
        print(f"⬇️ Swap: {cur} ↔ {nxt}")

    def rebase_to_index_zero(self):
        """Ctrl+9: Reorder doc ring so current line becomes index 0. F2 only."""
        if self.current_view != 1:
            print("⚠️ Rebase only available in F2")
            return
        self.line_ring.rebase_to_current()
        self.auto_save_circular()
        self.circular_view._offset = 0.0
        self.circular_view.update()
        print(f"💾 Rebase | New line 0: '{self.line_ring.current()[:50]}'")

    # ── UI init ───────────────────────────────────────────────────────────────

    def init_ui(self):
        self.showFullScreen()
        screen = self.screen().availableGeometry()
        cx = screen.width() // 2
        cy = screen.height() // 2
        entry_width = min(screen.width(), screen.height()) * 2 // 2 - 90
        self.entry.setFixedWidth(entry_width)
        self.entry.move(cx - entry_width // 2, cy - self.entry.height() // 2)
        self.setCentralWidget(self.stack)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        screen = self.screen().availableGeometry()
        cx = screen.width() // 2
        cy = screen.height() // 2
        entry_width = min(screen.width(), screen.height()) - 90
        self.entry.setFixedWidth(entry_width)
        self.entry.move(cx - entry_width // 2, cy - self.entry.height() // 2)

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

        # Global: rebase doc ring (F2 only, enforced inside)
        if self._matches(key, mods, 'rebase'):
            self.rebase_to_index_zero(); event.accept(); return

        # Global: reshuffle vault
        if self._matches(key, mods, 'reshuffle'):
            self.load_vault_lines()
            if self.current_view == 2 and self.vault_view:
                self.vault_view.update()
            event.accept(); return

        # Global: pick directory
        if self._matches(key, mods, 'pick_dir'):
            self.change_void_directory()
            event.accept(); return

        # View-specific
        if self.current_view == 0:
            self._handle_f1_keys(key, mods)
        elif self.current_view == 1:
            self._handle_f2_keys(key, mods, event)
        elif self.current_view == 2:
            self._handle_f3_keys(key, mods, event)

    def _handle_f1_keys(self, key, mods):
        if self._matches(key, mods, 'quit'):
            self.close()
        elif self._matches(key, mods, 'opacity_up'):
            self.opacity = min(1.0, self.opacity + 0.1)
            self.setWindowOpacity(self.opacity)
        elif self._matches(key, mods, 'opacity_down'):
            self.opacity = max(0.0, self.opacity - 0.1)
            self.setWindowOpacity(self.opacity)
        elif self._matches(key, mods, 'file_prev'):
            self.show_previous_file()
        elif self._matches(key, mods, 'file_next'):
            self.show_next_file()
        elif key == Qt.Key.Key_Up and mods == Qt.KeyboardModifier.NoModifier:
            self.line_ring.move(-1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.current_active_line_index = self.line_ring.index
            print(f"⬆️ F1: index={self.line_ring.index}")
        elif key == Qt.Key.Key_Down and mods == Qt.KeyboardModifier.NoModifier:
            self.line_ring.move(1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.current_active_line_index = self.line_ring.index
            print(f"⬇️ F1: index={self.line_ring.index}")

    def _handle_f2_keys(self, key, mods, event):
        if self.circular_view.edit_mode:
            if key == Qt.Key.Key_Escape:
                self.circular_view.cancel_edit()
                event.accept()
        else:
            if self._matches(key, mods, 'swap_up'):
                self.swap_line_up(); event.accept()
            elif self._matches(key, mods, 'swap_down'):
                self.swap_line_down(); event.accept()
            elif key == Qt.Key.Key_Up:
                self.circular_view.animate_move(-1)
                print(f"⬆️ F2: index={self.line_ring.index}")
                event.accept()
            elif key == Qt.Key.Key_Down:
                self.circular_view.animate_move(1)
                print(f"⬇️ F2: index={self.line_ring.index}")
                event.accept()
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    self.circular_view.enter_edit_mode()
                    print("✏️ F2: editing line")
                else:
                    self.circular_view.enter_insert_mode()
                    print("➕ F2: inserting line")
                event.accept()
            elif key == Qt.Key.Key_Escape:
                self.switch_to_view(0)

    def _handle_f3_keys(self, key, mods, event):
        if key == Qt.Key.Key_Up and mods == Qt.KeyboardModifier.NoModifier:
            self.vault_view.animate_move(-1)
            event.accept()
        elif key == Qt.Key.Key_Down and mods == Qt.KeyboardModifier.NoModifier:
            self.vault_view.animate_move(1)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.take_from_vault()
            event.accept()
        elif key == Qt.Key.Key_Escape:
            self.switch_to_view(0)
        elif self._matches(key, mods, 'quit'):
            self.close()
        elif self._matches(key, mods, 'opacity_up'):
            self.opacity = min(1.0, self.opacity + 0.1)
            self.setWindowOpacity(self.opacity)
        elif self._matches(key, mods, 'opacity_down'):
            self.opacity = max(0.0, self.opacity - 0.1)
            self.setWindowOpacity(self.opacity)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FullscreenCircleApp()
    sys.exit(app.exec())
