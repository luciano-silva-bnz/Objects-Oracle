# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('pessoa_rj/assets/rodape.png', 'pessoa_rj/assets'), ('pessoa_rj/assets/logo.png', 'pessoa_rj/assets'), ('pessoa_rj/assets/financeiro.ico', 'pessoa_rj/assets'), ('pessoa_rj/queries/bnz.sql', 'pessoa_rj/queries'), ('pessoa_rj/queries/mlt.sql', 'pessoa_rj/queries'), ('pessoa_rj/queries/ali.sql', 'pessoa_rj/queries')]
binaries = []
hiddenimports = ['convert', 'comprov', 'cryptography.hazmat.primitives.kdf', 'cryptography.hazmat.bindings._rust']
tmp_ret = collect_all('cryptography')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('oracledb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


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
)
