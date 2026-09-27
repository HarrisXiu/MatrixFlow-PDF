# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=collect_dynamic_libs('pypdfium2_raw'),
    datas=[('frontend/build', 'frontend/build'), ('assets/matrixflow-pdf.ico', 'assets')]
          + collect_data_files('webview') + collect_data_files('pypdfium2')
          + collect_data_files('pypdfium2_raw') + copy_metadata('pypdfium2'),
    hiddenimports=['webview.platforms.edgechromium', 'webview.platforms.winforms'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'tkinterdnd2', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'cefpython3', 'IPython', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='MatrixFlowPDF', version='assets/windows-version.txt', icon='assets/matrixflow-pdf.ico', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
