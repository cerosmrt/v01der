import math
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QFontMetrics, QFont, QKeyEvent

class CircularView(QWidget):
    line_saved = pyqtSignal()
    
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self._offset = 0.0
        self.line_height = 38
        
        self.max_alpha = 1.0
        self.min_alpha = 0.0
        
        self.circle_radius = 0
        self.current_animation = None
        self.edit_mode = False
        
        # Crear el editor
        self.editor = CustomLineEdit(self)
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
        if self.edit_mode:
            return
            
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
        self.edit_mode = True
        
        center_y = self.height() // 2
        editor_width = min(self.width() - 100, 800)
        self.editor.setFixedWidth(editor_width)
        self.editor.move((self.width() - editor_width) // 2, 
                         center_y - self.editor.height() // 2)
        
        current_text = self.ring.current()
        self.editor.setText(current_text)
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()
        
        self.update()

    def save_edit(self):
        new_text = self.editor.text().strip()
        
        if new_text:
            self.ring.lines[self.ring.index] = new_text
            print(f"✅ Línea actualizada: {new_text}")
            self.line_saved.emit()
        
        self.exit_edit_mode()

    def cancel_edit(self):
        self.exit_edit_mode()

    def exit_edit_mode(self):
        self.edit_mode = False
        self.editor.hide()
        self.setFocus()
        self.update()

    def calculate_alpha(self, distance_from_center_px):
        # 1. Distancia en unidades de línea
        dist = distance_from_center_px / self.line_height
        
        # 2. Función de Cauchy / Racional
        # El '+ 1' asegura que en el centro (dist=0) el alpha sea 1.0
        # El '1.5' es el factor de caída. 
        # Si querés que el degradado sea MÁS LARGO todavía, bajá el 1.5 a 1.0 o 0.8
        alpha = 1.0 / (1.0 + 1.5 * (dist ** 2))
        
        # Ajustamos el mínimo para que no desaparezcan tan rápido
        return max(0.02, min(self.max_alpha, alpha))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self.font())

        w = self.width()
        h = self.height()
        center_y = h // 2
        
        if self.edit_mode:
            painter.setOpacity(0.2)
            text = self.ring.current()
            text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
            y = int(center_y - text_rect.height() / 2)
            painter.drawText(0, y, w, text_rect.height(),
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            text)
        else:
            # Renderizar suficientes líneas
            if self.circle_radius > 0:
                max_lines = int(self.circle_radius / self.line_height) + 3
            else:
                max_lines = 20
            
            for i in range(-max_lines, max_lines + 1):
                # Calculamos la posición base con el offset de la animación
                y_pos = center_y + (i + self._offset) * self.line_height
                
                text = self.ring.get(i)
                text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
                
                # Coordenada Y donde se dibuja el texto
                draw_y = int(y_pos - text_rect.height() / 2)
                
                # La distancia al centro la medimos desde el centro de la línea
                distance_from_center = abs(y_pos - center_y)
                
                # Calcular alpha armónico
                alpha = self.calculate_alpha(distance_from_center)
                
                if alpha < 0.01:
                    continue
                
                painter.setOpacity(alpha)
                painter.drawText(0, draw_y, w, text_rect.height(),
                                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                                text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        screen_width = self.width()
        screen_height = self.height()
        self.circle_radius = min(screen_width, screen_height) // 2 - 35
        
        if self.edit_mode:
            center_y = self.height() // 2
            editor_width = min(self.width() - 100, 800)
            self.editor.setFixedWidth(editor_width)
            self.editor.move((self.width() - editor_width) // 2, 
                             center_y - self.editor.height() // 2)
        self.update()


class CustomLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.returnPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)