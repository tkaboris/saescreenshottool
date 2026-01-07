# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('QATeamViewClipper.ico', '.'),
        ('QATeamViewClipper.png', '.'),
        ('credentials.json', '.'),
    ],
    hiddenimports=[
        'win32api',
        'win32con',
        'win32gui',
        'win32clipboard',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'PIL.ImageFont',
        'PIL.ImageFilter',
        'PIL.PngImagePlugin',
        'google.auth',
        'google.oauth2',
        'google.oauth2.credentials',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.http',
    ],
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
    name='ViewClipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='QATeamViewClipper.ico',
    version='version_info.txt',
)
