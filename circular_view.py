from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QFontMetrics, QFont

class CircularView(QWidget):
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self._offset = 0.0
        self.line_height = 38
        self.visible_count = 9
        self.max_alpha = 1.0
        self.min_alpha = 0.15
        self.current_animation = None
        self.edit_mode = False  # Nuevo: modo edición
        
        # Crear el editor (invisible por defecto)
        self.editor = QLineEdit(self)
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("""
            QLineEdit {
                background-color: black;
                color: white;
                border: none;
                qproperty-alignment: AlignCenter;
                selection-background-color: white;
                selection-color: black;
            }
        """)
        self.editor.hide()
        self.editor.returnPressed.connect(self.save_edit)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()

    def animate_move(self, delta):
        """Anima el movimiento del scroll (solo en modo scroll)"""
        if self.edit_mode:
            return  # No scroll en modo edición
            
        if self.current_animation and self.current_animation.state() == QPropertyAnimation.State.Running:
            return
        
        anim = QPropertyAnimation(self, b"offset")
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.setStartValue(self._offset)
        anim.setEndValue(self._offset - delta)
        
        def on_finished():
            self.ring.move(delta)
            self._offset = 0.0
            self.update()
            self.current_animation = None
        
        anim.finished.connect(on_finished)
        anim.start()
        self.current_animation = anim

    def enter_edit_mode(self):
        """Activa modo edición"""
        self.edit_mode = True
        
        # Posicionar el editor en el centro
        center_y = self.height() // 2
        editor_width = min(self.width() - 100, 800)
        self.editor.setFixedWidth(editor_width)
        self.editor.move((self.width() - editor_width) // 2, 
                         center_y - self.editor.height() // 2)
        
        # Cargar texto actual
        current_text = self.ring.current()
        self.editor.setText(current_text)
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()
        
        self.update()  # Redibujar para ocultar otras líneas

    def save_edit(self):
        """Guarda la edición y vuelve a modo scroll"""
        new_text = self.editor.text().strip()
        
        if new_text:  # Solo guardar si hay texto
            # Actualizar la línea en el ring
            self.ring.lines[self.ring.index] = new_text
        
        self.exit_edit_mode()

    def cancel_edit(self):
        """Cancela la edición sin guardar"""
        self.exit_edit_mode()

    def exit_edit_mode(self):
        """Sale del modo edición"""
        self.edit_mode = False
        self.editor.hide()
        self.setFocus()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self.font())

        w = self.width()
        center_y = self.height() // 2
        half = self.visible_count // 2

        if self.edit_mode:
            # En modo edición: solo mostrar la línea central (muy tenue)
            painter.setOpacity(0.2)
            text = self.ring.current()
            text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
            y = int(center_y - text_rect.height() / 2)
            painter.drawText(0, y, w, text_rect.height(),
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            text)
        else:
            # Modo scroll normal: todas las líneas con fade
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

    def resizeEvent(self, event):
        """Reposicionar editor si la ventana cambia de tamaño"""
        super().resizeEvent(event)
        if self.edit_mode:
            center_y = self.height() // 2
            editor_width = min(self.width() - 100, 800)
            self.editor.setFixedWidth(editor_width)
            self.editor.move((self.width() - editor_width) // 2, 
                             center_y - self.editor.height() // 2)