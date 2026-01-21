# line_ring.py - Estructura circular de líneas con navegación mejorada
class LineRing:
    def __init__(self, lines=None):
        self.lines = list(lines) if lines else [""]
        self.index = 0

    def current(self):
        return self.lines[self.index]

    def move(self, delta):
        """Mueve el índice saltando líneas que son solo puntos '.'"""
        if not self.lines:
            return
        
        # Guardar posición inicial para evitar loops infinitos
        start_index = self.index
        moves = 0
        max_moves = len(self.lines)
        
        while moves < max_moves:
            self.index = (self.index + delta) % len(self.lines)
            moves += 1
            
            # Si la línea no es solo un punto, detener
            if self.lines[self.index].strip() != '.':
                return
            
            # Si todas las líneas son puntos, volver al inicio
            if moves >= max_moves:
                self.index = start_index
                return

    def get(self, offset=0):
        if not self.lines:
            return ""
        return self.lines[(self.index + offset) % len(self.lines)]

    def insert(self, text, after_current=False):
        pos = self.index + 1 if after_current else self.index
        self.lines.insert(pos, text)
        if after_current:
            self.move(1)

    def remove_current(self):
        if len(self.lines) <= 1:
            self.lines = [""]
            self.index = 0
            return
        del self.lines[self.index]
        if self.index >= len(self.lines):
            self.index = len(self.lines) - 1

    def to_list_from_current(self):
        """Para exportar/imprimir con la línea actual primero"""
        return self.lines[self.index:] + self.lines[:self.index]