import os
import datetime
import subprocess
import sys

# Generar nombre con timestamp
timestamp = datetime.datetime.now().strftime('%y-%m-%d_%H-%M-%S')
exe_name = f'voider-{timestamp}'

# Rutas
base_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(os.path.dirname(base_dir), 'builds')
icon_path = os.path.join(base_dir, 'voider.ico')
script_path = os.path.join(base_dir, 'new_interface.py')

# Comando de compilación con Nuitka
cmd = [
    sys.executable,  # Usa el mismo Python con el que ejecutás esto
    "-m", "nuitka",
    "--standalone",
    "--onefile",
    "--windows-disable-console",
    "--enable-plugin=pyqt6",
    "--enable-plugin=numpy",
    f"--include-data-file={icon_path}=voider.ico",
    f"--windows-icon-from-ico={icon_path}",
    f"--output-dir={build_dir}",
    "--nofollow-import-to=tkinter",
    f"--output-filename={exe_name}.exe",
    script_path
]

print(f"Compiling {exe_name}.exe with Nuitka...\n")
subprocess.run(cmd, shell=True)
print(f"\n✅ Done. Check the build folder: {os.path.join(build_dir, f'{exe_name}.exe')}")
