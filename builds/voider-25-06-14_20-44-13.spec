# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['z:\\programming\\Voider\\V2\\V01DER\\voider.py'],
    pathex=[],
    binaries=[('C:\\Users\\feder\\Documents\\Python310\\lib\\site-packages\\PyQt6\\Qt6\\plugins', 'PyQt6/Qt6/plugins')],
    datas=[('z:\\programming\\Voider\\V2\\V01DER\\voider.ico', '.')],
    hiddenimports=['numpy', 'sounddevice', 'scipy', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'pygame', 'torch', 'tensorflow'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='voider-25-06-14_20-44-13',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['z:\\programming\\Voider\\V2\\V01DER\\voider.ico'],
)
