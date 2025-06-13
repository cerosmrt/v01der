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

def handle_key_press(app, event=None):
    """Función original para mezclar archivos (guardada para uso futuro)."""
    random.shuffle(app.txt_files)
    if app.txt_files:
        app.current_file = app.txt_files[0]
        file_lines = app.file_line_map.get(app.current_file, [])
        if file_lines:
            app.current_line_index = random.randint(0, len(file_lines) - 1)
            app.current_line = file_lines[app.current_line_index]
            app.entry.setText(app.current_line)
            for file in app.txt_files:
                app.file_positions[file] = random.randint(0, len(app.file_line_map.get(file, [])) - 1) if app.file_line_map.get(file) else 0
            app.navigation_direction = random.choice([1, -1])
            print("\nShuffled files:", app.txt_files)
            print("File positions:", app.file_positions)
            print(f"Showing random line: {app.current_line}, Index: {app.current_line_index}")
            print(f"Navigation direction: {'normal' if app.navigation_direction == 1 else 'inverted'}")

def show_previous_file(app, event=None):
    if not app.txt_files:
        return
    if app.current_file:
        app.file_positions[app.current_file] = app.current_line_index
    current_file_index = app.txt_files.index(app.current_file) if app.current_file else 0
    previous_file_index = (current_file_index - 1) % len(app.txt_files)
    app.current_file = app.txt_files[previous_file_index]
    file_lines = app.file_line_map.get(app.current_file, [])
    if file_lines:
        app.current_line_index = app.file_positions.get(app.current_file, 0) % len(file_lines)
        app.current_line = file_lines[app.current_line_index]
        app.entry.setText(app.current_line)
        print(f"Previous File - Now at: {app.current_file}, Index: {app.current_line_index}, Line: {app.current_line}")

def show_next_file(app, event=None):
    if not app.txt_files:
        return
    if not app.entry.text().strip() and app.current_line == "":
        file_lines = app.file_line_map.get(app.current_file, [])
        if file_lines:
            app.current_line_index = app.file_positions.get(app.current_file, 0) % len(file_lines)
            app.current_line = file_lines[app.current_line_index]
            app.entry.setText(app.current_line)
            print(f"Next File - First show: {app.current_file}, Index: {app.current_line_index}, Line: {app.current_line}")
    else:
        if app.current_file:
            app.file_positions[app.current_file] = app.current_line_index
        current_file_index = app.txt_files.index(app.current_file) if app.current_file else -1
        next_file_index = (current_file_index + 1) % len(app.txt_files)
        app.current_file = app.txt_files[next_file_index]
        file_lines = app.file_line_map.get(app.current_file, [])
        if file_lines:
            app.current_line_index = app.file_positions.get(app.current_file, 0) % len(file_lines)
            app.current_line = file_lines[app.current_line_index]
            app.entry.setText(app.current_line)
            print(f"Next File - Now at: {app.current_file}, Index: {app.current_line_index}, Line: {app.current_line}")

def show_previous_line(app, event=None):
    if not app.current_file or not app.file_line_map.get(app.current_file, []):
        return
    file_lines = app.file_line_map[app.current_file]
    app.current_line_index = (app.current_line_index - 1) % len(file_lines)
    app.current_line = file_lines[app.current_line_index]
    app.entry.setText(app.current_line)
    app.file_positions[app.current_file] = app.current_line_index
    print(f"Previous Line - File: {app.current_file}, Index: {app.current_line_index}, Line: {app.current_line}")

def show_next_line(app, event=None):
    if not app.current_file or not app.file_line_map.get(app.current_file, []):
        return
    file_lines = app.file_line_map[app.current_file]
    app.current_line_index = (app.current_line_index + 1) % len(file_lines)
    app.current_line = file_lines[app.current_line_index]
    app.entry.setText(app.current_line)
    app.file_positions[app.current_file] = app.current_line_index
    print(f"Next Line - File: {app.current_file}, Index: {app.current_line_index}, Line: {app.current_line}")