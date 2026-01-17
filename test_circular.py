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

        # Cargar archivo 0.txt - probar múltiples rutas posibles
        possible_paths = [
            os.path.join("void_potential", "0.txt"),
            os.path.join("void", "0.txt"),
            "0.txt",
            os.path.join(os.path.dirname(__file__), "void_potential", "0.txt"),
            os.path.join(os.path.dirname(__file__), "void", "0.txt"),
        ]
        
        lines = None
        file_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        lines = [l.strip() for l in f if l.strip()]
                    file_path = path
                    print(f"✅ Archivo cargado: {path}")
                    break
                except Exception as e:
                    print(f"❌ Error leyendo {path}: {e}")
        
        # Si no se encontró ningún archivo, usar líneas de ejemplo
        if lines is None or not lines:
            lines = [
                "Bienvenido a Circular View",
                "No se encontró 0.txt",
                "Estas son líneas de ejemplo",
                "Usá ↑ y ↓ para navegar",
                "ESC para salir",
                "Creá void_potential/0.txt para ver tu contenido",
                "O void/0.txt también funciona",
                "El scroll es suave y circular",
                "Las líneas se repiten infinitamente"
            ]
            print(f"⚠️ Usando líneas de ejemplo. Creá uno de estos archivos:")
            for path in possible_paths[:3]:
                print(f"   - {path}")

        # Crear ring y vista
        self.ring = LineRing(lines)
        self.view = CircularView(self.ring, self)
        
        # Configurar fuente
        font = QFont("Consolas", 11)
        self.view.setFont(font)
        
        self.setCentralWidget(self.view)
        
        # Fullscreen
        self.showFullScreen()

    def keyPressEvent(self, event):
        """Captura las teclas de navegación"""
        key = event.key()
        
        if key == Qt.Key.Key_Up:
            self.view.animate_move(-1)  # Scroll hacia arriba (línea anterior)
            event.accept()
        elif key == Qt.Key.Key_Down:
            self.view.animate_move(1)   # Scroll hacia abajo (línea siguiente)
            event.accept()
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())