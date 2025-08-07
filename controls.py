# --- controls.py ---
import random
import os

def setup_controls(app):
    """Configura los controles de la aplicación."""
    print("Configurando controles...")
    # Initialize navigation state
    app.first_up_after_submission = False  # Tracks if next Up press is first after submission

def show_random_line_from_current_file(app, event=None):
    """Muestra una línea aleatoria del archivo activo."""
    try:
        if os.path.exists(app.current_file_path):
            with open(app.current_file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if lines:
                random_line = random.choice(lines)
                app.current_active_line = random_line
                with open(app.current_file_path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    for i, line in enumerate(all_lines):
                        if line.strip() == random_line:
                            app.current_active_line_index = i
                            break
                app.entry.setText(random_line)
                app.first_up_after_submission = False  # Reset navigation state
                print(f"Línea aleatoria mostrada del archivo activo: {random_line}")
            else:
                print(f"El archivo {os.path.basename(app.current_file_path)} está vacío.")
                app.current_active_line = None
                app.current_active_line_index = None
                app.first_up_after_submission = False
                app.entry.clear()
        else:
            print(f"El archivo {os.path.basename(app.current_file_path)} no existe.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
    except Exception as e:
        print(f"Error al mostrar línea aleatoria del archivo activo: {e}")
        app.current_active_line = None
        app.current_active_line_index = None
        app.first_up_after_submission = False
        app.entry.clear()

def show_random_line_from_random_file(app, event=None):
    """Muestra una línea aleatoria de un archivo .txt aleatorio de txt_files."""
    try:
        if not app.txt_files:
            print("No hay archivos .txt disponibles para seleccionar.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
            return
        
        random_file = random.choice(app.txt_files)
        app.switch_to_file(random_file)
        
        with open(random_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if lines:
            random_line = random.choice(lines)
            app.current_active_line = random_line
            with open(random_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                for i, line in enumerate(all_lines):
                    if line.strip() == random_line:
                        app.current_active_line_index = i
                        break
            app.entry.setText(random_line)
            app.first_up_after_submission = False  # Reset navigation state
            print(f"Línea aleatoria mostrada del archivo {os.path.basename(random_file)}: {random_line}")
        else:
            print(f"El archivo {os.path.basename(random_file)} está vacío.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
    except Exception as e:
        print(f"Error al mostrar línea aleatoria de archivo aleatorio: {e}")
        app.current_active_line = None
        app.current_active_line_index = None
        app.first_up_after_submission = False
        app.entry.clear()

def show_previous_current_file_line(app, event=None):
    """Muestra la línea anterior en el archivo activo, con lógica especial para la primera pulsación."""
    try:
        if os.path.exists(app.current_file_path):
            with open(app.current_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                print(f"El archivo {os.path.basename(app.current_file_path)} está vacío.")
                app.current_active_line = None
                app.current_active_line_index = None
                app.first_up_after_submission = False
                app.entry.clear()
                return
            
            # If first Up press after submission, show last inserted line
            if app.first_up_after_submission and hasattr(app, 'last_inserted_index') and app.last_inserted_index is not None:
                if app.last_inserted_index < len(lines) and lines[app.last_inserted_index].strip():
                    app.current_active_line = lines[app.last_inserted_index].strip()
                    app.current_active_line_index = app.last_inserted_index  # Set index for next navigation
                    app.entry.setText(app.current_active_line)
                    app.first_up_after_submission = False  # Allow normal navigation next time
                    print(f"Primera flecha arriba: Mostrando última línea enviada: {app.current_active_line}")
                    return
            
            # Normal navigation: Find previous non-empty line
            current_index = app.current_active_line_index if app.current_active_line_index is not None else len(lines)
            new_index = current_index - 1
            
            while new_index >= 0:
                if lines[new_index].strip():
                    app.current_active_line_index = new_index
                    app.current_active_line = lines[new_index].strip()
                    app.entry.setText(app.current_active_line)
                    app.first_up_after_submission = False  # Ensure normal navigation continues
                    print(f"Línea anterior mostrada: {app.current_active_line}")
                    return
                new_index -= 1
            
            print("No hay líneas anteriores no vacías.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
        else:
            print(f"El archivo {os.path.basename(app.current_file_path)} no existe.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
    except Exception as e:
        print(f"Error al mostrar línea anterior: {e}")
        app.current_active_line = None
        app.current_active_line_index = None
        app.first_up_after_submission = False
        app.entry.clear()

def show_next_current_file_line(app, event=None):
    """Muestra la línea siguiente en el archivo activo."""
    try:
        if os.path.exists(app.current_file_path):
            with open(app.current_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                print(f"El archivo {os.path.basename(app.current_file_path)} está vacío.")
                app.current_active_line = None
                app.current_active_line_index = None
                app.first_up_after_submission = False
                app.entry.clear()
                return
            
            # If index is None (e.g., empty input), start from last_inserted_index
            current_index = (app.last_inserted_index if hasattr(app, 'last_inserted_index') and app.last_inserted_index is not None else -1) if app.current_active_line_index is None else app.current_active_line_index
            new_index = current_index + 1
            
            while new_index < len(lines):
                if lines[new_index].strip():
                    app.current_active_line_index = new_index
                    app.current_active_line = lines[new_index].strip()
                    app.entry.setText(app.current_active_line)
                    app.first_up_after_submission = False  # Ensure normal navigation
                    print(f"Línea siguiente mostrada: {app.current_active_line}")
                    return
                new_index += 1
            
            print("No hay líneas siguientes no vacías.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
        else:
            print(f"El archivo {os.path.basename(app.current_file_path)} no existe.")
            app.current_active_line = None
            app.current_active_line_index = None
            app.first_up_after_submission = False
            app.entry.clear()
    except Exception as e:
        print(f"Error al mostrar línea siguiente: {e}")
        app.current_active_line = None
        app.current_active_line_index = None
        app.first_up_after_submission = False
        app.entry.clear()