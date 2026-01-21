# new_interface.py - App principal con sistema de 3 vistas sincronizadas
import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt

from files import setup_file_handling, void_line
from controls import setup_controls, show_previous_current_file_line, show_next_current_file_line
from noise_controls import NoiseController
from line_ring import LineRing
from circular_view import CircularView
from widgets import CustomLineEdit, NoiseOverlay
from views import NormalView, VersesView, sync_ring_with_file


class FullscreenCircleApp(QMainWindow):
    """Aplicación principal fullscreen con 3 vistas (F1/F2/F3) sincronizadas"""
    
    def __init__(self, read_dir=None, void_dir=None, file_to_open=None):
        super().__init__()
        
        # Configuración inicial
        self.opacity = 1.0
        self.read_dir = read_dir
        self.void_dir = void_dir
        self.file_to_open = file_to_open
        self.txt_files = []
        self.current_file_index = 0
        self.current_view = 0  # 0=F1, 1=F2, 2=F3
        self.use_spacebar_for_void = False
        
        # Configuración de ventana
        self.setWindowTitle("Voider")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self.setStyleSheet("background-color: black; color: white;")

        # Entry de texto personalizado
        self.entry = CustomLineEdit(self)
        self.entry.setFont(QFont("Consolas", 11))
        self.entry.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: white;
                border: none;
                selection-background-color: white;
                selection-color: black;
            }
        """)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.setFocus()

        # Controlador de ruido audio
        self.noise_controller = NoiseController(
            block_size=1024, volume=0.3, noise_type='brown',
            bitcrush={'bit_depth': 10, 'sample_rate_factor': 0.7},
            lfo_min_freq=0.03, lfo_max_freq=0.1, glitch_prob=0.005, cutoff_freq=2500
        )

        # Ring de líneas (estructura de datos central)
        self.line_ring = LineRing()

        # Stack de vistas
        self.stack = QStackedWidget()
        self.normal_view = NormalView(self)
        self.circular_view = None  # Se crea lazy
        self.verses_view = None    # Se crea lazy
        self.stack.addWidget(self.normal_view)

        # Setup lógico de voider
        self.setup_voider_logic()
        
        # Configuración de tecla void (Enter o Spacebar)
        self._print_void_mode_status()
        self._void_enter_connection = None
        self._void_space_connection = None
        self._connect_void_key()
        
        # Inicializar UI
        self.init_ui()
        
        # Empezar en F1 con entry vacío
        self.switch_to_view(0)
        self.entry.clear()

    def _print_void_mode_status(self):
        """Imprime el modo de void actual"""
        print("VOID MODE:", "Spacebar" if self.use_spacebar_for_void else "Enter")

    def _connect_void_key(self):
        """Conecta la tecla de void (Enter o Spacebar)"""
        self._disconnect_void_key()
        if self.use_spacebar_for_void:
            self._void_space_connection = self.entry.spacePressed.connect(lambda: void_line(self))
        else:
            self._void_enter_connection = self.entry.returnPressed.connect(lambda: void_line(self))

    def _disconnect_void_key(self):
        """Desconecta las señales de void anteriores"""
        if self._void_enter_connection:
            try: 
                self.entry.returnPressed.disconnect(self._void_enter_connection)
            except: 
                pass
            self._void_enter_connection = None
        if self._void_space_connection:
            try: 
                self.entry.spacePressed.disconnect(self._void_space_connection)
            except: 
                pass
            self._void_space_connection = None

    def toggle_void_key_mode(self):
        """Alterna entre Enter y Spacebar como tecla de void"""
        self.use_spacebar_for_void = not self.use_spacebar_for_void
        self._print_void_mode_status()
        self._connect_void_key()

    def switch_to_view(self, view_index):
        """
        Cambia entre vistas F1/F2/F3 PRESERVANDO el índice del ring.
        Esta es la función clave para la sincronización.
        """
        old_view = self.current_view
        self.current_view = view_index
        
        # Sincronizar ring con archivo (preserva índice si es posible)
        sync_ring_with_file(self)
        
        print(f"📍 F{old_view+1} → F{view_index+1} | Índice: {self.line_ring.index} | Línea: '{self.line_ring.current()}'")

        if view_index == 0:  # F1 - Vista normal con círculo
            self.stack.setCurrentWidget(self.normal_view)
            self.entry.show()
            self.entry.raise_()
            
            # Mostrar la línea actual del ring en el entry
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            self.entry.setFocus()

        elif view_index == 1:  # F2 - Vista circular
            # Crear vista circular si no existe
            if not self.circular_view:
                self.circular_view = CircularView(self.line_ring, self)
                self.circular_view.setFont(QFont("Consolas", 11))
                self.circular_view.line_saved.connect(self.auto_save_circular)
                self.stack.addWidget(self.circular_view)
            else:
                # Actualizar referencia al ring (mantiene índice)
                self.circular_view.ring = self.line_ring

            self.stack.setCurrentWidget(self.circular_view)
            self.entry.hide()
            self.circular_view.setFocus()
            self.circular_view.update()

        elif view_index == 2:  # F3 - Vista de versos
            # Crear vista de versos si no existe
            if not self.verses_view:
                self.verses_view = VersesView(self.line_ring, self)
                self.stack.addWidget(self.verses_view)
            else:
                # Actualizar referencia al ring (mantiene índice)
                self.verses_view.ring = self.line_ring

            verses = self.verses_view.calculate_verses()
            verse_idx = self.verses_view.find_current_verse()
            print(f"   └─ Verso {verse_idx+1}/{len(verses)}")

            self.stack.setCurrentWidget(self.verses_view)
            self.entry.hide()
            self.verses_view.setFocus()
            self.verses_view.update()

    def auto_save_circular(self):
        """Guarda cambios desde F2 y resincroniza el ring"""
        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                for line in self.line_ring.lines:
                    f.write(line + '\n')
            print(f"💾 Guardado desde F2 (índice={self.line_ring.index})")
            # Re-sincronizar después de guardar
            sync_ring_with_file(self)
        except Exception as e:
            print(f"❌ Error al guardar: {e}")

    def setup_voider_logic(self):
        """Inicializa la lógica de voider (archivos, controles)"""
        self.current_file_path = self.file_to_open or os.path.join(self.void_dir, '0.txt')
        self.void_file_path = os.path.join(self.void_dir, '0.txt')
        self.scan_txt_files()
        setup_file_handling(self)
        setup_controls(self)

    def scan_txt_files(self):
        """Escanea archivos .txt en el directorio void"""
        dir_path = os.path.dirname(self.current_file_path)
        self.txt_files = [
            os.path.join(dir_path, f) 
            for f in os.listdir(dir_path)
            if f.lower().endswith('.txt') and os.path.isfile(os.path.join(dir_path, f))
        ]
        self.txt_files.sort()
        
        if self.current_file_path in self.txt_files:
            self.current_file_index = self.txt_files.index(self.current_file_path)
        else:
            self.txt_files.append(self.current_file_path)
            self.txt_files.sort()
            self.current_file_index = self.txt_files.index(self.current_file_path)

    def switch_to_file(self, file_path):
        """Cambia al archivo especificado y resetea índice al inicio"""
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('')
        
        self.current_file_path = file_path
        self.current_file_index = self.txt_files.index(file_path)
        self.entry.clear()
        
        # Resetear índice al cambiar de archivo
        self.line_ring.index = 0
        print(f"📂 Archivo: {os.path.basename(file_path)}")
        sync_ring_with_file(self)
        
        # Actualizar vista actual
        self.switch_to_view(self.current_view)

    def show_previous_file(self):
        """Alt+Up: Archivo anterior"""
        if not self.txt_files: 
            return
        self.current_file_index = (self.current_file_index - 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def show_next_file(self):
        """Alt+Down: Archivo siguiente"""
        if not self.txt_files: 
            return
        self.current_file_index = (self.current_file_index + 1) % len(self.txt_files)
        self.switch_to_file(self.txt_files[self.current_file_index])

    def init_ui(self):
        """Inicializa la interfaz gráfica"""
        self.showFullScreen()
        screen = self.screen().availableGeometry()
        center_x = screen.width() // 2
        center_y = screen.height() // 2
        radius = min(screen.width(), screen.height()) // 2 - 35
        entry_width = radius * 2 - 40
        self.entry.setFixedWidth(entry_width)
        self.entry.move(center_x - entry_width // 2, center_y - self.entry.height() // 2)

        self.setCentralWidget(self.stack)
        
        # Overlay de ruido visual
        self.noise_overlay = NoiseOverlay(self)
        self.noise_overlay.resize(self.size())
        self.noise_overlay.show()
        self.noise_overlay.raise_()

    def resizeEvent(self, event):
        """Maneja redimensionamiento de ventana"""
        super().resizeEvent(event)
        if hasattr(self, 'noise_overlay'):
            self.noise_overlay.resize(self.size())

        screen = self.screen().availableGeometry()
        center_x = screen.width() // 2
        center_y = screen.height() // 2
        entry_width = min(screen.width(), screen.height()) - 90
        self.entry.setFixedWidth(entry_width)
        self.entry.move(center_x - entry_width // 2, center_y - self.entry.height() // 2)

    def keyPressEvent(self, event):
        """Router principal de eventos de teclado"""
        key = event.key()
        modifiers = event.modifiers()

        # Cambio de vistas - GLOBAL para todas
        if key == Qt.Key.Key_F1:
            self.switch_to_view(0)
            event.accept()
            return
        elif key == Qt.Key.Key_F2:
            self.switch_to_view(1)
            event.accept()
            return
        elif key == Qt.Key.Key_F3:
            self.switch_to_view(2)
            event.accept()
            return

        # Eventos específicos por vista
        if self.current_view == 0:  # F1
            self._handle_f1_keys(key, modifiers)
        elif self.current_view == 1:  # F2
            self._handle_f2_keys(key, modifiers, event)
        elif self.current_view == 2:  # F3
            self._handle_f3_keys(key, modifiers)

    def _handle_f1_keys(self, key, modifiers):
        """Manejo de teclas en vista F1"""
        if key == Qt.Key.Key_Escape:
            self.noise_controller.stop()
            self.close()
        
        # Ctrl+Up/Down: Opacidad
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.opacity = min(1.0, self.opacity + 0.1)
            self.setWindowOpacity(self.opacity)
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.opacity = max(0.0, self.opacity - 0.1)
            self.setWindowOpacity(self.opacity)
        
        # Alt+Up/Down: Cambiar archivo
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_previous_file()
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_next_file()
        
        # Up/Down: Navegar líneas (mueve índice del ring)
        elif key == Qt.Key.Key_Up:
            self.line_ring.move(-1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            print(f"⬆️ F1: Índice={self.line_ring.index}")
        elif key == Qt.Key.Key_Down:
            self.line_ring.move(1)
            self.entry.setText(self.line_ring.current())
            self.entry.setCursorPosition(0)
            print(f"⬇️ F1: Índice={self.line_ring.index}")

    def _handle_f2_keys(self, key, modifiers, event):
        """Manejo de teclas en vista F2"""
        if self.circular_view.edit_mode:
            if key == Qt.Key.Key_Escape:
                self.circular_view.cancel_edit()
                event.accept()
        else:
            if key == Qt.Key.Key_Up:
                self.circular_view.animate_move(-1)
                print(f"⬆️ F2: Índice={self.line_ring.index}")
                event.accept()
            elif key == Qt.Key.Key_Down:
                self.circular_view.animate_move(1)
                print(f"⬇️ F2: Índice={self.line_ring.index}")
                event.accept()
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.circular_view.enter_edit_mode()
                event.accept()
            elif key == Qt.Key.Key_Escape:
                self.switch_to_view(0)

    def _handle_f3_keys(self, key, modifiers):
        """Manejo de teclas en vista F3"""
        if key == Qt.Key.Key_Escape:
            self.noise_controller.stop()
            self.close()
        
        # Ctrl+Up/Down: Opacidad
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.opacity = min(1.0, self.opacity + 0.1)
            self.setWindowOpacity(self.opacity)
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.opacity = max(0.0, self.opacity - 0.1)
            self.setWindowOpacity(self.opacity)
        
        # Alt+Up/Down: Cambiar archivo
        elif key == Qt.Key.Key_Up and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_previous_file()
        elif key == Qt.Key.Key_Down and modifiers == Qt.KeyboardModifier.AltModifier:
            self.show_next_file()
        
        # Up/Down: Navegar versos (actualiza índice del ring)
        elif key == Qt.Key.Key_Up:
            verses = self.verses_view.calculate_verses()
            current = self.verses_view.find_current_verse()
            new_verse = (current - 1) % len(verses)
            self.line_ring.index = verses[new_verse]['start']
            self.verses_view.update()
            print(f"⬆️ F3: Verso {new_verse+1}/{len(verses)} | Índice={self.line_ring.index}")
        elif key == Qt.Key.Key_Down:
            verses = self.verses_view.calculate_verses()
            current = self.verses_view.find_current_verse()
            new_verse = (current + 1) % len(verses)
            self.line_ring.index = verses[new_verse]['start']
            self.verses_view.update()
            print(f"⬇️ F3: Verso {new_verse+1}/{len(verses)} | Índice={self.line_ring.index}")
        
        # Enter: Ir a F2 para editar la línea actual
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            print(f"↩️ F3→F2: Editando índice={self.line_ring.index}")
            self.switch_to_view(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    read_directory = 'read_potential'
    void_directory = 'void_potential'
    os.makedirs(read_directory, exist_ok=True)
    os.makedirs(void_directory, exist_ok=True)
    window = FullscreenCircleApp(read_dir=read_directory, void_dir=void_directory)
    sys.exit(app.exec())