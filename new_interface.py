# new_interface.py - SISTEMA DE 3 VISTAS
import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QLabel, QWidget, QStackedWidget
from PyQt6.QtGui import QColor, QPainter, QFont, QCursor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from files import setup_file_handling, void_line
from controls import setup_controls, show_random_line_from_current_file, show_previous_current_file_line, show_next_current_file_line, show_random_line_from_random_file
from noise_controls import NoiseController
from line_ring import LineRing
from circular_view import CircularView

class NormalView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setStyleSheet("background: black;")

    def paintEvent(self, event):
        if not self.parent_app:
            return
        if self.width() == 0 or self.height() == 0:
            return
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("white"), 10)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        w = self.width()
        h = self.height()
        center_x = w // 2
        center_y = h // 2
        radius = min(w, h) // 2 - 35
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

class VersesView(QWidget):
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self.verses = []
        self.current_verse_index = 0
        self.setStyleSheet("background: black; color: white;")

    def calculate_verses(self):
        verses = []
        current_verse = []
        start_index = 0
        for idx, line in enumerate(self.ring.lines):
            if line.strip() == '.':
                if current_verse:
                    verses.append({'lines': current_verse, 'start': start_index, 'end': idx - 1})
                    current_verse = []
                start_index = idx + 1
            else:
                current_verse.append(line)
        if current_verse:
            verses.append({'lines': current_verse, 'start': start_index, 'end': len(self.ring.lines) - 1})
        if not verses:
            verses.append({'lines': [""], 'start': 0, 'end': 0})
        return verses

    def find_current_verse(self):
        for idx, verse in enumerate(self.verses):
            if verse['start'] <= self.ring.index <= verse['end']:
                return idx
        return 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = QFont("Consolas", 11)
        painter.setPen(QColor("white"))
        w = self.width()
        h = self.height()
        line_height = 25
        verse_spacing = 60

        self.verses = self.calculate_verses()
        self.current_verse_index = self.find_current_verse()

        y_offset = h // 2 - (self.current_verse_index * (line_height * 5 + verse_spacing))

        for verse_idx, verse in enumerate(self.verses):
            is_current = (verse_idx == self.current_verse_index)
            verse_y = y_offset

            if is_current:
                painter.setOpacity(1.0)
                font.setPointSize(12)
            else:
                painter.setOpacity(0.3)
                font.setPointSize(10)

            painter.setFont(font)

            for line_idx, line in enumerate(verse['lines']):
                text_y = verse_y + (line_idx * line_height)

                if is_current:
                    painter.setOpacity(1.0)
                    painter.setPen(QColor("white"))
                    painter.drawLine(50, text_y, 50, text_y + line_height - 5)

                painter.setOpacity(1.0 if is_current else 0.3)
                painter.setPen(QColor("white"))
                painter.drawText(0, text_y, w, line_height,
                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                                line)

            y_offset += len(verse['lines']) * line_height + verse_spacing

class CustomLineEdit(QLineEdit):
    spacePressed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_Space:
            if self.parent.use_spacebar_for_void:
                self.spacePressed.emit()
                event.accept()
                return
            super().keyPressEvent(event)
            return
        if key == Qt.Key.Key_0 and (modifiers & Qt.KeyboardModifier.ControlModifier):
            show_random_line_from_random_file(self.parent, event)
            event.accept()
        elif key == Qt.Key.Key_Period and (modifiers & Qt.KeyboardModifier.ControlModifier):
            show_random_line_from_current_file(self.parent, event)
            event.accept()
        else:
            super().keyPressEvent(event)

class NoiseOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.noise_pixmap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.generate_noise)
        self.timer.start(50)
    def generate_noise(self):
        block_size = 1
        w, h = self.width(), self.height()
        h_blocks, w_blocks = h // block_size, w // block_size
        noise_gray = np.random.randint(0, 256, (h_blocks, w_blocks), dtype=np.uint8)
        image = QImage(noise_gray.data, w_blocks, h_blocks, w_blocks, QImage.Format.Format_Grayscale8)
        image = image.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        self.noise_pixmap = QPixmap.fromImage(image)
        self.update()
    def paintEvent(self, event):
        if self.noise_pixmap:
            painter = QPainter(self)
            painter.setOpacity(0.09)
            painter.drawPixmap(0, 0, self.noise_pixmap)

class FullscreenCircleApp(QMainWindow):
    def __init__(self, read_dir=None, void_dir=None, file_to_open=None):
        super().__init__()
        self.opacity = 1.0
        self.read_dir = read_dir
        self.void_dir = void_dir
        self.file_to_open = file_to_open
        self.txt_files = []
        self.current_file_index = 0
        self.setWindowTitle("Voider")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.setStyleSheet("background-color: black; color: white;")

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

        self.noise_controller = NoiseController(
            block_size=1024, volume=0.3, noise_type='brown',
            bitcrush={'bit_depth': 10, 'sample_rate_factor': 0.7},
            lfo_min_freq=0.03, lfo_max_freq=0.1, glitch_prob=0.005, cutoff_freq=2500
        )

        self.current_view = 0  # 0=F1, 1=F2, 2=F3
        self.line_ring = LineRing()

        self.stack = QStackedWidget()

        self.normal_view = NormalView(self)
        self.circular_view = None
        self.verses_view = None

        self.stack.addWidget(self.normal_view)
        self.setup_voider_logic()
        self.use_spacebar_for_void = False
        self._print_void_mode_status()
        self._void_enter_connection = None
        self._void_space_connection = None
        self._connect_void_key()
        self.init_ui()

        self.switch_to_view(0)
        self.entry.clear()  # Entry vacío al inicio

    def _print_void_mode_status(self):
        print("VOID MODE:", "Spacebar" if self.use_spacebar_for_void else "Enter")

    def _connect_void_key(self):
        self._disconnect_void_key()
        if self.use_spacebar_for_void:
            self._void_space_connection = self.entry.spacePressed.connect(lambda: void_line(self))
        else:
            self._void_enter_connection = self.entry.returnPressed.connect(lambda: void_line(self))

    def _disconnect_void_key(self):
        if self._void_enter_connection:
            try: self.entry.returnPressed.disconnect(self._void_enter_connection)
            except: pass
            self._void_enter_connection = None
        if self._void_space_connection:
            try: self.entry.spacePressed.disconnect(self._void_space_connection)
            except: pass
            self._void_space_connection = None

    def toggle_void_key_mode(self):
        self.use_spacebar_for_void = not self.use_spacebar_for_void
        self._print_void_mode_status()
        self._connect_void_key()

    def switch_to_view(self, view_index):
        self.current_view = view_index

        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
        except:
            lines = []

        old_index = self.line_ring.index if self.line_ring else 0
        self.line_ring = LineRing(lines or [""])
        self.line_ring.index = min(old_index, len(lines) - 1 if lines else 0)

        if view_index == 0:  # F1
            print("📍 Vista F1")
            self.stack.setCurrentWidget(self.normal_view)
            self.entry.show()
            self.entry.raise_()
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.entry.setFocus()

        elif view_index == 1:  # F2
            print("📍 Vista F2")
            if not self.circular_view:
                self.circular_view = CircularView(self.line_ring, self)
                self.circular_view.setFont(QFont("Consolas", 11))
                self.circular_view.line_saved.connect(self.auto_save_circular)
                self.stack.addWidget(self.circular_view)
            else:
                self.circular_view.ring = self.line_ring

            self.stack.setCurrentWidget(self.circular_view)
            self.entry.hide()
            self.circular_view.setFocus()
            self.circular_view.update()

        elif view_index == 2:  # F3
            print("📍 Vista F3")
            if not self.verses_view:
                self.verses_view = VersesView(self.line_ring, self)
                self.stack.addWidget(self.verses_view)
            else:
                self.verses_view.ring = self.line_ring

            self.stack.setCurrentWidget(self.verses_view)
            self.entry.hide()
            self.verses_view.setFocus()
            self.verses_view.update()

    def auto_save_circular(self):
        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                for line in self.line_ring.lines:
                    f.write(line + '\n')
            print(f"💾 Guardado desde F2")
        except Exception as e:
            print(f"❌ Error: {e}")

    def setup_voider_logic(self):
        self.current_file_path = self.file_to_open or os.path.join(self.void_dir, '0.txt')
        self.void_file_path = os.path.join(self.void_dir, '0.txt')
        self.scan_txt_files()
        setup_file_handling(self)
        setup_controls(self)

    def scan_txt_files(self):
        dir_path = os.path.dirname(self.current_file_path)
        self.txt_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
                          if f.lower().endswith('.txt') and os.path.isfile(os.path.join(dir_path, f))]
        self.txt_files.sort()
        if self.current_file_path in self.txt_files:
            self.current_file_index = self.txt_files.index(self.current_file_path)
        else:
            self.txt_files.append(self.current_file_path)
            self.txt_files.sort()
            self.current_file_index = self.txt_files.index(self.current_file_path)

    def switch_to_file(self, file_path):
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('')
        self.current_file_path = file_path
        self.current_file_index = self.txt_files.index(file_path)
        self.entry.clear()

    def show_previous_file(self):
        if not self.txt_files: return
        self.current_file_index = (self.current_file_index - 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def show_next_file(self):
        if not self.txt_files: return
        self.current_file_index = (self.current_file_index + 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def init_ui(self):
        self.showFullScreen()
        screen = self.screen().availableGeometry()
        center_x = screen.width() // 2
        center_y = screen.height() // 2
        radius = min(screen.width(), screen.height()) // 2 - 35
        entry_width = radius * 2 - 40
        self.entry.setFixedWidth(entry_width)
        self.entry.move(center_x - entry_width // 2, center_y - self.entry.height() // 2)

        self.setCentralWidget(self.stack)
        self.noise_overlay = NoiseOverlay(self)
        self.noise_overlay.resize(self.size())
        self.noise_overlay.show()
        self.noise_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'noise_overlay'):
            self.noise_overlay.resize(self.size())

        screen = self.screen().availableGeometry()
        center_x = screen.width() // 2
        center_y = screen.height() // 2
        entry_width = min(screen.width(), screen.height()) - 90
        self.entry.setFixedWidth(entry_width)
        self.entry.move(center_x - entry_width // 2, center_y - self.entry.height() // 2)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_F1:
            self.switch_to_view(0)
            event.accept()
            return
        elif key == Qt.Key.Key_F2:
            self.switch_to_view(1)
            event.accept()
            return
        elif key == Qt.Key.Key_F3:
            self.switch_to_view(2)
            event.accept()
            return

        if self.current_view == 0:  # F1
            if key == Qt.Key.Key_Escape:
                self.noise_controller.stop()
                self.close()
            elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.opacity = min(1.0, self.opacity + 0.1)
                self.setWindowOpacity(self.opacity)
            elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.opacity = max(0.0, self.opacity - 0.1)
                self.setWindowOpacity(self.opacity)
            elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.AltModifier:
                self.show_previous_file()
            elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.AltModifier:
                self.show_next_file()
            elif key == Qt.Key.Key_Up:
                show_previous_current_file_line(self)
            elif key == Qt.Key.Key_Down:
                show_next_current_file_line(self)

        elif self.current_view == 1:  # F2
            if self.circular_view.edit_mode:
                if key == Qt.Key.Key_Escape:
                    self.circular_view.cancel_edit()
                    event.accept()
            else:
                if key == Qt.Key.Key_Up:
                    self.circular_view.animate_move(-1)
                    event.accept()
                elif key == Qt.Key.Key_Down:
                    self.circular_view.animate_move(1)
                    event.accept()
                elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    self.circular_view.enter_edit_mode()
                    event.accept()
                elif key == Qt.Key.Key_Escape:
                    self.switch_to_view(0)

        elif self.current_view == 2:  # F3
            if key == Qt.Key.Key_Escape:
                self.noise_controller.stop()
                self.close()
            elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.opacity = min(1.0, self.opacity + 0.1)
                self.setWindowOpacity(self.opacity)
            elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.opacity = max(0.0, self.opacity - 0.1)
                self.setWindowOpacity(self.opacity)
            elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.AltModifier:
                self.show_previous_file()
            elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.AltModifier:
                self.show_next_file()
            elif key == Qt.Key.Key_Up:
                verses = self.verses_view.calculate_verses()
                current = self.verses_view.find_current_verse()
                new_verse = (current - 1) % len(verses)
                self.line_ring.index = verses[new_verse]['start']
                self.verses_view.update()
            elif key == Qt.Key.Key_Down:
                verses = self.verses_view.calculate_verses()
                current = self.verses_view.find_current_verse()
                new_verse = (current + 1) % len(verses)
                self.line_ring.index = verses[new_verse]['start']
                self.verses_view.update()
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.switch_to_view(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    read_directory = 'read_potential'
    void_directory = 'void_potential'
    os.makedirs(read_directory, exist_ok=True)
    os.makedirs(void_directory, exist_ok=True)
    window = FullscreenCircleApp(read_dir=read_directory, void_dir=void_directory)
    sys.exit(app.exec())