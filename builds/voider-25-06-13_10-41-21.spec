# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['..\\new_interface.py'],
    pathex=[],
    binaries=[('C:\\Users\\feder\\Documents\\Python310\\Lib\\site-packages\\PyQt6\\Qt6\\plugins', 'PyQt6\\Qt6\\plugins')],
    datas=[('z:\\programming\\Voider\\V2\\V01DER\\voider.ico', '.')],
    hiddenimports=['watchdog', 'pygame', 'numpy', 'scipy', 'scipy.signal'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='voider-25-06-13_10-41-21',
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
