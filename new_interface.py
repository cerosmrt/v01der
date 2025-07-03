# --- new_interface.py ---
import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QLabel, QWidget
from PyQt6.QtGui import QColor, QPainter, QFont, QCursor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer
from files import setup_file_handling, void_line
from controls import setup_controls, show_random_line_from_zero, show_previous_zero_line, show_next_zero_line
from noise_controls import NoiseController

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_0:
            print("Tecla 0 detectada en QLineEdit, ejecutando show_random_line_from_zero")
            self.parent.last_inserted_index = None
            show_random_line_from_zero(self.parent, event)
            event.accept()
        elif (key == Qt.Key.Key_Up or key == Qt.Key.Key_Down) and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.parent.keyPressEvent(event)
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
        painter.drawEllipse(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.radius * 2,
            self.radius * 2
        )

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
            painter.setOpacity(0.09)  # <- Más visible
            painter.drawPixmap(0, 0, self.noise_pixmap)

class FullscreenCircleApp(QMainWindow):
    def __init__(self, read_dir=None, void_dir=None):
        super().__init__()
        self.opacity = 1.0
        self.read_dir = read_dir or os.path.dirname(os.path.abspath(__file__))
        self.void_dir = void_dir or os.path.join(self.read_dir, 'void')
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
        self.entry.returnPressed.connect(lambda: void_line(self))

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

        self.setup_voider_logic()
        self.init_ui()

    def setup_voider_logic(self):
        os.makedirs(self.void_dir, exist_ok=True)
        self.void_file_path = os.path.join(self.void_dir, '0.txt')
        print(f"void_file_path inicializado: {self.void_file_path}")
        self.current_zero_line = None
        self.current_zero_line_index = None
        self.last_inserted_index = None
        setup_file_handling(self)
        setup_controls(self)

    def init_ui(self):
        print("Initializing UI")
        self.showFullScreen()
        screen = self.screen().availableGeometry()
        self.center_x = screen.width() // 2
        self.center_y = screen.height() // 2
        self.radius = min(screen.width(), screen.height()) // 2 - 35
        entry_width = self.radius * 2 - 40
        self.entry.setFixedWidth(entry_width)
        self.entry.move(self.center_x - entry_width // 2,
                        self.center_y - self.entry.height() // 2)
        self.loading.move(self.center_x - 150, self.center_y - 50)
        self.loading.show()
        QTimer.singleShot(1500, self.loading.deleteLater)

        self.circle_background = CircleBackground(self, self.center_x, self.center_y, self.radius)
        self.circle_background.resize(self.size())
        self.circle_background.show()

        self.noise_overlay = NoiseOverlay(self)
        self.noise_overlay.resize(self.size())
        self.noise_overlay.show()
        self.noise_overlay.raise_()  # <- Esto lo pone sobre todo

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'noise_overlay'):
            self.noise_overlay.resize(self.size())
        if hasattr(self, 'circle_background'):
            self.circle_background.resize(self.size())

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        print(f"Tecla en ventana: {key}, Modificadores: {modifiers}")

        if key == Qt.Key.Key_Escape:
            self.noise_controller.stop()
            self.close()
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.increase_opacity()
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.decrease_opacity()
        elif key == Qt.Key.Key_Up:
            show_previous_zero_line(self)
        elif key == Qt.Key.Key_Down:
            show_next_zero_line(self)

    def increase_opacity(self):
        self.opacity = min(1.0, self.opacity + 0.1)
        self.setWindowOpacity(self.opacity)

    def decrease_opacity(self):
        self.opacity = max(0.0, self.opacity - 0.1)
        self.setWindowOpacity(self.opacity)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FullscreenCircleApp()
    window.show()
    sys.exit(app.exec())
