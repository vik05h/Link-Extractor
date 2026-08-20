# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

flet_datas, flet_binaries, flet_hiddenimports = collect_all('flet')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=flet_binaries,
    datas=[
        ('assets', 'assets'),
        ('app_icon.png', '.'),
        ('app_icon.ico', '.')
    ] + flet_datas,
    hiddenimports=[
        'scraper',
        'engine',
        'validator',
        'history',
        'integrations',
        'updater',
        'utils',
        'ui',
        'ui.constants',
        'ui.state',
        'ui.screens',
        'ui.screens.extractor',
        'ui.screens.pipeline',
        'ui.screens.history',
        'ui.screens.settings',
        'pyperclip',
        'sqlite3',
        'playwright'
    ] + flet_hiddenimports,
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
    [],
    exclude_binaries=True,
    name='LinkExtractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
    version='file_version_info.txt'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LinkExtractor',
)
