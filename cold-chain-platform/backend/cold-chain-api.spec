# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['local_server.py'],
    pathex=['.'],
    binaries=[('C:/Users/zuoyiqing/AppData/Local/Programs/Python/Python313/Lib/site-packages/ortools/.libs/*.dll', '.')],
    datas=[],
    hiddenimports=['passlib.handlers.pbkdf2', 'jose.backends.cryptography_backend'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='cold-chain-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
