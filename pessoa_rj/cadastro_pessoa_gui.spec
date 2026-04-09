# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

PROJECT_DIR = Path.cwd()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from pessoa_rj.version import APP_NAME, APP_VERSION, APP_VERSION_TUPLE, COMPANY_NAME, COPYRIGHT, EXECUTABLE_NAME

datas = [
    ('pessoa_rj/assets/rodape.png', 'pessoa_rj/assets'),
    ('pessoa_rj/assets/logo.png', 'pessoa_rj/assets'),
    ('pessoa_rj/assets/financeiro.ico', 'pessoa_rj/assets'),
    ('pessoa_rj/queries/bnz.sql', 'pessoa_rj/queries'),
    ('pessoa_rj/queries/mlt.sql', 'pessoa_rj/queries'),
    ('pessoa_rj/queries/ali.sql', 'pessoa_rj/queries'),
]
binaries = []
hiddenimports = [
    'pessoa_rj.tools.convert',
    'pessoa_rj.tools.comprov',
    'pessoa_rj.tools.gerar_planilha_fgts',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.bindings._rust',
]
tmp_ret = collect_all('cryptography')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('oracledb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

version_file = PROJECT_DIR / "_build_version_info.txt"
version_file.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={APP_VERSION_TUPLE},
    prodvers={APP_VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{COMPANY_NAME}'),
          StringStruct('FileDescription', '{APP_NAME}'),
          StringStruct('FileVersion', '{APP_VERSION}'),
          StringStruct('InternalName', 'cadastro_pessoa_gui'),
          StringStruct('OriginalFilename', '{EXECUTABLE_NAME}'),
          StringStruct('ProductName', '{APP_NAME}'),
          StringStruct('ProductVersion', '{APP_VERSION}'),
          StringStruct('LegalCopyright', '{COPYRIGHT}')
        ])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)""",
    encoding="utf-8",
)

a = Analysis(
    ['cadastro_pessoa_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='cadastro_pessoa_gui',
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
    icon=['pessoa_rj\\assets\\financeiro.ico'],
    version=str(version_file),
)
