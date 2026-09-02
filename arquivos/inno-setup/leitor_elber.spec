# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

source_dir = r"E:\labserver\leitor-temperatura-elber\leitor_elber_ibr"

datas = [
    (os.path.join(source_dir, "app.py"), "."),
    (os.path.join(source_dir, "parser_ibr.py"), "."),
    (os.path.join(source_dir, "report.py"), "."),
]

# Coletar metadados das bibliotecas principais
for pkg in ["streamlit", "pandas", "matplotlib", "reportlab"]:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

# Coletar arquivos de dados estáticos
datas += collect_data_files("streamlit")
datas += collect_data_files("matplotlib")
datas += collect_data_files("reportlab")

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pandas",
    "matplotlib",
    "reportlab",
]
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("reportlab")

excludes = [
    "pandas.tests",
    "matplotlib.tests",
    "tkinter.test",
]

a = Analysis(
    [os.path.join(source_dir, "launcher.py")],
    pathex=[source_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LeitorElberIBR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LeitorElberIBR",
)
