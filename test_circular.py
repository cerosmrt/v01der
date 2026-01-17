from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
import sys
import os

from line_ring import LineRing
from circular_view import CircularView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circular View Test")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.setStyleSheet("background: black; color: white;")

        # Cargar archivo 0.txt
        possible_paths = [
            os.path.join("void_potential", "0.txt"),
            os.path.join("void", "0.txt"),
            "0.txt",
            os.path.join(os.path.dirname(__file__), "void_potential", "0.txt"),
            os.path.join(os.path.dirname(__file__), "void", "0.txt"),
        ]
        
        lines = None
        self.file_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        lines = [l.strip() for l in f if l.strip()]
                    self.file_path = path
                    print(f"✅ Archivo cargado: {path}")
                    break
                except Exception as e:
                    print(f"❌ Error leyendo {path}: {e}")
        
        if lines is None or not lines:
            lines = [
                "Bienvenido a Circular View",
                "Presiona Enter para editar",
                "Usa ↑ y ↓ para navegar",
                "ESC para salir",
                "Las ediciones se guardan automáticamente"
            ]
            print(f"⚠️ Usando líneas de ejemplo")

        # Crear ring y vista
        self.ring = LineRing(lines)
        self.view = CircularView(self.ring, self)
        
        # Conectar señal de guardado automático
        self.view.line_saved.connect(self.auto_save)
        
        font = QFont("Consolas", 11)
        self.view.setFont(font)
        
        self.setCentralWidget(self.view)
        self.showFullScreen()

    def auto_save(self):
        """Guarda automáticamente después de cada edición"""
        if self.file_path:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    for line in self.ring.lines:
                        f.write(line + '\n')
                print(f"💾 Auto-guardado en {self.file_path}")
            except Exception as e:
                print(f"❌ Error en auto-guardado: {e}")

    def keyPressEvent(self, event):
        """Captura las teclas de navegación y edición"""
        key = event.key()
        
        if self.view.edit_mode:
            # En modo edición, ESC cancela (Enter lo maneja el editor)
            if key == Qt.Key.Key_Escape:
                self.view.cancel_edit()
                event.accept()
        else:
            # En modo scroll
            if key == Qt.Key.Key_Up:
                self.view.animate_move(-1)
                event.accept()
            elif key == Qt.Key.Key_Down:
                self.view.animate_move(1)
                event.accept()
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.view.enter_edit_mode()
                event.accept()
            elif key == Qt.Key.Key_Escape:
                self.save_and_exit()

    def save_and_exit(self):
        """Guardar cambios y salir (por si acaso, aunque ya hay auto-save)"""
        self.auto_save()  # Un último save antes de salir
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())