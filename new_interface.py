import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QLabel, QWidget
from PyQt6.QtGui import QColor, QPainter, QFont, QCursor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from files import setup_file_handling, void_line
from controls import setup_controls, show_random_line_from_current_file, show_previous_current_file_line, show_next_current_file_line, show_random_line_from_random_file
from noise_controls import NoiseController
from line_ring import LineRing
from circular_view import CircularView

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


class CircleBackground(QWidget):
    def __init__(self, parent=None, center_x=0, center_y=0, radius=0):
        super().__init__(parent)
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("white"), 10)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.center_x - self.radius, self.center_y - self.radius,
                            self.radius * 2, self.radius * 2)

    def resizeEvent(self, event):
        self.resize(self.parent().size())


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
        self.setStyleSheet("background-color: black;")

        self.entry = CustomLineEdit(self)
        self.entry.setFont(QFont("Consolas", 11))
        self.entry.setStyleSheet("""
            QLineEdit {
                background-color: black;
                color: white;
                border: none;
                qproperty-alignment: AlignCenter;
                selection-background-color: white;
                selection-color: black;
            }
        """)
        self.entry.setFocus()

        self.loading = QLabel("Loading potentiality", self)
        self.loading.setFont(QFont("Consolas", 11))
        self.loading.setStyleSheet("color: white; background-color: black;")
        self.loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading.resize(300, 100)
        self.loading.hide()

        self.noise_controller = NoiseController(
            block_size=1024, volume=0.3, noise_type='brown',
            bitcrush={'bit_depth': 10, 'sample_rate_factor': 0.7},
            lfo_min_freq=0.03, lfo_max_freq=0.1, glitch_prob=0.005, cutoff_freq=2500
        )

        # ── Modo circular ────────────────────────────────
        self.circular_mode = False
        self.line_ring = None
        self.circular_view = None
        # ─────────────────────────────────────────────────

        self.setup_voider_logic()

        self.use_spacebar_for_void = False
        self._print_void_mode_status()
        self._void_enter_connection = None
        self._void_space_connection = None
        self._connect_void_key()

        self.init_ui()

    # Métodos para modo void (Enter / Space) ─────────────
    def _print_void_mode_status(self):
        print("VOID MODE:", "Spacebar" if self.use_spacebar_for_void else "Enter", "(F2 para cambiar)")

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
        self.entry.setFocus()

    # Toggle modo circular ───────────────────────────────
    def toggle_circular_mode(self):
        self.circular_mode = not self.circular_mode

        if self.circular_mode:
            try:
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip()]
                self.line_ring = LineRing(lines or [""])
            except:
                self.line_ring = LineRing([""])

            self.circular_view = CircularView(self.line_ring, self)
            self.circular_view.resize(self.size())
            self.circular_view.show()
            self.entry.hide()
            self.circular_view.setFocus()
        else:
            if self.circular_view:
                self.circular_view.deleteLater()
                self.circular_view = None
            self.entry.show()
            self.entry.setFocus()

    # ─────────────────────────────────────────────────────

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
        self.center_x = screen.width() // 2
        self.center_y = screen.height() // 2
        self.radius = min(screen.width(), screen.height()) // 2 - 35
        entry_width = self.radius * 2 - 40

        self.entry.setFixedWidth(entry_width)
        self.entry.move(self.center_x - entry_width // 2, self.center_y - self.entry.height() // 2)

        self.loading.move(self.center_x - 150, self.center_y - 50)
        self.loading.show()
        QTimer.singleShot(1500, self.loading.deleteLater)

        self.circle_background = CircleBackground(self, self.center_x, self.center_y, self.radius)
        self.circle_background.resize(self.size())
        self.circle_background.show()

        self.noise_overlay = NoiseOverlay(self)
        self.noise_overlay.resize(self.size())
        self.noise_overlay.show()
        self.noise_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'noise_overlay'):
            self.noise_overlay.resize(self.size())
        if hasattr(self, 'circle_background'):
            self.circle_background.resize(self.size())
        if hasattr(self, 'circular_view') and self.circular_view:
            self.circular_view.resize(self.size())

        screen = self.screen().availableGeometry()
        self.center_x = screen.width() // 2
        self.center_y = screen.height() // 2
        self.radius = min(screen.width(), screen.height()) // 2 - 35
        entry_width = self.radius * 2 - 40
        self.entry.setFixedWidth(entry_width)
        self.entry.move(self.center_x - entry_width // 2, self.center_y - self.entry.height() // 2)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_F2:
            self.toggle_void_key_mode()
            event.accept()
            return

        if key == Qt.Key.Key_F3:           # ← tecla para toggle circular (cambia si quieres)
            self.toggle_circular_mode()
            event.accept()
            return

        if self.circular_mode:
            if key == Qt.Key.Key_Up:
                self.circular_view.animate_move(-1)
                event.accept()
            elif key == Qt.Key.Key_Down:
                self.circular_view.animate_move(1)
                event.accept()
            elif key == Qt.Key.Key_Escape:
                self.toggle_circular_mode()
                event.accept()
            return

        # Modo normal
        if key == Qt.Key.Key_Escape:
            self.noise_controller.stop()
            self.close()
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.increase_opacity()
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.decrease_opacity()
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_previous_file()
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_next_file()
        elif key == Qt.Key.Key_Up:
            show_previous_current_file_line(self)
        elif key == Qt.Key.Key_Down:
            show_next_current_file_line(self)

    def increase_opacity(self):
        self.opacity = min(1.0, self.opacity + 0.1)
        self.setWindowOpacity(self.opacity)

    def decrease_opacity(self):
        self.opacity = max(0.0, self.opacity - 0.1)
        self.setWindowOpacity(self.opacity)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    read_directory = 'read_potential'
    void_directory = 'void_potential'
    os.makedirs(read_directory, exist_ok=True)
    os.makedirs(void_directory, exist_ok=True)
    window = FullscreenCircleApp(read_dir=read_directory, void_dir=void_directory)
    sys.exit(app.exec())