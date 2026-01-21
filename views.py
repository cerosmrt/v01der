# views.py - Vistas F1, F2, F3 con sincronización de índice
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QPainter, QFont, QPen
from PyQt6.QtCore import Qt


class NormalView(QWidget):
    """Vista F1: Círculo minimalista con entrada de texto central"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setStyleSheet("background: black;")

    def paintEvent(self, event):
        """Dibuja un círculo blanco centrado"""
        if not self.parent_app:
            return
        if self.width() == 0 or self.height() == 0:
            return
            
        painter = QPainter(self)
        if not painter.isActive():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("white"), 10)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        w = self.width()
        h = self.height()
        center_x = w // 2
        center_y = h // 2
        radius = min(w, h) // 2 - 35
        
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)


class VersesView(QWidget):
    """Vista F3: Muestra versos/párrafos separados por puntos"""
    
    def __init__(self, ring, parent=None):
        super().__init__(parent)
        self.ring = ring
        self.verses = []
        self.current_verse_index = 0
        self.setStyleSheet("background: black; color: white;")

    def calculate_verses(self):
        """
        Calcula los versos basándose en puntos '.' como separadores.
        Retorna lista de dicts con 'lines', 'start', 'end'.
        """
        verses = []
        current_verse = []
        start_index = 0
        
        for idx, line in enumerate(self.ring.lines):
            if line.strip() == '.':
                if current_verse:
                    verses.append({
                        'lines': current_verse, 
                        'start': start_index, 
                        'end': idx - 1
                    })
                    current_verse = []
                start_index = idx + 1
            else:
                current_verse.append(line)
        
        # Último verso si no termina con punto
        if current_verse:
            verses.append({
                'lines': current_verse, 
                'start': start_index, 
                'end': len(self.ring.lines) - 1
            })
        
        # Fallback si no hay versos
        if not verses:
            verses.append({'lines': [""], 'start': 0, 'end': 0})
        
        return verses

    def find_current_verse(self):
        """Encuentra qué verso contiene el índice actual del ring"""
        for idx, verse in enumerate(self.verses):
            if verse['start'] <= self.ring.index <= verse['end']:
                return idx
        return 0

    def paintEvent(self, event):
        """Dibuja todos los versos con el actual centrado y resaltado"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = QFont("Consolas", 11)
        painter.setPen(QColor("white"))
        
        w = self.width()
        h = self.height()
        line_height = 25
        verse_spacing = 60

        # Calcular versos y encontrar el actual
        self.verses = self.calculate_verses()
        self.current_verse_index = self.find_current_verse()

        # Centrar verticalmente el verso actual
        y_offset = h // 2 - (self.current_verse_index * (line_height * 5 + verse_spacing))

        for verse_idx, verse in enumerate(self.verses):
            is_current = (verse_idx == self.current_verse_index)
            verse_y = y_offset

            # Estilo diferente para verso actual vs otros
            if is_current:
                painter.setOpacity(1.0)
                font.setPointSize(12)
            else:
                painter.setOpacity(0.3)
                font.setPointSize(10)

            painter.setFont(font)

            # Dibujar cada línea del verso
            for line_idx, line in enumerate(verse['lines']):
                text_y = verse_y + (line_idx * line_height)
                
                # Calcular índice global de la línea
                line_global_index = verse['start'] + line_idx
                is_exact_line = (line_global_index == self.ring.index)

                # Resaltar la línea exacta del índice actual
                if is_current and is_exact_line:
                    painter.setOpacity(1.0)
                    painter.setPen(QColor("yellow"))
                    painter.drawLine(50, text_y, 50, text_y + line_height - 5)
                    painter.setPen(QColor("white"))
                elif is_current:
                    painter.setOpacity(1.0)
                    painter.setPen(QColor("white"))
                    painter.drawLine(50, text_y, 50, text_y + line_height - 5)
                else:
                    painter.setOpacity(0.3)
                    painter.setPen(QColor("white"))

                # Dibujar texto centrado
                painter.drawText(0, text_y, w, line_height,
                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                                line)

            y_offset += len(verse['lines']) * line_height + verse_spacing


def sync_ring_with_file(app):
    """
    Sincroniza el line_ring con el archivo actual, preservando el índice.
    Los puntos SÍ se cargan (son visibles), pero se saltean al navegar.
    """
    try:
        with open(app.current_file_path, 'r', encoding='utf-8') as f:
            # Cargar TODAS las líneas incluyendo puntos
            lines = [l.strip() for l in f if l.strip()]
            
        # Debug: contar puntos
        num_dots = sum(1 for l in lines if l == '.')
        print(f"   📊 Líneas cargadas: {len(lines)} (incluyendo {num_dots} puntos)")
    except Exception as e:
        print(f"⚠️ Error leyendo archivo: {e}")
        lines = []

    # Preservar índice si existe y es válido
    old_index = app.line_ring.index if app.line_ring and hasattr(app.line_ring, 'index') else 0
    
    # Crear nuevo ring con TODAS las líneas (puntos incluidos)
    from line_ring import LineRing
    app.line_ring = LineRing(lines or [""])
    
    # Restaurar índice si sigue siendo válido
    if old_index < len(app.line_ring.lines):
        app.line_ring.index = old_index
    else:
        app.line_ring.index = max(0, len(app.line_ring.lines) - 1)
    
    print(f"🔄 Ring sincronizado: {len(app.line_ring.lines)} líneas, índice={app.line_ring.index}")
    return app.line_ring