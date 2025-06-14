# --- files.py ---
import os
import random
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def setup_file_handling(app):
    app.txt_files = []
    update_txt_files(app)
    index_all_lines(app)
    if app.txt_files:
        app.current_file = app.txt_files[0]
        app.current_line_index = 0
        app.current_line = ""
        app.entry.clear()
    
    app.event_handler = FileSystemEventHandler()
    app.event_handler.on_created = lambda event: on_directory_change(app, event)
    app.event_handler.on_deleted = lambda event: on_directory_change(app, event)
    app.observer = Observer()
    app.observer.schedule(app.event_handler, app.void_dir, recursive=False)
    app.observer.start()

def update_txt_files(app):
    if not os.path.exists(app.void_dir):
        os.makedirs(app.void_dir)
    if not os.path.exists(app.void_file_path):
        with open(app.void_file_path, 'w', encoding='utf-8') as void_file:
            void_file.write('')
    new_txt_files = [f for f in os.listdir(app.read_dir) if f.endswith('.txt') and f != '0.txt']
    if not hasattr(app, 'txt_files') or not app.txt_files:
        app.txt_files = new_txt_files
        app.file_positions = {file: 0 for file in app.txt_files}
    else:
        app.txt_files = new_txt_files
        for file in new_txt_files:
            if file not in app.file_positions:
                app.file_positions[file] = 0

def index_all_files(app):
    all_files = os.listdir(app.read_dir)
    app.txt_files = [
        f for f in all_files
        if f.endswith('.txt') and f != '0.txt' and os.path.getsize(os.path.join(app.read_dir, f)) > 0
    ]
    if app.txt_files and not hasattr(app, 'current_file'):
        app.current_file = app.txt_files[0]

def index_all_lines(app):
    app.all_lines = []
    app.file_line_map = {}

    for txt_file in app.txt_files:
        file_path = os.path.join(app.read_dir, txt_file)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]
                app.file_line_map[txt_file] = lines
                app.all_lines.extend(lines)

    print("Líneas indexadas (total):", len(app.all_lines))
    print("Primeras 5 líneas:", app.all_lines[:5])
    print("Líneas por archivo:", {k: len(v) for k, v in app.file_line_map.items()})

def refresh_files(app, event=None):
    print("Refrescando archivos y líneas...")
    update_txt_files(app)
    index_all_lines(app)
    app.current_file = app.txt_files[0] if app.txt_files else None
    app.current_line_index = 0
    app.current_line = ""
    app.entry.clear()
    print("Refresh completo. Entry vacío, listo para navegar.")

def on_directory_change(app, event):
    if event.event_type in ('created', 'deleted'):
        old_files = set(app.txt_files)
        update_txt_files(app)
        new_files = set(app.txt_files)
        if old_files != new_files:
            index_all_lines(app)
            print("Reindexado por cambio en archivos")

def void_line(app, event=None):
    import re
    try:
        line = app.entry.text().strip()
        app.entry.clear()
        app.entry.setFocus()

        if line:
            # --- FORMATO ---
            # Proteger los puntos suspensivos
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
                    lines.insert(insert_index, formatted_text + '\n')
                    app.last_inserted_index = insert_index

                with open(app.void_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    f.flush()
                    os.fsync(f.fileno())
        else:
            app.current_zero_line_index = None
            app.current_zero_line = None

        return 'break'

    except Exception as e:
        print(f"Error en void_line: {e}")
        app.entry.clear()
        app.entry.setFocus()
        return 'break'