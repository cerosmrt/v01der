# widgets.py - Widgets reutilizables
import numpy as np
from PyQt6.QtWidgets import QLineEdit, QWidget
from PyQt6.QtGui import QPainter, QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

class CustomLineEdit(QLineEdit):
    """QLineEdit personalizado con soporte para spacebar como tecla de void"""
    spacePressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        # Manejo de spacebar para void
        if key == Qt.Key.Key_Space:
            if self.parent.use_spacebar_for_void:
                self.spacePressed.emit()
                event.accept()
                return
            super().keyPressEvent(event)
            return
        
        # Atajos con Ctrl
        if key == Qt.Key.Key_0 and (modifiers & Qt.KeyboardModifier.ControlModifier):
            from controls import show_random_line_from_random_file
            show_random_line_from_random_file(self.parent, event)
            event.accept()
        elif key == Qt.Key.Key_Period and (modifiers & Qt.KeyboardModifier.ControlModifier):
            from controls import show_random_line_from_current_file
            show_random_line_from_current_file(self.parent, event)
            event.accept()
        else:
            super().keyPressEvent(event)


class NoiseOverlay(QWidget):
    """Overlay de ruido visual generativo en tiempo real"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.noise_pixmap = None
        
        # Timer para generar nuevo ruido cada 50ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.generate_noise)
        self.timer.start(50)
    
    def generate_noise(self):
        """Genera un patrón de ruido aleatorio tipo TV sin señal"""
        block_size = 1
        w, h = self.width(), self.height()
        
        if w == 0 or h == 0:
            return
            
        h_blocks, w_blocks = h // block_size, w // block_size
        noise_gray = np.random.randint(0, 256, (h_blocks, w_blocks), dtype=np.uint8)
        
        image = QImage(noise_gray.data, w_blocks, h_blocks, w_blocks, 
                      QImage.Format.Format_Grayscale8)
        image = image.scaled(w, h, 
                           Qt.AspectRatioMode.IgnoreAspectRatio, 
                           Qt.TransformationMode.FastTransformation)
        
        self.noise_pixmap = QPixmap.fromImage(image)
        self.update()
    
    def paintEvent(self, event):
        """Dibuja el ruido con opacidad baja"""
        if self.noise_pixmap:
            painter = QPainter(self)
            painter.setOpacity(0.09)
            painter.drawPixmap(0, 0, self.noise_pixmap)