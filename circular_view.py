from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QFontMetrics

class CircularView(QWidget):
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self._offset = 0.0
        self.line_height = 38          # ajusta según tu fuente
        self.visible_count = 9         # impares → centro limpio
        self.max_alpha = 1.0
        self.min_alpha = 0.15
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()

    def animate_move(self, delta):
        anim = QPropertyAnimation(self, b"offset")
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.setStartValue(self._offset)
        anim.setEndValue(self._offset - delta)  # -delta → sube al mover "abajo"
        anim.finished.connect(lambda: [
            self.ring.move(delta),
            setattr(self, '_offset', 0.0),
            self.update()
        ])
        anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self.font())

        w = self.width()
        center_y = self.height() // 2
        half = self.visible_count // 2

        for i in range(-half, half + 1):
            dist = abs(i + self._offset)
            alpha = max(self.min_alpha, self.max_alpha - dist * 0.28)
            painter.setOpacity(alpha)

            text = self.ring.get(i)
            text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)

            y = int(center_y + (i + self._offset) * self.line_height - text_rect.height() / 2)
            painter.drawText(0, y, w, text_rect.height(),
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            text)