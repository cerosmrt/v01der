import os
import datetime
import PyInstaller.__main__

# Obtener fecha y hora actual con precisión
timestamp = datetime.datetime.now().strftime('%y-%m-%d_%H-%M-%S')
exe_name = f'voider-{timestamp}'
build_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'builds')
icon_path = os.path.join(os.path.dirname(__file__), 'voider.ico')

args = [
    'new_interface.py',  # Changed to target new_interface.py
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    f'--name={exe_name}',
    f'--add-data={icon_path};.',
    '--hidden-import=watchdog',
    '--hidden-import=PyQt6.QtMultimedia',  # Added for white noise audio
    f'--distpath={build_dir}\\dist',
    f'--workpath={build_dir}\\build',
    f'--specpath={build_dir}'
]

print(f"Generating {exe_name}.exe...")
PyInstaller.__main__.run(args)
print(f"Done, check {os.path.join(build_dir, 'dist', exe_name)}.exe")