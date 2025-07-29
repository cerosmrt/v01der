import random
import os
from files import setup_file_handling, void_line
from tools import clean_text
from PyQt6.QtWidgets import QApplication

def setup_controls(app):
    pass  # Los eventos están en keyPressEvent y returnPressed

def show_random_line_from_current_file(app, event=None):
    """Muestra una línea aleatoria del archivo activo, evitando la línea actual."""
    try:
        current_file_path = app.current_file_path # Usa el archivo activo
        print(f"Intentando leer: {current_file_path}")
        if os.path.exists(current_file_path):
            with open(current_file_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f.readlines() if line.strip()]
            if lines:
                if len(lines) == 1:
                    selected_line = lines[0] # Solo hay una línea, no hay alternativa
                    selected_index = 0
                else:
                    # Hay múltiples líneas, excluir la actual
                    current_line = getattr(app, 'current_active_line', None)
                    available_lines = [line for line in lines if line != current_line]
                    
                    if not available_lines:
                        available_lines = lines # Fallback: usar todas las líneas
                    
                    selected_line = random.choice(available_lines)
                    selected_index = lines.index(selected_line) #
                
                app.current_active_line = selected_line
                app.current_active_line_index = selected_index
                app.entry.setText(selected_line)
                app.entry.setCursorPosition(0)
                print(f"Random line from active file: {selected_line}, Index: {selected_index}") #
            else:
                print(f"{os.path.basename(current_file_path)} está vacío.")
                app.entry.clear()
                app.current_active_line = None
                app.current_active_line_index = None 
        else:
            print(f"{os.path.basename(current_file_path)} no existe.")
            app.entry.clear()
            app.current_active_line = None
            app.current_active_line_index = None
    except Exception as e:
        print(f"Error en show_random_line_from_current_file: {e}")
        app.entry.clear()

def show_previous_current_file_line(app, event=None):
    """Muestra la línea previa en el archivo activo, con comportamiento circular y contextual."""
    try:
        current_file_path = app.current_file_path # Usa el archivo activo
        print(f"Navegando a línea previa en: {current_file_path}")
        if not os.path.exists(current_file_path):
            print(f"{os.path.basename(current_file_path)} no existe.")
            app.entry.clear()
            return

        with open(current_file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f.readlines() if line.strip()] 
        
        if not lines:
            print(f"{os.path.basename(current_file_path)} está vacío.")
            app.entry.clear()
            app.current_active_line_index = None
            app.current_active_line = None
            return

        if not app.entry.text().strip() and app.last_inserted_index is not None:
            app.current_active_line_index = app.last_inserted_index 
            print(f"Entry vacío, mostrando última línea enviada, Index: {app.current_active_line_index}")
        elif app.current_active_line_index is None:
            app.current_active_line_index = len(lines) - 1
            print(f"Sin índice actual, empezando desde la última línea, Index: {app.current_active_line_index}")
        else:
            app.current_active_line_index = (app.current_active_line_index - 1) % len(lines) 
            print(f"Navegando a línea previa, Index: {app.current_active_line_index}")

        app.current_active_line = lines[app.current_active_line_index]
        app.entry.setText(app.current_active_line)
        app.entry.setCursorPosition(0)
        print(f"Previous Line - {os.path.basename(current_file_path)}, Index: {app.current_active_line_index}, Line: {app.current_active_line}")
    except Exception as e:
        print(f"Error en show_previous_current_file_line: {e}") 
        app.entry.clear()

def show_next_current_file_line(app, event=None):
    """Muestra la línea siguiente en el archivo activo, con comportamiento circular."""
    try:
        current_file_path = app.current_file_path # Usa el archivo activo
        print(f"Navegando a línea siguiente en: {current_file_path}")
        if not os.path.exists(current_file_path):
            print(f"{os.path.basename(current_file_path)} no existe.")
            app.entry.clear()
            return

        with open(current_file_path, 'r', encoding='utf-8') as f: 
            lines = [line.rstrip('\n') for line in f.readlines() if line.strip()]
        
        if not lines:
            print(f"{os.path.basename(current_file_path)} está vacío.")
            app.entry.clear()
            app.current_active_line_index = None
            app.current_active_line = None
            return 

        if not app.entry.text().strip() and app.last_inserted_index is not None:
            app.current_active_line_index = (app.last_inserted_index + 1) % len(lines)
            print(f"Entry vacío, mostrando línea siguiente a la última enviada, Index: {app.current_active_line_index}")
        elif app.current_active_line_index is None:
            app.current_active_line_index = 0 
            print(f"Sin índice actual, empezando desde la primera línea, Index: {app.current_active_line_index}")
        else:
            app.current_active_line_index = (app.current_active_line_index + 1) % len(lines)
            print(f"Navegando a línea siguiente, Index: {app.current_active_line_index}")

        app.current_active_line = lines[app.current_active_line_index]
        app.entry.setText(app.current_active_line)
        app.entry.setCursorPosition(0)
        print(f"Next Line - {os.path.basename(current_file_path)}, Index: {app.current_active_line_index}, Line: {app.current_active_line}")
    except Exception as e: 
        print(f"Error en show_next_current_file_line: {e}")
        app.entry.clear()