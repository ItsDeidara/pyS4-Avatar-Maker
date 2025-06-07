# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['G:\\PS4_Archive\\Tools\\PS4 Avatar Maker - Lapy\\pyS4 Avatar Maker\\run.py'],
    pathex=[],
    binaries=[],
    datas=[('G:\\PS4_Archive\\Tools\\PS4 Avatar Maker - Lapy\\pyS4 Avatar Maker\\src\\pys4_avatar_maker\\default_avatar.png', 'src/pys4_avatar_maker')],
    hiddenimports=['imageio.plugins'],
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
    name='pyS4_Avatar_Maker',
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
)
