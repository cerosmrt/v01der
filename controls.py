# --- controls.py ---
import random
import os
from files import setup_file_handling, void_line
from tools import clean_text
from PyQt6.QtWidgets import QApplication

def setup_controls(app):
    pass  # Los eventos están en keyPressEvent y returnPressed

def show_random_line_from_zero(app, event=None):
    """Muestra una línea aleatoria de 0.txt y guarda su índice para reemplazo."""
    try:
        zero_file_path = app.void_file_path
        print(f"Intentando leer: {zero_file_path}")
        if os.path.exists(zero_file_path):
            with open(zero_file_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f.readlines() if line.strip()]
            if lines:
                app.current_zero_line = random.choice(lines)
                app.current_zero_line_index = lines.index(app.current_zero_line)
                app.entry.setText(app.current_zero_line)
                app.entry.setCursorPosition(0)  # Mover cursor al inicio
                print(f"Random line from 0.txt: {app.current_zero_line}, Index: {app.current_zero_line_index}")
            else:
                print("0.txt está vacío.")
                app.entry.clear()
                app.current_zero_line = None
                app.current_zero_line_index = None
        else:
            print("0.txt no existe.")
            app.entry.clear()
            app.current_zero_line = None
            app.current_zero_line_index = None
    except Exception as e:
        print(f"Error en show_random_line_from_zero: {e}")

def show_previous_zero_line(app, event=None):
    """Muestra la línea previa en 0.txt, con comportamiento circular y contextual."""
    try:
        zero_file_path = app.void_file_path
        print(f"Navegando a línea previa en: {zero_file_path}")
        if not os.path.exists(zero_file_path):
            print("0.txt no existe.")
            app.entry.clear()
            return

        with open(zero_file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f.readlines() if line.strip()]
        
        if not lines:
            print("0.txt está vacío.")
            app.entry.clear()
            app.current_zero_line_index = None
            app.current_zero_line = None
            return

        if not app.entry.text().strip() and app.last_inserted_index is not None:
            app.current_zero_line_index = app.last_inserted_index
            print(f"Entry vacío, mostrando última línea enviada, Index: {app.current_zero_line_index}")
        elif app.current_zero_line_index is None:
            app.current_zero_line_index = len(lines) - 1
            print(f"Sin índice actual, empezando desde la última línea, Index: {app.current_zero_line_index}")
        else:
            app.current_zero_line_index = (app.current_zero_line_index - 1) % len(lines)
            print(f"Navegando a línea previa, Index: {app.current_zero_line_index}")

        app.current_zero_line = lines[app.current_zero_line_index]
        app.entry.setText(app.current_zero_line)
        app.entry.setCursorPosition(0)
        print(f"Previous Line - 0.txt, Index: {app.current_zero_line_index}, Line: {app.current_zero_line}")
    except Exception as e:
        print(f"Error en show_previous_zero_line: {e}")
        app.entry.clear()

def show_next_zero_line(app, event=None):
    """Muestra la línea siguiente en 0.txt, con comportamiento circular."""
    try:
        zero_file_path = app.void_file_path
        print(f"Navegando a línea siguiente en: {zero_file_path}")
        if not os.path.exists(zero_file_path):
            print("0.txt no existe.")
            app.entry.clear()
            return

        with open(zero_file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f.readlines() if line.strip()]
        
        if not lines:
            print("0.txt está vacío.")
            app.entry.clear()
            app.current_zero_line_index = None
            app.current_zero_line = None
            return

        if not app.entry.text().strip() and app.last_inserted_index is not None:
            app.current_zero_line_index = (app.last_inserted_index + 1) % len(lines)
            print(f"Entry vacío, mostrando línea siguiente a la última enviada, Index: {app.current_zero_line_index}")
        elif app.current_zero_line_index is None:
            app.current_zero_line_index = 0
            print(f"Sin índice actual, empezando desde la primera línea, Index: {app.current_zero_line_index}")
        else:
            app.current_zero_line_index = (app.current_zero_line_index + 1) % len(lines)
            print(f"Navegando a línea siguiente, Index: {app.current_zero_line_index}")

        app.current_zero_line = lines[app.current_zero_line_index]
        app.entry.setText(app.current_zero_line)
        app.entry.setCursorPosition(0)
        print(f"Next Line - 0.txt, Index: {app.current_zero_line_index}, Line: {app.current_zero_line}")
    except Exception as e:
        print(f"Error en show_next_zero_line: {e}")
        app.entry.clear()