# --- new_interface.py ---
import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QLabel, QWidget
from PyQt6.QtGui import QColor, QPainter, QFont, QCursor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer
from files import setup_file_handling, void_line
from controls import setup_controls, show_random_line_from_current_file, show_previous_current_file_line, show_next_current_file_line 
from noise_controls import NoiseController

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key.Key_0:
            # If no slash in the current QLineEdit text, trigger shuffle
            if '/' not in self.text(): 
                print("Key 0 detected in QLineEdit without slash, executing show_random_line_from_current_file") 
                self.parent.last_inserted_index = None 
                show_random_line_from_current_file(self.parent, event)
                event.accept() # Consume the event so '0' isn't written
            else:
                # If there's a slash, allow '0' to be written normally
                super().keyPressEvent(event) 
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
            painter.setOpacity(0.09)  # More visible 
            painter.drawPixmap(0, 0, self.noise_pixmap)

class FullscreenCircleApp(QMainWindow):
    def __init__(self, read_dir=None, void_dir=None, file_to_open=None):
        super().__init__()
        self.opacity = 1.0
        self.read_dir = read_dir
        self.void_dir = void_dir
        self.file_to_open = file_to_open
        self.txt_files = []  # List to store .txt files in the directory
        self.current_file_index = 0  # Index of the current file in txt_files
        
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
        # Set the current file path based on file_to_open
        if self.file_to_open:
            self.current_file_path = self.file_to_open
        else:
            self.current_file_path = os.path.join(self.void_dir, '0.txt')
        
        self.void_file_path = os.path.join(self.void_dir, '0.txt')  # Keep reference to 0.txt
        print(f"void_file_path (0.txt): {self.void_file_path}")
        print(f"current_file_path (active file): {self.current_file_path}")
        
        # Scan the directory for .txt files
        self.scan_txt_files()
        
        self.current_active_line = None 
        self.current_active_line_index = None 
        self.last_inserted_index = None 
        setup_file_handling(self)  # This will ensure the file exists
        setup_controls(self)

    def scan_txt_files(self):
        """Scans the directory of the current file for .txt files and stores them in txt_files."""
        dir_path = os.path.dirname(self.current_file_path)
        self.txt_files = [
            os.path.join(dir_path, f) for f in os.listdir(dir_path)
            if f.lower().endswith('.txt') and os.path.isfile(os.path.join(dir_path, f))
        ]
        self.txt_files.sort()  # Sort alphabetically for consistent navigation
        if self.current_file_path in self.txt_files:
            self.current_file_index = self.txt_files.index(self.current_file_path)
        else:
            self.txt_files.append(self.current_file_path)
            self.txt_files.sort()
            self.current_file_index = self.txt_files.index(self.current_file_path)
        print(f"Found {len(self.txt_files)} .txt files in {dir_path}: {self.txt_files}")

    def switch_to_file(self, file_path):
        """Switches the active file to the specified file_path and resets state."""
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"Created file: {file_path}")
        
        self.current_file_path = file_path
        self.current_file_index = self.txt_files.index(file_path)
        self.current_active_line = None
        self.current_active_line_index = None
        self.last_inserted_index = None
        self.entry.clear()
        print(f"Switched to file: {os.path.basename(file_path)}, Index: {self.current_file_index}")

    def show_previous_file(self):
        """Switches to the previous .txt file in the list."""
        if not self.txt_files:
            print("No .txt files available to navigate.")
            return
        self.current_file_index = (self.current_file_index - 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def show_next_file(self):
        """Switches to the next .txt file in the list."""
        if not self.txt_files:
            print("No .txt files available to navigate.")
            return
        self.current_file_index = (self.current_file_index + 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

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
        self.noise_overlay.raise_() # Put it on top of everything

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'noise_overlay'):
            self.noise_overlay.resize(self.size()) 
        if hasattr(self, 'circle_background'):
            self.circle_background.resize(self.size())

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        print(f"Key in window: {key}, Modifiers: {modifiers}")

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
            show_previous_current_file_line(self) # Updated for active file
        elif key == Qt.Key.Key_Down:
            show_next_current_file_line(self) # Updated for active file

    def increase_opacity(self):
        self.opacity = min(1.0, self.opacity + 0.1)
        self.setWindowOpacity(self.opacity)

    def decrease_opacity(self):
        self.opacity = max(0.0, self.opacity - 0.1)
        self.setWindowOpacity(self.opacity)