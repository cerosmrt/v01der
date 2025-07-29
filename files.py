import os
import random
import re

def setup_file_handling(app):
    """Inicializa el manejo de 0.txt en el directorio void y el archivo activo."""
    if not os.path.exists(app.void_dir):
        os.makedirs(app.void_dir)
    # Asegura que 0.txt exista al inicio
    if not os.path.exists(app.void_file_path):
        with open(app.void_file_path, 'w', encoding='utf-8') as void_file:
            void_file.write('')
    
    # Inicializa el archivo activo al 0.txt
    app.current_file_path = app.void_file_path 
    app.current_active_line = None
    app.current_active_line_index = None
    app.last_inserted_index = None 

def void_line(app, event=None):
    """Procesa la línea ingresada, formateándola y guardándola en el archivo activo."""
    try:
        line = app.entry.text().strip()
        app.entry.clear()
        app.entry.setFocus()

        if line:
            # --- Manejo de comandos de cambio de archivo ---
            if line.startswith("//"):
                target_filename = line[2:].strip()
                if not target_filename: # Si solo se escribe "//", quizás no hacer nada o ir a 0.txt
                    target_filename = "0" # Por ejemplo, "//" va a 0.txt
                
                # Normalizar el nombre del archivo
                if not target_filename.endswith(".txt"):
                    target_filename += ".txt"
                
                new_file_full_path = os.path.join(app.void_dir, target_filename)

                if new_file_full_path != app.current_file_path:
                    # Cambiar el archivo activo
                    app.current_file_path = new_file_full_path
                    # Crear el archivo si no existe
                    if not os.path.exists(app.current_file_path):
                        with open(app.current_file_path, 'w', encoding='utf-8') as f:
                            f.write('')
                        print(f"Archivo creado: {os.path.basename(app.current_file_path)}")
                    
                    print(f"Cambiado al archivo: {os.path.basename(app.current_file_path)}")
                    # Resetear el estado de navegación para el nuevo archivo
                    app.current_active_line = None
                    app.current_active_line_index = None
                    app.last_inserted_index = None
                else:
                    print(f"Ya estás en el archivo: {os.path.basename(app.current_file_path)}")
                return 'break' # Finalizar procesamiento de esta línea

            # --- FORMATO NORMAL DE TEXTO (si no es un comando de archivo) ---
            protected = line.replace("...", "<ELLIPSIS>")
            raw_sentences = re.split(r'\.(?=\s|$)', protected) 
            formatted_lines = []
            for raw in raw_sentences:
                s = raw.strip()
                if not s:
                    continue
                s = s.replace("<ELLIPSIS>", "...") 
                s = s[0].upper() + s[1:] if s else s
                if not s.endswith('.') and not s.endswith('...'):
                    s += '.'
                formatted_lines.append(s) 
            formatted_text = '\n'.join(formatted_lines)
            # --- FIN FORMATO ---

            # Escribir en el archivo activo
            with open(app.current_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines() 

            if hasattr(app, 'current_active_line_index') and app.current_active_line_index is not None:
                if app.current_active_line_index < len(lines): 
                    lines[app.current_active_line_index] = formatted_text + '\n'
                    app.last_inserted_index = app.current_active_line_index
                app.current_active_line_index = None 
                app.current_active_line = None
            else:
                insert_index = (app.last_inserted_index + 1) if hasattr(app, 'last_inserted_index') and app.last_inserted_index is not None else len(lines)
                lines[insert_index:insert_index] = [line + '\n' for line in formatted_lines]
                app.last_inserted_index = insert_index + len(formatted_lines) - 1 
                app.current_active_line_index = None
                app.current_active_line = None

            with open(app.current_file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines) 
                f.flush()
                os.fsync(f.fileno())
            
            print(f"Líneas insertadas en {os.path.basename(app.current_file_path)}: {len(formatted_lines)}, nuevo índice: {app.last_inserted_index}") 

        else:
            app.current_active_line_index = None 
            app.current_active_line = None

        return 'break'

    except Exception as e:
        print(f"Error en void_line: {e}") 
        app.entry.clear()
        app.entry.setFocus()
        return 'break'