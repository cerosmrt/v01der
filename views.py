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
        self._cached_ring_lines = None  # Cache para detectar cambios
        self.setStyleSheet("background: black; color: white;")
    
    def recalculate_verses_if_needed(self):
        """Solo recalcula si el ring cambió"""
        if self._cached_ring_lines != self.ring.lines:
            self.verses = self.calculate_verses()
            self._cached_ring_lines = self.ring.lines[:]
            print(f"🔍 Calculados {len(self.verses)} bloques")
        self.current_verse_index = self.find_current_verse()

    def calculate_verses(self):
        """
        Calcula los versos basándose en puntos '.' como separadores.
        SOLO '.' es separador válido. Todo lo demás es contenido normal.
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

        # Usar cache en vez de recalcular siempre
        self.recalculate_verses_if_needed()

        # Calcular altura acumulada hasta el bloque actual
        height_before_current = 0
        for idx in range(self.current_verse_index):
            verse_height = len(self.verses[idx]['lines']) * line_height
            height_before_current += verse_height + verse_spacing
        
        # Altura del bloque actual
        current_verse_height = len(self.verses[self.current_verse_index]['lines']) * line_height
        
        # Centrar: poner el MEDIO del bloque actual en h//2
        y_offset = h // 2 - height_before_current - (current_verse_height // 2)

        for verse_idx, verse in enumerate(self.verses):
            is_current = (verse_idx == self.current_verse_index)
            verse_y = y_offset

            # TODO el bloque actual se resalta, no solo una línea
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

                # Resaltar TODO el bloque actual
                if is_current:
                    painter.setOpacity(1.0)
                    painter.setPen(QColor("white"))
                    # Línea vertical para TODO el bloque
                    painter.drawLine(50, text_y, 50, text_y + line_height - 5)
                else:
                    painter.setOpacity(0.3)
                    painter.setPen(QColor("white"))

                # Dibujar texto centrado
                painter.drawText(0, text_y, w, line_height,
                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                                line)

            # Avanzar offset DESPUÉS del verso
            y_offset += len(verse['lines']) * line_height
            
            # Dibujar punto separador DESPUÉS del verso (si no es el último)
            if verse_idx < len(self.verses) - 1:
                dot_y = y_offset + verse_spacing // 2
                painter.setOpacity(0.5)  # Puntos con opacidad media
                painter.drawText(0, dot_y, w, line_height,
                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                                ".")
            
            # Añadir espacio después del punto
            y_offset += verse_spacing


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
    
    # CRÍTICO: Si después de sincronizar estamos en un punto, avanzar
    if app.line_ring.lines and app.line_ring.current().strip() == '.':
        print(f"   ⚠️ Índice apunta a punto, avanzando...")
        app.line_ring.move(1)  # Esto saltea puntos automáticamente
    
    print(f"🔄 Ring sincronizado: {len(app.line_ring.lines)} líneas, índice={app.line_ring.index}")
    return app.line_ring