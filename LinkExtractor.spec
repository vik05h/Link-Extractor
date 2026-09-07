# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

wv_datas, wv_binaries, wv_hiddenimports = collect_all('webview')
pn_datas, pn_binaries, pn_hiddenimports = collect_all('pythonnet')
clr_datas, clr_binaries, clr_hiddenimports = collect_all('clr_loader')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=wv_binaries + pn_binaries + clr_binaries,
    datas=[
        ('dist_web', 'dist_web'),
        ('assets', 'assets'),
        ('app_icon.png', '.'),
        ('app_icon.ico', '.')
    ] + wv_datas + pn_datas + clr_datas,
    hiddenimports=[
        'bridge',
        'scraper',
        'engine',
        'validator',
        'history',
        'integrations',
        'updater',
        'utils',
        'community',
        'pyperclip',
        'sqlite3',
        'playwright'
    ] + wv_hiddenimports + pn_hiddenimports + clr_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['flet', 'flet_desktop'],
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
