# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['z:\\programming\\Voider\\V2\\V01DER\\voider.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'sounddevice'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'numpy.distutils'],
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
    name='voider-25-09-22_08-57-56',
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
