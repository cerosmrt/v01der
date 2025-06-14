import os
import datetime
import sys
import PyInstaller.__main__

timestamp = datetime.datetime.now().strftime('%y-%m-%d_%H-%M-%S')
exe_name = f'voider-{timestamp}'

# Ruta base del proyecto
base_dir = os.path.dirname(os.path.abspath(__file__))
build_root = os.path.join(base_dir, 'builds')
dist_dir = os.path.join(build_root, 'dist')
work_dir = os.path.join(build_root, 'build')
spec_dir = build_root
icon_path = os.path.join(base_dir, 'voider.ico')

# Ruta a plugins de Qt
qt_plugins_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'plugins')

# Crear carpetas si no existen
os.makedirs(dist_dir, exist_ok=True)
os.makedirs(work_dir, exist_ok=True)

args = [
    '--clean',
    '--log-level=DEBUG',
    'new_interface.py',
    '--onefile',
    '--windowed',
    f'--icon={icon_path}',
    f'--name={exe_name}',
    f'--add-data={icon_path}{os.pathsep}.',
    f'--add-binary={qt_plugins_path}{os.pathsep}PyQt6/Qt6/plugins',

    # Hidden imports para numpy y otros módulos comunes que fallan
    '--hidden-import=watchdog',
    '--hidden-import=pygame',
    '--hidden-import=numpy',
    '--hidden-import=numpy.core._methods',
    '--hidden-import=numpy.lib.format',

    # Fuerza a incluir todo lo necesario de numpy
    '--collect-all=numpy',

    f'--distpath={dist_dir}',
    f'--workpath={work_dir}',
    f'--specpath={spec_dir}'
]

print(f"\n🔧 Generando {exe_name}.exe...\n")
PyInstaller.__main__.run(args)
print(f"\n✅ ¡Listo! El ejecutable está en: {os.path.join(dist_dir, exe_name)}.exe\n")
