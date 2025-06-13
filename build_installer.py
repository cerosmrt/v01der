import os
import datetime
import sys
import PyInstaller.__main__

timestamp = datetime.datetime.now().strftime('%y-%m-%d_%H-%M-%S')
exe_name = f'voider-{timestamp}'
build_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'builds')
icon_path = os.path.join(os.path.dirname(__file__), 'voider.ico')
qt_plugins_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'plugins')

args = [
    'new_interface.py',
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    f'--name={exe_name}',
    f'--add-data={icon_path};.',
    f'--add-binary={qt_plugins_path};PyQt6\\Qt6\\plugins',
    '--hidden-import=watchdog',
    '--hidden-import=pygame',
    f'--distpath={build_dir}\\dist',
    f'--workpath={build_dir}\\build',
    f'--specpath={build_dir}'
]

print(f"Generating {exe_name}.exe...")
PyInstaller.__main__.run(args)
print(f"Done, check {os.path.join(build_dir, 'dist', exe_name)}.exe")