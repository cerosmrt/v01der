# --- files.py ---
import os
import random
import re

def setup_file_handling(app):
    """Inicializa el manejo de 0.txt en el directorio void."""
    if not os.path.exists(app.void_dir):
        os.makedirs(app.void_dir)
    if not os.path.exists(app.void_file_path):
        with open(app.void_file_path, 'w', encoding='utf-8') as void_file:
            void_file.write('')
    app.current_zero_line = None
    app.current_zero_line_index = None
    app.last_inserted_index = None

def void_line(app, event=None):
    """Procesa la línea ingresada, formateándola y guardándola en 0.txt."""
    try:
        line = app.entry.text().strip()
        app.entry.clear()
        app.entry.setFocus()

        if line:
            # --- FORMATO ---
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

            if line.startswith("/"):
                base, ext = os.path.splitext(app.void_file_path)
                if line == "/":
                    num_digits = random.randint(1, 10)
                    random_number = ''.join([str(random.randint(0, 9)) for _ in range(num_digits)])
                    new_file_path = f"{base}_{random_number}{ext}"
                else:
                    new_name = line[1:]
                    new_file_path = os.path.join(app.void_dir, f"{new_name}{ext}")
                if os.path.exists(new_file_path):
                    with open(app.void_file_path, 'r', encoding='utf-8') as void_file:
                        content_to_append = void_file.read()
                    with open(new_file_path, 'a', encoding='utf-8') as target_file:
                        target_file.write(content_to_append)
                    with open(app.void_file_path, 'w', encoding='utf-8') as void_file:
                        void_file.write('')
                else:
                    os.rename(app.void_file_path, new_file_path)
                    with open(app.void_file_path, 'w', encoding='utf-8') as void_file:
                        void_file.write('')
                app.last_inserted_index = None
                app.current_zero_line_index = None
            else:
                with open(app.void_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if hasattr(app, 'current_zero_line_index') and app.current_zero_line_index is not None:
                    if app.current_zero_line_index < len(lines):
                        lines[app.current_zero_line_index] = formatted_text + '\n'
                        app.last_inserted_index = app.current_zero_line_index
                    app.current_zero_line_index = None
                    app.current_zero_line = None
                else:
                    insert_index = (app.last_inserted_index + 1) if hasattr(app, 'last_inserted_index') and app.last_inserted_index is not None else len(lines)
                    lines[insert_index:insert_index] = [line + '\n' for line in formatted_lines]
                    app.last_inserted_index = insert_index + len(formatted_lines) - 1  # Actualización clave
                    app.current_zero_line_index = None
                    app.current_zero_line = None

                with open(app.void_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    f.flush()
                    os.fsync(f.fileno())
                
                print(f"Líneas insertadas: {len(formatted_lines)}, nuevo índice: {app.last_inserted_index}")  # Depuración

        else:
            app.current_zero_line_index = None
            app.current_zero_line = None

        return 'break'

    except Exception as e:
        print(f"Error en void_line: {e}")
        app.entry.clear()
        app.entry.setFocus()
        return 'break'