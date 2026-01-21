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
        self.insert_mode = False  # Nueva: modo insertar línea debajo
        
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
        
        # Animación simple - el move() del ring ya maneja el skip de puntos
        anim = QPropertyAnimation(self, b"offset")
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.setStartValue(self._offset)
        anim.setEndValue(self._offset - delta)
        
        def on_finished():
            self.ring.move(delta)  # Esto ya saltea puntos
            self._offset = 0.0
            self.update()
            self.current_animation = None
        
        anim.finished.connect(on_finished)
        anim.start()
        self.current_animation = anim

    def enter_edit_mode(self):
        """Entra en modo edición de la línea actual"""
        self.edit_mode = True
        self.insert_mode = False
        
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

    def enter_insert_mode(self):
        """Entra en modo insertar nueva línea DEBAJO de la actual"""
        self.edit_mode = True
        self.insert_mode = True
        
        center_y = self.height() // 2
        editor_width = min(self.width() - 100, 800)
        self.editor.setFixedWidth(editor_width)
        
        # Posicionar editor DEBAJO de la línea central (media línea abajo)
        editor_y = center_y + int(self.line_height * 0.6)
        self.editor.move((self.width() - editor_width) // 2, 
                         editor_y - self.editor.height() // 2)
        
        # Editor vacío para nueva línea
        self.editor.setText("")
        self.editor.show()
        self.editor.setFocus()
        
        print("➕ Modo insertar: Nueva línea debajo")
        self.update()

    def save_edit(self):
        new_text = self.editor.text().strip()
        
        if new_text:
            if self.insert_mode:
                # Insertar NUEVA línea debajo de la actual
                self.ring.lines.insert(self.ring.index + 1, new_text)
                # Mover índice a la nueva línea
                self.ring.index += 1
                print(f"➕ Nueva línea insertada: {new_text}")
            else:
                # Editar línea actual
                self.ring.lines[self.ring.index] = new_text
                print(f"✅ Línea actualizada: {new_text}")
            
            self.line_saved.emit()
        
        self.exit_edit_mode()

    def cancel_edit(self):
        self.exit_edit_mode()

    def exit_edit_mode(self):
        self.edit_mode = False
        self.insert_mode = False
        self.editor.hide()
        self.setFocus()
        self.update()

    def calculate_alpha(self, distance_from_center_px):
        # Distancia en unidades de línea
        dist = distance_from_center_px / self.line_height
        
        # Función de Cauchy / Racional
        alpha = 1.0 / (1.0 + 1.5 * (dist ** 2))
        
        return max(0.02, min(self.max_alpha, alpha))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fm = QFontMetrics(self.font())

        w = self.width()
        h = self.height()
        center_y = h // 2
        
        if self.edit_mode:
            # Si estamos en modo edición/inserción, mostrar líneas con opacidad baja
            if self.circle_radius > 0:
                max_lines = int(self.circle_radius / self.line_height) + 3
            else:
                max_lines = 20
            
            for i in range(-max_lines, max_lines + 1):
                y_pos = center_y + (i + self._offset) * self.line_height
                text = self.ring.get(i)
                text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
                draw_y = int(y_pos - text_rect.height() / 2)
                distance_from_center = abs(y_pos - center_y)
                
                # En modo edición, todas las líneas con opacidad media
                alpha = self.calculate_alpha(distance_from_center) * 0.4
                
                if alpha < 0.01:
                    continue
                
                painter.setOpacity(alpha)
                painter.drawText(0, draw_y, w, text_rect.height(),
                                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                                text)
        else:
            # Modo navegación normal
            if self.circle_radius > 0:
                max_lines = int(self.circle_radius / self.line_height) + 3
            else:
                max_lines = 20
            
            for i in range(-max_lines, max_lines + 1):
                y_pos = center_y + (i + self._offset) * self.line_height
                text = self.ring.get(i)
                text_rect = fm.boundingRect(0, 0, w, 1000, Qt.AlignmentFlag.AlignCenter, text)
                draw_y = int(y_pos - text_rect.height() / 2)
                distance_from_center = abs(y_pos - center_y)
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