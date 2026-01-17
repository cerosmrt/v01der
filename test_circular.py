from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QFontMetrics
import sys, os

class LineRing:
    def __init__(self, lines=None):
        self.lines = list(lines) if lines else [""]
        self.index = 0

    def move(self, delta):
        if self.lines:
            self.index = (self.index + delta) % len(self.lines)

    def get(self, offset=0):
        if not self.lines: return ""
        return self.lines[(self.index + offset) % len(self.lines)]

class CircularView(QWidget):
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self._offset = 0.0
        self.line_height = 38
        self.visible_count = 9
        self.max_alpha = 1.0
        self.min_alpha = 0.15

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
        anim.setEndValue(self._offset - delta)
        anim.finished.connect(lambda: [self.ring.move(delta), setattr(self, '_offset', 0.0), self.update()])
        anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self.font())

        w, h = self.width(), self.height()
        center_y = h // 2
        half = self.visible_count // 2

        for i in range(-half, half + 1):
            dist = abs(i + self._offset)
            alpha = max(self.min_alpha, self.max_alpha - dist * 0.28)
            painter.setOpacity(alpha)

            text = self.ring.get(i)
            rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
            y = int(center_y + (i + self._offset) * self.line_height - rect.height() / 2)
            painter.drawText(0, y, w, rect.height(),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    file_path = r"Z:\programming\Voider\V2\V01DER\void\0.txt"

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    except:
        lines = ["Error leyendo 0.txt", "(archivo vacío o no existe)"]

    window = QMainWindow()
    window.setStyleSheet("background: black; color: white;")
    window.setWindowTitle("Circular Test")

    ring = LineRing(lines or ["(vacío)"])
    view = CircularView(ring, window)
    window.setCentralWidget(view)

    window.showFullScreen()
    sys.exit(app.exec())