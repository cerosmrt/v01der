class LineRing:
    def __init__(self, lines=None):
        self.lines = list(lines) if lines else [""]
        self.index = 0

    def current(self):
        return self.lines[self.index]

    def move(self, delta):
        if not self.lines:
            return
        self.index = (self.index + delta) % len(self.lines)

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